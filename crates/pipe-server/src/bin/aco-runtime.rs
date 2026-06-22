//! Standalone binary entry point.
//!
//! Reads `--workspace <dir>` (default: cwd) and starts the
//! server. The Tauri shell can spawn this as a sidecar, OR
//! link it in-process via the `Server::run()` API.

use std::path::PathBuf;

use pipe_server::{register_all, Dispatcher, Server, ServerConfig, ServerState};

#[tokio::main(flavor = "multi_thread", worker_threads = 4)]
async fn main() -> std::io::Result<()> {
    let mut args = std::env::args().skip(1);
    let mut workspace = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--workspace" => {
                if let Some(v) = args.next() {
                    workspace = PathBuf::from(v);
                }
            }
            "--rpc" => {
                eprintln!("--rpc override is honoured by ACO_RPC_PIPE env var instead");
            }
            _ => {
                eprintln!("ignoring unknown arg: {arg}");
            }
        }
    }

    let cfg = ServerConfig::default();
    tracing::info!(rpc = %cfg.rpc_path, events = %cfg.events_path, workspace = %workspace.display(), "starting aco-runtime (Rust)");

    let mut d = Dispatcher::new();
    let state = ServerState::new(workspace);
    register_all(&mut d, state.clone());

    let server = Server::new(cfg, d, state.events.clone());
    server.run().await
}