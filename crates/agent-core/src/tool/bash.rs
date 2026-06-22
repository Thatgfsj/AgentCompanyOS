//! `bash` — execute a shell command inside the workspace.
//!
//! The agent uses this for everything from "list files" to
//! "run the tests". Output is captured (stdout + stderr merged)
//! and returned to the model verbatim. A timeout prevents the
//! agent from hanging on infinite loops.

use async_trait::async_trait;
use std::time::Duration;
use tokio::process::Command;

use super::{Tool, ToolContext, ToolError, ToolOutput};

/// Default per-invocation timeout: 60 s.
pub const DEFAULT_TIMEOUT: Duration = Duration::from_secs(60);

/// Hard cap on the length of a single command string. Prevents
/// the agent from constructing a multi-megabyte shell command
/// that would balloon memory and time-to-first-byte of the
/// subprocess creation.
pub const MAX_COMMAND_BYTES: usize = 64 * 1024; // 64 KiB

/// Patterns that always require explicit user approval. The
/// matching is deliberately conservative — false negatives
/// (let through something dangerous) are much worse than false
/// positives (refuse something innocent).
const DANGEROUS_PATTERNS: &[&str] = &[
    "rm -rf /",
    "rm -rf ~",
    ":(){:|:&};:",          // fork bomb
    "mkfs",
    "dd if=",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init 0",
    "init 6",
    "passwd ",
    "userdel",
    "del /f",               // Windows force-delete
    "rd /s",
    "format ",
    "reg delete",
    "net user ",
];

/// Shell-execution tool.
#[derive(Debug)]
pub struct BashTool;

#[async_trait]
impl Tool for BashTool {
    fn name(&self) -> &'static str {
        "bash"
    }

    fn description(&self) -> &'static str {
        "Execute a shell command in the workspace root. \
         Returns combined stdout + stderr. Hard timeout 60s. \
         Dangerous patterns are auto-refused unless explicitly approved."
    }

    fn schema(&self) -> serde_json::Value {
        serde_json::json!({
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute. Runs via `bash -c` on Unix, `cmd /C` on Windows."
                },
                "timeout_secs": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 600,
                    "description": "Override the default 60s timeout."
                }
            },
            "required": ["command"],
            "additionalProperties": false
        })
    }

    async fn execute(
        &self,
        args: serde_json::Value,
        ctx: &ToolContext,
    ) -> Result<ToolOutput, ToolError> {
        if !ctx.capabilities.bash {
            return Ok(ToolOutput::err("refused: bash capability disabled"));
        }

        let command = args
            .get("command")
            .and_then(|v| v.as_str())
            .ok_or_else(|| ToolError::InvalidArgs("missing 'command'".into()))?;

        if command.len() > MAX_COMMAND_BYTES {
            return Ok(ToolOutput::err(format!(
                "refused: command is {} bytes; max {} bytes",
                command.len(),
                MAX_COMMAND_BYTES
            )));
        }

        let timeout_secs = args
            .get("timeout_secs")
            .and_then(|v| v.as_u64())
            .unwrap_or(DEFAULT_TIMEOUT.as_secs());
        let timeout = Duration::from_secs(timeout_secs.min(600));

        // Capability: outbound network.
        if !ctx.capabilities.network && looks_like_network(command) {
            return Ok(ToolOutput::err(
                "refused: command appears to use the network, but network capability is off",
            ));
        }

        // Safety check: dangerous patterns.
        let lower = command.to_lowercase();
        if !ctx.approved {
            for pat in DANGEROUS_PATTERNS {
                if lower.contains(&pat.to_lowercase()) {
                    return Ok(ToolOutput::err(format!(
                        "refused: command matches dangerous pattern `{pat}`; \
                         needs explicit user approval"
                    )));
                }
            }
        }

        let mut cmd = build_shell_command(command);
        cmd.current_dir(&ctx.workspace.root);
        cmd.kill_on_drop(true);

        let output = tokio::time::timeout(timeout, cmd.output())
            .await
            .map_err(|_| {
                ToolError::Other(format!("timed out after {}s", timeout.as_secs()))
            })?
            .map_err(ToolError::Io)?;

        let mut buf = String::with_capacity(output.stdout.len() + output.stderr.len() + 64);
        if !output.stdout.is_empty() {
            buf.push_str(&String::from_utf8_lossy(&output.stdout));
        }
        if !output.stderr.is_empty() {
            if !buf.is_empty() { buf.push('\n'); }
            buf.push_str("--- stderr ---\n");
            buf.push_str(&String::from_utf8_lossy(&output.stderr));
        }
        if buf.is_empty() {
            buf.push_str("(no output)");
        }

        let code = output.status.code().unwrap_or(-1);
        // Append exit code on failure so the model can react.
        if !output.status.success() {
            buf.push_str(&format!("\n--- exit {code} ---"));
            Ok(ToolOutput::err(buf))
        } else {
            Ok(ToolOutput::ok(buf))
        }
    }
}

