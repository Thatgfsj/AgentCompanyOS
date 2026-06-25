//! Typed event bus for Flowntier.
//!
//! Carries `WfEvent` between the Rust core, the Tauri webview, and the
//! Python runtime. This is the **only** IPC channel the runtime is
//! allowed to use for state changes (file I/O is a separate concern).
//!
//! See `docs/ARCHITECTURE.md` §7 and `docs/WORKFLOW_SPEC.md` §8.

#![forbid(unsafe_code)]
#![warn(missing_docs)]

use std::sync::Arc;

use async_trait::async_trait;
use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use tokio::sync::broadcast;

/// A workflow event. Mirrors `docs/WORKFLOW_SPEC.md` §8.
///
/// Note: derives `PartialEq` but not `Eq` because `TokenUsage`'s
/// `cost_usd: Option<f64>` contains an `f64`, and `f64` doesn't
/// implement `Eq` (NaN != NaN).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum WfEvent {
    /// State machine transitioned from one state to another.
    Transition {
        /// Workflow id.
        wf_id: String,
        /// Previous state.
        from: Option<String>,
        /// New state.
        to: String,
        /// Triggering event.
        event: String,
        /// Actor that caused the transition (e.g. `agent:chief`).
        actor: String,
        /// ISO 8601 timestamp.
        ts: String,
    },
    /// Token usage reported by a provider.
    TokenUsage {
        /// Agent id that incurred the usage.
        agent_id: String,
        /// Provider id.
        provider: String,
        /// Model id.
        model: String,
        /// Input tokens (excluding cached).
        input_tokens: u32,
        /// Output tokens.
        output_tokens: u32,
        /// Cached input tokens (if any).
        cached_tokens: u32,
        /// Cost in USD, if known.
        cost_usd: Option<f64>,
    },
    /// A line of console output.
    Console {
        /// Source agent.
        agent_id: String,
        /// Log level.
        level: LogLevel,
        /// Free-form message.
        message: String,
    },
    /// A milestone reached (drives the UI timeline).
    Milestone {
        /// Phase name (matches `WORKFLOW_SPEC.md` §2).
        phase: String,
        /// Human label, e.g. "✓ Plan generated".
        label: String,
    },
    /// A user query raised by the Chief.
    UserQuery {
        /// Stable id of this query.
        query_id: String,
        /// Question to the user.
        question: String,
        /// Optional choices.
        options: Vec<String>,
    },
    /// Per-task status update from the orchestrator.
    TaskStatus {
        /// ISO 8601 timestamp.
        ts: String,
        /// Task id (matches TaskNode.id in the parsed plan).
        task_id: String,
        /// Human-readable title for UI display.
        task_title: String,
        /// New status: PENDING | DISPATCHED | RUNNING | DONE |
        /// APPROVED | FAILED | REPAIRING | AWAITING_REVIEW.
        task_status: String,
        /// Optional one-line summary.
        task_summary: Option<String>,
        /// Optional list of files modified.
        task_files: Option<Vec<String>>,
    },
}

/// Severity for `WfEvent::Console`.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum LogLevel {
    /// Verbose tracing.
    Trace,
    /// Debug info.
    Debug,
    /// Normal info.
    Info,
    /// Warnings.
    Warn,
    /// Errors.
    Error,
}

/// Errors that may occur while publishing or subscribing.
#[derive(Debug, Error)]
pub enum EventBusError {
    /// No active subscribers; the event was dropped.
    #[error("no active subscribers")]
    NoSubscribers,
    /// The bus is closed.
    #[error("event bus is closed")]
    Closed,
    /// Underlying channel lag.
    #[error("subscriber lagged behind by {0} events")]
    Lag(u64),
}

/// A trait for things that can publish events.
#[async_trait]
pub trait Publisher: Send + Sync {
    /// Publish an event to all subscribers.
    async fn publish(&self, event: WfEvent) -> Result<(), EventBusError>;
}

/// A trait for things that can subscribe to events.
pub trait Subscriber: Send + Sync {
    /// Returns a stream of events. Multiple calls yield independent streams.
    fn subscribe(&self) -> Box<dyn EventStream>;
}

/// Stream of workflow events.
pub trait EventStream: Send {
    /// Blocking receive.
    fn recv(&mut self) -> Result<WfEvent, EventBusError>;
}

/// In-process event bus backed by a Tokio broadcast channel.
#[derive(Clone)]
pub struct EventBus {
    tx: broadcast::Sender<Arc<WfEvent>>,
    subscriber_count: Arc<RwLock<u64>>,
}

impl std::fmt::Debug for EventBus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("EventBus")
            .field("subscriber_count", &*self.subscriber_count.read())
            .finish_non_exhaustive()
    }
}

impl Default for EventBus {
    fn default() -> Self {
        Self::new(1024)
    }
}

impl EventBus {
    /// Create a new bus with the given channel capacity.
    pub fn new(capacity: usize) -> Self {
        let (tx, _rx) = broadcast::channel(capacity);
        Self {
            tx,
            subscriber_count: Arc::new(RwLock::new(0)),
        }
    }

    /// Number of active subscribers (best-effort).
    pub fn subscriber_count(&self) -> u64 {
        *self.subscriber_count.read()
    }
}

#[async_trait]
impl Publisher for EventBus {
    async fn publish(&self, event: WfEvent) -> Result<(), EventBusError> {
        let event = Arc::new(event);
        self.tx
            .send(event)
            .map_err(|err| match err {
                tokio::sync::broadcast::error::SendError(_) => EventBusError::NoSubscribers,
            })?;
        Ok(())
    }
}

impl Subscriber for EventBus {
    fn subscribe(&self) -> Box<dyn EventStream> {
        let rx = self.tx.subscribe();
        *self.subscriber_count.write() += 1;
        Box::new(BroadcastStream {
            rx,
            _counter: SubscriberGuard {
                count: self.subscriber_count.clone(),
            },
        })
    }
}

struct BroadcastStream {
    rx: broadcast::Receiver<Arc<WfEvent>>,
    _counter: SubscriberGuard,
}

struct SubscriberGuard {
    count: Arc<RwLock<u64>>,
}

impl Drop for SubscriberGuard {
    fn drop(&mut self) {
        let mut g = self.count.write();
        *g = g.saturating_sub(1);
    }
}

impl EventStream for BroadcastStream {
    fn recv(&mut self) -> Result<WfEvent, EventBusError> {
        match self.rx.blocking_recv() {
            Ok(arc) => Ok((*arc).clone()),
            Err(broadcast::error::RecvError::Lagged(n)) => Err(EventBusError::Lag(n)),
            Err(broadcast::error::RecvError::Closed) => Err(EventBusError::Closed),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn publish_to_no_subscribers_is_ok() {
        let bus = EventBus::new(16);
        let result = bus
            .publish(WfEvent::Milestone {
                phase: "planning".into(),
                label: "✓ test".into(),
            })
            .await;
        assert!(result.is_err(), "should error with no subscribers");
    }

    #[tokio::test]
    async fn subscriber_receives_published_event() {
        let bus = EventBus::new(16);
        let mut sub = bus.subscribe();
        bus.publish(WfEvent::Milestone {
            phase: "planning".into(),
            label: "✓ test".into(),
        })
        .await
        .expect("publish should succeed");
        let event = tokio::task::spawn_blocking(move || sub.recv())
            .await
            .expect("spawn_blocking should succeed")
            .expect("recv should succeed");
        match event {
            WfEvent::Milestone { label, .. } => assert_eq!(label, "✓ test"),
            other => panic!("unexpected event: {other:?}"),
        }
    }
}
