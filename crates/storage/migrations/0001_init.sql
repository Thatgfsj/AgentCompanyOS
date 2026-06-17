-- 0001_init.sql
-- Initial schema for ACO. See docs/STORAGE_SPEC.md §4.

CREATE TABLE workflows (
  id              TEXT PRIMARY KEY,
  created_at      INTEGER NOT NULL,
  updated_at      INTEGER NOT NULL,
  state           TEXT NOT NULL,
  phase           TEXT NOT NULL,
  user_request    TEXT NOT NULL,
  plan_doc        TEXT,
  summary         TEXT,
  final_status    TEXT,
  total_input_tokens  INTEGER NOT NULL DEFAULT 0,
  total_output_tokens INTEGER NOT NULL DEFAULT 0,
  total_cost_usd REAL
);

CREATE INDEX idx_workflows_created ON workflows(created_at DESC);
CREATE INDEX idx_workflows_state   ON workflows(state);

CREATE TABLE workflow_log (
  wf_id       TEXT NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
  seq         INTEGER NOT NULL,
  ts          INTEGER NOT NULL,
  from_state  TEXT,
  to_state    TEXT,
  event       TEXT,
  actor       TEXT,
  context     TEXT,
  PRIMARY KEY (wf_id, seq)
);

CREATE INDEX idx_log_ts ON workflow_log(wf_id, ts);

CREATE TABLE tasks (
  id              TEXT PRIMARY KEY,
  wf_id           TEXT NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
  parent_id       TEXT REFERENCES tasks(id),
  title           TEXT NOT NULL,
  status          TEXT NOT NULL,
  assigned_to     TEXT,
  model           TEXT,
  repair_count    INTEGER NOT NULL DEFAULT 0,
  input_tokens    INTEGER NOT NULL DEFAULT 0,
  output_tokens   INTEGER NOT NULL DEFAULT 0,
  cost_usd        REAL,
  files_modified  TEXT,
  started_at      INTEGER,
  finished_at     INTEGER,
  result          TEXT
);

CREATE INDEX idx_tasks_wf ON tasks(wf_id);
CREATE INDEX idx_tasks_status ON tasks(status);

CREATE TABLE usage (
  id              TEXT PRIMARY KEY,
  ts              INTEGER NOT NULL,
  task_id         TEXT REFERENCES tasks(id),
  wf_id           TEXT REFERENCES workflows(id) ON DELETE CASCADE,
  agent_id        TEXT NOT NULL,
  provider        TEXT NOT NULL,
  model           TEXT NOT NULL,
  input_tokens    INTEGER NOT NULL,
  output_tokens   INTEGER NOT NULL,
  cached_tokens   INTEGER NOT NULL DEFAULT 0,
  cost_usd        REAL,
  finish_reason   TEXT
);

CREATE INDEX idx_usage_ts   ON usage(ts);
CREATE INDEX idx_usage_task ON usage(task_id);
CREATE INDEX idx_usage_wf   ON usage(wf_id);

CREATE TABLE prompts (
  id              TEXT PRIMARY KEY,
  ts              INTEGER NOT NULL,
  wf_id           TEXT REFERENCES workflows(id) ON DELETE CASCADE,
  task_id         TEXT REFERENCES tasks(id),
  agent_id        TEXT NOT NULL,
  role            TEXT NOT NULL,
  content         TEXT NOT NULL,
  model           TEXT,
  input_tokens    INTEGER,
  output_tokens   INTEGER
);

CREATE TABLE config_snapshots (
  wf_id       TEXT PRIMARY KEY REFERENCES workflows(id) ON DELETE CASCADE,
  aco_toml    TEXT NOT NULL,
  providers   TEXT NOT NULL,
  router      TEXT NOT NULL
);

CREATE TABLE project_memory (
  id          TEXT PRIMARY KEY,
  project_id  TEXT NOT NULL,
  key         TEXT NOT NULL,
  value       TEXT NOT NULL,
  source      TEXT,
  created_at  INTEGER NOT NULL,
  updated_at  INTEGER NOT NULL,
  UNIQUE (project_id, key)
);

CREATE INDEX idx_memory_project ON project_memory(project_id);

CREATE TABLE plugins (
  id          TEXT PRIMARY KEY,
  version     TEXT NOT NULL,
  path        TEXT NOT NULL,
  manifest    TEXT NOT NULL,
  state       TEXT NOT NULL,
  enabled_at  INTEGER,
  last_error  TEXT
);

-- FTS5 over workflows/tasks/log/prompts/memory.
CREATE VIRTUAL TABLE search_idx USING fts5(
  kind UNINDEXED,
  ref_id UNINDEXED,
  wf_id UNINDEXED,
  content,
  tokenize = 'porter unicode61 remove_diacritics 2'
);
