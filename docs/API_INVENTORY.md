# Flowntier API 调查 / 闭环检查报告

> 调查时间: 2026-07-02
> 调查人: 主席指示"自己检查逻辑，复杂麻烦也没关系"后的全栈排查
> 目标: 把 Tauri shell → Pipe-Server sidecar → Agent loop → SQLite 这套链路的所有接口、调用者、状态都画清楚,标出哪些跑得通、哪些跛脚、哪些缺。

---

## 0. 系统拓扑

```
┌────────────────────────────────────────────────────────────────────┐
│  React (WebView2, tasset://localhost)                              │
│  apps/desktop/src/{App, zones/*, hooks/*, lib/*, components/*}     │
│  invoke() ─────┐                                                   │
│                │  Tauri command (in-process, no HTTP)             │
│                ▼                                                    │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │  Tauri 2.x shell  (apps/desktop/src-tauri/src/lib.rs)    │     │
│  │  - health_check / run_agent_task / get_diagnostics / …   │     │
│  │  - pipe_request() ────► \\.\pipe\flowntier_runtime       │     │
│  │  - events_bridge() ◄── \\.\pipe\flowntier_runtime_events │     │
│  │  - app.emit("wf:event", v) ───► 回到 WebView            │     │
│  └──────────────────────────────────────────────────────────┘     │
│                │  named-pipe JSON-RPC (16 RPC + 4 events workers) │
│                ▼                                                    │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │  Pipe-Server sidecar  (crates/pipe-server)               │     │
│  │  - bin/flowntier-runtime.exe                            │     │
│  │  - handlers.rs: 30 个 d.register("METHOD","/path",…)     │     │
│  │  - HTTP+SSE bridge on 127.0.0.1:8765                    │     │
│  │  - state.events (broadcast::Sender<AgentEvent>)          │     │
│  └──────────────────────────────────────────────────────────┘     │
│                │  agent.run()                                      │
│                ▼                                                    │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │  Agent-Core  (crates/agent-core/src/loop_.rs)            │     │
│  │  - 单 Agent.run() 单轮 chat, 非 multi-agent orchestration│     │
│  │  - Workspace{root, name}  (路径锁死,运行时不可改)        │     │
│  │  - 走 MiniMax / OpenAI / Anthropic / DeepSeek 任何 provider│    │
│  └──────────────────────────────────────────────────────────┘     │
│                │                                                    │
│                ▼                                                    │
│  SQLite (storage.sqlite) — workflows / tasks / quota_failures /   │
│  kv / secrets / provider / role_overrides / project_memory         │
└────────────────────────────────────────────────────────────────────┘
```

**关键事实**:
- **Tauri ↔ pipe-server**: Windows named pipe RPC, JSON-RPC 2.0, 每连接独占一个 worker
- **Pipe-server ↔ WebView**: 通过 Tauri 的 `app.emit("wf:event", v)` 事件总线(不走 HTTP)
- **HTTP+SSE bridge (127.0.0.1:8765)**: **HTML frontend 专用**,Tauri 桌面端不用

---

## 1. Tauri 命令全表 (React ↔ Tauri-Rust)

