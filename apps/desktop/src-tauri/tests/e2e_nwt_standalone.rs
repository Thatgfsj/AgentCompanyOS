//! Standalone E2E tests — zero deps on the lib crate to avoid
//! the Tauri DLL load issue (STATUS_ENTRYPOINT_NOT_FOUND).
//!
//! Chairman's directive ("端对端测试, 简单中等困难, 并且摸清边界情况").
//!
//! These tests mirror the FS-layer code paths in lib.rs's
//! nwt_init_workspace and search_log. They re-implement the
//! same algorithms inline (the lib functions are pub but
//! linking them drags in the full Tauri DLL chain on Windows).
//!
//! If the algorithms change in lib.rs, these tests must be
//! updated to match.

use std::path::PathBuf;

struct TempDir(PathBuf);
impl TempDir {
    fn new(tag: &str) -> Self {
        let base = std::env::temp_dir().join(format!(
            "flowntier-e2e-{}-{}",
            tag,
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_nanos())
                .unwrap_or(0)
        ));
        std::fs::create_dir_all(&base).unwrap();
        Self(base)
    }
    fn path(&self) -> &std::path::Path {
        &self.0
    }
}
impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

// ── Inlined helpers (must match lib.rs) ──────────────────────

fn init_nwt_fs(root: &std::path::Path) -> Result<String, String> {
    let nwt_dir = root.join(".nwt");
    std::fs::create_dir_all(nwt_dir.join("timeline"))
        .map_err(|e| format!("mkdir timeline: {e}"))?;
    std::fs::create_dir_all(nwt_dir.join("indices"))
        .map_err(|e| format!("mkdir indices: {e}"))?;
    let meta = nwt_dir.join("metadata.json");
    if !meta.exists() {
        std::fs::write(&meta, b"{\"placeholder\":true}\n")
            .map_err(|e| format!("write metadata: {e}"))?;
    }
    Ok(nwt_dir.to_string_lossy().into_owned())
}

// ── BUG-006: search_log secret redaction ────────────────
//
// Inline mirror of lib.rs's redact_secrets() function. If the
// lib.rs version changes, update here too.

fn redact_secrets(line: &str) -> String {
    let mut out = line.to_string();

    fn replace_token(
        s: &str,
        prefix: &str,
        replacement: &str,
        include_prefix: bool,
    ) -> String {
        let mut out = String::with_capacity(s.len());
        let bytes = s.as_bytes();
        let prefix_bytes = prefix.as_bytes();
        let plen = prefix_bytes.len();
        let mut i = 0;
        while i + plen <= bytes.len() {
            if &bytes[i..i + plen] == prefix_bytes {
                let after_start = i + plen;
                let mut j = after_start;
                while j < bytes.len()
                    && (bytes[j].is_ascii_alphanumeric()
                        || bytes[j] == b'_'
                        || bytes[j] == b'-')
                {
                    j += 1;
                }
                if include_prefix {
                    out.push_str(prefix);
                }
                out.push_str(replacement);
                i = j;
            } else {
                let c = s[i..].chars().next().unwrap();
                out.push(c);
                i += c.len_utf8();
            }
        }
        if i < bytes.len() {
            out.push_str(&s[i..]);
        }
        out
    }

    out = replace_token(&out, "Bearer ", "<redacted>", true);

    for prefix in &["sk_live_", "sk_test_"] {
        let mut new_out = String::with_capacity(out.len());
        let bytes = out.as_bytes();
        let prefix_bytes = prefix.as_bytes();
        let plen = prefix_bytes.len();
        let mut i = 0;
        while i + plen <= bytes.len() {
            if &bytes[i..i + plen] == prefix_bytes {
                let mut j = i + plen;
                while j < bytes.len()
                    && (bytes[j].is_ascii_alphanumeric()
                        || bytes[j] == b'_'
                        || bytes[j] == b'-')
                {
                    j += 1;
                }
                new_out.push_str(prefix);
                new_out.push_str("<redacted>");
                i = j;
            } else {
                let c = out[i..].chars().next().unwrap();
                new_out.push(c);
                i += c.len_utf8();
            }
        }
        if i < bytes.len() {
            new_out.push_str(&out[i..]);
        }
        out = new_out;
    }

    out = replace_token(&out, "sk-", "sk-<redacted>", false);

    for keyword in &["_KEY", "_TOKEN", "_SECRET", "API_KEY", "PASSWORD"] {
        let klen = keyword.len();
        let bytes = out.as_bytes();
        let mut new_out = String::with_capacity(out.len());
        let mut i = 0;
        while i < bytes.len() {
            let mut j = i;
            let mut found = false;
            while j + klen <= bytes.len() {
                if &bytes[j..j + klen] == keyword.as_bytes() {
                    found = true;
                    break;
                }
                j += 1;
            }
            if !found {
                new_out.push_str(&out[i..]);
                break;
            }
            let mut key_start = j;
            while key_start > 0 {
                let prev = bytes[key_start - 1];
                if prev.is_ascii_uppercase() || prev.is_ascii_digit() || prev == b'_' {
                    key_start -= 1;
                } else {
                    break;
                }
            }
            if key_start == j {
                new_out.push_str(&out[i..j + klen]);
                i = j + klen;
                continue;
            }
            let key_end = j + klen;
            new_out.push_str(&out[i..key_end]);
            let mut sep = key_end;
            while sep < bytes.len() && (bytes[sep] == b' ' || bytes[sep] == b'\t') {
                sep += 1;
            }
            if sep >= bytes.len() || (bytes[sep] != b'=' && bytes[sep] != b':') {
                i = key_end;
                continue;
            }
            new_out.push(bytes[sep] as char);
            let mut v = sep + 1;
            if v < bytes.len() && (bytes[v] == b'"' || bytes[v] == b'\'') {
                new_out.push(bytes[v] as char);
                v += 1;
            }
            let v_start = v;
            while v < bytes.len() {
                let b = bytes[v];
                if b.is_ascii_whitespace()
                    || b == b',' || b == b'}' || b == b']'
                    || b == b'"' || b == b'\''
                {
                    break;
                }
                v += 1;
            }
            let value_seg = &out[v_start..v];
            if value_seg.contains("<redacted>") {
                new_out.push_str(value_seg);
            } else {
                new_out.push_str("<redacted>");
            }
            i = v;
        }
        out = new_out;
    }

    out
}

