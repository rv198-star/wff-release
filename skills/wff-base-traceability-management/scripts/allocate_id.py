from __future__ import annotations

import argparse
from pathlib import Path

from common import SUPPORTED_ARTIFACT_TYPES, ProjectScope, default_db_path, now_iso, open_db


ALLOWED_TYPES = set(SUPPORTED_ARTIFACT_TYPES)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Allocate a canonical artifact ID within a project scope.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project-key", required=True)
    parser.add_argument("--artifact-type", required=True, choices=sorted(ALLOWED_TYPES))
    parser.add_argument("--db-path", default="")
    return parser.parse_args()


def next_id(conn, scope_id: str, artifact_type: str) -> str:
    now = now_iso()
    row = conn.execute(
        "SELECT next_value FROM id_counters WHERE project_scope = ? AND artifact_type = ?",
        (scope_id, artifact_type),
    ).fetchone()

    if row is None:
        conn.execute(
            "INSERT INTO id_counters (project_scope, artifact_type, next_value, updated_at) VALUES (?, ?, ?, ?)",
            (scope_id, artifact_type, 2, now),
        )
        conn.commit()
        return f"{artifact_type}-0001"

    current = int(row["next_value"])
    conn.execute(
        "UPDATE id_counters SET next_value = ?, updated_at = ? WHERE project_scope = ? AND artifact_type = ?",
        (current + 1, now, scope_id, artifact_type),
    )
    conn.commit()
    return f"{artifact_type}-{current:04d}"


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    scope = ProjectScope(project_key=args.project_key, project_root=project_root)
    db_path = Path(args.db_path).resolve() if args.db_path else default_db_path(project_root)
    conn = open_db(db_path)
    artifact_id = next_id(conn, scope.scope_id, args.artifact_type)
    print(artifact_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
