"""Run real API auth against an isolated local preview database (no worker)."""
import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo))
    os.chdir(repo)
    root = repo / ".tmp" / "auth-workspace"
    root.mkdir(parents=True, exist_ok=True)
    os.environ.update(DATABASE_URL=f"sqlite:///{(root / 'preview.db').as_posix()}", DATABASE_CLOUD="false",
                      INCIDENT_STORAGE_DIR=str(root / "storage"), APP_ENV="development", AUTH_COOKIE_SECURE="false",
                      CORS_ORIGINS="http://127.0.0.1:3000,http://localhost:3000")
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import select

    from backend.config import get_settings
    from backend.db import get_session_factory, session_scope
    from backend.models.auth import User
    from backend.services.auth import hash_password
    get_settings.cache_clear()
    get_session_factory.cache_clear()
    config = Config(str(repo / "alembic.ini"))
    command.upgrade(config, "head")
    # These branch-fixture accounts exist only in this isolated preview DB.
    with session_scope() as session:
        for name, role in [("operator", "engineer"), ("reviewer", "reviewer"), ("admin", "admin")]:
            email = f"{name}@example.com"
            if not session.scalar(select(User).where(User.email == email)):
                session.add(User(email=email, display_name=name.title(), roles=[role],
                                 password_hash=hash_password("cD4!yz"), must_change_password=False))
    print("Isolated preview prepared: operator@example.com, reviewer@example.com, admin@example.com")
    if not args.prepare_only:
        import uvicorn
        uvicorn.run("api.main:app", host="127.0.0.1", port=args.port, proxy_headers=False)


if __name__ == "__main__":
    main()
