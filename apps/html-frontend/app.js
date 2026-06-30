// Flowntier HTML Frontend (v0.4.21, event 000057)
//
// A self-contained, browser-runnable shell that talks to the
// pipe-server's HTTP+SSE bridge (POST /rpc + GET /events on
// 127.0.0.1:8765 by default). No Tauri, no bundler, no framework.
//
// How to run:
//   1. Start the pipe server: `cargo run -p pipe-server --bin flowntier-runtime`
//   2. Open this index.html in any browser (double-click or
//      `python -m http.server` from apps/html-frontend/).
//
// The frontend is intentionally minimal: ChatZone (text I/O +
// SSE event stream) + a quota-status side panel pulled from
// GET /api/quota/status every 15 s. The full Settings provider
// management UI is a v0.5 follow-up; the JSON-RPC contract
// already supports it (list_providers / put_secret / etc.) —
// anyone with a fetch tab can drive it.

const BRIDGE_BASE = localStorage.getItem('flowntier.bridge') || 'http://127.0.0.1:8765';

// ── i18n ──────────────────────────────────────────────────────────
const i18n = {
  'zh-CN': {
    'ui.language': '语言',
    'chat.title': '对话',
    'chat.role': '角色',
    'chat.welcome': '— 开始对话 —',
    'chat.send': '发送',
    'chat.inputPlaceholder': '跟角色说点什么…（Ctrl+Enter 发送）',
    'chat.resolveLoading': '解析中…',
    'chat.connected': '已连接',
    'chat.disconnected': '已断开',
    'settings.quota.heading': '角色额度状态',
    'settings.quota.empty': '正常 — 没有挂起的失败。',
    'settings.quota.failed': '本次失败 · 重试等 5h 刷新点',
    'settings.quota.pending_5h_wait': '主理已挂 · 等下一个 5h 刷新点',
    'settings.quota.rate_limited': '已停 · 重置',
    'settings.quota.reset': '重置',
    'settings.logs.heading': '日志',
    'chatZone.quotaNudgeTitle': 'Quota Refresh',
    'chatZone.quotaNudge': 'AI 之前疑似到达上限，目前已经刷新，检查工作进度并且继续工作',
    'resolve.defaultOk': '默认',
    'resolve.noKey': '未配置 API 密钥',
    'resolve.unconfigured': '未配置',
    'resolve.hint': '在 设置 → 角色 → 模型 分配 里选个默认模型',
    'role.chief': '主理', 'role.worker': '工匠', 'role.planner': '规划',
    'role.critic:a': '缺陷猎手', 'role.critic:b': '质检师', 'role.reporter': '汇报',
  },
  'en-US': {
    'ui.language': 'Language',
    'chat.title': 'Chat',
    'chat.role': 'Role',
    'chat.welcome': '— start a conversation —',
    'chat.send': 'Send',
    'chat.inputPlaceholder': 'Say something… (Ctrl+Enter to send)',
    'chat.resolveLoading': 'Resolving…',
    'chat.connected': 'connected',
    'chat.disconnected': 'disconnected',
    'settings.quota.heading': 'Quota Status',
    'settings.quota.empty': 'All clear — no failed (role, model) pairs.',
    'settings.quota.failed': 'Failed · awaiting 5h refresh',
    'settings.quota.pending_5h_wait': 'Chief down · awaiting 5h refresh',
    'settings.quota.rate_limited': 'Stopped · click Reset',
    'settings.quota.reset': 'Reset',
    'settings.logs.heading': 'Logs',
    'chatZone.quotaNudgeTitle': 'Quota Refresh',
    'chatZone.quotaNudge': 'AI may have hit a quota limit; quota has now refreshed. Resume work.',
    'resolve.defaultOk': 'default',
    'resolve.noKey': 'no API key',
    'resolve.unconfigured': 'unconfigured',
    'resolve.hint': 'open Settings → Roles → Model → pick a default model',
    'role.chief': 'Chief', 'role.worker': 'Worker', 'role.planner': 'Planner',
    'role.critic:a': 'Bug Hunter', 'role.critic:b': 'Reviewer', 'role.reporter': 'Reporter',
  },
};