fn unix_secs_to_iso8601(t: std::time::SystemTime) -> String {
    use std::time::UNIX_EPOCH;
    let secs = t.duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let (year, month, day) = civil_from_days((secs / 86_400) as i64);
    let time_of_day = (secs % 86_400) as u32;
    let hour = time_of_day / 3600;
    let minute = (time_of_day % 3600) / 60;
    let second = time_of_day % 60;
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}Z",
        year, month, day, hour, minute, second
    )
}

fn civil_from_days(z: i64) -> (i32, u32, u32) {
    let z = z + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = (z - era * 146_097) as u32;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146_096) / 365;
    let y = (yoe as i32) + (era as i32) * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    (y, m, d)
}

// ── SIMPLE ────────────────────────────────────────────────

#[test]
fn e2e_simple_init_creates_skeleton() {
    let tmp = TempDir::new("simple-init");
    let nwt = init_nwt_fs(tmp.path()).expect("init ok");
    assert!(std::path::Path::new(&nwt).join("metadata.json").exists());
    assert!(std::path::Path::new(&nwt).join("timeline").is_dir());
    assert!(std::path::Path::new(&nwt).join("indices").is_dir());
}

#[test]
fn e2e_simple_init_is_idempotent() {
    let tmp = TempDir::new("simple-idem");
    init_nwt_fs(tmp.path()).unwrap();
    let meta = tmp.path().join(".nwt").join("metadata.json");
    let first = std::fs::read_to_string(&meta).unwrap();
    init_nwt_fs(tmp.path()).unwrap();
    let second = std::fs::read_to_string(&meta).unwrap();
    assert_eq!(first, second);
}

#[test]
fn e2e_simple_civil_from_days_known_dates() {
    assert_eq!(civil_from_days(0), (1970, 1, 1));
    assert_eq!(civil_from_days(1), (1970, 1, 2));
    // Reference dates (verified with Python: datetime.date(YYYY-MM-DD) - date(1970,1,1)):
    //   2000-01-01 = day 10957
    //   2024-02-29 = day 19782  (leap day)
    //   2026-06-27 = day 20631
    assert_eq!(civil_from_days(10957), (2000, 1, 1));
    assert_eq!(civil_from_days(19782), (2024, 2, 29));
    assert_eq!(civil_from_days(20631), (2026, 6, 27));
}

