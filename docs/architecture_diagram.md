# RAV18 backend MVP architecture

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

The frontend currently uses an older contract. The required service-layer changes are listed in [backend-contract-v1.1.md](backend-contract-v1.1.md). The storage path returned for evidence is internal; a media-access route or signed URL remains to be specified.
