//! HTTP + Server-Sent-Events bridge for the pipe server (v0.4.21,
//! event 000057).
//!
//! The pipe server's primary transport is named pipes
//! (`\\.\pipe\flowntier_runtime` on Windows, Unix domain sockets
//! on macOS/Linux). That's the right choice for the Tauri desktop
//! shell on the same machine — but it locks out every browser
//! on the planet, because no browser can read named pipes.
//!
//! For the **HTML frontend** (a portable browser-runnable shell
//! that runs on macOS, Linux, headless servers, embedded devices,
//! or just a plain `chrome.exe` from any user account), we expose
//! the same JSON-RPC API + events stream over loopback HTTP:
//!
//! * `POST /rpc`         — JSON-RPC 2.0 request body, JSON-RPC 2.0
//!                         response body. CORS: `Access-Control-Allow-Origin: *`.
//! * `GET /events`       — Server-Sent Events stream, one
//!                         `data: <json>\n\n` per AgentEvent.
//! * `GET /health`       — returns 200 + `{"ok":true}`.
//!
//! The bridge is **loopback-only** (127.0.0.1) on purpose: the
//! pipe server is a local sidecar, not a network service. If the
//! chairman wants to expose it, the right answer is SSH/tunnel,
//! not opening this port to the world.
//!
//! Wire-shape note: the JSON-RPC envelope we accept is the same
//! shape used by the named-pipe transport — `{"jsonrpc":"2.0",
//! "id":N,"method":"GET","params":{"path":"/api/...","body":...}}`
//! — so handlers.rs can stay untouched. The bridge is a pure
//! protocol adapter.
//!
//! SSE frame format mirrors the named-pipe newline-delimited
//! stream one-to-one: each `AgentEvent` serialised to JSON + a
//! trailing `\n\n`. Browser `EventSource` consumes this natively
//! (with `event: <kind>` line if the browser cares, but plain
//! `data:` lines are fine for our generic consumer).
//!
//! Lives for the lifetime of the runtime process. Spawned by
//! `bin/flowntier-runtime.rs` after `register_all` (so the
//! `Dispatcher` is fully populated).

use std::net::SocketAddr;
use std::sync::Arc;

use agent_core::AgentEvent;
use serde_json::Value;
use tokio::io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt, BufReader};
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::broadcast;
use tracing::{error, info, warn};

use crate::dispatcher::Dispatcher;
use crate::protocol::RpcRequest;

/// Default bind address: loopback only.
pub const DEFAULT_BIND: &str = "127.0.0.1:8765";

/// Bind a TcpListener on the given bind string and return the
/// listener + its actual local address. Useful for tests that
/// pass `"127.0.0.1:0"` and need to know the OS-assigned port.
pub async fn bind_listener(bind: &str) -> std::io::Result<(TcpListener, SocketAddr)> {
    let l = TcpListener::bind(bind).await?;
    let addr = l.local_addr()?;
    Ok((l, addr))
}

/// Spawn the HTTP+SSE bridge. Returns when the listener exits
/// (which on production means the runtime is shutting down).
pub async fn run_http_bridge(
    bind: String,
    dispatcher: Arc<Dispatcher>,
    events_tx: broadcast::Sender<AgentEvent>,
) -> std::io::Result<()> {
    let listener = TcpListener::bind(&bind).await?;
    run_http_bridge_on(listener, dispatcher, events_tx).await
}

/// Run the HTTP+SSE bridge on an already-bound listener. Production
/// code calls `run_http_bridge(bind, …)` which binds internally;
/// tests use `bind_listener("127.0.0.1:0")` to learn the
/// OS-assigned port and then call this to start serving without
/// the bind race.
pub async fn run_http_bridge_on(
    listener: TcpListener,
    dispatcher: Arc<Dispatcher>,
    events_tx: broadcast::Sender<AgentEvent>,
) -> std::io::Result<()> {
    let addr = listener.local_addr()?;
    info!(bind = %addr, "v0.4.21: HTTP+SSE bridge listening (loopback only)");

    loop {
        let (stream, peer) = match listener.accept().await {
            Ok(v) => v,
            Err(e) => {
                error!(error = %e, "http_bridge: accept failed");
                continue;
            }
        };
        // Defence in depth: refuse non-loopback peers. The bind is
        // already 127.0.0.1, but if someone restarts with a wider
        // bind we still bail.
        if !peer.ip().is_loopback() {
            warn!(peer = %peer, "http_bridge: refusing non-loopback connection");
            drop(stream);
            continue;
        }
        let d = dispatcher.clone();
        let tx = events_tx.clone();
        tokio::spawn(async move {
            if let Err(e) = serve_http_connection(stream, d, tx).await {
                warn!(peer = %peer, error = %e, "http_bridge: connection error");
            }
        });
    }
}

