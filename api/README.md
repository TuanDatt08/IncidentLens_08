# API — HTTP boundary của IncidentLens

Role API sở hữu routes, request/response contracts, errors, CORS, status codes và OpenAPI. Nghiệp vụ/persistence ở [backend](../backend/README.md).

- [AGENTS](AGENTS.md)
- [Contract v1.1](docs/backend-contract-v1.1.md)
- [Routes và integration](docs/routes.md)
- [Development](docs/development.md)
- [Work items](docs/work-items.md)

Entry point: `api.main:app`; active routes `/api/v1` trong `incidents.py`, `jobs.py`, `reports.py`, `evidence.py`, `audit.py`, `media.py`. `routes.py` là template router không được mount. `/api/v2` mới là SPEC trong tools, chưa implementation.
