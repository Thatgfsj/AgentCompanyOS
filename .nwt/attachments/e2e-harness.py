import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

# Tauri v2 calls `window.__TAURI_INTERNALS__.invoke(cmd, args, options)`.
# We mock BOTH the internals (the real path) and the legacy
# __TAURI__.invoke (in case the bundle uses it).
MOCK = r"""
(() => {
  const handler = async (cmd, args = {}) => {
    await new Promise(r => setTimeout(r, 30));
    if (cmd === 'get_workdir') return 'C:/Users/thatg/e2e-shots/_testworkdir';
    if (cmd === 'set_workdir_with_nwt') return 'C:/Users/thatg/e2e-shots/_testworkdir/.nwt';
    if (cmd === 'kv_get') {
      // first_run must return v:false to skip Welcome; other keys return null
      if (args.key === 'first_run') return { k: 'first_run', v: false };
      return { k: args.key, v: null };
    }
    if (cmd === 'kv_set') return null;
    if (cmd === 'list_providers') return { providers: [] };
    if (cmd === 'list_secrets') return [];
    if (cmd === 'list_custom_providers') return [];
    if (cmd === 'list_roles') return [];
    if (cmd === 'list_plugins') return [];
    if (cmd === 'update_router_roles') return null;
    if (cmd === 'data_dir') return 'C:/Users/thatg/e2e-shots/_testappdata';
    if (cmd === 'rpc_version') return { sidecar: '0.4.0', min_compatible: '0.4.0' };
    if (cmd === 'search_log') return {
      matches: [
        '2026-06-27 ERROR [FE-3a7b9c2d] panic caught at worker.rs:42',
        '2026-06-27 WARN retry count exceeded for token api_key=sk-...',
      ],
      scanned: 42,
      truncated: false
    };
    if (cmd === 'discover_models') return { ok: true, models: [
      { id: 'gpt-4o', display: 'GPT-4o' },
      { id: 'gpt-4-turbo', display: 'GPT-4 Turbo' },
    ] };
    if (cmd === 'add_custom_provider') return null;
    if (cmd === 'load_sample_workflow') return {
      display_name: 'Sample: 实现 POST /auth/login',
      user_request: '实现一个 POST /auth/login 接口',
      description: 'A realistic sample workflow that exercises every role.'
    };
    if (cmd === 'start_workflow_cmd') {
      const wfId = 'wf-' + Math.random().toString(36).slice(2, 10);
      window.__lastWfId = wfId;
      setTimeout(() => startMockWorkflow(wfId), 50);
      return { id: wfId };
    }
    if (cmd === 'get_workflow_status') return { state: 'IN_PROGRESS', active_phase: 2, percent: 0.35 };
    if (cmd === 'list_workflows') return [];
    if (cmd === 'plugin:updater|check') return null;
    console.warn('[mock] unhandled invoke:', cmd);
    return null;
  };
  // Tauri v2 internals — the real path
  window.__TAURI_INTERNALS__ = {
    invoke: handler,
    transformCallback: (cb) => cb,
    unregisterCallback: () => {},
    metadata: { plugins: {} },
  };
  // Also expose legacy shape in case
  window.__TAURI__ = {
    invoke: handler,
    core: { invoke: handler },
    event: { listen: () => Promise.resolve(() => {}) },
  };
  window.__emitEvent = (ev) => window.dispatchEvent(new CustomEvent('wf:event', { detail: ev }));
  function startMockWorkflow(wfId) {
    const ts = () => new Date().toISOString();
    const events = [
      { kind: 'milestone', phase: 'requirement', status: 'started', ts: ts() },
      { kind: 'console', agent_id: 'agent:chief', level: 'info', message: '收到需求，开始规划', ts: ts() },
      { kind: 'task_status', task_id: 't1', task_status: 'IN_PROGRESS', task_summary: '设计 API', ts: ts() },
      { kind: 'milestone', phase: 'planning', status: 'completed', ts: ts() },
      { kind: 'console', agent_id: 'agent:planner', level: 'info', message: '已生成 4 任务计划', ts: ts() },
      { kind: 'task_status', task_id: 't1', task_status: 'DONE', task_summary: 'API 设计完成', ts: ts() },
      { kind: 'milestone', phase: 'development', status: 'in_progress', ts: ts() },
      { kind: 'console', agent_id: 'agent:worker', level: 'info', message: '开始写代码', ts: ts() },
      { kind: 'console', agent_id: 'agent:worker', level: 'info', message: 'POST /auth/login 路由完成', ts: ts() },
      { kind: 'milestone', phase: 'review', status: 'started', ts: ts() },
      { kind: 'console', agent_id: 'agent:critic:a', level: 'info', message: '代码审查通过', ts: ts() },
      { kind: 'milestone', phase: 'review', status: 'completed', ts: ts() },
      { kind: 'milestone', phase: 'delivery', status: 'started', ts: ts() },
      { kind: 'console', agent_id: 'agent:reporter', level: 'info', message: '汇总报告生成', ts: ts() },
      { kind: 'milestone', phase: 'delivery', status: 'completed', ts: ts() },
    ];
    let i = 0;
    const t = setInterval(() => {
      if (i >= events.length) { clearInterval(t); return; }
      window.__emitEvent(events[i++]);
    }, 200);
  }
})();
"""

