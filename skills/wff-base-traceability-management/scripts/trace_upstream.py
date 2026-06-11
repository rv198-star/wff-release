from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from common import ProjectScope, default_db_path, open_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trace upstream dependencies for an artifact.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project-key", required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--db-path", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    scope = ProjectScope(project_key=args.project_key, project_root=project_root)
    db_path = Path(args.db_path).resolve() if args.db_path else default_db_path(project_root)
    conn = open_db(db_path)

    rows = conn.execute(
        "SELECT from_artifact_id, to_artifact_id FROM links WHERE project_scope = ? AND link_type = 'depends_on'",
        (scope.scope_id,),
    ).fetchall()
    upstream_map: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        upstream_map[row["from_artifact_id"]].append(row["to_artifact_id"])

    seen: set[str] = set()

    def walk(artifact_id: str, depth: int = 0) -> None:
        indent = "  " * depth
        print(f"{indent}- {artifact_id}")
        if artifact_id in seen:
            print(f"{indent}  (cycle-detected, stop)")
            return
        seen.add(artifact_id)
        for parent in upstream_map.get(artifact_id, []):
            walk(parent, depth + 1)

    walk(args.artifact_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