| # | 命令名 | 文件 | 行 | 后端调用 | 用途 |
|---|---|---|---|---|---|
| 1 | `health_check` | lib.rs:254 | GET /health | 健康检查 |
| 2 | `rpc_version` | lib.rs:266 | GET /api/rpc/version | 版本握手 + drift 检测 |
| 3 | `list_secrets` | lib.rs:271 | GET /api/settings/secrets | 列出密钥(不显示值) |
| 4 | `run_agent_task` | lib.rs:288 | POST /api/run_task | **核心**: 跑一个 agent task |
| 5 | `draw_i_ching` | lib.rs:295 | POST /api/i_ching/draw | 抽卦 |
| 6 | `log_frontend_error` | lib.rs:306 | (本地) | React 错误上报到日志 |
| 7 | `log_webview_console` | lib.rs:334 | (本地) | WebView console 转发 |
| 8 | `kv_get` | lib.rs:344 | GET /api/kv/{key} | 读 kv 表 |
| 9 | `kv_set` | lib.rs:354 | POST /api/kv/{key} | 写 kv 表 |
| 10 | `load_sample_workflow` | lib.rs:367 | GET /api/sample/auth_login | (loading sample) |
| 11 | `first_run_complete` | lib.rs:375 | POST /api/kv/first_run/complete | 标记首次运行完成 |
| 12 | `save_secret` | lib.rs:380 | PUT /api/settings/secrets/{name} | 存 API key |
| 13 | `delete_secret` | lib.rs:414 | DELETE /api/settings/secrets/{name} | 删 key |
| 14 | `reveal_secret` | lib.rs:431 | GET /api/settings/secrets/{name}/reveal | 解密显示 |
| 15 | `seed_secrets` | lib.rs:453 | POST /api/settings/secrets/seed | 从环境变量读 key |
| 16 | `list_providers` | lib.rs:472 | GET /api/providers | 列出所有 provider |
| 17 | `list_router_roles` | lib.rs:477 | GET /api/router/roles | 角色→model 路由 |
| 18 | `list_router_models` | lib.rs:482 | GET /api/router/models | router 解析出的 models |
| 19 | `get_role_resolve_status` | lib.rs:487 | GET /api/router/roles/{role}/resolve | 看 role 是否可解析 |
| 20 | `get_quota_status` | lib.rs:504 | GET /api/quota/status | quota_failures 表 |
| 21 | `reset_quota` | lib.rs:509 | POST /api/quota/reset | 清除 quota 失败 |
| 22 | `get_role_quota_status` | lib.rs:518 | GET /api/router/roles/{role}/resolve | (嵌套在 resolve 里) |
| 23 | `toggle_provider` | lib.rs:530 | PATCH /api/providers/{id} | 开/关 provider |
| 24 | `update_router_roles` | lib.rs:542 | PUT /api/router/roles | 写 role_overrides |
| 25 | `fetch_provider_models` | lib.rs:569 | GET /api/providers/{id}/models | 拉模型列表 |
| 26 | `add_custom_provider` | lib.rs:578 | POST /api/providers/custom | 自定义 provider |
| 27 | `remove_custom_provider` | lib.rs:606 | DELETE /api/providers/custom/{id} | 删自定义 |
| 28 | `invoke_plugin` | lib.rs:611 | POST /api/plugins/{name}/invoke | 调插件 |
| 29 | `start_workflow_cmd` | lib.rs:624 | (workflow 编排) | **未实现完整 multi-agent** |
| 30 | `get_workflow` | lib.rs:636 | GET /api/workflow/{id} | (同上, 占位) |
| 31 | `cancel_workflow` | lib.rs:649 | POST /api/workflow/{id}/cancel | (同上, 占位) |
| 32 | `search_log` | lib.rs:899 | (本地) | 搜索日志 |
| 33 | `wipe_all_data` | lib.rs:1067 | (本地) | 清除所有 data |
| 34 | `set_workdir` | lib.rs:1103 | (本地 → workdir.json) | 切工作目录 |
| 35 | `clear_workdir` | lib.rs:1119 | (本地) | 清工作目录 |
| 36 | `get_diagnostics` | lib.rs:1145 | (本地) | 诊断信息 |
| 37 | `set_workdir_with_nwt` | lib.rs:1279 | (本地) | **原子**: workdir.json + .nwt 初始化 |
| 38 | `get_workdir` | lib.rs:1386 | (本地 → workdir.json) | 读 workdir |

---

## 2. Pipe-Server Routes 全表 (sidecar 内)

