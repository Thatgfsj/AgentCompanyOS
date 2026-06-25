//! Built-in RPC handlers.
//!
//! This module wires a handful of common endpoints so the Tauri
//! client has something to talk to. New handlers are added as
//! the Python routes get ported.

use agent_core::provider::openai::OpenAiProvider;
use agent_core::tool::ToolRegistry;
use agent_core::workspace::Workspace;
use agent_core::{Agent, AgentConfig, AgentEvent};
use serde_json::{json, Value};
use std::sync::Arc;
use tokio::sync::broadcast;

use crate::dispatcher::Dispatcher;
use crate::secrets::SecretStore;

/// Shared state held by the pipe server.
#[derive(Clone)]
pub struct ServerState {
    /// Event bus that all event-pipe clients subscribe to.
    pub events: broadcast::Sender<AgentEvent>,
    /// Default tool registry.
    pub tools: Arc<ToolRegistry>,
    /// CWD-style workspace root for the current pipe server run.
    pub workspace: Workspace,
    /// v0.4: persistent secret store (OS keystore + AES-GCM).
    pub secrets: Arc<SecretStore>,
    /// v0.4: SQLite repository for provider / custom_provider /
    /// kv tables.
    pub repo: Arc<storage::Repository>,
}

impl ServerState {
    /// New default state. Opens the SQLite repo at
    /// `<data_dir>/storage.sqlite` and constructs a SecretStore
    /// bound to the same data dir.
    pub async fn new(
        workspace_root: std::path::PathBuf,
        data_dir: std::path::PathBuf,
    ) -> Self {
        let (events, _rx) = broadcast::channel(1024);

        let db_path = data_dir.join("storage.sqlite");
        let repo = match storage::Repository::open(&db_path).await {
            Ok(r) => Arc::new(r),
            Err(e) => {
                eprintln!("[flowntier-runtime] failed to open storage: {e}");
                // Fallback to in-memory; the v0.4 secret endpoints
                // will work but data won't persist.
                Arc::new(
                    storage::Repository::open_in_memory()
                        .await
                        .expect("in-memory storage always opens"),
                )
            }
        };
        let secrets = Arc::new(SecretStore::new(repo.clone(), data_dir));

        Self {
            events,
            tools: Arc::new(ToolRegistry::with_builtins()),
            workspace: Workspace::new(workspace_root, "flowntier"),
            secrets,
            repo,
        }
    }
}

/// Register every built-in handler on `d`.
pub fn register_all(d: &mut Dispatcher, state: ServerState) {
    let state = Arc::new(state);

    // Health check.
    let s1 = state.clone();
    d.register("GET", "/api/ping", move |_body| {
        let _ = &s1;
        Box::pin(async {
            Ok((200, json!({
                "ok": true,
                "runtime": "flowntier-rs",
                "version": env!("CARGO_PKG_VERSION"),
            })))
        })
    });

    // List providers — minimal; the full implementation lives in
    // `crates/provider-presets` (W3 follow-up).
    let s2 = state.clone();
    d.register("GET", "/api/providers", move |_body| {
        let _ = &s2;
        Box::pin(async {
            Ok((200, json!({
                "providers": [],
                "note": "provider presets not yet wired in v0.3 W3",
            })))
        })
    });

    // Run a workflow / task envelope. This is the central
    // entry point that the Tauri client will use to talk to
    // the agent loop. For now we require the caller to pass
    // a fully-formed provider spec — the router (W3 follow-up)
    // will resolve names to providers.
    let s3 = state.clone();
    d.register("POST", "/api/run_task", move |body| {
        let state = s3.clone();
        Box::pin(async move { run_task(body, state).await })
    });

    // ── Stub handlers for endpoints the Tauri shell calls but
    // the v0.2.5-era Python server implemented. These are
    // best-effort placeholders that return a shape the UI
    // already expects; full implementations land as the
    // corresponding Rust modules come online (v0.4+).
    //
    // We keep them in this file rather than in a separate
    // handlers_i_ching module because they belong to a
    // different domain (provider / router / secret store /
    // plugin registry) and have no shared logic to factor out.
    register_placeholder_handlers(d, state.clone());
}

