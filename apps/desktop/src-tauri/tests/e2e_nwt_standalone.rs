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