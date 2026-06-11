from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ProjectScope, default_db_path, load_schema_sql, now_iso, open_db


FORBIDDEN_TRUTH_FIELDS = {
    "accepted-claim",
    "accepted-claims",
    "backfilled-claims",
    "canonical-claim-index",
    "canonical-claims",
    "canonical-truth",
    "claim-index",
    "claim-text",
    "claims",
    "corrected-claims",
    "derived-accepted-claims",
}


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register claim-controlled render evidence without creating canonical claims."
    )
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project-key", required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--block-id", required=True)
    parser.add_argument("--view-id", default="")
    parser.add_argument("--rendered-claim-refs", default="")
    parser.add_argument("--source-claim-refs", default="")
    parser.add_argument("--proposed-claim-refs", default="")
    parser.add_argument("--audit-status", default="not-audited")
    parser.add_argument("--artifact-version", default="")
    parser.add_argument("--artifact-hash", default="")
    parser.add_argument("--claim-surface-version", default="")
    parser.add_argument("--claim-surface-hash", default="")
    parser.add_argument("--db-path", default="")

    forbidden_options = [f"--{field}" for field in sorted(FORBIDDEN_TRUTH_FIELDS)]
    parser.add_argument(
        "forbidden_truth_fields",
        nargs="*",
        help=f"Forbidden truth fields. Do not pass: {', '.join(forbidden_options)}",
    )
    args, unknown_args = parser.parse_known_args()
    for value in [*unknown_args, *args.forbidden_truth_fields]:
        normalized = value.lstrip("-").replace("_", "-")
        if normalized in FORBIDDEN_TRUTH_FIELDS:
            parser.error(f"registry evidence rows cannot accept canonical truth field: --{normalized}")
    if unknown_args:
        parser.error(f"unrecognized arguments: {' '.join(unknown_args)}")
    return args


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
    conn.executescript(load_schema_sql(Path(__file__).resolve().parent))

    require_artifact(conn, scope.scope_id, args.artifact_id)

    now = now_iso()
    rendered_claim_refs_json = json.dumps(parse_csv(args.rendered_claim_refs), ensure_ascii=False)
    source_claim_refs_json = json.dumps(parse_csv(args.source_claim_refs), ensure_ascii=False)
    proposed_claim_refs_json = json.dumps(parse_csv(args.proposed_claim_refs), ensure_ascii=False)
    existing = conn.execute(
        "SELECT id FROM claim_evidence_refs WHERE project_scope = ? AND artifact_id = ? AND block_id = ? AND COALESCE(view_id, '') = ?",
        (scope.scope_id, args.artifact_id, args.block_id, args.view_id),
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE claim_evidence_refs SET rendered_claim_refs_json=?, source_claim_refs_json=?, proposed_claim_refs_json=?, audit_status=?, artifact_version=?, artifact_hash=?, claim_surface_version=?, claim_surface_hash=?, updated_at=? WHERE id=?",
            (
                rendered_claim_refs_json,
                source_claim_refs_json,
                proposed_claim_refs_json,
                args.audit_status,
                args.artifact_version,
                args.artifact_hash,
                args.claim_surface_version,
                args.claim_surface_hash,
                now,
                existing["id"],
            ),
        )
    else:
        conn.execute(
            "INSERT INTO claim_evidence_refs (project_scope, artifact_id, block_id, view_id, rendered_claim_refs_json, source_claim_refs_json, proposed_claim_refs_json, audit_status, artifact_version, artifact_hash, claim_surface_version, claim_surface_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                scope.scope_id,
                args.artifact_id,
                args.block_id,
                args.view_id,
                rendered_claim_refs_json,
                source_claim_refs_json,
                proposed_claim_refs_json,
                args.audit_status,
                args.artifact_version,
                args.artifact_hash,
                args.claim_surface_version,
                args.claim_surface_hash,
                now,
                now,
            ),
        )

    conn.commit()
    print(f"registered claim evidence {args.artifact_id}#{args.block_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
