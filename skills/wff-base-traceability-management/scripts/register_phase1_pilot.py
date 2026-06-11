from __future__ import annotations

import argparse
from pathlib import Path

from common import ProjectScope, default_db_path, now_iso, open_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Register Phase-1 pilot links for four coarse-grained artifacts.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project-key", required=True)
    parser.add_argument("--ids", required=True, help="Comma-separated IDs in Stage-01..04 order")
    parser.add_argument("--db-path", default="")
    return parser.parse_args()


def ensure_artifact(conn, project_scope: str, artifact_id: str) -> None:
    row = conn.execute(
        "SELECT artifact_id FROM artifacts WHERE project_scope = ? AND artifact_id = ?",
        (project_scope, artifact_id),
    ).fetchone()
    if row is None:
        raise SystemExit(f"Artifact not found for pilot registration: {artifact_id}")


def create_link(conn, project_scope: str, from_id: str, to_id: str, link_type: str) -> None:
    existing = conn.execute(
        "SELECT id FROM links WHERE project_scope = ? AND from_artifact_id = ? AND to_artifact_id = ? AND link_type = ?",
        (project_scope, from_id, to_id, link_type),
    ).fetchone()
    if existing:
        return
    conn.execute(
        "INSERT INTO links (project_scope, from_artifact_id, to_artifact_id, link_type, source_path, evidence_anchor, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (project_scope, from_id, to_id, link_type, None, None, now_iso()),
    )


def main() -> int:
    args = parse_args()
    ids = [part.strip() for part in args.ids.split(",") if part.strip()]
    if len(ids) != 4:
        raise SystemExit("Phase-1 pilot requires exactly 4 IDs in Stage-01..04 order")

    project_root = Path(args.project_root).resolve()
    scope = ProjectScope(project_key=args.project_key, project_root=project_root)
    db_path = Path(args.db_path).resolve() if args.db_path else default_db_path(project_root)
    conn = open_db(db_path)

    for artifact_id in ids:
        ensure_artifact(conn, scope.scope_id, artifact_id)

    create_link(conn, scope.scope_id, ids[0], ids[1], "feeds")
    create_link(conn, scope.scope_id, ids[1], ids[2], "feeds")
    create_link(conn, scope.scope_id, ids[2], ids[3], "feeds")

    create_link(conn, scope.scope_id, ids[1], ids[0], "depends_on")
    create_link(conn, scope.scope_id, ids[2], ids[1], "depends_on")
    create_link(conn, scope.scope_id, ids[3], ids[2], "depends_on")

    conn.commit()
    print(f"phase1_pilot_registered ids={','.join(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