let currentLang = localStorage.getItem('flowntier.lang') || 'zh-CN';
function t(key) { return (i18n[currentLang] && i18n[currentLang][key]) || key; }
function applyI18n() {
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    el.textContent = t(el.getAttribute('data-i18n'));
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
    el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
  });
}

// ── RPC client ────────────────────────────────────────────────────
let nextId = 1;
async function rpc(method, path, body) {
  const id = nextId++;
  let resp;
  try {
    resp = await fetch(`${BRIDGE_BASE}/rpc`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id, method, params: { path, body: body || {} } }),
    });
  } catch (e) {
    setStatus(false, e.message || 'fetch failed');
    throw e;
  }
  const data = await resp.json();
  if (data.error) throw new Error(`${data.error.code}: ${data.error.message}`);
  return data.result; // {status, body}
}

// ── SSE events ────────────────────────────────────────────────────
let es = null;
function connectSSE() {
  if (es) { es.close(); es = null; }
  es = new EventSource(`${BRIDGE_BASE}/events`);
  es.onopen = () => setStatus(true);
  es.onerror = () => setStatus(false, 'SSE dropped; will retry on next tick');
  es.onmessage = (msg) => {
    try { handleEvent(JSON.parse(msg.data)); }
    catch (e) { log('event parse failed: ' + e); }
  };
}

function handleEvent(ev) {
  // v0.4.20 quota nudge banner
  if (ev.kind === 'done' && typeof ev.status === 'string' && ev.status.startsWith('QUOTA_NUDGE:')) {
    const banner = document.getElementById('nudgeBanner');
    banner.querySelector('.body').textContent = ev.summary || t('chatZone.quotaNudge');
    banner.style.display = 'block';
    setTimeout(() => { banner.style.display = 'none'; }, 60_000);
    return;
  }
  // Chat stream chunks
  const t = document.getElementById('transcript');
  if (ev.kind === 'text' && typeof ev.delta === 'string') {
    appendLast('assistant', ev.delta);
    return;
  }
  if (ev.kind === 'done') {
    appendSystem(`[done: ${ev.status}]`);
    return;
  }
  if (ev.kind === 'tool_started' || ev.kind === 'tool_finished') {
    appendSystem(`[${ev.kind}] ${ev.tool || ''} ${ev.message || ''}`);
    return;
  }
  // Default: log to console pane
  log('event: ' + JSON.stringify(ev));
}

function appendLast(who, text) {
  const t = document.getElementById('transcript');
  let last = t.querySelector('.transcript > div:last-child');
  if (!last || !last.classList.contains(who)) {
    last = document.createElement('div');
    last.className = who;
    t.querySelector('.transcript').appendChild(last);
  }
  last.textContent += text;
  t.scrollTop = t.scrollHeight;
}
function appendSystem(text) {
  const t = document.getElementById('transcript');
  const d = document.createElement('div');
  d.className = 'system';
  d.textContent = text;
  t.querySelector('.transcript').appendChild(d);
  t.scrollTop = t.scrollHeight;
}
function log(msg) {
  const lp = document.getElementById('logPane');
  const line = `[${new Date().toISOString().slice(11,19)}] ${msg}\n`;
  lp.textContent += line;
  lp.scrollTop = lp.scrollHeight;
}

