from __future__ import annotations

import argparse
from pathlib import Path

from common import ProjectScope, default_db_path, now_iso, open_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update bound artifacts after a file move/rename.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project-key", required=True)
    parser.add_argument("--old-path", required=True)
    parser.add_argument("--new-path", required=True)
    parser.add_argument("--db-path", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    scope = ProjectScope(project_key=args.project_key, project_root=project_root)
    db_path = Path(args.db_path).resolve() if args.db_path else default_db_path(project_root)
    conn = open_db(db_path)

    now = now_iso()
    result = conn.execute(
        "UPDATE artifacts SET source_path = ?, updated_at = ? WHERE project_scope = ? AND source_path = ?",
        (args.new_path, now, scope.scope_id, args.old_path),
    )
    conn.commit()
    print(f"updated_bindings={result.rowcount}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
