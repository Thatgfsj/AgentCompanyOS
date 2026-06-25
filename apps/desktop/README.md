# @flowntier/desktop

Tauri 2 + React 19 desktop shell.

## Develop

```bash
pnpm tauri:dev
```

This will start Vite on port 1420 and launch the Tauri webview.

## Build

```bash
pnpm tauri:build
```

Produces a signed/unsigned bundle for the current OS in
`src-tauri/target/release/bundle/`.

## Layout

```
apps/desktop/
├── index.html              ← Vite entry
├── src/                    ← React + TS
│   ├── App.tsx
│   ├── zones/              ← Z1-Z5 components
│   ├── main.tsx
│   └── index.css
├── src-tauri/              ← Rust side
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── capabilities/
│   └── src/
└── vite.config.ts
```

See `history/docs/UI_GUIDELINES.md` for the Mission Control layout this implements (archived in v0.3).
