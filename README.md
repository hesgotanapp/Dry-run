# Dry Run — Forward Testing Tracker

A standalone PWA for logging and reviewing forward-testing (paper/sim trading) results. Manual entry only — no broker integration, no accounts, no backend. Everything is stored locally on-device via `localStorage`.

Built to run installed on an iPhone home screen (Safari → Share → Add to Home Screen).

## Structure

- `index.html` — the entire app: markup, styles, and logic (vanilla JS, no build step)
- `manifest.webmanifest` — PWA manifest
- `sw.js` — service worker (offline caching)
- `icons/` — app icons (apple-touch-icon, manifest icons, favicon)
- `fonts/` — self-hosted Plus Jakarta Sans + JetBrains Mono (variable woff2)
- `_devserver.js` — zero-dependency Node static file server, for local preview only
- `_generate-icons.ps1` — regenerates the icon set if you ever want to change the mark

## Local preview

```
node _devserver.js
```

Then open `http://localhost:8080`.

## Deploying

Any static host with HTTPS works (GitHub Pages, Netlify, Vercel, Cloudflare Pages, etc.) — just serve this folder as-is. HTTPS (or `localhost`) is required for the service worker to register, which is required for offline support and a clean "Add to Home Screen" install.