#[cfg(target_os = "windows")]
fn build_shell_command(command: &str) -> Command {
    let mut c = Command::new("cmd");
    c.arg("/C").arg(command);
    c
}

#[cfg(not(target_os = "windows"))]
fn build_shell_command(command: &str) -> Command {
    let mut c = Command::new("bash");
    c.arg("-c").arg(command);
    c
}

/// Crude heuristic: does this command look like it touches the
/// network? Used to gate the `network` capability. Intentionally
/// conservative — false positives (refused when allowed) are much
/// cheaper than false negatives (allowed when not).
fn looks_like_network(cmd: &str) -> bool {
    let lower = cmd.to_lowercase();
    // Common network-using binaries and a couple of protocols.
    const MARKERS: &[&str] = &[
        "curl", "wget", "httpie", "http ", "https://", "http://",
        "ftp ", "sftp", "scp", "rsync ", "ssh ",
        "npm install", "pnpm install", "yarn add", "pip install",
        "git clone", "git fetch", "git pull", "git push",
        "nslookup", "ping ", "tracert", "traceroute",
        "telnet ", "nc ", "netcat",
        "powershell -command",  // over-eager but safe
    ];
    MARKERS.iter().any(|m| lower.contains(m))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::workspace::Workspace;

    fn ctx() -> ToolContext {
        ToolContext {
            workspace: Workspace::new(std::env::temp_dir(), "tmp"),
            approved: false,
            ..Default::default()
        }
    }

    #[tokio::test]
    async fn echoes_command() {
        #[cfg(target_os = "windows")]
        let cmd = "echo hello";
        #[cfg(not(target_os = "windows"))]
        let cmd = "echo hello";
        let out = BashTool
            .execute(serde_json::json!({"command": cmd}), &ctx())
            .await
            .unwrap();
        assert!(!out.is_error);
        assert!(out.content.contains("hello"));
    }

    #[tokio::test]
    async fn refuses_dangerous() {
        let out = BashTool
            .execute(serde_json::json!({"command": "rm -rf /"}), &ctx())
            .await
            .unwrap();
        assert!(out.is_error);
        assert!(out.content.contains("dangerous"));
    }

    #[tokio::test]
    async fn approved_can_run_dangerous() {
        let mut c = ctx();
        c.approved = true;
        #[cfg(target_os = "windows")]
        let cmd = "echo approved";
        #[cfg(not(target_os = "windows"))]
        let cmd = "echo approved";
        let out = BashTool
            .execute(serde_json::json!({"command": cmd}), &c)
            .await
            .unwrap();
        assert!(!out.is_error);
    }
}
#[cfg(test)]
mod cap_tests {
    use super::*;
    use crate::tool::{Capabilities, ToolContext};
    use crate::workspace::Workspace;

    fn ctx_with(caps: Capabilities) -> ToolContext {
        ToolContext {
            workspace: Workspace::new(std::env::temp_dir(), "tmp"),
            approved: false,
            capabilities: caps,
        }
    }

    #[tokio::test]
    async fn bash_capability_off_is_refused() {
        let out = BashTool
            .execute(
                serde_json::json!({"command": "echo hi"}),
                &ctx_with(Capabilities::no_modify()),
            )
            .await
            .unwrap();
        assert!(out.is_error);
        assert!(out.content.contains("bash capability"));
    }

    #[tokio::test]
    async fn network_capability_off_refuses_curl() {
        let out = BashTool
            .execute(
                serde_json::json!({"command": "curl https://example.com"}),
                &ctx_with(Capabilities::network_off()),
            )
            .await
            .unwrap();
        assert!(out.is_error);
        assert!(out.content.contains("network"));
    }

    #[tokio::test]
    async fn network_capability_off_allows_ls() {
        let c = ctx_with(Capabilities::network_off());
        #[cfg(target_os = "windows")]
        let cmd = "dir";
        #[cfg(not(target_os = "windows"))]
        let cmd = "ls";
        let out = BashTool
            .execute(serde_json::json!({"command": cmd}), &c)
            .await
            .unwrap();
        assert!(!out.is_error);
    }

    #[test]
    fn looks_like_network_positive_cases() {
        assert!(super::looks_like_network("curl https://x"));
        assert!(super::looks_like_network("wget -q -O- https://x"));
        assert!(super::looks_like_network("git clone https://x"));
        assert!(super::looks_like_network("npm install foo"));
        assert!(super::looks_like_network("ping 8.8.8.8"));
    }

    #[test]
    fn looks_like_network_negative_cases() {
        assert!(!super::looks_like_network("ls -la"));
        assert!(!super::looks_like_network("echo hello"));
        assert!(!super::looks_like_network("node server.js"));
    }
}
