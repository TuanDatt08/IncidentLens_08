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

The mock layer uses the same TypeScript interfaces as the API layer. Provisional
schemas are documented with `NEED_CONFIRMATION` in `types/`.