/// Route one HTTP/1.1 request. We hand-roll HTTP because we don't
/// want to pull in `hyper`/`axum` for a 100-LOC bridge.
///
/// Note on buffering: we use `read_until(b"\r\n\r\n")` to read
/// EXACTLY the headers — not a generic `read(&mut [u8; 1024])`
/// that could overshoot and silently swallow body bytes. The
/// `split_off` then puts already-read body bytes into a
/// `Leftover` buffer we keep in `ConnState`.
async fn serve_http_connection(
    mut stream: TcpStream,
    dispatcher: Arc<Dispatcher>,
    events_tx: broadcast::Sender<AgentEvent>,
) -> std::io::Result<()> {
    let mut reader = BufReader::new(&mut stream);

    // 1. Read headers until we see `\r\n\r\n`. Tokio's
//    `read_until` only supports a single byte terminator, so
//    we read until `\n` then check for the full CRLFCRLF.
    let mut header_buf: Vec<u8> = Vec::with_capacity(1024);
    loop {
        match reader.read_until(b'\n', &mut header_buf).await {
            Ok(0) => return Ok(()),
            Ok(_) => {}
            Err(_) => return write_400(&mut stream, "header read failed").await,
        }
        if header_buf.windows(4).any(|w| w == b"\r\n\r\n") {
            break;
        }
        if header_buf.len() > 64 * 1024 {
            return write_400(&mut stream, "headers too large").await;
        }
    }
    let header_n = header_buf.len();

    // 2. Split header vs body bytes. BufReader's internal buffer
    //    may already contain body bytes that were read past
    //    `\r\n\r\n` — pull them out via fill_buf + consume.
    let leftover_in_buffer;
    {
        let already_in_internal = reader.fill_buf().await?;
        leftover_in_buffer = already_in_internal.to_vec();
        let consumed = already_in_internal.len();
        reader.consume(consumed);
    }
    let mut leftover = header_buf.split_off(header_n);
    leftover.extend_from_slice(&leftover_in_buffer);

    let header_str = match std::str::from_utf8(&header_buf) {
        Ok(s) => s,
        Err(_) => return write_400(&mut stream, "non-UTF8 headers").await,
    };

    let mut lines = header_str.split("\r\n");
    let request_line = lines.next().unwrap_or("");
    let mut header_parts = request_line.split_whitespace();
    let method = header_parts.next().unwrap_or("").to_string();
    let path = header_parts.next().unwrap_or("").to_string();

    let mut headers = std::collections::HashMap::new();
    for line in lines {
        if line.is_empty() {
            break;
        }
        if let Some(idx) = line.find(':') {
            let k = line[..idx].trim().to_lowercase();
            let v = line[idx + 1..].trim().to_string();
            headers.insert(k, v);
        }
    }

    // CORS preflight (browsers auto-issue OPTIONS).
    if method == "OPTIONS" {
        write_cors_preflight(&mut stream).await?;
        stream.shutdown().await?;
        return Ok(());
    }

    match (method.as_str(), path.as_str()) {
        ("GET", "/health") => write_health(&mut stream).await?,
        ("POST", "/rpc") => {
            // Drop the BufReader borrow before passing &mut stream
            // to handlers that need both halves.
            drop(reader);
            handle_rpc(&mut stream, &headers, dispatcher, &mut leftover).await?
        }
        ("GET", "/events") => {
            drop(reader);
            handle_events(&mut stream, events_tx).await?;
            // /events is a streaming response that never closes
            // on its own; we don't reach the shutdown line below.
            return Ok(());
        }
        _ => write_404(&mut stream).await?,
    }
    // Half-close the write side so clients reading until EOF
    // (e.g. our test harness, browsers using fetch() without
    // keep-alive) get a clean EOF instead of a TCP timeout.
    stream.shutdown().await?;
    Ok(())
}

/// POST /rpc: read JSON-RPC body, dispatch via Dispatcher, write
/// response. Body length comes from the Content-Length header;
/// browsers always set it for fetch().
///
/// `leftover` holds bytes that arrived past the `\r\n\r\n`
/// terminator (BufReader's internal buffer). We drain them first,
/// then read the rest from the stream.
async fn handle_rpc(
    stream: &mut TcpStream,
    headers: &std::collections::HashMap<String, String>,
    dispatcher: Arc<Dispatcher>,
    leftover: &mut Vec<u8>,
) -> std::io::Result<()> {
    let content_length: usize = match headers.get("content-length") {
        Some(v) => match v.parse() {
            Ok(n) => n,
            Err(_) => return write_400(stream, "bad content-length").await,
        },
        None => return write_400(stream, "missing content-length").await,
    };
    if content_length > 1_048_576 {
        return write_400(stream, "body too large (max 1 MiB)").await;
    }

    let mut body = vec![0u8; content_length];
    // Drain leftover first.
    let take = leftover.len().min(content_length);
    body[..take].copy_from_slice(&leftover[..take]);
    leftover.clear();
    // Read the rest directly from the stream (no BufReader — we
    // dropped it before calling this handler).
    let mut cursor = take;
    while cursor < content_length {
        let n = stream.read(&mut body[cursor..]).await?;
        if n == 0 {
            return write_400(stream, "body underrun").await;
        }
        cursor += n;
    }

    let req: RpcRequest = match serde_json::from_slice(&body) {
        Ok(r) => r,
        Err(e) => {
            return write_json(
                stream,
                400,
                &serde_json::json!({"error": format!("invalid JSON-RPC: {e}")}),
            )
            .await;
        }
    };

    let resp = dispatcher.dispatch(req.id, req).await;
    let resp_json = serde_json::to_vec(&resp).unwrap_or_else(|_| {
        br#"{"jsonrpc":"2.0","id":0,"error":{"code":-32603,"message":"response serialise failed"}}"#.to_vec()
    });
    write_json_bytes(stream, 200, &resp_json).await
}

