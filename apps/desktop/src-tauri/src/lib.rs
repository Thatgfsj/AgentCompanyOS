//! Tauri app glue for the desktop shell. Bridges React commands to
//! the ACO `tauri-core` library.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;
use tauri_plugin_shell::ShellExt;
use tauri_core::{start_workflow, AppState, NewWorkflowRequest, NewWorkflowResponse};

/// v0.2.3: Spawn the bundled Python runtime sidecar via the shell
/// plugin and wait for it to be reachable on 127.0.0.1:7317.
fn spawn_runtime_sidecar(app: &tauri::AppHandle) {
    use std::time::{Duration, Instant};
    const HEALTH_URL: &str = "http://127.0.0.1:7317/health";

    // Kill any existing aco_runtime processes first
    #[cfg(target_os = "windows")]
    {
        let _ = std::process::Command::new("taskkill")
            .args(["/f", "/im", "aco_runtime.exe"])
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .status();
        // Wait for port to be released
        std::thread::sleep(Duration::from_millis(1000));
    }

    // Already up? (e.g. dev mode)
    if ureq_get_status(HEALTH_URL, Duration::from_millis(500)).is_some() {
        println!("[aco] runtime already running on 7317, skipping sidecar spawn");
        return;
    }

    println!("[aco] runtime not running, spawning sidecar...");

    // Use the shell plugin to launch the sidecar
    let sidecar_command = match app.shell().sidecar("aco_runtime") {
        Ok(cmd) => cmd,
        Err(e) => {
            eprintln!("[aco] failed to create sidecar command: {}", e);
            return;
        }
    };

    match sidecar_command.spawn() {
        Ok((mut rx, child)) => {
            println!("[aco] runtime sidecar spawned, pid={:?}", child.pid());

            // Drain sidecar stdout/stderr in background
            tauri::async_runtime::spawn(async move {
                use tauri_plugin_shell::process::CommandEvent;
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            println!("[sidecar] {}", String::from_utf8_lossy(&line));
                        }
                        CommandEvent::Stderr(line) => {
                            eprintln!("[sidecar:err] {}", String::from_utf8_lossy(&line));
                        }
                        CommandEvent::Terminated(status) => {
                            eprintln!("[sidecar] terminated with status: {:?}", status);
                            break;
                        }
                        _ => {}
                    }
                }
            });

            // Poll /health for up to 30s
            let deadline = Instant::now() + Duration::from_secs(30);
            while Instant::now() < deadline {
                if ureq_get_status(HEALTH_URL, Duration::from_millis(500)).is_some() {
                    println!("[aco] runtime sidecar is healthy!");
                    return;
                }
                std::thread::sleep(Duration::from_millis(500));
            }
            eprintln!("[aco] runtime sidecar did not become healthy in 30s");
        }
        Err(e) => {
            eprintln!("[aco] failed to spawn sidecar: {}", e);
        }
    }
}

fn ureq_get_status(url: &str, timeout: std::time::Duration) -> Option<u16> {
    use std::io::{Read, Write};
    use std::net::{SocketAddr, TcpStream};
    let url = url.strip_prefix("http://")?;
    let (host_port, path) = match url.split_once('/') {
        Some((hp, rest)) => (hp, format!("/{}", rest)),
        None => (url, "/".to_string()),
    };
    let (host, port) = match host_port.rsplit_once(':') {
        Some((h, p)) => (h, p),
        None => return None,
    };
    let port: u16 = port.parse().ok()?;
    let addr: SocketAddr = format!("{}:{}", host, port).parse().ok()?;
    let mut stream = TcpStream::connect_timeout(&addr, timeout).ok()?;
    stream.set_read_timeout(Some(timeout)).ok()?;
    stream.set_write_timeout(Some(timeout)).ok()?;
    let req = format!(
        "GET {} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\n\r\n",
        path, host_port
    );
    stream.write_all(req.as_bytes()).ok()?;
    let mut buf = [0u8; 64];
    let n = stream.read(&mut buf).ok()?;
    let header = std::str::from_utf8(&buf[..n.min(32)]).ok()?;
    let mut parts = header.split_whitespace();
    let _ = parts.next()?; // HTTP/1.1
    parts.next()?.parse().ok()
}

#[tauri::command]
async fn start_workflow_cmd(
    state: tauri::State<'_, AppState>,
    req: NewWorkflowRequest,
) -> Result<NewWorkflowResponse, String> {
    start_workflow(state, req).await
}

#[tauri::command]
async fn get_workflow(
    state: tauri::State<'_, AppState>,
    id: String,
) -> Result<Option<serde_json::Value>, String> {
    state
        .repo
        .get_workflow(&id)
        .await
        .map(|opt| opt.map(workflow_to_json))
        .map_err(|e| e.to_string())
}

#[tauri::command]
async fn cancel_workflow(
    _state: tauri::State<'_, AppState>,
    _id: String,
) -> Result<(), String> {
    Ok(())
}

fn workflow_to_json(wf: storage::Workflow) -> serde_json::Value {
    serde_json::json!({
        "id": wf.id,
        "createdAt": wf.created_at,
        "updatedAt": wf.updated_at,
        "state": wf.state,
        "phase": wf.phase,
        "userRequest": wf.user_request,
        "planDoc": wf.plan_doc,
        "summary": wf.summary,
        "finalStatus": wf.final_status.map(|s| match s {
            storage::WorkflowStatus::Active  => "ACTIVE",
            storage::WorkflowStatus::Done    => "DONE",
            storage::WorkflowStatus::Failed  => "FAILED",
            storage::WorkflowStatus::Aborted => "ABORTED",
        }),
        "totalInputTokens": wf.total_input_tokens,
        "totalOutputTokens": wf.total_output_tokens,
        "totalCostUsd": wf.total_cost_usd,
    })
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let handle = app.handle().clone();
            tauri::async_runtime::block_on(async move {
                // Spawn the Python runtime sidecar
                spawn_runtime_sidecar(&handle);

                // Build AppState (connects to the runtime)
                match AppState::build().await {
                    Ok(state) => {
                        handle.manage(state);
                    }
                    Err(e) => {
                        eprintln!("[aco] failed to build AppState: {}", e);
                        std::process::exit(1);
                    }
                }
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![start_workflow_cmd, get_workflow, cancel_workflow])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