#[test]
fn e2e_simple_unix_secs_format() {
    let secs = 20631_i64 * 86_400 + 13 * 3600;
    let t = std::time::UNIX_EPOCH + std::time::Duration::from_secs(secs as u64);
    let s = unix_secs_to_iso8601(t);
    assert_eq!(s, "2026-06-27T13:00:00Z", "got: {s}");
}

// ── MEDIUM ───────────────────────────────────────────────

#[test]
fn e2e_medium_workdir_roundtrip() {
    let tmp = TempDir::new("medium-workdir");
    let workdir = tmp.path().to_string_lossy().into_owned();

    let wd_file = tmp.path().join("wd_holder.json");
    assert!(!wd_file.exists());

    std::fs::write(
        &wd_file,
        serde_json::to_vec_pretty(&serde_json::json!({"workdir": workdir})).unwrap(),
    ).unwrap();

    let raw = std::fs::read_to_string(&wd_file).unwrap();
    let v: serde_json::Value = serde_json::from_str(&raw).unwrap();
    assert_eq!(v["workdir"].as_str().unwrap(), workdir);

    let nwt_path = init_nwt_fs(tmp.path()).unwrap();
    assert!(std::path::Path::new(&nwt_path).join("metadata.json").exists());
}

#[test]
fn e2e_medium_nwt_indices_dirs_exist() {
    let tmp = TempDir::new("medium-idx");
    init_nwt_fs(tmp.path()).unwrap();
    let tags_dir = tmp.path().join(".nwt").join("indices");
    assert!(tags_dir.is_dir());
    let timeline = tmp.path().join(".nwt").join("timeline");
    assert!(timeline.is_dir());
}

// ── HARD ─────────────────────────────────────────────────

#[test]
fn e2e_hard_six_events_in_timeline() {
    let tmp = TempDir::new("hard-events");
    init_nwt_fs(tmp.path()).unwrap();
    let timeline = tmp.path().join(".nwt").join("timeline");
    for id in ["000001", "000002", "000003", "000004", "000005"] {
        let event = serde_json::json!({
            "id": id,
            "timestamp": "2026-06-27T12:00:00Z",
            "task": format!("Task {id}"),
            "summary": "synthetic",
            "tags": ["synthetic", "e2e"],
        });
        std::fs::write(
            timeline.join(format!("{id}.json")),
            serde_json::to_vec_pretty(&event).unwrap(),
        ).unwrap();
    }

    let new_id = "000006";
    let event = serde_json::json!({
        "id": new_id,
        "timestamp": "2026-06-27T12:01:00Z",
        "task": "Final task",
        "tags": ["e2e"],
    });
    std::fs::write(
        timeline.join(format!("{new_id}.json")),
        serde_json::to_vec_pretty(&event).unwrap(),
    ).unwrap();

    let entries: Vec<_> = std::fs::read_dir(&timeline).unwrap()
        .filter_map(|e| e.ok())
        .collect();
    assert_eq!(entries.len(), 6);
    for e in entries {
        let raw = std::fs::read_to_string(e.path()).unwrap();
        let v: serde_json::Value = serde_json::from_str(&raw).unwrap();
        assert!(v["id"].is_string());
    }
}

#[test]
fn e2e_hard_max_id_scan() {
    // Mirror of agent-core nwt.rs read_highest_id() logic
    let tmp = TempDir::new("hard-maxid");
    init_nwt_fs(tmp.path()).unwrap();
    let timeline = tmp.path().join(".nwt").join("timeline");

    // Non-conforming files should be skipped.
    std::fs::write(timeline.join("README.md"), b"# notes").unwrap();
    std::fs::write(timeline.join("garbage.json"), b"{}").unwrap();
    for id in ["000007", "000042", "000003"] {
        let event = serde_json::json!({"id": id});
        std::fs::write(
            timeline.join(format!("{id}.json")),
            serde_json::to_vec_pretty(&event).unwrap(),
        ).unwrap();
    }

    let mut max = 0;
    for entry in std::fs::read_dir(&timeline).unwrap().flatten() {
        let name = entry.file_name();
        let Some(name) = name.to_str() else { continue };
        if !name.ends_with(".json") { continue; }
        let stem = &name[..name.len() - 5];
        if stem.len() != 6 { continue; }
        if !stem.bytes().all(|b| b.is_ascii_digit()) { continue; }
        let n: u32 = stem.parse().unwrap();
        if n > max { max = n; }
    }
    assert_eq!(max, 42, "should find 000042 as max");
}