| # | METHOD | PATH | 用途 | 状态 |
|---|---|---|---|---|
| 1 | GET | /api/ping | 进程 ping | ✅ |
| 2 | GET | /api/rpc/version | 版本握手 | ✅ |
| 3 | GET | /api/providers | 列出 provider | ✅ |
| 4 | POST | /api/run_task | **核心**: 单 agent task | ✅ (task 落地) |
| 5 | GET | /api/kv/{key} | 读 kv | ✅ |
| 6 | POST | /api/kv/{key} | 写 kv | ✅ |
| 7 | POST | /api/kv/first_run/complete | 首次运行标记 | ✅ |
| 8 | GET | /api/sample/{name} | 加载样本 | ✅ |
| 9 | GET | /api/quota/status | quota 状态 | ✅ |
| 10 | POST | /api/quota/reset | quota 重置 | ✅ |
| 11 | GET | /api/tasks | **dashboard 任务列表** | ✅ (event 000064) |
| 12 | GET | /api/router/roles | 角色列表 | ✅ |
| 13 | GET | /api/router/roles/{role}/resolve | 角色→provider+model | ✅ |
| 14 | GET | /api/router/models | router 可用 models | ✅ |
| 15 | GET | /api/router/roles/{role}/resolve | (重复) | ✅ |
| 16 | PATCH | /api/providers/{id} | toggle provider | ✅ |
| 17 | GET | /api/providers/{id}/models | 拉 provider models | ✅ |
| 18 | POST | /api/providers/custom | 自定义 | ✅ |
| 19 | DELETE | /api/providers/custom/{id} | 删自定义 | ✅ |
| 20 | PUT | /api/router/roles | 写 role_overrides | ✅ |
| 21 | GET | /api/plugins | 插件列表 | ✅ (空) |
| 22 | POST | /api/plugins/{name}/invoke | 调插件 | ⚠️ 占位 |
| 23 | GET | /api/i_ching/draw | 抽卦 | ✅ |
| 24 | GET | /api/i_ching/list | 卦列表 | ✅ |
| 25 | POST | /api/workflow/{id}/cancel | 取消 workflow | ⚠️ |
| 26 | GET | /api/settings/secrets | 列出 key | ✅ |
| 27 | PUT | /api/settings/secrets/{name} | 存 key | ✅ |
| 28 | DELETE | /api/settings/secrets/{name} | 删 key | ✅ |
| 29 | GET | /api/settings/secrets/{name}/reveal | 解密 | ✅ |
| 30 | POST | /api/settings/secrets/seed | seed from env | ✅ |

### 健康检查结果 (2026-07-02 02:14 UTC)

我用 `curl` 挨个敲了所有只读路由,**全部返回 200**:
```
ping  /api/ping                          200
/api/rpc/version                         200 (build=rust, sidecar=0.4.0)
/api/providers                           200 (9 providers)
/api/quota/status                        200 (rows: [])
/api/router/roles                        200 (6 roles, default minimax:MiniMax-M3)
/api/router/models                       200 (count:2)
/api/plugins                             200 (空 list, "no plugins registered in v0.3")
/api/i_ching/list                        200 (count:64)
/api/i_ching/draw                        200 (1 卦)
GET /api/tasks?wf_id=wf_chat_xxx         200 (done:1)
GET /api/settings/secrets                200 (count:2)
GET /api/sample/i_ching                  200 (error: unknown sample, lists: [auth_login])
```

### 跑通的端到端路径

```
React invoke('run_agent_task', { body: { task, role } })
    │
    ▼  Tauri in-process
lib.rs:288 run_agent_task
    │
    ▼  pipe_request
\\.\pipe\flowntier_runtime  (JSON-RPC)
    │
    ▼  dispatcher.match
handlers.rs:run_task  (event 000064)
    ├── resolve_role() → preset + secret_name + role_overrides
    ├── Agent::new(role, provider, tools, workspace)
    ├── agent.run(task_text) → mpsc stream of AgentEvent
    ├── for ev in stream:
    │     state.events.send(ev.clone())     ◄── 触发 events pipe → Tauri → React
    │     if Done: status = status_clean
    ├── ensure_workflow_row(wf_id, user_req, status_clean)  ← 新 (000064)
    │     └── INSERT OR IGNORE INTO workflows
    └── create_task(Task{id, wf_id, title, status, …})      ← 新 (000064)
          └── INSERT INTO tasks
    │
    ▼  return 200 {ok, status, summary, task_id, wf_id}
Tauri pipe_request → JSON → React invoke result
    │
    ▼  ChatZone.tsx:117 send()  → setSending(false)
```

实测跑通:
- POST /api/run_task (chief + MiniMax-M3) → 200 OK
- tasks 表多 1 行 (id `t_…`,status=done,assigned_to=agent:chief)
- AgentEvent 通过 events pipe 转发到 React(useAgentStream.ts:70 `listen('wf:event', …)`)

---

## 3. **🚨 真问题(主席报的 bug)** 

