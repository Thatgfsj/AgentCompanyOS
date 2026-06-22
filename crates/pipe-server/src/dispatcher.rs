//! RPC method dispatcher.
//!
//! Maps `(method, path)` strings to an async handler. Handlers
//! receive the request body and return a JSON body or a tuple
//! `(status, body)`.
//!
//! The set of registered handlers mirrors what the Python
//! runtime used to serve under FastAPI. Only a minimal subset is
//! implemented here — enough to unblock the Tauri client; new
//! methods land as they're ported.

use serde_json::Value;
use std::collections::HashMap;
use std::sync::Arc;

use crate::protocol::{codes, RpcParams, RpcResponse};

/// A handler: takes the request body, returns `(status, body)`.
pub type Handler = Arc<dyn Fn(Value) -> HandlerFuture + Send + Sync>;
pub type HandlerFuture =
    std::pin::Pin<Box<dyn std::future::Future<Output = Result<(u16, Value), String>> + Send>>;

/// A registry of RPC handlers keyed by method name.
#[derive(Default, Clone)]
pub struct Dispatcher {
    handlers: HashMap<String, Handler>,
}

impl std::fmt::Debug for Dispatcher {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Dispatcher")
            .field("methods", &self.handlers.keys().collect::<Vec<_>>())
            .finish()
    }
}

impl Dispatcher {
    /// New empty dispatcher.
    pub fn new() -> Self {
        Self::default()
    }

    /// Register a handler for `method`.
    pub fn register<F>(&mut self, method: impl Into<String>, f: F)
    where
        F: Fn(Value) -> HandlerFuture + Send + Sync + 'static,
    {
        self.handlers.insert(method.into(), Arc::new(f));
    }

    /// List registered method names (sorted, deterministic).
    pub fn methods(&self) -> Vec<String> {
        let mut v: Vec<_> = self.handlers.keys().cloned().collect();
        v.sort();
        v
    }

    /// Dispatch an RPC request.
    pub async fn dispatch(&self, req_id: u64, params: RpcParams) -> RpcResponse {
        let body = params.body.unwrap_or(Value::Null);
        let Some(handler) = self.handlers.get(&params.path) else {
            return RpcResponse::err(
                req_id,
                codes::NOT_FOUND,
                format!("no handler registered for path {:?}", params.path),
            );
        };
        match handler(body).await {
            Ok((status, body)) => RpcResponse::status(req_id, status, body),
            Err(e) => RpcResponse::err(req_id, codes::INTERNAL, e),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn dispatches_known_method() {
        let mut d = Dispatcher::new();
        d.register("/api/ping", |_body| {
            Box::pin(async { Ok((200, serde_json::json!({"pong": true}))) })
        });
        let resp = d
            .dispatch(1, RpcParams { path: "/api/ping".into(), body: None })
            .await;
        let r = resp.result.unwrap();
        assert_eq!(r.status, 200);
        assert_eq!(r.body["pong"], serde_json::json!(true));
    }

    #[tokio::test]
    async fn unknown_method_is_not_found() {
        let d = Dispatcher::new();
        let resp = d
            .dispatch(2, RpcParams { path: "/nope".into(), body: None })
            .await;
        let e = resp.error.unwrap();
        assert_eq!(e.code, codes::NOT_FOUND);
    }
}