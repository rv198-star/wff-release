from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ProjectScope, default_db_path, open_db


def decode_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if str(item).strip()]


def table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return bool(row)


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
    claim_evidence_refs = []
    if table_exists(conn, "claim_evidence_refs"):
        for row in conn.execute(
            "SELECT artifact_id, block_id, view_id, rendered_claim_refs_json, source_claim_refs_json, proposed_claim_refs_json, audit_status, artifact_version, artifact_hash, claim_surface_version, claim_surface_hash FROM claim_evidence_refs WHERE project_scope = ? ORDER BY artifact_id, block_id, view_id",
            (scope.scope_id,),
        ).fetchall():
            claim_evidence_refs.append(
                {
                    "artifact_id": row["artifact_id"],
                    "block_id": row["block_id"],
                    "view_id": row["view_id"] or "",
                    "rendered_claim_refs": decode_json_list(row["rendered_claim_refs_json"]),
                    "source_claim_refs": decode_json_list(row["source_claim_refs_json"]),
                    "proposed_claim_refs": decode_json_list(row["proposed_claim_refs_json"]),
                    "audit_status": row["audit_status"],
                    "artifact_version": row["artifact_version"] or "",
                    "artifact_hash": row["artifact_hash"] or "",
                    "claim_surface_version": row["claim_surface_version"] or "",
                    "claim_surface_hash": row["claim_surface_hash"] or "",
                }
            )

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
                    "claim_evidence_ref_count": len(claim_evidence_refs),
                    "artifacts": artifacts,
                    "links": links,
                    "claim_evidence_refs": claim_evidence_refs,
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
    print("claim_evidence_refs:")
    for evidence in claim_evidence_refs:
        print(
            f"- {evidence['artifact_id']}#{evidence['block_id']} [{evidence['audit_status']}] "
            f"rendered={','.join(evidence['rendered_claim_refs'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