OUT = Path("C:/Users/thatg/e2e-shots")
OUT.mkdir(exist_ok=True)
Path("C:/Users/thatg/e2e-shots/_testworkdir").mkdir(parents=True, exist_ok=True)


async def screenshot(page, name):
    p = OUT / f"{name}.png"
    await page.screenshot(path=str(p))
    print(f"  saved {name}.png")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})

        page = await ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))
        page.on("console", lambda m: errors.append(f"[{m.type}] {m.text[:200]}") if m.type == "error" else None)
        await page.add_init_script(MOCK)
        await page.goto("http://localhost:1421/")
        await page.wait_for_timeout(2500)

        # ===== 1. Cold start =====
        await screenshot(page, "01-cold-start")
        body = await page.locator("body").inner_text()
        print(f"\n[1] Cold start: body preview: {body[:200]}")

        # Workdir dialog only shows if get_workdir returns null
        if "设置工作目录" in body:
            print("\n[1a] Workdir dialog shown (workdir=null)")
            await page.locator("input").first.fill("C:/Users/thatg/e2e-shots/_testworkdir")
            await page.wait_for_timeout(500)
            await page.get_by_text("确认并开始").first.click()
            await page.wait_for_timeout(3000)
            await screenshot(page, "02-after-confirm")
            body = await page.locator("body").inner_text()
            print(f"\n[2] After confirm: body preview: {body[:400]}")
        elif "第 1 步" in body or "Step 1" in body:
            print("\n[1b] Welcome shown directly (workdir already set)")
        elif "还没有工作流" in body:
            print("\n[1c] Dashboard shown directly")

        # ===== 3. Walk Welcome =====
        if "第 1 步" in body or "Step 1" in body:
            print("\n[3] Welcome step 1 detected")
            await screenshot(page, "03-welcome1")
            try:
                await page.get_by_text("跳过此步").first.click(timeout=3000)
                await page.wait_for_timeout(2000)
                await screenshot(page, "03a-welcome2")
            except Exception as e:
                print(f"  step 1 skip: {e}")
            try:
                await page.get_by_text("跳过，先到工作台").first.click(timeout=3000)
                await page.wait_for_timeout(2000)
                await screenshot(page, "03b-welcome3")
                await page.get_by_text("进入工作台").first.click(timeout=3000)
                await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"  step 2 skip: {e}")
        elif "还没有工作流" in body:
            print("\n[3] Welcome bypassed; on dashboard directly")
        else:
            print(f"\n[3] UNKNOWN state")

        # ===== 4. Empty dashboard =====
        await screenshot(page, "04-empty-dashboard")
        body = await page.locator("body").inner_text()
        print(f"\n[4] Empty dashboard: {body[:600]}")

        # ===== 5. Run sample workflow =====
        try:
            # Need to scroll the cmd bar into view if the sample button is below the fold
            sample_btn = page.get_by_text("或试试示例任务").first
            await sample_btn.scroll_into_view_if_needed()
            await sample_btn.click(timeout=3000)
            await page.wait_for_timeout(800)
            await screenshot(page, "05-sample-submit")
            await page.wait_for_timeout(2000)
            await screenshot(page, "06-running-mid")
            await page.wait_for_timeout(3500)
            await screenshot(page, "07-running-late")
            await page.wait_for_timeout(2500)
            await screenshot(page, "08-running-done")
            body = await page.locator("body").inner_text()
            print(f"\n[5] Post-workflow: {body[:1500]}")
        except Exception as e:
            print(f"\n[5] workflow run fail: {e}")
            # Try clicking the cmd bar instead
            try:
                await page.locator("input[placeholder*='POST']").first.scroll_into_view_if_needed()
                await page.locator("input[placeholder*='POST']").first.fill("实现一个登录接口")
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(2000)
                await screenshot(page, "05b-cmd-submit")
                await page.wait_for_timeout(3500)
                await screenshot(page, "06-cmd-running")
            except Exception as e2:
                print(f"  cmd also fail: {e2}")

        # ===== 6. Settings modal =====
        try:
            await page.get_by_text("设置").first.click(timeout=3000)
            await page.wait_for_timeout(1500)
            await screenshot(page, "09-settings")
            await page.evaluate("document.querySelectorAll('main').forEach(m => m.scrollTop = 500)")
            await page.wait_for_timeout(500)
            await screenshot(page, "09b-settings-scrolled")
            await page.get_by_text("添加 AI 供应商").first.click(timeout=2000)
            await page.wait_for_timeout(1500)
            await screenshot(page, "10-add-provider")
            await page.keyboard.press("Escape")
        except Exception as e:
            print(f"\n[6] settings fail: {e}")

        # ===== 7. Bug search with mocked matches =====
        try:
            await page.wait_for_timeout(800)
            bug_input = page.locator("input[placeholder*='FE-']").first
            await bug_input.fill("FE-3a7b9c2d")
            await page.wait_for_timeout(500)
            await page.screenshot(path=str(OUT / "11-bug-typed.png"))
            await bug_input.press("Enter")
            await page.wait_for_timeout(1500)
            await screenshot(page, "12-bug-results")
            await page.keyboard.press("Escape")
        except Exception as e:
            print(f"\n[7] bug search fail: {e}")

        # ===== 8. Long command =====
        try:
            await page.wait_for_timeout(800)
            cmd = page.locator("input[placeholder*='POST']").first
            long_text = "实现一个支持 JWT 鉴权的完整登录流程 " + ("包含 refresh token 鉴权 " * 30) + "并写完整的单元测试用例"
            await cmd.fill(long_text)
            await page.wait_for_timeout(500)
            await screenshot(page, "13-long-cmd")
            # Try submitting
            await cmd.press("Enter")
            await page.wait_for_timeout(500)
            await screenshot(page, "14-long-cmd-submit")
        except Exception as e:
            print(f"\n[8] long cmd fail: {e}")

        # ===== 9. Empty cmd =====
        try:
            cmd = page.locator("input[placeholder*='POST']").first
            await cmd.fill("")
            await page.wait_for_timeout(500)
            await cmd.press("Enter")
            await page.wait_for_timeout(500)
            await screenshot(page, "15-empty-cmd")
        except Exception as e:
            print(f"\n[9] empty cmd fail: {e}")

        print("\n=== CONSOLE/PAGE ERRORS ===")
        for e in errors[:30]:
            print(f"  {e[:200]}")

        await browser.close()

asyncio.run(main())