//! End-to-end test: bring up the pipe server in-process, open a
//! client connection, send a JSON-RPC request, and verify the
//! response.

use std::time::Duration;

use pipe_server::{register_all, Dispatcher, Server, ServerConfig, ServerState};

fn free_pipe_name(tag: &str, kind: &str) -> String {
    // Both Windows named pipes and Unix domain sockets get a
    // unique path per test invocation.
    let unique = format!(
        "{}-{}-{}",
        tag,
        kind,
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    );

    #[cfg(windows)]
    {
        // Windows: \\.\pipe\aco_test_<unique>
        format!(r"\\.\pipe\aco_test_{unique}")
    }
    #[cfg(not(windows))]
    {
        // Unix: per-test temp dir + .sock
        let dir = std::env::temp_dir().join(format!("aco-pipe-test-{unique}"));
        std::fs::create_dir_all(&dir).unwrap();
        let p = dir.join(format!("{kind}.sock"));
        let _ = std::fs::remove_file(&p);
        p.to_string_lossy().into_owned()
    }
}

// ── Transport abstraction for the test client ────────────────────

#[cfg(not(windows))]
mod client {
    use std::time::Duration;
    use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
    use tokio::net::UnixStream;

    pub async fn connect_and_request(
        addr: &str,
        body: serde_json::Value,
    ) -> serde_json::Value {
        let mut conn = UnixStream::connect(addr).await.expect("connect failed");
        let mut line = serde_json::to_vec(&body).unwrap();
        line.push(b'\n');
        conn.write_all(&line).await.unwrap();

        let mut reader = BufReader::new(&mut conn);
        let mut buf = String::new();
        let n = tokio::time::timeout(Duration::from_secs(3), reader.read_line(&mut buf))
            .await
            .expect("server did not respond in 3s")
            .expect("read failed");
        assert!(n > 0, "empty response");
        serde_json::from_str(&buf).expect("server sent non-JSON")
    }
}

#[cfg(windows)]
mod client {
    use std::time::Duration;
    use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
    use tokio::net::windows::named_pipe::ClientOptions;

    pub async fn connect_and_request(
        addr: &str,
        body: serde_json::Value,
    ) -> serde_json::Value {
        let mut conn = ClientOptions::new()
            .open(addr)
            .expect("connect failed");
        let mut line = serde_json::to_vec(&body).unwrap();
        line.push(b'\n');
        conn.write_all(&line).await.unwrap();

        let mut reader = BufReader::new(&mut conn);
        let mut buf = String::new();
        let n = tokio::time::timeout(Duration::from_secs(3), reader.read_line(&mut buf))
            .await
            .expect("server did not respond in 3s")
            .expect("read failed");
        assert!(n > 0, "empty response");
        serde_json::from_str(&buf).expect("server sent non-JSON")
    }
}

async fn spawn_server(tag: &str) -> (String, tokio::task::JoinHandle<std::io::Result<()>>) {
    let rpc_path = free_pipe_name(tag, "rpc");
    let events_path = free_pipe_name(tag, "events");
    let cfg = ServerConfig {
        rpc_path: rpc_path.clone(),
        events_path,
    };
    let mut d = Dispatcher::new();
    let state = ServerState::new(std::env::temp_dir());
    register_all(&mut d, state.clone());
    let server = Server::new(cfg, d, state.events.clone());
    let handle = tokio::spawn(async move { server.run().await });
    tokio::time::sleep(Duration::from_millis(200)).await;
    (rpc_path, handle)
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn ping_over_pipe_returns_ok() {
    let (addr, handle) = spawn_server("ping").await;
    let resp = client::connect_and_request(
        &addr,
        serde_json::json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "/api/ping",
            "params": {"path": "/api/ping", "body": null}
        }),
    )
    .await;
    assert_eq!(resp["jsonrpc"], "2.0");
    assert_eq!(resp["id"], 1);
    assert_eq!(resp["result"]["status"], 200);
    assert_eq!(resp["result"]["body"]["ok"], serde_json::json!(true));
    assert_eq!(resp["result"]["body"]["runtime"], serde_json::json!("aco-rs"));
    handle.abort();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn unknown_method_returns_jsonrpc_error() {
    let (addr, handle) = spawn_server("404").await;
    let resp = client::connect_and_request(
        &addr,
        serde_json::json!({
            "jsonrpc": "2.0",
            "id": 9,
            "method": "/nope",
            "params": {"path": "/nope", "body": null}
        }),
    )
    .await;
    assert_eq!(resp["error"]["code"], -32601);
    handle.abort();
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn providers_endpoint_returns_ok() {
    let (addr, handle) = spawn_server("providers").await;
    let resp = client::connect_and_request(
        &addr,
        serde_json::json!({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "/api/providers",
            "params": {"path": "/api/providers", "body": null}
        }),
    )
    .await;
    assert_eq!(resp["result"]["status"], 200);
    assert!(resp["result"]["body"]["providers"].is_array());
    handle.abort();
}