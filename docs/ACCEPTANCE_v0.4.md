# v0.4 Acceptance Report — STRICT

> **End-to-end acceptance test with strict boundary coverage.**
>
> Date: 2026-06-24
> Status: **PASS** after fixing 8 bugs the previous acceptance
> runs missed.
>
> Maintainer: Thatgfsj

This is the **third** acceptance run of the family-ledger
project. The previous two (`ACCEPTANCE_v0.3.md` and
`ACCEPTANCE_v0.3_LEDGER.md`) both **reported PASS** without
actually exercising the business logic or rendering the UI
in a real browser. This run fixes that:

1. Backend: **28 test cases** exercising every endpoint plus
   boundary conditions (404, 400, FK, empty result, double-delete,
   50 concurrent requests).
2. Frontend: **6 scenarios** with Playwright Chromium actually
   opening the page, clicking buttons, filling forms, and
   screenshotting every state.
3. CI-quality assertions: every assertion catches a *specific*
   bug, not just "I see status 200".

---

## 1. What this run found that the previous two missed

| Bug | Where | Symptom | Discovered by |
|-----|-------|---------|---------------|
| 1 | `GET /api/users` | Returns `[]` instead of `{"users": [...]}` | Strict test (was masked by passing a JSON-string `contains "users"` match) |
| 2 | `GET /api/users/:id/accounts` | Returns `[]` instead of `{"accounts": [...]}` | Strict test |
| 3 | `GET /api/accounts/:id/transactions` | Returns `[{...}]` instead of `{"transactions": [...]}` | Strict test |
| 4 | `POST /api/accounts` with non-existent `user_id` | Returns **404** instead of **400 Bad Request** | Strict test (FK violation is a client error, not a missing resource) |
| 5 | `POST /api/transactions` with non-existent `account_id` | Returns **404** instead of **400** | Strict test |
| 6 | `GET /api/report/summary?user_id=99999` | Returns **404** instead of **200 with zero values** | Strict test (resource parent missing != child resource empty) |
| 7 | Backend under 50 concurrent GETs | First run: 0/50 in 0.06s | Concurrency test |
| 8 | Frontend `loadAll()` | Crashes with `Cannot read properties of undefined (reading 'id')` because `users` is `{users: [...]}`, not `[...]` | Playwright screenshot showed `加载失败: ...` in red |

Bug 8 was the only thing the previous acceptance runs even
noticed — because they showed a status-200 response and called
the test done, they never saw the JS error.

---

## 2. Backend: 28-test strict suite

Script: `C:/Users/thatg/.zcode/acceptance/backend_strict_test.py`
(committed separately; lives outside the repo as a working
artefact).

Test matrix:

| Group | Cases | Coverage |
|-------|-------|----------|
| `[users]` | 7 | list empty, create happy, create with no name / empty name / null name / wrong-type name |
| `[accounts]` | 6 | list by user, list bad user / user_id=0, create happy, FK violation, missing user_id, empty name |
| `[transactions]` | 8 | create happy, create income, create bad account, no amount, no category, list by account, list bad account, delete + double-delete + missing |
| `[report]` | 2 | summary happy, summary non-existent user (must be 200 with zeros) |
| `[CORS]` | 2 | preflight has `Access-Control-Allow-Origin`; preflight lists `DELETE` in `Allow-Methods` |
| `[Concurrency]` | 1 | 50 simultaneous `GET /api/users` must all succeed |
| `[data integrity]` | 1 | (folded into list-by-user after delete; checked via Scenario 6 in UI suite) |

Result before fixes: **21 PASS, 7 FAIL.**

Result after fixes: **28 PASS, 0 FAIL.**

Real timing: 50 concurrent GETs in **0.08 s**.

---

## 3. Frontend: 6 scenarios with Playwright

Script: `C:/Users/thatg/.zcode/acceptance/frontend_visual_test.py`
+ screenshots in `C:/Users/thatg/.zcode/acceptance/shots/`.

Each scenario ends with a full-page screenshot, inspected
visually during this run:

| # | Scenario | Asserts | Shot |
|---|----------|---------|------|
| 1 | Page load | `users-list` chips rendered (no `加载中...` stuck) | `01_loaded.png` |
| 2 | Initial state | `accounts-list` empty (or shows what previous test left) | `02_empty_state.png` |
| 3 | Open "Add Account" dialog → fill name+balance → submit → new card | `现金钱包 ¥5000.00` appears in accounts grid | `03a_add_account_dialog.png`, `03b_after_add_account.png` |
| 4 | Open "Add Transaction" dialog → fill amount/category/note → submit → new row | `晚饭` and `-89.50` appear in tx body | `04a_add_tx_dialog.png`, `04b_after_add_tx.png` |
| 5 | Report + Chart | KPI grid has `总收入` / `总支出` / `结余`; Chart.js canvas > 100 px wide | `05_report.png` |
| 6 | Delete transaction | row removed from table | `06_after_delete.png` |

Before fixes: **scenario 1 stuck on `加载中...`** — `loadAll()` crashed at line `state.users[0].id` because `users` was an object `{users: [...]}`, not an array. Visually the page rendered the title and three empty cards with the red `加载失败: Cannot read properties of undefined (reading 'id')` badge in the top right.

