from __future__ import annotations

import argparse
from pathlib import Path

from common import ProjectScope, default_db_path, now_iso, open_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bind an artifact ID to a file/anchor location.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project-key", required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--artifact-type", required=True)
    parser.add_argument("--source-path", required=True)
    parser.add_argument("--source-anchor", default="")
    parser.add_argument("--stage-or-lane", default="")
    parser.add_argument("--status", default="draft")
    parser.add_argument("--language-role", default="runtime-canonical-en")
    parser.add_argument("--canonical-of", default="")
    parser.add_argument("--db-path", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    scope = ProjectScope(project_key=args.project_key, project_root=project_root)
    db_path = Path(args.db_path).resolve() if args.db_path else default_db_path(project_root)
    conn = open_db(db_path)

    existing = conn.execute(
        "SELECT * FROM artifacts WHERE project_scope = ? AND artifact_id = ?",
        (scope.scope_id, args.artifact_id),
    ).fetchone()
    now = now_iso()

    if existing:
        conn.execute(
            "UPDATE artifacts SET artifact_type=?, stage_or_lane=?, status=?, source_path=?, source_anchor=?, language_role=?, canonical_of=?, updated_at=? WHERE project_scope=? AND artifact_id=?",
            (
                args.artifact_type,
                args.stage_or_lane,
                args.status,
                args.source_path,
                args.source_anchor,
                args.language_role,
                args.canonical_of or None,
                now,
                scope.scope_id,
                args.artifact_id,
            ),
        )
    else:
        conn.execute(
            "INSERT INTO artifacts (project_scope, artifact_id, artifact_type, stage_or_lane, status, source_path, source_anchor, language_role, canonical_of, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                scope.scope_id,
                args.artifact_id,
                args.artifact_type,
                args.stage_or_lane,
                args.status,
                args.source_path,
                args.source_anchor,
                args.language_role,
                args.canonical_of or None,
                now,
                now,
            ),
        )

    conn.commit()
    print(f"bound {args.artifact_id} -> {args.source_path}#{args.source_anchor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
