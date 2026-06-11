from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ProjectScope, default_db_path, open_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report current registry contents.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project-key", required=True)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--db-path", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    scope = ProjectScope(project_key=args.project_key, project_root=project_root)
    db_path = Path(args.db_path).resolve() if args.db_path else default_db_path(project_root)
    conn = open_db(db_path)
    meta = conn.execute(
        "SELECT project_key, project_root, project_label, schema_version FROM registry_meta LIMIT 1"
    ).fetchone()

    artifacts = [dict(row) for row in conn.execute(
        "SELECT artifact_id, artifact_type, stage_or_lane, status, source_path, source_anchor, language_role, canonical_of FROM artifacts WHERE project_scope = ? ORDER BY artifact_id",
        (scope.scope_id,),
    ).fetchall()]
    links = [dict(row) for row in conn.execute(
        "SELECT from_artifact_id, to_artifact_id, link_type FROM links WHERE project_scope = ? ORDER BY id",
        (scope.scope_id,),
    ).fetchall()]

    if args.format == "json":
        print(
            json.dumps(
                {
                    "project_key": scope.project_key,
                    "project_root": str(project_root),
                    "project_scope": scope.scope_id,
                    "trace_registry_root": str(db_path.parent),
                    "registry_db_path": str(db_path),
                    "project_label": meta["project_label"] if meta else "",
                    "schema_version": meta["schema_version"] if meta else "",
                    "artifact_count": len(artifacts),
                    "link_count": len(links),
                    "artifacts": artifacts,
                    "links": links,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(f"project_scope={scope.scope_id}")
    print(f"trace_registry_root={db_path.parent}")
    print(f"registry_db_path={db_path}")
    print("artifacts:")
    for artifact in artifacts:
        anchor = f"#{artifact['source_anchor']}" if artifact["source_anchor"] else ""
        print(f"- {artifact['artifact_id']} [{artifact['artifact_type']}] {artifact['source_path']}{anchor}")
    print("links:")
    for link in links:
        print(f"- {link['from_artifact_id']} -[{link['link_type']}]-> {link['to_artifact_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