// ── Quota status polling ──────────────────────────────────────────
const QUOTA_POLL_MS = 15_000;
async function refreshQuota() {
  try {
    const r = await rpc('GET', '/api/quota/status');
    const list = document.getElementById('quotaList');
    if (!r.body.rows || r.body.rows.length === 0) {
      list.innerHTML = `<div class="quota-empty">${escapeHtml(t('settings.quota.empty'))}</div>`;
      return;
    }
    list.innerHTML = '';
    for (const row of r.body.rows) {
      const el = document.createElement('div');
      el.className = 'quota-row';
      const dotColor =
        row.status === 'failed' ? 'var(--warn)' :
        row.status === 'pending_5h_wait' ? 'var(--pending)' :
        row.status === 'rate_limited' ? 'var(--fail)' :
        'var(--text-3)';
      const labelKey =
        row.status === 'failed' ? 'failed' :
        row.status === 'pending_5h_wait' ? 'pending_5h_wait' :
        row.status === 'rate_limited' ? 'rate_limited' : 'failed';
      el.innerHTML = `
        <span class="dot" style="background:${dotColor}"></span>
        <span class="role">${escapeHtml(row.role_id)}</span>
        <span style="color:var(--text-3)">·</span>
        <span class="model">${escapeHtml(row.model_id)}</span>
        <span style="color:var(--text-3)">·</span>
        <span class="label">${escapeHtml(t('settings.quota.' + labelKey))}</span>
        ${row.status === 'rate_limited'
          ? `<span class="x" data-role="${escapeAttr(row.role_id)}" data-model="${escapeAttr(row.model_id)}">${escapeHtml(t('settings.quota.reset'))}</span>`
          : ''}
      `;
      list.appendChild(el);
    }
    list.querySelectorAll('.x').forEach((b) => {
      b.onclick = async () => {
        await rpc('POST', '/api/quota/reset', {
          role: b.getAttribute('data-role'),
          model_id: b.getAttribute('data-model'),
        });
        refreshQuota();
      };
    });
  } catch (e) {
    log('refreshQuota: ' + e);
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

// ── Role resolve status ───────────────────────────────────────────
async function refreshResolve() {
  const role = document.getElementById('rolePicker').value;
  const el = document.getElementById('resolveStatus');
  el.classList.remove('error');
  el.textContent = t('chat.resolveLoading');
  try {
    const r = await rpc('GET', `/api/router/roles/${encodeURIComponent(role)}/resolve`);
    const body = r.body;
    if (body.ok) {
      const apiKind = body.api_kind || 'openai-compat';
      el.textContent = `${t('resolve.defaultOk')}: ${body.provider_short}:${body.model_id} (${apiKind})`;
    } else {
      el.classList.add('error');
      const errKey =
        (body.error || '').toLowerCase().includes('api key') ? 'resolve.noKey' :
        'resolve.unconfigured';
      el.textContent = `${t(errKey)} — ${body.hint || t('resolve.hint')}`;
    }
  } catch (e) {
    el.classList.add('error');
    el.textContent = 'RPC failed: ' + e;
  }
}

// ── Send chat ─────────────────────────────────────────────────────
async function sendChat() {
  const role = document.getElementById('rolePicker').value;
  const input = document.getElementById('userInput');
  const text = input.value.trim();
  if (!text) return;
  appendSystem(`[→ ${role}] ${text}`);
  input.value = '';
  const btn = document.getElementById('sendBtn');
  btn.disabled = true;
  try {
    await rpc('POST', '/api/run_task', { task: text, role });
  } catch (e) {
    appendSystem(`[error] ${e}`);
  } finally {
    btn.disabled = false;
    input.focus();
  }
}

// ── Status pill ───────────────────────────────────────────────────
function setStatus(ok, msg) {
  const pill = document.getElementById('statusPill');
  pill.classList.toggle('ok', !!ok);
  pill.classList.toggle('fail', !ok);
  pill.textContent = ok ? `● ${t('chat.connected')}` : `○ ${msg || t('chat.disconnected')}`;
}

// ── Init ──────────────────────────────────────────────────────────
function init() {
  applyI18n();
  document.getElementById('langPicker').value = currentLang;
  document.getElementById('langPicker').onchange = (e) => {
    currentLang = e.target.value;
    localStorage.setItem('flowntier.lang', currentLang);
    applyI18n();
    refreshQuota();
    refreshResolve();
  };
  document.getElementById('rolePicker').onchange = refreshResolve;
  document.getElementById('sendBtn').onclick = sendChat;
  document.getElementById('userInput').addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); sendChat(); }
  });
  // Bridge: try to ping /health before opening SSE so the user
  // gets a clear "disconnected" state instead of silent SSE retries.
  fetch(`${BRIDGE_BASE}/health`).then((r) => r.ok ? setStatus(true) : setStatus(false, 'health ' + r.status))
    .catch((e) => setStatus(false, e.message || 'unreachable'));
  connectSSE();
  refreshResolve();
  refreshQuota();
  setInterval(refreshQuota, QUOTA_POLL_MS);
}

init();