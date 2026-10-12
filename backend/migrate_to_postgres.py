"""Copy a consistent SQLite snapshot to PostgreSQL without overwriting reviews."""
import argparse
import json
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import URL, make_url

from backend.models import tables_v2  # noqa: F401
from backend.models.tables import Base


def canonical(value):
    if isinstance(value, datetime):
        return (value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)).isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [canonical(item) for item in value]
    return value


def copy_records(source, target, *, apply=True, batch_size=500):
    tables = Base.metadata.sorted_tables
    counts = {}
    with source.connect() as reader, target.begin() as writer:
        for name in ("jobs", "jobs_v2"):
            table = Base.metadata.tables[name]
            if reader.scalar(select(func.count()).select_from(table).where(table.c.status.in_(["queued", "running"]))):
                raise ValueError("Source has active jobs; finish or cancel them before migration")
        for table in tables:
            pk = list(table.primary_key.columns)
            if len(pk) != 1:
                raise ValueError(f"Unsupported primary key: {table.name}")
            rows = reader.execute(select(table)).mappings()
            summary = {"source": 0, "inserted": 0, "existing": 0}
            while batch := rows.fetchmany(batch_size):
                records = [dict(row) for row in batch]
                existing = {row[pk[0].name]: dict(row) for row in writer.execute(select(table).where(pk[0].in_([row[pk[0].name] for row in records]))).mappings()}
                new = []
                for row in records:
                    previous = existing.get(row[pk[0].name])
                    if previous is not None:
                        if canonical(previous) != canonical(row):
                            raise ValueError(f"Migration conflict in {table.name}: existing record differs")
                        summary["existing"] += 1
                    else:
                        new.append(row)
                if new and apply:
                    writer.execute(table.insert(), new)
                summary["source"] += len(records)
                summary["inserted"] += len(new)
            counts[table.name] = summary
        if apply and target.dialect.name == "postgresql":
            # Preserve imported integer IDs and advance their PostgreSQL sequences.
            for table in tables:
                pk = list(table.primary_key.columns)[0]
                sequence = writer.scalar(text("SELECT pg_get_serial_sequence(:table, :column)"), {"table": table.name, "column": pk.name})
                if sequence:
                    maximum = writer.scalar(select(func.max(pk)))
                    if maximum is not None:
                        writer.execute(text("SELECT setval(CAST(:sequence AS regclass), :maximum, true)"), {"sequence": sequence, "maximum": maximum})
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--apply", action="store_true", help="Commit data; otherwise validate and show counts only")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    from backend.config import get_settings
    target_url = get_settings().database_url
    if make_url(target_url).get_backend_name() != "postgresql":
        raise ValueError("DATABASE_URL must target PostgreSQL")
    if not args.source.is_file():
        raise ValueError("Source SQLite database does not exist")
    target = create_engine(target_url, pool_pre_ping=True)
    with tempfile.TemporaryDirectory() as directory:
        snapshot = Path(directory) / "source.db"
        with sqlite3.connect(args.source.resolve().as_uri() + "?mode=ro", uri=True) as original, sqlite3.connect(snapshot) as destination:
            original.backup(destination)
        source = create_engine(URL.create("sqlite", database=str(snapshot)))
        try:
            known = set(Base.metadata.tables) | {"alembic_version"}
            with source.connect() as reader, target.connect() as writer:
                if reader.scalar(text("SELECT version_num FROM alembic_version")) != writer.scalar(text("SELECT version_num FROM alembic_version")):
                    raise ValueError("Schema versions differ; run Alembic upgrade head first")
                for name in set(inspect(source).get_table_names()) - known:
                    if reader.scalar(text('SELECT count(*) FROM "' + name.replace('"', '""') + '"')):
                        raise ValueError(f"Unknown nonempty source table: {name}")
            result = {"applied": args.apply, "tables": copy_records(source, target, apply=args.apply)}
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result, indent=2))
        finally:
            source.dispose()
            target.dispose()


if __name__ == "__main__":
    main()