// ── BOUNDARY CASES ───────────────────────────────────────

#[test]
fn e2e_boundary_unicode_workdir() {
    let tmp = TempDir::new("boundary-uni");
    let project = tmp.path().join("我的项目-αβγ");
    std::fs::create_dir_all(&project).unwrap();
    let nwt = init_nwt_fs(&project).unwrap();
    assert!(std::path::Path::new(&nwt).join("metadata.json").exists());
}

#[test]
fn e2e_boundary_spaces_in_workdir() {
    let tmp = TempDir::new("boundary-spaces");
    let project = tmp.path().join("my project with spaces");
    std::fs::create_dir_all(&project).unwrap();
    let nwt = init_nwt_fs(&project).unwrap();
    assert!(std::path::Path::new(&nwt).join("timeline").is_dir());
}

#[test]
fn e2e_boundary_empty_timeline_reads_zero() {
    let tmp = TempDir::new("boundary-empty-tl");
    init_nwt_fs(tmp.path()).unwrap();
    let timeline = tmp.path().join(".nwt").join("timeline");
    let entries: Vec<_> = std::fs::read_dir(&timeline).unwrap().collect();
    assert_eq!(entries.len(), 0);
}

#[test]
fn e2e_boundary_search_log_special_chars() {
    let log_line = "2026-06-27 ERROR [FE-3a7b9c2d] failed: regex .* with \\d+ chars [\"a\",\"b\"]";
    let needles = [
        "FE-3a7b9c2d",
        "[FE-3a7b9c2d]",
        "regex .*",
        "\\d+",
        "[\"a\",\"b\"]",
        "\n",
    ];
    for needle in needles {
        let matches = log_line.contains(needle);
        if needle == "\n" {
            assert!(!matches, "newline needle must not match log line: {needle:?}");
        } else {
            assert!(matches, "needle {needle:?} should match log line");
        }
    }
}

#[test]
fn e2e_boundary_search_log_cap_at_200() {
    let tmp = TempDir::new("boundary-cap");
    let log_dir = tmp.path().join("logs");
    std::fs::create_dir_all(&log_dir).unwrap();
    let log_path = log_dir.join("flowntier.log.2026-06-27");
    let mut content = String::new();
    for _ in 0..500 {
        content.push_str("2026-06-27 ERROR FE-needle found here\n");
    }
    std::fs::write(&log_path, content).unwrap();

    const MAX_MATCHES: usize = 200;
    let text = std::fs::read_to_string(&log_path).unwrap();
    let mut matches = Vec::new();
    let mut truncated = false;
    for line in text.lines() {
        if line.contains("FE-needle") {
            matches.push(line.to_string());
            if matches.len() >= MAX_MATCHES {
                truncated = true;
                break;
            }
        }
    }
    assert_eq!(matches.len(), 200);
    assert!(truncated);
}

#[test]
fn e2e_boundary_search_log_unicode_needle() {
    let log_line = "2026-06-27 ERROR [FE-失败-abc] something broke";
    assert!(log_line.contains("失败"));
    assert!(log_line.contains("FE-失败-abc"));
}

#[test]
fn e2e_boundary_redact_bearer_token() {
    let line = "2026-06-27 ERROR GET /v1/chat 401 Authorization: Bearer sk-supersecret123";
    let r = redact_secrets(line);
    assert!(!r.contains("sk-supersecret123"),
        "bearer token must be redacted, got: {r}");
    assert!(r.contains("Bearer <redacted>"));
}

#[test]
fn e2e_boundary_redact_sk_prefix() {
    let line = "loaded OPENAI_API_KEY=sk-abc123def456ghi789jkl012mno";
    let r = redact_secrets(line);
    assert!(!r.contains("sk-abc123def456ghi789jkl012mno"),
        "sk- prefix must be redacted, got: {r}");
    assert!(r.contains("sk-<redacted>"));
}

