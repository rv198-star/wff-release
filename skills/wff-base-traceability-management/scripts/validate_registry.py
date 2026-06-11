from __future__ import annotations

import argparse
from pathlib import Path

from common import ProjectScope, default_db_path, open_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the traceability registry integrity.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project-key", required=True)
    parser.add_argument("--db-path", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    scope = ProjectScope(project_key=args.project_key, project_root=project_root)
    db_path = Path(args.db_path).resolve() if args.db_path else default_db_path(project_root)
    conn = open_db(db_path)

    issues: list[str] = []

    meta = conn.execute("SELECT project_key, project_root FROM registry_meta LIMIT 1").fetchone()
    if not meta:
        issues.append("missing registry_meta")
    else:
        if meta["project_key"] != scope.project_key or Path(meta["project_root"]).resolve() != project_root:
            issues.append("cross-project contamination: registry_meta does not match requested project scope")

    duplicate_ids = conn.execute(
        "SELECT artifact_id, COUNT(*) AS c FROM artifacts WHERE project_scope = ? GROUP BY artifact_id HAVING COUNT(*) > 1",
        (scope.scope_id,),
    ).fetchall()
    for row in duplicate_ids:
        issues.append(f"duplicate artifact id: {row['artifact_id']}")

    missing_canonical = conn.execute(
        "SELECT artifact_id, canonical_of FROM artifacts WHERE project_scope = ? AND language_role = 'audit-mirror-zh' AND canonical_of IS NULL",
        (scope.scope_id,),
    ).fetchall()
    for row in missing_canonical:
        issues.append(f"missing canonical_of for zh mirror: {row['artifact_id']}")

    broken_canonical = conn.execute(
        "SELECT a.artifact_id, a.canonical_of FROM artifacts a LEFT JOIN artifacts c ON a.project_scope = c.project_scope AND a.canonical_of = c.artifact_id WHERE a.project_scope = ? AND a.language_role = 'audit-mirror-zh' AND a.canonical_of IS NOT NULL AND c.artifact_id IS NULL",
        (scope.scope_id,),
    ).fetchall()
    for row in broken_canonical:
        issues.append(f"broken canonical_of link: {row['artifact_id']} -> {row['canonical_of']}")

    broken_links = conn.execute(
        "SELECT l.id, l.from_artifact_id, l.to_artifact_id, l.link_type FROM links l LEFT JOIN artifacts af ON l.project_scope = af.project_scope AND l.from_artifact_id = af.artifact_id LEFT JOIN artifacts at ON l.project_scope = at.project_scope AND l.to_artifact_id = at.artifact_id WHERE l.project_scope = ? AND (af.artifact_id IS NULL OR at.artifact_id IS NULL)",
        (scope.scope_id,),
    ).fetchall()
    for row in broken_links:
        issues.append(
            f"broken link[{row['id']}]: {row['from_artifact_id']} -[{row['link_type']}]-> {row['to_artifact_id']}"
        )

    if issues:
        print("VALIDATION: FAIL")
        for issue in issues:
            print(f"- {issue}")
        return 1

    artifact_count = conn.execute(
        "SELECT COUNT(*) AS c FROM artifacts WHERE project_scope = ?",
        (scope.scope_id,),
    ).fetchone()[0]
    link_count = conn.execute(
        "SELECT COUNT(*) AS c FROM links WHERE project_scope = ?",
        (scope.scope_id,),
    ).fetchone()[0]
    print("VALIDATION: PASS")
    print(f"artifacts={artifact_count}")
    print(f"links={link_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
