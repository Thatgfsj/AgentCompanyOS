//! Claude Code CLI adapter.
//!
//! Spawns the `claude` binary in a portable-pty, captures its
//! stdout/stderr, and parses the resulting `TASK_RESULT` JSON.
//!
//! See `docs/AGENT_PROTOCOL.md` §5.3 and `docs/ARCHITECTURE.md` §9.

#![forbid(unsafe_code)]
#![warn(missing_docs)]

use std::path::PathBuf;
use std::time::Duration;

use async_trait::async_trait;
use portable_pty::{native_pty_system, CommandBuilder, PtySize};
use thiserror::Error;
use tokio::sync::mpsc;
use tracing::{debug, warn};

/// Errors from the adapter.
#[derive(Debug, Error)]
pub enum AdapterError {
    /// Failed to spawn the CLI.
    #[error("failed to spawn claude: {0}")]
    Spawn(String),
    /// I/O error.
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
    /// The CLI timed out.
    #[error("claude timed out after {0:?}")]
    Timeout(Duration),
}

/// A parsed task result from the Claude Code CLI.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, PartialEq, Eq)]
pub struct TaskResult {
    /// Task id from the input.
    pub task_id: String,
    /// Outcome.
    pub status: TaskStatus,
    /// Human-readable summary.
    pub summary: String,
    /// Files the worker modified.
    pub files_modified: Vec<ModifiedFile>,
    /// Test result counts.
    pub tests_run: Option<TestCounts>,
}

impl TaskResult {
    /// Try to parse a `TASK_RESULT` JSON object out of free-form CLI output.
    /// Returns `None` if no valid JSON is found.
    #[must_use]
    pub fn extract_from_output(output: &str) -> Option<Self> {
        // The CLI streams both the worker's prose and the final JSON.
        // We scan for the LAST top-level JSON object in the output.
        let mut depth: i32 = 0;
        let mut start: Option<usize> = None;
        let mut end: usize = 0;
        for (i, ch) in output.char_indices() {
            if ch == '{' {
                if depth == 0 {
                    start = Some(i);
                }
                depth += 1;
            } else if ch == '}' {
                depth -= 1;
                if depth == 0 {
                    end = i + 1;
                    if let Some(s) = start {
                        let candidate = &output[s..end];
                        if let Ok(parsed) = serde_json::from_str::<Self>(candidate) {
                            return Some(parsed);
                        }
                    }
                }
            }
        }
        None
    }
}

/// Status of a task.
#[derive(Debug, Clone, Copy, serde::Serialize, serde::Deserialize, PartialEq, Eq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum TaskStatus {
    /// Task completed.
    Done,
    /// Task failed.
    Failed,
    /// Task partially completed.
    Partial,
}

/// A modified file.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, PartialEq, Eq)]
pub struct ModifiedFile {
    /// Path (relative to workspace).
    pub path: String,
    /// Lines added.
    pub lines_added: u32,
    /// Lines removed.
    pub lines_removed: u32,
}

/// Test result counts.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, PartialEq, Eq)]
pub struct TestCounts {
    /// Tests that passed.
    pub passed: u32,
    /// Tests that failed.
    pub failed: u32,
    /// Tests that were skipped.
    pub skipped: u32,
}

/// A trait for spawning the Claude Code CLI.
#[async_trait]
pub trait ClaudeRunner: Send + Sync {
    /// Run the CLI with the given task JSON and return the parsed
    /// result plus raw output.
    async fn run(
        &self,
        task_json: &str,
        workspace: &std::path::Path,
        timeout: Duration,
    ) -> Result<(TaskResult, String), AdapterError>;
}

/// Default implementation that uses `portable-pty` to spawn the
/// `claude` CLI.
pub struct PtyClaudeRunner {
    /// Path to the `claude` binary. Defaults to `claude` on `$PATH`.
    pub binary: PathBuf,
}

impl Default for PtyClaudeRunner {
    fn default() -> Self {
        Self {
            binary: PathBuf::from("claude"),
        }
    }
}

#[async_trait]
impl ClaudeRunner for PtyClaudeRunner {
    async fn run(
        &self,
        task_json: &str,
        workspace: &std::path::Path,
        timeout: Duration,
    ) -> Result<(TaskResult, String), AdapterError> {
        let pty_system = native_pty_system();
        let pair = pty_system
            .openpty(PtySize {
                rows: 30,
                cols: 120,
                pixel_width: 0,
                pixel_height: 0,
            })
            .map_err(|e| AdapterError::Spawn(e.to_string()))?;

        let mut cmd = CommandBuilder::new(&self.binary);
        cmd.arg("--non-interactive");
        cmd.arg("--input-format");
        cmd.arg("json");
        cmd.cwd(workspace);

        // The CLI reads the task on stdin.
        let mut writer = pair
            .master
            .take_writer()
            .map_err(|e| AdapterError::Spawn(e.to_string()))?;
        let task_json = task_json.to_string();
        let _ = std::thread::spawn(move || {
            use std::io::Write;
            if let Err(e) = writer.write_all(task_json.as_bytes()) {
                warn!(error = %e, "failed to write task JSON to claude stdin");
            }
            if let Err(e) = writer.flush() {
                warn!(error = %e, "failed to flush claude stdin");
            }
            // Drop closes stdin, signalling EOF to the child.
        });

        let mut reader = pair
            .master
            .try_clone_reader()
            .map_err(|e| AdapterError::Spawn(e.to_string()))?;

        let mut child = pair
            .slave
            .spawn_command(cmd)
            .map_err(|e| AdapterError::Spawn(e.to_string()))?;
        drop(pair.slave);

        // Drain stdout in a background thread and ship lines over
        // an mpsc channel.
        let (tx, mut rx) = mpsc::channel::<String>(256);
        let reader_handle = std::thread::spawn(move || {
            use std::io::{BufRead, BufReader};
            let buf = BufReader::new(&mut reader);
            for line in buf.lines().map_while(Result::ok) {
                if tx.blocking_send(line).is_err() {
                    break;
                }
            }
        });

        let mut collected = String::new();
        let outcome = tokio::time::timeout(timeout, async {
            while let Some(line) = rx.recv().await {
                debug!(target: "claude", "{}", line);
                collected.push_str(&line);
                collected.push('\n');
            }
        })
        .await;

        if outcome.is_err() {
            let _ = child.kill();
            return Err(AdapterError::Timeout(timeout));
        }

        let _ = reader_handle.join();
        let status = child.wait().map_err(AdapterError::Io)?;
        debug!(?status, "claude finished");

        let result = TaskResult::extract_from_output(&collected).ok_or_else(|| {
            AdapterError::Spawn(format!(
                "no TASK_RESULT JSON found in {} bytes of output",
                collected.len()
            ))
        })?;
        Ok((result, collected))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extract_result_from_noisy_output() {
        let output = r#"
Thinking about the task...
```rust
fn add(a: i32, b: i32) -> i32 { a + b }
```
{"task_id":"t1","status":"DONE","summary":"added add()","files_modified":[{"path":"src/math.py","lines_added":1,"lines_removed":0}],"tests_run":{"passed":1,"failed":0,"skipped":0}}
Goodbye.
"#;
        let result = TaskResult::extract_from_output(output).expect("parse");
        assert_eq!(result.task_id, "t1");
        assert_eq!(result.status, TaskStatus::Done);
        assert_eq!(result.files_modified.len(), 1);
    }

    #[test]
    fn extract_returns_none_when_no_json() {
        let output = "no json here, just prose";
        assert!(TaskResult::extract_from_output(output).is_none());
    }
}
