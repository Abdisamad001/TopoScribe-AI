# Local Packet Tracer API proxy

These Next.js route handlers (`/api/pt/*`) are **local-only**. They must not ship to production.

- Canonical source: `frontend/local/pt-api/`
- Activated for `next dev` as `src/app/api/pt/` (gitignored mirror)
- Removed before `npm run build` so `output: 'export'` can emit `out/`

Use `npm run dev` (enables routes) or `npm run build` (disables routes, static export).