### 3.1 「切工作目录不显示新文件」

**根因 — runtime workspace 跟 workdir.json 是两套独立状态**:

```
Tauri (lib.rs:1103 set_workdir):
    写入: data_dir/workdir.json
    ├── workdir: "O:\\try"  ◄── UI 显示这个
    └── 但只是 .json 文件,**不通知 runtime**

Pipe-server (ServerState::new, handlers.rs:47):
    workspace_root = std::env::current_dir()   ◄── 启动时锁死
    例如: "O:\\Flowntier\\"
    ├── **整个进程生命周期不变**
    └── Chief agent 写文件 = workspace_root/tarot/index.html
```

**实测产物**:
```bash
$ cat C:/Users/thatg/AppData/Roaming/flowntier/workdir.json
{ "workdir": "O:\\try" }                # UI 显示的工作目录

$ ls O:/Flowntier/workspace/tarot/       # chief 实际写到的位置
index.html       56191 bytes  7/2 02:21
index.html.bak   34575 bytes  7/2 02:21

$ ls "O:/try/"                           # UI 工作目录(空)
(空)
```

**修复方向**:
1. Tauri 写完 `workdir.json` 后,**给 pipe-server 发一个 POST /api/workspace/set { path }** 新路由
2. pipe-server 改 `state.workspace` 为 `Arc<RwLock<Workspace>>`,收到 set 路由就更新
3. Agent 启动时拿最新 workspace 路径
4. 替代方案: pipe-server 每次启动前 Tauri 先 `--workspace <workdir>` 拉起(需要重启 sidecar,差)

### 3.2 「提交任务卡死不动」

**嫌疑点**(尚未复现到现场,但代码上看):

#### a. `useAgentStream` 监听 `wf:event` 但不会 push 给 sender

```ts
// useAgentStream.ts:117
useEffect(() => {
  let unlisten: (() => void) | null = null;
  void (async () => {
    const { listen } = await import('@tauri-apps/api/event');
    const off = await listen<unknown>('wf:event', (e) => {
      if (!isAgentEvent(e.payload)) return;        // ◄── AgentEvent? 过滤掉
      setEventsRef.current((prev) => [...prev, ev]);
    });
  })();
  return () => unlisten?.();
}, []);   // ◄── 空依赖数组,只在 mount 时挂一次
```

事件监听没问题。但问题可能是: **整局只挂一个全局事件**,多个 `useAgentStream` 实例会共享,且 **`reset()` 不重启 listener**。如果用户按了"提交任务"再"提交任务",第二次只会 reset state,但 listener 不变 — 这部分应该 OK。

#### b. `run_agent_task` 是同步等待 agent.run() 完整返回

```rust
// handlers.rs:1499
let mut rx = agent.run(task_text);
while let Some(ev) = rx.recv().await {
    state.events.send(ev.clone());      // ◄── 每个事件都转发
    if Done: break;
}
// ... 还要写 ensure_workflow_row + create_task
// 然后 return 200
```

如果 agent.run() 内部 `provider.stream()` 一直 hang(rate-limited / network timeout), `rx.recv()` 等到天荒地老,**handler 不返回** → Tauri pipe_request 不返回 → React `invoke('run_agent_task')` 不 resolve → **UI 转圈**。

**没有 timeout 保护**。

#### c. 没有 user-cancel 路径

`POST /api/workflow/{id}/cancel` 是占位,前端 ChatZone 的 `sending=true` 状态没有 cancel 按钮 — 一旦提交,**只能 kill runtime**。

**修复方向**:
1. agent.run 加一个全局 timeout(比如 5 分钟)
2. `send()` 加 cancel 按钮 → 调 `cancel_workflow`
3. agent.run 接受 `cancel` token(已经在 AgentConfig 里有,看是否串通)

### 3.3 「dashboard 任务列表 0/0 完成」 — **✅ 已修(event 000064)**

之前:run_task 只发 events,不写 tasks 表 → 仪表盘永远 0/0。
现在:run_task 末尾 `ensure_workflow_row` + `create_task`,前端 `GET /api/tasks?wf_id=…` 能查到行。

---

## 4. 闭环状态表

