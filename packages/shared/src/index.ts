/**
 * @aco/shared — cross-language types for ACO.
 *
 * This package is the **source of truth** for IPC events, errors,
 * and protocol messages. Rust and Python generate their own types
 * from the JSON Schema emitted by `pnpm schema:gen`. CI runs
 * `pnpm types:sync` to detect drift.
 *
 * See `docs/ARCHITECTURE.md` §6 and `docs/AGENT_PROTOCOL.md` §3.
 */

export * from './events.js';
export * from './errors.js';
export * from './protocol.js';
