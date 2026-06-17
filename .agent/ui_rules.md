# UI Rules

> Rules for the React 19 / Tailwind v4 / shadcn/ui front-end.

**Version:** v0.1
**Enforced by:** ESLint, `prettier --check`, manual review
**Last updated:** 2026-06-18
**See also:** [UI_GUIDELINES.md](../docs/UI_GUIDELINES.md)

---

## 1. Component model

* **Function components only.** No class components.
* **One component per file.** File name = component name.
* **Default export is the component.** Named exports for utilities.
* **Co-locate styles, tests, and stories** with the component:

  ```
  Button/
    index.tsx          # the component
    Button.test.tsx    # vitest
    Button.stories.tsx # storybook (v0.2)
    Button.module.css  # if needed; usually Tailwind only
  ```

* **No `React.FC`.** Use plain function signatures.
* **No `defaultProps`.** Use destructuring with defaults.

---

## 2. Props

* **Props are typed via `interface`, not `type`** (better error messages).
* **Props are readonly.** No mutations.
* **Spread `...rest` props** when wrapping a DOM element.
* **No `any`.** Use `unknown` + a Zod schema if needed.
* **Callbacks are typed:** `(e: MouseEvent) => void` not `Function`.
* **Optional props end with `?`:** `disabled?: boolean`.

---

## 3. State

* **Server state** → TanStack Query. Always.
* **Local UI state** → Zustand store (per-zone) or `useState`.
* **Form state** → React Hook Form + Zod.
* **No Redux. Ever.**
* **No `useEffect` for data fetching.** Use TanStack Query.
* **`useEffect` for sync with external systems only** (DOM, Tauri
  IPC, event bus).

---

## 4. Styling

* **Tailwind utility classes only** (no inline `style={}` except
  for dynamic values that can't be expressed as utilities).
* **Design tokens from `UI_GUIDELINES.md §4`** — never hardcode
  hex colors.
* **Dark mode first** (mission control aesthetic); light mode in
  v0.2.
* **`cn()` utility for conditional classes** (clsx + tailwind-merge).
* **No `!important`** unless overriding a third-party style.
* **No `@apply` in component files.** Use utilities inline.

---

## 5. Accessibility (a11y)

This is a hard requirement, not a nice-to-have.

* **Every interactive element is keyboard-reachable.**
* **Every interactive element has an `aria-label` or visible text.**
* **Color is never the only signal.** Add an icon or text.
* **Focus rings are visible** (never `outline: none` without a
  replacement).
* **`prefers-reduced-motion`** is honored on every animation.
* **WCAG 2.1 AA contrast** on all text/background pairs.
* **All form fields have `<label>`** or `aria-label`.
* **Live regions** for console + reasoning bubbles (`aria-live="polite"`).

---

## 6. Performance

* **`React.memo`** for components that render often with the same props.
* **`useMemo` / `useCallback`** only when measured to help.
* **Virtualize long lists** (`@tanstack/react-virtual`).
* **Code-split by route** (React Router lazy).
* **No barrel files** in hot paths (`import { Button } from '@/ui'`
  pulls everything). Use direct paths.
* **Images use `next/image` style** sizing (or `<img loading="lazy">`).

---

## 7. Routing

* **React Router v6+** with the data router.
* **Routes are typed** with a single `routes.ts`.
* **No nested route definitions in components.**
* **404 page** with a useful message and a "back to home" link.

---

## 8. Forms

* **React Hook Form + Zod** for any form > 1 field.
* **Zod schema is the single source of truth** for both validation
  and types (`z.infer<typeof schema>`).
* **Error messages are user-friendly**, not raw Zod errors.
* **Submit button shows loading state** (`isSubmitting`).
* **Successful submit shows a toast** and either resets the form
  or navigates away.

---

## 9. Error handling

* **Error boundaries** at the route level.
* **`fallback` UI** explains what happened + offers "Reload" / "Back".
* **Console errors are reported to Rust** via Tauri IPC (for
  the bottom console to display).
* **User-facing errors are friendly.** "Something went wrong
  loading this. Reload?" — not "TypeError: undefined".

---

## 10. Internationalization (i18n)

* **No hardcoded strings in components.** Use `t('key')`.
* **All strings live in `packages/ui/src/i18n/<locale>.json`.**
* **`pnpm i18n:extract`** regenerates the keys; **CI fails** on
  missing keys.
* **v0.1 ships English only**; **v0.3 ships Simplified Chinese**.

---

## 11. Testing

* **Vitest** for unit + component tests.
* **Playwright** for E2E.
* **MSW** for mocking Tauri IPC + WebSocket in tests.
* **Tests live next to the component** (see §1).
* **One behavior per test** (see [coding_rules.md §7](./coding_rules.md)).
* **Snapshot tests for pure presentational components** (Button,
  Card). Not for behavior.

---

## 12. Dependencies

* **shadcn/ui** is the default component library. New components
  are added to `packages/ui/` via `npx shadcn@latest add <name>`.
* **Framer Motion** for animations; **Lottie** if Framer can't
  do it.
* **Xterm.js** for the console (no replacement).
* **Monaco** for read-only code/diff views.
* **React Flow** for the plan graph.
* **No new UI library** without Thatgfsj's sign-off.

---

## 13. Anti-patterns (forbidden)

* ❌ `useEffect` to derive state — derive it during render.
* ❌ Prop drilling > 3 levels — use Zustand or context.
* ❌ Inline event handlers with side effects — extract a function.
* ❌ `dangerouslySetInnerHTML`.
* ❌ `window.alert` / `window.confirm` — use the shadcn/ui modal.
* ❌ Copy-pasted components — extract a shared component.
* ❌ Hardcoded color/spacing — use design tokens.
* ❌ `console.log` left in production — use a logger that ships to
  the bottom console.
* ❌ Magic numbers — name them or use a constant.

---

**Rules end. Run `pnpm lint` before every commit.**