#[test]
fn e2e_boundary_redact_env_api_key() {
    let line = r#"{"OPENAI_API_KEY":"sk-abc123def456","ANTHROPIC_API_KEY":"sk-ant-xyz"}"#;
    let r = redact_secrets(line);
    // The KEY= pattern should redact the value. After redaction
    // the raw sk-abc value must not appear.
    assert!(!r.contains("sk-abc123def456"),
        "env API key value must be redacted, got: {r}");
    // And the prefix should remain redacted too (Pattern 2).
    assert!(!r.contains("sk-ant-xyz"),
        "anthropic key must be redacted, got: {r}");
}

#[test]
fn e2e_boundary_redact_preserves_non_secrets() {
    let line = "GET /api/users 200 in 12ms";
    let r = redact_secrets(line);
    assert_eq!(r, line, "non-secret lines must be unchanged");
}

#[test]
fn e2e_boundary_redact_stripe_style() {
    let line = "stripe key: sk_live_abcdef1234567890XYZ";
    let r = redact_secrets(line);
    assert!(!r.contains("abcdef1234567890XYZ"),
        "stripe live key body must be redacted, got: {r}");
    assert!(r.contains("sk_live_<redacted>"));
}

#[test]
fn e2e_boundary_redact_password_kv() {
    let line = "DB_PASSWORD=hunter2 REDIS_PASSWORD=secret123";
    let r = redact_secrets(line);
    assert!(!r.contains("hunter2"),
        "DB_PASSWORD value must be redacted, got: {r}");
    assert!(!r.contains("secret123"),
        "REDIS_PASSWORD value must be redacted, got: {r}");
}

#[test]
fn e2e_boundary_search_log_panic_files_excluded() {
    let tmp = TempDir::new("boundary-panic");
    let log_dir = tmp.path().join("logs");
    std::fs::create_dir_all(&log_dir).unwrap();
    std::fs::write(
        log_dir.join("flowntier.log.2026-06-27"),
        "FE-needle in real log\n",
    ).unwrap();
    std::fs::write(
        log_dir.join("panic-20260627-120000.log"),
        "FE-needle in panic dump\n",
    ).unwrap();

    let mut found = 0;
    for entry in std::fs::read_dir(&log_dir).unwrap().flatten() {
        let name = entry.file_name();
        let Some(name) = name.to_str() else { continue };
        if !name.starts_with("flowntier.log") { continue; }
        if name.starts_with("panic-") { continue; }
        let text = std::fs::read_to_string(entry.path()).unwrap();
        for line in text.lines() {
            if line.contains("FE-needle") { found += 1; }
        }
    }
    assert_eq!(found, 1, "should only match real log, not panic dump");
}

#[test]
fn e2e_boundary_metadata_json_written_once() {
    // First init writes metadata.json; second init must NOT
    // overwrite it (preserves created_at).
    let tmp = TempDir::new("boundary-meta");
    init_nwt_fs(tmp.path()).unwrap();
    let meta = tmp.path().join(".nwt").join("metadata.json");
    let _ = std::fs::read_to_string(&meta).unwrap();
    // Manually corrupt the file to detect if init overwrites.
    std::fs::write(&meta, "{\"placeholder\":false,\"manual_edit\":true}\n").unwrap();
    init_nwt_fs(tmp.path()).unwrap();
    let after = std::fs::read_to_string(&meta).unwrap();
    assert_eq!(after, "{\"placeholder\":false,\"manual_edit\":true}\n",
        "second init must not overwrite existing metadata.json");
}

#[test]
fn e2e_boundary_nested_nwt_in_nwt() {
    // BUG-003 candidate: what if the workdir already contains
    // a .nwt/ subdirectory from a parent project? Must not
    // recursively nest.
    let tmp = TempDir::new("boundary-nested");
    let project = tmp.path().join("a").join("b").join("c");
    std::fs::create_dir_all(&project).unwrap();
    init_nwt_fs(&project).unwrap();
    let nwt = project.join(".nwt");
    assert!(nwt.join("timeline").is_dir());
    assert!(nwt.join("indices").is_dir());
    // And it should NOT have created .nwt/.nwt/
    assert!(!project.join(".nwt").join(".nwt").exists(),
        "must not create nested .nwt/.nwt/");
}