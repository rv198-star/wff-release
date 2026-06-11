from __future__ import annotations

import argparse
from pathlib import Path

from common import ProjectScope, default_db_path, now_iso, open_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bind a Chinese audit mirror to an English canonical artifact.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project-key", required=True)
    parser.add_argument("--canonical-id", required=True)
    parser.add_argument("--source-path", required=True)
    parser.add_argument("--source-anchor", default="")
    parser.add_argument("--db-path", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    scope = ProjectScope(project_key=args.project_key, project_root=project_root)
    db_path = Path(args.db_path).resolve() if args.db_path else default_db_path(project_root)
    conn = open_db(db_path)

    canonical = conn.execute(
        "SELECT artifact_id, artifact_type, stage_or_lane, status FROM artifacts WHERE project_scope = ? AND artifact_id = ?",
        (scope.scope_id, args.canonical_id),
    ).fetchone()
    if canonical is None:
        raise SystemExit(f"Canonical artifact not found: {args.canonical_id}")

    mirror_id = f"{args.canonical_id}-ZH"
    now = now_iso()
    existing = conn.execute(
        "SELECT artifact_id FROM artifacts WHERE project_scope = ? AND artifact_id = ?",
        (scope.scope_id, mirror_id),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE artifacts SET source_path=?, source_anchor=?, language_role='audit-mirror-zh', canonical_of=?, updated_at=? WHERE project_scope=? AND artifact_id=?",
            (args.source_path, args.source_anchor, args.canonical_id, now, scope.scope_id, mirror_id),
        )
    else:
        conn.execute(
            "INSERT INTO artifacts (project_scope, artifact_id, artifact_type, stage_or_lane, status, source_path, source_anchor, language_role, canonical_of, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                scope.scope_id,
                mirror_id,
                canonical["artifact_type"],
                canonical["stage_or_lane"],
                canonical["status"],
                args.source_path,
                args.source_anchor,
                "audit-mirror-zh",
                args.canonical_id,
                now,
                now,
            ),
        )
    conn.commit()
    print(f"bound_mirror {mirror_id} -> {args.canonical_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
