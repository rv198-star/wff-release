from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    SCHEMA_VERSION,
    SUPPORTED_ARTIFACT_TYPES,
    ProjectScope,
    default_db_path,
    load_schema_sql,
    now_iso,
    open_db,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a project-bound traceability registry.")
    parser.add_argument("--project-root", required=True, help="Business project root path")
    parser.add_argument("--project-key", required=True, help="Project key used for registry scope")
    parser.add_argument("--project-label", default="", help="Optional human-readable project label")
    parser.add_argument("--db-path", default="", help="Optional explicit SQLite path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    scope = ProjectScope(project_key=args.project_key, project_root=project_root)
    db_path = Path(args.db_path).resolve() if args.db_path else default_db_path(project_root)

    conn = open_db(db_path)
    schema_sql = load_schema_sql(Path(__file__).resolve().parent)
    conn.executescript(schema_sql)

    existing = conn.execute("SELECT project_key, project_root FROM registry_meta LIMIT 1").fetchone()
    if existing:
        if existing["project_key"] != scope.project_key or Path(existing["project_root"]).resolve() != project_root:
            raise SystemExit(
                f"Registry already initialized for another project: {existing['project_key']} @ {existing['project_root']}"
            )
        print(f"Registry already initialized: {db_path}")
        print(f"project_scope={scope.scope_id}")
        return 0

    now = now_iso()
    conn.execute(
        "INSERT INTO registry_meta (project_key, project_root, project_label, schema_version, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (scope.project_key, str(project_root), args.project_label, SCHEMA_VERSION, now, now),
    )
    for artifact_type in SUPPORTED_ARTIFACT_TYPES:
        conn.execute(
            "INSERT INTO id_counters (project_scope, artifact_type, next_value, updated_at) VALUES (?, ?, ?, ?)",
            (scope.scope_id, artifact_type, 1, now),
        )
    conn.commit()

    print(f"Registry initialized: {db_path}")
    print(f"project_scope={scope.scope_id}")
    print(f"schema_version={SCHEMA_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