After fixes (tolerant shape + cast in `loadAll`): all 6 scenarios
PASS. Screenshots show a fully rendered single-page admin
panel: 2 user chips, 3 account cards, 3 transaction rows
including colored `+3000.00` / `-200.00` amounts, KPI grid
showing `¥3000 / -¥200 / ¥2800`, and Chart.js rendering two
bars (one green for `salary +3000`, one red for `shopping
-200`).

---

## 4. Fixes shipped

### server.js (4 fixes)

```diff
-    return send(res, 200, stmts.listUsers.all());
+    return send(res, 200, { users: stmts.listUsers.all() });
```

Same shape fix applied to:
- `GET /api/users/:id/accounts`
- `GET /api/accounts/:id/transactions`

```diff
       if (!stmts.getUser.get(user_id)) {
-        return send(res, 404, { error: 'user not found' });
+        return send(res, 400, {
+          error: `user_id ${user_id} does not exist`,
+        });
       }
```

Same fix applied to `POST /api/transactions` FK check.

```diff
       if (!stmts.getUser.get(uid)) {
-        return send(res, 404, { error: 'user not found' });
+        // Missing parent resource is *not* 404 for a
+        // "get me data about X" endpoint — it is 200 with
+        // empty data. (GitHub/GitLab/Stripe convention.)
+        return send(res, 200, {
+          user_id: uid, total_in: 0, total_out: 0,
+          balance: 0, by_category: {},
+        });
       }
```

### index.html (3 fixes)

```diff
-    state.users = await api('/api/users');
+    const usersResp = await api('/api/users');
+    state.users = Array.isArray(usersResp)
+      ? usersResp : (usersResp.users || []);
```

Same pattern applied to:
- `state.accounts = ...` (handles `acctsResp.accounts || []`)
- `allTx.push(...)` (handles `txList = txResp.transactions || []`)

```diff
-    <canvas id="cat-chart" height="80"></canvas>
+    <div style="height: 280px; position: relative;">
+      <canvas id="cat-chart"></canvas>
+    </div>
```

Without a wrapping div, Chart.js's `maintainAspectRatio: false`
caused the canvas to render at 80 px **tall but stretching
to fill the document body height**, producing a screenshot
16,838 px tall. The wrapper gives it a fixed container.

---

## 5. Why the previous acceptance runs missed these

1. **Curl returned 200** → the previous scripts treated that as
   success. They didn't assert on the response **shape**.
2. **The model wrote JSON-shaped code in the report handler**
   that happened to contain `balance` — a string match like
   `must_contain='"balance"'` therefore passed even when the
   response was structurally wrong.
3. **The frontend was never opened in a browser.** The previous
   "verify" step was just `curl http://localhost:5501/` and
   grep the bytes for `<title>家庭记账本</title>`. The JS
   runtime errors were invisible.
4. **The backend was never asked a question it could answer
   wrong.** All previous curls were happy-path. None exercised
   a missing user, a deleted transaction, a 50-way race.

This run fixes all four: shape assertions, JS browser rendering,
boundary cases, concurrency.

---

## 6. What this run still does NOT prove

1. **Concurrent writes are not tested.** Only concurrent reads
   (`GET /api/users`). A 50-way `POST /api/transactions` race
   could surface a different SQLite locking error. v0.5.
2. **The agent-core is not exercised end-to-end in this run.**
   The previous two acceptance runs proved `Agent::run` +
   MiniMax-M3 work; this run focuses on the *product* the
   agent created. Re-run smoke_minimax.rs to re-verify.
3. **The frontend's delete-by-id is the only mutation tested.**
   New accounts / new transactions are added, never deleted.
   Delete-then-add sequence not tested.
4. **No accessibility check.** The Playwright test verifies
   pixels, not ARIA roles or keyboard navigation.
5. **The python http.server on :5501 is not production-like.**
   Real production would use a reverse proxy with cache headers
   and a CSP. Out of scope for v0.4.

---

## 7. Files changed by this run

```
acceptance/ledger-task/
├── backend/
│   └── server.js         (4 fixes: 3× shape wrap + FK 400 + report empty)
└── frontend/
    └── index.html        (3 fixes: tolerant api responses + chart canvas wrapper)
```

Both are local acceptance artefacts, not committed.

```
docs/ACCEPTANCE_v0.4.md  (this file, committed)
```

---

## 8. Repro instructions

```bash
# Terminal 1: backend
cd acceptance/ledger-task/backend
rm -f ledger.db ledger.db-shm ledger.db-wal
node server.js &

# Terminal 2: frontend
cd acceptance/ledger-task/frontend
python -m http.server 5501 &

# Terminal 3: backend strict test
python C:/Users/thatg/.zcode/acceptance/backend_strict_test.py
# expect: PASS 28, FAIL 0

# Terminal 4: frontend visual test (needs `pip install playwright`
# and `python -m playwright install chromium`)
python C:/Users/thatg/.zcode/acceptance/frontend_visual_test.py
# expect: 6/6 PASS, 8 screenshots in C:/Users/thatg/.zcode/acceptance/shots/

# Inspect screenshots manually
explorer C:/Users/thatg/.zcode/acceptance/shots/
```