fn register_placeholder_handlers(d: &mut Dispatcher, state: Arc<ServerState>) {
    // ── Secrets: v0.4 real persistence (OS keystore + AES-GCM).
    // The Tauri shell writes a plaintext via PUT
    // /api/settings/secrets/{name}; the pipe server encrypts
    // with the OS keystore DEK and stores ciphertext + nonce
    // in SQLite. The plaintext is never returned to the UI
    // (only metadata). The agent loop calls GET
    // /api/settings/secrets/{name}/reveal to fetch the plaintext
    // at runtime.
    let list_state = state.clone();
    d.register("GET", "/api/settings/secrets", move |_body| {
        let s = list_state.clone();
        Box::pin(async move {
            match s.secrets.list().await {
                Ok(list) => Ok((200, json!({ "secrets": list, "count": list.len() }))),
                Err(e) => Ok((500, json!({ "error": format!("list_secrets: {e}") }))),
            }
        })
    });

    let put_state = state.clone();
    d.register("PUT", "/api/settings/secrets/{name}", move |body| {
        let s = put_state.clone();
        Box::pin(async move {
            let name = body.get("name").and_then(|v| v.as_str())
                .ok_or_else(|| "missing 'name' in path".to_string())?.to_string();
            let value = body.get("value").and_then(|v| v.as_str())
                .ok_or_else(|| "missing 'value' in body".to_string())?.to_string();
            if value.len() > 4096 {
                return Ok((400, json!({ "error": "secret value exceeds 4 KiB cap" })));
            }
            if name.is_empty() || name.len() > 128 {
                return Ok((400, json!({ "error": "secret name must be 1..=128 chars" })));
            }
            match s.secrets.put(&name, &value).await {
                Ok(()) => Ok((200, json!({ "saved": true, "name": name }))),
                Err(e) => Ok((500, json!({ "error": format!("put_secret: {e}") }))),
            }
        })
    });

    let del_state = state.clone();
    d.register("DELETE", "/api/settings/secrets/{name}", move |body| {
        let s = del_state.clone();
        Box::pin(async move {
            let name = body.get("name").and_then(|v| v.as_str())
                .ok_or_else(|| "missing 'name' in path".to_string())?.to_string();
            match s.secrets.delete(&name).await {
                Ok(removed) => Ok((200, json!({ "deleted": removed, "name": name }))),
                Err(e) => Ok((500, json!({ "error": format!("delete_secret: {e}") }))),
            }
        })
    });

    // Internal-only: returns plaintext. The Tauri shell's IPC
    // bridge should NOT expose this to the webview. Used by
    // the agent loop when making provider requests.
    let reveal_state = state.clone();
    d.register("GET", "/api/settings/secrets/{name}/reveal", move |body| {
        let s = reveal_state.clone();
        Box::pin(async move {
            let name = body.get("name").and_then(|v| v.as_str())
                .ok_or_else(|| "missing 'name' in path".to_string())?.to_string();
            match s.secrets.reveal(&name).await {
                Ok(value) => Ok((200, json!({ "name": name, "value": value }))),
                Err(crate::secrets::SecretStoreError::NotFound(_)) => {
                    Ok((404, json!({ "error": "not found", "name": name })))
                }
                Err(e) => Ok((500, json!({ "error": format!("reveal: {e}") }))),
            }
        })
    });

    // v0.4: trigger the legacy plaintext migration if a
    // v0.3-era secrets.json exists at <data_dir>/secrets.json.
    let seed_state = state.clone();
    d.register("POST", "/api/settings/secrets/seed", move |_body| {
        let s = seed_state.clone();
        Box::pin(async move {
            let legacy = s.secrets.data_dir().join("secrets.json");
            match s.secrets.migrate_legacy_plaintext(&legacy).await {
                Ok(n) => Ok((200, json!({
                    "seeded": n,
                    "source": legacy.display().to_string(),
                }))),
                Err(e) => Ok((500, json!({ "error": format!("seed: {e}") }))),
            }
        })
    });

    // Router: per-role default-model + fallback chain. The
    // real implementation reads from config/router.toml. For
    // v0.3 we return a minimal default that the UI can render.
    d.register("GET", "/api/router/roles", |_body| {
        Box::pin(async {
            Ok((
                200,
                json!({
                    "roles": [
                        { "role": "agent:chief",    "default_model": "anthropic:claude-sonnet-4", "fallback_chain": [] },
                        { "role": "agent:worker",   "default_model": "anthropic:claude-sonnet-4", "fallback_chain": [] },
                        { "role": "agent:planner",  "default_model": "anthropic:claude-sonnet-4", "fallback_chain": [] },
                        { "role": "agent:critic:a", "default_model": "anthropic:claude-sonnet-4", "fallback_chain": [] },
                        { "role": "agent:critic:b", "default_model": "anthropic:claude-sonnet-4", "fallback_chain": [] },
                        { "role": "agent:reporter", "default_model": "anthropic:claude-sonnet-4", "fallback_chain": [] },
                    ],
                }),
            ))
        })
    });
    d.register("GET", "/api/router/models", |_body| {
        Box::pin(async {
            Ok((
                200,
                json!({
                    "models": [],
                    "note": "no provider models known yet; the v0.4 router will fill this in from /api/providers/*/models responses",
                }),
            ))
        })
    });

    // Provider toggle / custom provider CRUD. v0.3 doesn't yet
    // persist these; return 501-style 'not implemented' so the
    // UI can surface a friendly message instead of the JSON-RPC
    // generic error.
    d.register("PATCH", "/api/providers/{id}", |_body| {
        Box::pin(async {
            Ok((
                501,
                json!({
                    "error": "provider toggle not yet implemented in the Rust sidecar; v0.4 will persist this.",
                }),
            ))
        })
    });
    d.register("GET", "/api/providers/{id}/models", |_body| {
        Box::pin(async {
            Ok((
                501,
                json!({
                    "error": "live model fetch not yet implemented in the Rust sidecar; v0.4 will call each provider's /models endpoint.",
                }),
            ))
        })
    });
    d.register("POST", "/api/providers/custom", |_body| {
        Box::pin(async {
            Ok((
                501,
                json!({
                    "error": "custom providers are not yet persisted in the Rust sidecar.",
                }),
            ))
        })
    });
    d.register("DELETE", "/api/providers/custom/{id}", |_body| {
        Box::pin(async {
            Ok((
                501,
                json!({
                    "error": "custom provider deletion not yet implemented in the Rust sidecar.",
                }),
            ))
        })
    });
    d.register("PUT", "/api/router/roles", |body| {
        // PUT (update) variant — distinguished from GET above by
        // the dispatcher key. We register on the same path so the
        // last write wins; the GET handler above never sees the PUT
        // body because Dispatcher only routes by method+path.
        let _ = body;
        Box::pin(async {
            Ok((
                200,
                json!({
                    "ok": true,
                    "note": "router role update accepted (no-op stub); v0.4 will persist the role -> model mapping.",
                }),
            ))
        })
    });

    // Plugin registry. v0.3 ships zero user-loadable plugins in
    // the sidecar; the Tauri shell's plugin panel will render
    // an empty list, which matches the spec.
    d.register("GET", "/api/plugins", |_body| {
        Box::pin(async {
            Ok((
                200,
                json!({
                    "plugins": [],
                    "note": "no plugins registered in v0.3; the Tauri shell's plugin panel is empty by design.",
                }),
            ))
        })
    });
    d.register("POST", "/api/plugins/{name}/invoke", |body| {
        let _ = body;
        Box::pin(async {
            Ok((
                501,
                json!({
                    "error": "plugin invocation not yet implemented; no plugins are registered in v0.3.",
                }),
            ))
        })
    });

    // I Ching oracle (64-gua divination). Implements the full
    // King Wen sequence. The data set is a 12 KB JSON file
    // baked into the binary; the draw path uses
    // `rand::random::<u64>()` for uniform selection across the
    // 64 hexagrams.
    d.register("GET", "/api/i_ching/draw", |_body| {
        Box::pin(async {
            match crate::i_ching::draw_hexagram() {
                Ok(hex) => Ok((
                    200,
                    json!({
                        "draw": {
                            "id": hex.id,
                            "name_zh": hex.name_zh,
                            "name_pinyin": hex.name_pinyin,
                            "name_en": hex.name_en,
                            "binary": hex.binary,
                            "lines": hex.lines().iter().map(|l| json!({
                                "position": l.position,
                                "kind": match l.kind {
                                    crate::i_ching::LineKind::Yang => "yang",
                                    crate::i_ching::LineKind::Yin  => "yin",
                                },
                                "glyph": l.glyph,
                            })).collect::<Vec<_>>(),
                            "judgment": hex.judgment,
                            "image": hex.image,
                        },
                        "drawn_at_ms": std::time::SystemTime::now()
                            .duration_since(std::time::UNIX_EPOCH)
                            .map(|d| d.as_millis() as u64)
                            .unwrap_or(0),
                    }),
                )),
                Err(e) => Ok((500, json!({ "error": e }))),
            }
        })
    });
    d.register("GET", "/api/i_ching/list", |_body| {
        Box::pin(async {
            match crate::i_ching::all_hexagrams() {
                Ok(hexes) => Ok((
                    200,
                    json!({
                        "list": hexes.iter().map(|h| json!({
                            "id": h.id,
                            "name_zh": h.name_zh,
                            "name_pinyin": h.name_pinyin,
                            "name_en": h.name_en,
                            "binary": h.binary,
                        })).collect::<Vec<_>>(),
                        "count": hexes.len(),
                    }),
                )),
                Err(e) => Ok((500, json!({ "error": e }))),
            }
        })
    });

    // Workflow control. The end-to-end workflow loop is not
    // yet wired up; start_workflow_cmd is exposed but the
    // actual run is gated on v0.4 work.
    d.register("POST", "/api/workflow/{id}/cancel", |_body| {
        Box::pin(async {
            Ok((
                200,
                json!({
                    "ok": true,
                    "note": "no active workflow to cancel; v0.4 will route this through the in-process agent loop.",
                }),
            ))
        })
    });
}

