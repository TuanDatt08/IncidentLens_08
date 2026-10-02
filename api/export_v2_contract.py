"""Export the checked-in V2 OpenAPI contract without contacting a provider."""

import json
from pathlib import Path


def contract() -> dict:
    from api.main import app
    schema = app.openapi()
    return {"openapi": schema["openapi"], "info": {"title": "IncidentLens V2", "version": "2.0"}, "paths": {path: routes for path, routes in schema["paths"].items() if path.startswith("/api/v2/")}, "components": schema["components"]}


if __name__ == "__main__":
    Path("api/docs/openapi-v2.json").write_text(json.dumps(contract(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
