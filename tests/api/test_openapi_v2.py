import json
from pathlib import Path

from api.export_v2_contract import contract


def test_pinned_v2_contract_matches_routes_and_models():
    assert json.loads(Path("api/docs/openapi-v2.json").read_text(encoding="utf-8")) == contract()
