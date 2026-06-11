from __future__ import annotations

import argparse
from pathlib import Path

from common import ProjectScope, default_db_path, now_iso, open_db


ALLOWED_LINK_TYPES = {"depends_on", "feeds"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a link between two registered artifacts.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project-key", required=True)
    parser.add_argument("--from-artifact-id", required=True)
    parser.add_argument("--to-artifact-id", required=True)
    parser.add_argument("--link-type", required=True, choices=sorted(ALLOWED_LINK_TYPES))
    parser.add_argument("--source-path", default="")
    parser.add_argument("--evidence-anchor", default="")
    parser.add_argument("--db-path", default="")
    return parser.parse_args()


def require_artifact(conn, project_scope: str, artifact_id: str) -> None:
    row = conn.execute(
        "SELECT artifact_id FROM artifacts WHERE project_scope = ? AND artifact_id = ?",
        (project_scope, artifact_id),
    ).fetchone()
    if not row:
        raise SystemExit(f"Artifact not found in scope: {artifact_id}")


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    scope = ProjectScope(project_key=args.project_key, project_root=project_root)
    db_path = Path(args.db_path).resolve() if args.db_path else default_db_path(project_root)
    conn = open_db(db_path)

    require_artifact(conn, scope.scope_id, args.from_artifact_id)
    require_artifact(conn, scope.scope_id, args.to_artifact_id)

    existing = conn.execute(
        "SELECT id FROM links WHERE project_scope = ? AND from_artifact_id = ? AND to_artifact_id = ? AND link_type = ?",
        (scope.scope_id, args.from_artifact_id, args.to_artifact_id, args.link_type),
    ).fetchone()
    if existing:
        print(f"link already exists: {args.from_artifact_id} -[{args.link_type}]-> {args.to_artifact_id}")
        return 0

    conn.execute(
        "INSERT INTO links (project_scope, from_artifact_id, to_artifact_id, link_type, source_path, evidence_anchor, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            scope.scope_id,
            args.from_artifact_id,
            args.to_artifact_id,
            args.link_type,
            args.source_path or None,
            args.evidence_anchor or None,
            now_iso(),
        ),
    )
    conn.commit()
    print(f"linked {args.from_artifact_id} -[{args.link_type}]-> {args.to_artifact_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