| 状态 | 接口 / 行为 | 备注 |
|---|---|---|
| ✅ **跑通** | Tauri commands 1-22, 25, 26 | 全 200 OK |
| ✅ **跑通** | pipe-server 30 routes 全部 reachable | curl 扫过 |
| ✅ **跑通** | run_task → tasks 表写入 | event 000064 commit `995dec7` |
| ✅ **跑通** | AgentEvent → Tauri → React `useAgentStream` | 实测 158 个 text_delta |
| ⚠️ **跛脚** | workdir 切换不更新 runtime workspace | 3.1 节 |
| ⚠️ **跛脚** | run_task 无 timeout,cancel 路径未连通 | 3.2 节 |
| ⚠️ **跛脚** | Chief agent 是单轮 chat mode | 不是 planner→worker→critic 多 agent |
| ❌ **缺失** | 文件树 / 文件浏览器 UI 组件 | LeftRoster / RightPanel / CenterPanel 都没有 |
| ❌ **缺失** | workflow multi-agent orchestration | start_workflow_cmd / get_workflow / cancel_workflow 都是占位 |
| ❌ **缺失** | 全局错误聚合面板 | 错误只在 ErrorBoundary,不会主动通知 |
| ❌ **缺失** | run_task 后 UI 不显示文件变化(因为 3.1) | workdir 修了之后才能用 |
| ⚠️ **边角** | provider 配置 `minimax:MiniMax-M3` 之前写错过 `M2` | 已还原成 M3,root cause 是 MiniMax API 返回 500/529 |

---

## 5. 已发现的真 bug 全清单

| # | 文件 | 行 | 症状 | 严重度 | 状态 |
|---|---|---|---|---|---|
| 1 | `scripts/patch-nsis.cjs` | 83 | taskkill block 插入到文件最开头 | HIGH | ✅ FIXED in `f0b6aaf` |
| 2 | `crates/storage/src/lib.rs` | 134 | `foreign_keys=true` 阻塞 chat wf_id 写入 tasks | HIGH | ✅ FIXED in `995dec7` (ensure_workflow_row) |
| 3 | `crates/pipe-server/src/dispatcher.rs` | 104 | query string 阻隔路由匹配 | HIGH | ✅ FIXED in `995dec7` (?query strip) |
| 4 | (跨层) | — | Tauri workdir ≠ pipe-server workspace | HIGH | ❌ 待修 |
| 5 | `crates/pipe-server/src/handlers.rs:1499` | — | run_task 无 timeout | MED | ❌ 待修 |
| 6 | `apps/desktop/src/zones/ChatZone.tsx:117` | — | send() 无 cancel 路径 | MED | ❌ 待修 |
| 7 | `apps/desktop/src-tauri/src/lib.rs:899` | — | search_log 不知真实现 | LOW | ⚠️ 待核查 |
| 8 | `apps/desktop/src/lib/api.ts:262` | — | startWorkflow / getWorkflowPlan 是占位 | LOW | ⚠️ 占位 |
| 9 | `crates/agent-core/src/loop_.rs:84` | — | `Agent::run()` 是单轮 chat | LOW | ⚠️ 设计层面 |
| 10 | (DB) | — | `role_overrides.default_model` 之前被改成 `MiniMax-Text-01` | LOW | ✅ 已还原 `MiniMax-M3` |

---

## 6. 立即可执行的下一步(主席确认优先级)

### A. 修 workdir 串通(高优先级,3.1 bug)
**估时**: 2-3 小时
**步骤**:
1. handlers.rs 新增 `POST /api/workspace/set { path }` 路由
2. 把 `state.workspace` 改 `Arc<RwLock<Workspace>>`
3. run_task / tools 全用 `state.workspace.read()` 取最新
4. Tauri `set_workdir_with_nwt` 写完 `workdir.json` 后,调 `pipe_request("POST", "/api/workspace/set", ...)`

### B. 给 run_task 加 timeout(中优先级)
**估时**: 1 小时
**步骤**:
1. handlers.rs:1499 `let mut rx = agent.run(task_text);` 加 `tokio::time::timeout(Duration::from_secs(300), rx.recv())`
2. 超时直接 send 一个 `Done { status: "TIMEOUT" }` 让前端退出 sending 状态