/// GET /events: SSE stream of AgentEvents. Each event is one
/// `data: <json>\n\n` chunk. Browsers auto-reconnect on close.
async fn handle_events(
    stream: &mut TcpStream,
    events_tx: broadcast::Sender<AgentEvent>,
) -> std::io::Result<()> {
    let mut rx = events_tx.subscribe();

    // SSE preamble.
    let header = "HTTP/1.1 200 OK\r\n\
        Content-Type: text/event-stream\r\n\
        Cache-Control: no-cache\r\n\
        Connection: keep-alive\r\n\
        Access-Control-Allow-Origin: *\r\n\
        \r\n";
    stream.write_all(header.as_bytes()).await?;

    // Initial comment so the browser fires `open`.
    stream.write_all(b": connected\n\n").await?;
    stream.flush().await?;

    loop {
        match rx.recv().await {
            Ok(ev) => {
                let payload = match serde_json::to_string(&ev) {
                    Ok(s) => s,
                    Err(_) => continue,
                };
                if stream.write_all(b"data: ").await.is_err() {
                    return Ok(());
                }
                if stream.write_all(payload.as_bytes()).await.is_err() {
                    return Ok(());
                }
                if stream.write_all(b"\n\n").await.is_err() {
                    return Ok(());
                }
                if stream.flush().await.is_err() {
                    return Ok(());
                }
            }
            Err(broadcast::error::RecvError::Lagged(n)) => {
                let _ = stream
                    .write_all(format!(": lagged {n}\n\n").as_bytes())
                    .await;
                let _ = stream.flush().await;
            }
            Err(broadcast::error::RecvError::Closed) => return Ok(()),
        }
    }
}

async fn write_health(w: &mut TcpStream) -> std::io::Result<()> {
    write_json(w, 200, &serde_json::json!({"ok": true})).await
}

async fn write_404(w: &mut TcpStream) -> std::io::Result<()> {
    write_json(w, 404, &serde_json::json!({"error": "not found"})).await
}

async fn write_400(w: &mut TcpStream, msg: &str) -> std::io::Result<()> {
    write_json(w, 400, &serde_json::json!({"error": msg})).await
}

async fn write_cors_preflight(w: &mut TcpStream) -> std::io::Result<()> {
    let resp = "HTTP/1.1 204 No Content\r\n\
        Access-Control-Allow-Origin: *\r\n\
        Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n\
        Access-Control-Allow-Headers: Content-Type\r\n\
        Access-Control-Max-Age: 86400\r\n\
        Connection: close\r\n\
        \r\n";
    w.write_all(resp.as_bytes()).await?;
    w.flush().await
}

async fn write_json(
    w: &mut TcpStream,
    status: u16,
    body: &Value,
) -> std::io::Result<()> {
    let bytes = serde_json::to_vec(body).unwrap_or_else(|_| b"{}".to_vec());
    write_json_bytes(w, status, &bytes).await
}

async fn write_json_bytes(
    w: &mut TcpStream,
    status: u16,
    body: &[u8],
) -> std::io::Result<()> {
    let reason = match status {
        200 => "OK",
        204 => "No Content",
        400 => "Bad Request",
        404 => "Not Found",
        500 => "Internal Server Error",
        _ => "Status",
    };
    let header = format!(
        "HTTP/1.1 {status} {reason}\r\n\
         Content-Type: application/json\r\n\
         Content-Length: {}\r\n\
         Access-Control-Allow-Origin: *\r\n\
         Connection: close\r\n\
         \r\n",
        body.len(),
    );
    w.write_all(header.as_bytes()).await?;
    w.write_all(body).await?;
    w.flush().await
}

/// Resolve the bind address from env. Lets chairman override for
/// tests / multi-instance.
pub fn bind_from_env() -> String {
    std::env::var("FLOWNTIER_HTTP_BRIDGE")
        .unwrap_or_else(|_| DEFAULT_BIND.to_string())
}

/// Quick reachability check used by e2e tests: parse "host:port"
/// and return both halves. Invalid → loopback default.
pub fn parse_bind(s: &str) -> SocketAddr {
    s.parse().unwrap_or_else(|_| "127.0.0.1:8765".parse().unwrap())
}