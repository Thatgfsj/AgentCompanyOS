//! Local IPC server for ACO (v0.3+).
//!
//! Replaces `apps/runtime/src/aco_runtime/pipe_server.py`
//! with a pure-Rust implementation that runs in the same
//! process as the Tauri shell (or as a standalone binary).
//!
//! Two channels:
//! - **RPC**: JSON-RPC 2.0 over newline-delimited JSON,
//!   request/response, one connection = one round-trip.
//! - **Events**: server-push; one JSON object per event.
//!
//! Wire format is unchanged from the Python implementation
//! so the Tauri Rust client (`apps/desktop/src-tauri`) does
//! not need any modifications.

pub mod dispatcher;
pub mod handlers;
pub mod protocol;
pub mod server;

pub use dispatcher::Dispatcher;
pub use handlers::{register_all, ServerState};
pub use protocol::{codes, RpcError, RpcParams, RpcRequest, RpcResponse, RpcResult, MAX_LINE};
pub use server::{Server, ServerConfig};