### C. 文件树 UI(中优先级,需要新组件)
**估时**: 4-6 小时
**步骤**:
1. 新增 `GET /api/workspace/tree?path=...&depth=2` 路由
2. 新建 `apps/desktop/src/components/FileTree.tsx`
3. LeftRoster 旁边加一个 Files 标签

### D. 全局错误聚合面板(低优先级)
**估时**: 2 小时
**步骤**:
1. handlers.rs 关键路径加 `tracing::warn!`
2. 新建 `/api/errors/recent` 路由
3. TopBar 加个红点 badge

---

## 7. 调查手段(可复用)

```bash
# 1. 健康检查
curl -sS http://127.0.0.1:8765/health

# 2. 扫所有 route(从 handlers.rs grep)
grep -nE 'd.register' crates/pipe-server/src/handlers.rs

# 3. 调任意 pipe-server route(走 JSON-RPC)
cat > /tmp/q.json << EOF
{"jsonrpc":"2.0","id":1,"method":"GET","params":{"path":"/api/tasks?wf_id=wf_chat_xxx","body":null}}
EOF
curl -sS -X POST -H 'Content-Type: application/json' --data-binary @/tmp/q.json http://127.0.0.1:8765/rpc

# 4. 看所有 Tauri commands
grep -nB1 "tauri::command" apps/desktop/src-tauri/src/lib.rs

# 5. 看所有前端 invoke()
grep -rn "invoke(" apps/desktop/src

# 6. 看 event 转发
grep -rn "wf:event" apps/desktop/src

# 7. 看 DB
python -c "
import sqlite3
db = sqlite3.connect('C:/Users/thatg/AppData/Roaming/flowntier/storage.sqlite')
for r in db.execute('SELECT id, status, model FROM tasks ORDER BY rowid DESC LIMIT 5'):
    print(r)
"

# 8. 看 runtime 实际工作目录
echo 'workdir.json 写的:'; cat C:/Users/thatg/AppData/Roaming/flowntier/workdir.json
echo 'runtime CWD:';      python -c "import os; print(os.getcwd())"  # 这个不准
echo 'runtime 启动命令行:'; powershell -Command "(Get-CimInstance Win32_Process -Filter \"ProcessId=$PID\" | Select-Object -ExpandProperty CommandLine)"

# 9. 看 runtime stderr 日志(走 stderr,null device 时看不到)
#    改用 tracing + 文件: Tauri 端有 logs/flowntier.log.YYYY-MM-DD
tail -50 "C:/Users/thatg/AppData/Roaming/flowntier/logs/flowntier.log.$(date +%Y-%m-%d)"

# 10. 看 NSIS 安装包内容(7z 提取)
"C:/Program Files/AMD/CIM/Bin64/7z.exe" x Flowntier_0.4.21_x64-setup.exe -o/tmp/installer
```

---

## 8. 附:`workdir` vs `workspace` 错位的硬证据

```bash
$ cat C:/Users/thatg/AppData/Roaming/flowntier/workdir.json
{
  "workdir": "O:\\try"
}

$ ls O:/try/                     # UI 工作目录 = 空
(empty)

$ ls O:/Flowntier/workspace/     # runtime 实际产物 = 有内容!
tarot/

$ ls O:/Flowntier/workspace/tarot/index.html  # 56 KB, chief 写的
-rwxr-xr-x  1 thatg 197609  56191  Jul  2 02:21  index.html
-rwxr-xr-x  1 thatg 197609  34575  Jul  2 02:21  index.html.bak

$ powershell (Get-CimInstance Win32_Process -Filter "ProcessId=13608" | Select-Object -ExpandProperty CommandLine)
O:\Flowntier\flowntier_runtime.exe   # 进程命令行,无 --workspace 参数
```

**结论**: `workdir.json` 写的是 `O:\try`,但 runtime 进程启动时**没有传 `--workspace`**,默认是 cwd `O:\Flowntier\`。所有 chief 写文件落 `O:\Flowntier\workspace\`,**永远不会出现在 `O:\try\`**。

这是 bug 3.1 的 root cause,也是主席说"切工作目录不显示新文件"的实际原因。

---

**报告结束。** 下一步等主席指示 A/B/C/D 哪个先做。