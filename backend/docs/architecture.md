# Backend MVP architecture

```mermaid
flowchart LR
    FE[Next.js frontend] -->|REST /api/v1| API[FastAPI]
    FE -->|poll job_id| API
    API --> PG[(PostgreSQL: six tables)]
    API --> FS[(Incident file storage)]
    WORKER[Analysis worker] -->|lease and heartbeat| PG
    WORKER --> FS
    WORKER -->|Pass 1 and Pass 2| VLM[Vision language model]
    WORKER -->|report, evidence, audit| PG
```

Frontend source has implemented most v1.1 service changes: job polling, IDs/envelopes, versioned PATCH and evidence time conversion. Audit envelope/rendering still has gaps; browser E2E remains unverified. See [frontend integration](../../frontend/docs/api-integration.md) and the [public contract](../../api/docs/backend-contract-v1.1.md). Evidence storage paths are internal; local demo media routes serve video and evidence by `incident_id` and `evidence_id`.
