# IncidentLens frontend

Next.js MVP for RAV-18 IncidentLens. Backend logic lives in `backend/`; the local
FastAPI layer lives in the `api/` directory.

## Run locally

```bash
cd frontend
npm install
npm run dev
```

The default mode is mock mode. Copy `.env.example` to `.env.local` to configure
it explicitly. Set `NEXT_PUBLIC_USE_MOCK_API=false` and point
`NEXT_PUBLIC_API_BASE_URL` at the FastAPI API when the IncidentLens endpoints are
available.

## MVP routes

- `/incidents` — incident list
- `/incidents/new` — video/log upload
- `/incidents/[id]/processing` — analysis progress
- `/incidents/[id]` — review, evidence, editable report and workflow actions

The mock layer uses TypeScript v1 interfaces. Most v1.1 API integration is in
place; audit envelope/rendering remains incomplete. See
[integration details](docs/api-integration.md).

## Role documentation

- [AGENTS.md](AGENTS.md) — trách nhiệm và kiểm tra của Frontend.
- [docs/README.md](docs/README.md) — implementation, integration, development và work items.
- [Shared SPEC/ADR/planning/tasks](../tools/README.md) — nguồn chuẩn toàn dự án.