async fn run_task(body: Value, state: Arc<ServerState>) -> Result<(u16, Value), String> {
    // ── Parse request ─────────────────────────────────────────
    let task_text = body
        .get("task")
        .and_then(|v| v.as_str())
        .ok_or_else(|| "missing 'task'".to_string())?;
    let provider_kind = body
        .get("provider_kind")
        .and_then(|v| v.as_str())
        .unwrap_or("openai_compat");
    let base_url = body
        .get("base_url")
        .and_then(|v| v.as_str())
        .ok_or_else(|| "missing 'base_url'".to_string())?;
    let base_url = agent_core::provider::openai::validate_base_url(base_url)
        .map_err(|e| format!("invalid base_url: {e}"))?;
    let model = body
        .get("model")
        .and_then(|v| v.as_str())
        .ok_or_else(|| "missing 'model'".to_string())?
        .to_string();
    // Two ways to pass the key: explicit `api_key` (preferred for
    // an embedded sidecar) or `api_key_env` (read from process env
    // — useful when the Tauri shell wants to keep secrets out of
    // the JSON payload).
    let api_key = match body.get("api_key").and_then(|v| v.as_str()) {
        Some(s) if !s.is_empty() => s.to_string(),
        _ => match body.get("api_key_env").and_then(|v| v.as_str()) {
            Some(var) => std::env::var(var).map_err(|_| {
                format!("api_key_env '{var}' not set in process environment")
            })?,
            None => String::new(),
        },
    };
    let role = body
        .get("role")
        .and_then(|v| v.as_str())
        .unwrap_or("agent:worker");
    let wf_id = body
        .get("wf_id")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    // ── Build provider ────────────────────────────────────────
    let provider: Arc<dyn agent_core::Provider> = match provider_kind {
        "openai" => Arc::new(OpenAiProvider::openai(model, api_key)),
        "openai_compat" => Arc::new(OpenAiProvider::compat(base_url, model, api_key)),
        other => return Err(format!("unsupported provider_kind: {other}")),
    };

    // ── Build agent ───────────────────────────────────────────
    let role_enum = match role {
        "agent:chief" => agent_core::prompt::Role::Chief,
        "agent:critic:a" => agent_core::prompt::Role::BugHunter,
        "agent:critic:b" => agent_core::prompt::Role::Reviewer,
        "agent:planner" => agent_core::prompt::Role::Planner,
        "agent:reporter" => agent_core::prompt::Role::Reporter,
        _ => agent_core::prompt::Role::Worker,
    };
    let agent = Agent::new(
        role_enum,
        provider,
        state.tools.clone(),
        state.workspace.clone(),
        AgentConfig::default(),
    );

    // ── Stream events to subscribers while running ────────────
    let mut rx = agent.run(task_text);
    let mut last_status = "UNKNOWN".to_string();
    let mut summary: Option<String> = None;
    while let Some(ev) = rx.recv().await {
        // Best-effort fan-out; if no subscribers, that's fine.
        let _ = state.events.send(ev.clone());
        if let AgentEvent::Done { status, summary: s, .. } = ev {
            last_status = status;
            summary = s;
        }
        if matches!(last_status.as_str(), "DONE" | "FAILED" | "ABORTED" | "ABORTED_REPEAT") {
            // If the wf_id was provided, replace the empty one.
            if !wf_id.is_empty() {
                last_status = format!("{last_status} (wf={wf_id})");
            }
            break;
        }
    }

    Ok((
        200,
        json!({
            "ok": true,
            "status": last_status,
            "summary": summary,
        }),
    ))
}