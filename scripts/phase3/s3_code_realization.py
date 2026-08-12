"""Generation-only P3-S3 code/test realization from accepted S2 authority.

S2 owns implementation meaning. This module only materializes the accepted
slice decisions into backend/test files and evidence receipts. It never runs
those files and it never upgrades Trace/runtime state.
"""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from common.action_card_authority_projection import project_s3_durable_persistence_decisions
from common.agentic_decision_authority import canonical_digest, write_json_atomic
from phase3.contract_tools import generate_migration_sql, parse_schema_tables
from phase3.impl_context import load_phase2_source_texts
from phase3.schema_test_scaffolder import scaffold_schema_tests


S3_REALIZATION_SCHEMA = "wff.p3-s3-code-realization.v1"


class S3CodeRealizationError(ValueError):
    pass


def _strings(value: Any) -> list[str]:
    return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in values if item))


def _safe_target(output_dir: Path, raw_path: str) -> Path:
    relative = Path(str(raw_path or "").strip())
    if not str(relative) or relative.is_absolute() or ".." in relative.parts:
        raise S3CodeRealizationError(f"unsafe S3 target: {raw_path}")
    root = output_dir.resolve()
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise S3CodeRealizationError(f"S3 target escapes workspace: {raw_path}") from exc
    return target
def _file_digest(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()

def generate_s3_db_support(*, phase2_root: Path, output_dir: Path, authority: Mapping[str, Any] | None = None, delta_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Generate migration/static schema tests only; runtime SQL tests belong to execution/verification."""
    from phase3.agentic_implementation_authority import p3_schema_type_overrides
    esp_text, _, _ = load_phase2_source_texts(phase2_root)
    tables = parse_schema_tables(esp_text)
    overrides = p3_schema_type_overrides(authority or {}, delta_records) if authority else {}
    scalar_types = {"string": "text", "boolean": "boolean", "integer": "integer", "uuid": "uuid"}
    for table in tables:
        table_name = str(table.get("table_name") or "")
        for field in table.get("fields", []):
            key = f"{table_name}.{field.get('field_name', '')}"; logical_type = str(field.get("data_type") or "").strip().lower()
            lowered = overrides.get(key) or scalar_types.get(logical_type)
            if lowered: field["data_type"] = lowered
            elif logical_type in {"array", "object", "number"}: raise S3CodeRealizationError(f"non-mechanical schema type requires P3 Authority Delta: {key}:{logical_type}")
    for record in delta_records or []:
        additions = (record.get("resolution_payload") or {}).get("schema_field_additions", {}) if isinstance(record.get("resolution_payload"), Mapping) else {}
        for table_name, fields in additions.items():
            target = next((table for table in tables if table.get("table_name") == table_name), None)
            if target is None: raise S3CodeRealizationError(f"P3 schema addition references unknown table:{table_name}")
            known = {field.get("field_name") for field in target.get("fields", [])}
            for field in fields:
                if field.get("field_name") in known: continue
                item = dict(field); item["nullable"] = "yes" if field.get("nullable") is True else "no" if field.get("nullable") is False else field.get("nullable", "yes"); target["fields"].append(item)
    migration_path = output_dir / "db" / "migrations" / "001_initial_schema.sql"
    migration_path.parent.mkdir(parents=True, exist_ok=True); migration_path.write_text(generate_migration_sql(tables), encoding="utf-8")
    summary = {
        "artifact_kind": "phase3-impl-db-schema-report", "quality_gate": "generated-not-executed",
        "migration_path": str(migration_path), "table_count": len(tables),
        "schema_summary": scaffold_schema_tests(esp_text, output_dir / "tests" / "schema"),
        "sql_summary": {"output_dir": str(output_dir / "tests" / "sql"), "files_created": [], "count": 0,
                        "mode": "deferred-to-execution-verification", "reason": "runtime SQL tests require the execution-stage backend/DB harness"},
        "claim_ceiling": "migration/static schema tests generated; runtime SQL tests and DB proof require execution/verification",
    }
    write_json_atomic(output_dir / "db-schema-report.json", summary); return summary
def _identifier(value: str, fallback: str = "S3Realization") -> str:
    parts = re.findall(r"[A-Za-z0-9]+", value)
    result = "".join(part[:1].upper() + part[1:] for part in parts) or fallback
    return result if not result[0].isdigit() else f"S3{result}"


def _binding_payload(row: Mapping[str, Any], authority: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "sliceId": str(row.get("slice_id") or ""),
        "operationId": str(row.get("operation_id") or ""),
        "nonOperationRealizationId": str(row.get("non_operation_realization_id") or ""),
        "contractId": str(row.get("contract_id") or ""),
        "implementationDecisionId": str(authority.get("decision_id") or ""),
        "implementationDecisionDigest": str(authority.get("decision_digest") or ""),
        "semanticOwner": str(row.get("semantic_owner") or ""),
        "aggregate": str(row.get("aggregate") or ""),
        "domainInvariants": _strings(row.get("domain_invariants")),
        "stateMutation": str(row.get("state_mutation") or ""),
        "authorization": str(row.get("authorization") or ""),
        "failureBehavior": str(row.get("failure_behavior") or ""),
        "persistenceEffects": str(row.get("persistence_effects") or ""),
        "durablePersistenceDecisions": project_s3_durable_persistence_decisions(row.get("durable_persistence_decisions")), "authorityDeltaRefs": _strings(row.get("authority_delta_refs")),
        "integrationBehavior": str(row.get("integration_behavior") or ""),
        "preservedConstraintIds": _strings(row.get("preserved_constraint_ids")),
        "componentIds": _strings(row.get("component_ids")),
        "contextActionCardRefs": _strings(row.get("context_action_card_refs")),
        "claimCeiling": str(row.get("claim_ceiling") or ""),
    }

def _relative_import(from_path: Path, to_path: Path) -> str:
    raw = os.path.relpath(to_path.with_suffix(""), from_path.parent).replace(os.sep, "/")
    return raw if raw.startswith(".") else f"./{raw}"

def _support_module() -> str:
    return """// P3-S3 generation-only support. No runtime evidence is implied by this file.
export type S3DurablePersistenceDecision = { operationId: string; persistenceMode: string; commandKind: string; idempotencyMode: string; identityComponents: readonly string[]; durableCarrier: { kind: string; carrierId: string; fieldBindings: readonly { identityComponent: string; carrierField: string }[]; enforcement: { mode: string; fields: readonly string[] } }; writerServiceId: string; replayBehavior: string; reason: string; claimCeiling: string };

export type S3SliceBinding = {
  sliceId: string;
  operationId: string;
  nonOperationRealizationId: string;
  contractId: string;
  implementationDecisionId: string;
  implementationDecisionDigest: string;
  semanticOwner: string;
  aggregate: string;
  domainInvariants: readonly string[];
  stateMutation: string;
  authorization: string;
  failureBehavior: string;
  persistenceEffects: string;
  durablePersistenceDecisions: readonly S3DurablePersistenceDecision[]; authorityDeltaRefs: readonly string[];
  integrationBehavior: string;
  preservedConstraintIds: readonly string[];
  componentIds: readonly string[];
  contextActionCardRefs: readonly string[];
  claimCeiling: string;
};

export type S3ExecutionContext = {
  input?: Record<string, unknown>;
  actor?: Record<string, unknown>;
  currentState?: Record<string, unknown>;
  evidence?: Record<string, unknown>;
};

export interface S3PolicyPort {
  authorize(binding: S3SliceBinding, context: S3ExecutionContext): Promise<void> | void;
}

export interface S3RepositoryPort {
  realize(binding: S3SliceBinding, context: S3ExecutionContext): Promise<Record<string, unknown>>;
}

export interface S3IntegrationPort {
  invoke(binding: S3SliceBinding, context: S3ExecutionContext): Promise<unknown>;
}

export interface S3StorageAdapter {
  realize(binding: S3SliceBinding, context: S3ExecutionContext): Promise<Record<string, unknown>>;
}

export class S3BoundaryError extends Error {
  constructor(readonly sliceId: string, readonly boundary: string, message: string) {
    super(message);
  }
}

export function selectS3Binding(bindings: readonly S3SliceBinding[], sliceId: string): S3SliceBinding {
  const binding = bindings.find((row) => row.sliceId === sliceId);
  if (!binding) throw new S3BoundaryError(sliceId, "slice-identity", `Unknown S3 slice: ${sliceId}`);
  return binding;
}

export async function realizeDecisionBoundSlice(
  binding: S3SliceBinding,
  context: S3ExecutionContext,
  dependencies: { policy: S3PolicyPort; repository: S3RepositoryPort; integration?: S3IntegrationPort },
): Promise<Record<string, unknown>> {
  await dependencies.policy.authorize(binding, context);
  const persisted = await dependencies.repository.realize(binding, context);
  const integrationEvidence = dependencies.integration
    ? await dependencies.integration.invoke(binding, context)
    : undefined;
  return {
    slice_id: binding.sliceId,
    operation_id: binding.operationId,
    non_operation_realization_id: binding.nonOperationRealizationId,
    implementation_decision_digest: binding.implementationDecisionDigest,
    persisted,
    integration_evidence: integrationEvidence,
    claim_ceiling: binding.claimCeiling,
  };
}
"""


AGENTIC_SENTINEL = "WFF_AGENTIC_BODY_REQUIRED"
_AGENTIC_REGION_RE = re.compile(
    r"(?P<begin>^[ \t]*// @wff:agentic-begin id=(?P<id>[A-Za-z0-9_.-]+)\n)(?P<body>.*?)(?P<end>^[ \t]*// @wff:agentic-end id=(?P=id)$)",
    re.MULTILINE | re.DOTALL,
)


def _agentic_region(block_id: str, *, indent: str = "    ") -> str:
    return (
        f"{indent}// @wff:agentic-begin id={block_id}\n"
        f'{indent}throw new Error("{AGENTIC_SENTINEL}:{block_id}");\n'
        f"{indent}// @wff:agentic-end id={block_id}"
    )


def _region_rows(text: str) -> dict[str, str]:
    return {match.group("id"): match.group("body") for match in _AGENTIC_REGION_RE.finditer(text)}


def _shell_projection(text: str) -> str:
    return _AGENTIC_REGION_RE.sub(
        lambda match: match.group("begin") + f"<{match.group('id')}:agentic-body>\n" + match.group("end"),
        text,
    )


def _merge_agentic_regions(path: Path, rendered: str, source_path: Path | None = None) -> tuple[str, list[dict[str, str]]]:
    expected = _region_rows(rendered)
    if not expected: return rendered, []
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    existing_rows = _region_rows(existing) if existing else {}
    existing_materialized = any(AGENTIC_SENTINEL not in body for body in existing_rows.values())
    source = existing if existing_materialized else (source_path.read_text(encoding="utf-8") if source_path and source_path.exists() else existing)
    current = _region_rows(source) if source else {}
    if source and not current: raise S3CodeRealizationError(f"S3 ownership source is legacy/unmarked: {path}")
    preserved = {block_id: body for block_id, body in current.items() if AGENTIC_SENTINEL not in body}
    if preserved and set(current) != set(expected): raise S3CodeRealizationError(f"S3 Agentic block denominator changed: {path}")
    if existing_materialized and preserved and _shell_projection(existing) != _shell_projection(rendered): raise S3CodeRealizationError(f"protected S3 template shell changed outside Agentic blocks: {path}")
    merged = _AGENTIC_REGION_RE.sub(lambda match: match.group("begin") + preserved.get(match.group("id"), match.group("body")) + match.group("end"), rendered)
    records = [{"block_id": block_id, "status": "authoring-required" if AGENTIC_SENTINEL in body else "materialized", "sha256": "sha256:" + sha256(body.encode()).hexdigest()} for block_id, body in _region_rows(merged).items()]
    return merged, records


def _render_service(path: Path, rows: list[dict[str, Any]], authority: Mapping[str, Any], support_path: Path) -> str:
    import_path = _relative_import(path, support_path)
    bindings = json.dumps([_binding_payload(row, authority) for row in rows], ensure_ascii=False, indent=2)
    class_name = _identifier(path.stem, "S3Service")
    workspace_root = support_path.parents[4]
    port_paths = sorted({target for row in rows for target in _strings(row.get("implementation_targets")) if target.endswith(".port.ts")})
    named_ports: list[tuple[str, str, str]] = []
    if len(port_paths) > 1:
        for raw_port in port_paths:
            port_path = _safe_target(workspace_root, raw_port)
            interface_name = _identifier(port_path.stem, "S3Port")
            member_base = _identifier(port_path.stem.removesuffix(".port"), "integration")
            member_name = member_base[:1].lower() + member_base[1:]
            named_ports.append((interface_name, member_name, _relative_import(path, port_path)))
    named_imports = "".join(f'import type {{ {interface_name} }} from "{relative}.js";\n' for interface_name, _, relative in named_ports)
    named_parameters = "".join(f"    private readonly {member_name}: {interface_name},\n" for interface_name, member_name, _ in named_ports)
    return f'''import {{ type S3ExecutionContext, type S3IntegrationPort, type S3PolicyPort, type S3RepositoryPort }} from "{import_path}.js";\n{named_imports}\nexport const s3Bindings = {bindings} as const;\n\nexport class {class_name} {{\n  constructor(\n    private readonly policy: S3PolicyPort,\n    private readonly repository: S3RepositoryPort,\n{named_parameters}    private readonly integration?: S3IntegrationPort,\n  ) {{}}\n\n  async execute(sliceId: string, context: S3ExecutionContext): Promise<Record<string, unknown>> {{\n{_agentic_region("service-execute")}\n  }}\n}}\n'''


def _render_repository(path: Path, rows: list[dict[str, Any]], authority: Mapping[str, Any], support_path: Path) -> str:
    import_path = _relative_import(path, support_path)
    bindings = json.dumps([_binding_payload(row, authority) for row in rows], ensure_ascii=False, indent=2)
    class_name = _identifier(path.stem, "S3Repository")
    return f'''import {{ type S3ExecutionContext, type S3StorageAdapter }} from "{import_path}.js";\n\nexport const s3Bindings = {bindings} as const;\n\nexport class {class_name} {{\n  constructor(private readonly storage: S3StorageAdapter) {{}}\n\n  async realize(sliceId: string, context: S3ExecutionContext): Promise<Record<string, unknown>> {{\n{_agentic_region("repository-realize")}\n  }}\n}}\n'''


def _render_policy(path: Path, rows: list[dict[str, Any]], authority: Mapping[str, Any], support_path: Path) -> str:
    import_path = _relative_import(path, support_path)
    bindings = json.dumps([_binding_payload(row, authority) for row in rows], ensure_ascii=False, indent=2)
    class_name = _identifier(path.stem, "S3Policy")
    return f'''import {{ type S3ExecutionContext }} from "{import_path}.js";\n\nexport const s3Bindings = {bindings} as const;\n\nexport class {class_name} {{\n  assertEvaluated(sliceId: string, allowed: boolean, context: S3ExecutionContext): void {{\n{_agentic_region("policy-evaluate")}\n  }}\n}}\n'''


def _render_port(path: Path, rows: list[dict[str, Any]], authority: Mapping[str, Any], support_path: Path) -> str:
    import_path = _relative_import(path, support_path)
    bindings = [_binding_payload(row, authority) for row in rows]
    interface_name = _identifier(path.stem, "S3Port")
    return (
        f'import {{ selectS3Binding, type S3ExecutionContext }} from "{import_path}.js";\n\n'
        + "export const s3Bindings = "
        + json.dumps(bindings, ensure_ascii=False, indent=2)
        + " as const;\n\n"
        + f"export interface {interface_name} {{\n"
        + "  invoke(sliceId: string, context: S3ExecutionContext): Promise<unknown>;\n"
        + "}\n\n"
        + "export function providerIntent(sliceId: string): string {\n"
        + "  return selectS3Binding(s3Bindings, sliceId).integrationBehavior;\n"
        + "}\n"
    )


def _render_generic(path: Path, rows: list[dict[str, Any]], authority: Mapping[str, Any], support_path: Path) -> str:
    import_path = _relative_import(path, support_path)
    bindings = [_binding_payload(row, authority) for row in rows]
    return (
        f'import {{ selectS3Binding, type S3ExecutionContext }} from "{import_path}.js";\n\n'
        + "export const s3Bindings = "
        + json.dumps(bindings, ensure_ascii=False, indent=2)
        + " as const;\n\n"
        + "export function describeS3Realization(sliceId: string, _context: S3ExecutionContext) {\n"
        + "  return selectS3Binding(s3Bindings, sliceId);\n"
        + "}\n"
    )


def _target_role(path: Path) -> str:
    name = path.name
    if name.endswith(".repository.ts"):
        return "repository"
    if name.endswith(".service.ts"):
        return "service"
    if name.endswith(".policy.ts") or name.endswith(".guard.ts"):
        return "policy"
    if name.endswith(".port.ts"):
        return "port"
    return "module"


def _render_target(path: Path, rows: list[dict[str, Any]], authority: Mapping[str, Any], support_path: Path) -> str:
    role = _target_role(path)
    if role == "service":
        return _render_service(path, rows, authority, support_path)
    if role == "repository":
        return _render_repository(path, rows, authority, support_path)
    if role == "policy":
        return _render_policy(path, rows, authority, support_path)
    if role == "port":
        return _render_port(path, rows, authority, support_path)
    return _render_generic(path, rows, authority, support_path)


def _test_requires_agentic(test_path: Path) -> bool:
    return any(part in {"unit", "integration", "policies"} for part in test_path.parts)


def _render_test(test_path: Path, rows: list[dict[str, Any]], authority: Mapping[str, Any], primary_target: Path) -> str:
    import_path = _relative_import(test_path, primary_target)
    expected = json.dumps([_binding_payload(row, authority) for row in rows], ensure_ascii=False, indent=2)
    behavior = ""
    if _test_requires_agentic(test_path):
        behavior = f"\n  it('proves Agentic-owned executable behavior for the accepted slice', async () => {{\n{_agentic_region('behavior-assertion')}\n  }});\n"
    return f'''import {{ describe, expect, it }} from 'vitest';\nimport {{ s3Bindings }} from '{import_path}.js';\n\nconst expectedRows = {expected} as const;\n\ndescribe('P3-S3 accepted implementation authority realization', () => {{\n  it('retains exact accepted slice semantics', () => {{\n    for (const expected of expectedRows) {{\n      const binding = s3Bindings.find((row) => row.sliceId === expected.sliceId);\n      expect(binding).toEqual(expect.objectContaining(expected));\n    }}\n  }});{behavior}}});\n'''


def _kernel_test(support_path: Path, test_path: Path) -> str:
    import_path = _relative_import(test_path, support_path)
    return f"""import {{ describe, expect, it }} from 'vitest';
import {{ realizeDecisionBoundSlice, selectS3Binding, S3BoundaryError, type S3SliceBinding }} from '{import_path}.js';

const binding: S3SliceBinding = {{
  sliceId: 'S3-TEST', operationId: 'TestOperation', nonOperationRealizationId: '', contractId: 'TEST-CONTRACT',
  implementationDecisionId: 'TEST-DECISION', implementationDecisionDigest: 'sha256:test', semanticOwner: 'TEST', aggregate: 'TEST',
  domainInvariants: ['preserve invariant'], stateMutation: 'bounded mutation', authorization: 'authorize first',
  failureBehavior: 'fail without persistence', persistenceEffects: 'persist after authorization', durablePersistenceDecisions: [], authorityDeltaRefs: [], integrationBehavior: 'none',
  preservedConstraintIds: ['TEST-CONSTRAINT'], componentIds: ['TEST-CMP'], contextActionCardRefs: [], claimCeiling: 'test only',
}};

describe('P3-S3 realization kernel', () => {{
  it('selects the exact binding and rejects an unknown slice', () => {{
    expect(selectS3Binding([binding], 'S3-TEST')).toBe(binding);
    expect(() => selectS3Binding([binding], 'S3-MISSING')).toThrow(S3BoundaryError);
  }});

  it('authorizes before persistence and does not require integration', async () => {{
    const calls: string[] = [];
    const result = await realizeDecisionBoundSlice(binding, {{ input: {{ value: 1 }} }}, {{
      policy: {{ authorize: async () => {{ calls.push('policy'); }} }},
      repository: {{ realize: async () => {{ calls.push('repository'); return {{ ok: true }}; }} }},
    }});
    expect(calls).toEqual(['policy', 'repository']);
    expect(result.implementation_decision_digest).toBe('sha256:test');
  }});
}});
"""


def realize_s3_code_and_tests(*, output_dir: Path, authority: Mapping[str, Any], agentic_source_root: Path | None = None) -> dict[str, Any]:
    """Materialize accepted S2 slices. This function never executes generated code/tests."""
    from phase3.agentic_implementation_authority import p3_agentic_implementation_authority_is_valid

    if not p3_agentic_implementation_authority_is_valid(authority):
        raise S3CodeRealizationError("accepted P3 implementation authority is invalid")
    slice_decisions = authority.get("slice_decisions")
    if not isinstance(slice_decisions, dict) or not slice_decisions:
        raise S3CodeRealizationError("S2 authority has no slice_decisions for S3 realization")
    rows = [dict(row) for _, row in sorted(slice_decisions.items()) if isinstance(row, dict)]
    if not rows:
        raise S3CodeRealizationError("S2 authority has no implemented slice rows")
    for row in rows:
        if str(row.get("implementation_decision_digest") or "") != str(authority.get("decision_digest") or ""):
            raise S3CodeRealizationError(f"slice {row.get('slice_id')} decision digest diverges from authority")
        if not _strings(row.get("implementation_targets")) or not _strings(row.get("test_targets")):
            raise S3CodeRealizationError(f"slice {row.get('slice_id')} lacks S3 implementation/test targets")
        if str(row.get("operation_id") or "").strip() and not str(row.get("contract_id") or "").strip():
            raise S3CodeRealizationError(f"operation slice {row.get('slice_id')} lost exact contract identity")

    output_dir = output_dir.resolve()
    source_root = agentic_source_root.resolve() if agentic_source_root else None
    if source_root:
        source_receipt = json.loads((source_root / "p3-s3-code-realization-receipt.json").read_text(encoding="utf-8"))
        if source_receipt.get("decision_digest") != authority.get("decision_digest"): raise S3CodeRealizationError("Agentic source root is bound to another P3 decision")
    support_path = output_dir / "apps" / "api" / "src" / "common" / "s3-realization.ts"
    support_path.parent.mkdir(parents=True, exist_ok=True)
    support_path.write_text(_support_module(), encoding="utf-8")

    implementation_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    test_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for target in _strings(row.get("implementation_targets")):
            implementation_groups[target].append(row)
        for target in _strings(row.get("test_targets")):
            test_groups[target].append(row)

    test_records: list[dict[str, Any]] = []
    for raw_path, target_rows in sorted(test_groups.items()):
        path = _safe_target(output_dir, raw_path)
        primary_raw = _strings(target_rows[0].get("implementation_targets"))[0]
        primary_target = _safe_target(output_dir, primary_raw)
        path.parent.mkdir(parents=True, exist_ok=True)
        content, blocks = _merge_agentic_regions(path, _render_test(path, target_rows, authority, primary_target), source_root / raw_path if source_root else None)
        path.write_text(content, encoding="utf-8")
        test_records.append(
            {
                "path": raw_path,
                "slice_ids": [str(row.get("slice_id") or "") for row in target_rows],
                "owner_mode": "mixed-assembly" if blocks else "workflow-template",
                "agentic_blocks": blocks,
                "sha256": _file_digest(path),
            }
        )

    implementation_records: list[dict[str, Any]] = []
    for raw_path, target_rows in sorted(implementation_groups.items()):
        path = _safe_target(output_dir, raw_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content, blocks = _merge_agentic_regions(path, _render_target(path, target_rows, authority, support_path), source_root / raw_path if source_root else None)
        path.write_text(content, encoding="utf-8")
        implementation_records.append(
            {
                "path": raw_path,
                "role": _target_role(path),
                "slice_ids": [str(row.get("slice_id") or "") for row in target_rows],
                "owner_mode": "mixed-assembly" if blocks else "workflow-template",
                "agentic_blocks": blocks,
                "sha256": _file_digest(path),
            }
        )

    kernel_test_path = output_dir / "tests" / "support" / "s3-realization-kernel.test.ts"
    kernel_test_path.parent.mkdir(parents=True, exist_ok=True)
    kernel_test_path.write_text(_kernel_test(support_path, kernel_test_path), encoding="utf-8")

    declared_impl = sorted(implementation_groups)
    declared_tests = sorted(test_groups)
    generated_impl = sorted(record["path"] for record in implementation_records)
    generated_tests = sorted(record["path"] for record in test_records)
    missing = sorted(set(declared_impl + declared_tests) - set(generated_impl + generated_tests))
    if missing:
        raise S3CodeRealizationError("S3 realization failed to materialize declared targets: " + ", ".join(missing))
    rows_by_slice = {str(row.get("slice_id") or ""): row for row in rows}
    for record in implementation_records + test_records:
        text = _safe_target(output_dir, record["path"]).read_text(encoding="utf-8")
        for slice_id in record["slice_ids"]:
            row = rows_by_slice[slice_id]
            required_tokens = [slice_id, str(authority.get("decision_digest") or "")] + _strings(row.get("preserved_constraint_ids"))
            contract_id = str(row.get("contract_id") or "").strip()
            if contract_id:
                required_tokens.append(contract_id)
            absent = [token for token in required_tokens if token not in text]
            if absent:
                raise S3CodeRealizationError(
                    f"S3 rendered target {record['path']} lost accepted slice semantics: " + ", ".join(absent)
                )

    ownership_records = implementation_records + test_records
    unresolved_blocks = [
        {"path": record["path"], "block_id": block["block_id"], "slice_ids": record["slice_ids"]}
        for record in ownership_records
        for block in record.get("agentic_blocks", [])
        if block.get("status") == "authoring-required"
    ]
    unresolved_slice_ids = {slice_id for row in unresolved_blocks for slice_id in row["slice_ids"]}
    authoring_status = "authoring-required" if unresolved_blocks else "materialized"

    operation_rows: list[dict[str, Any]] = []
    non_operation_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    for row in rows:
        base = {
            "slice_id": str(row.get("slice_id") or ""),
            "operation_id": str(row.get("operation_id") or ""),
            "non_operation_realization_id": str(row.get("non_operation_realization_id") or ""),
            "implementation_decision_id": authority.get("decision_id"),
            "implementation_decision_digest": authority.get("decision_digest"),
            "implementation_targets": _strings(row.get("implementation_targets")),
            "test_targets": _strings(row.get("test_targets")),
            "constraint_ids": _strings(row.get("preserved_constraint_ids")),
            "binding_status": "authoring-required" if str(row.get("slice_id") or "") in unresolved_slice_ids else "generated-not-executed",
        }
        if base["operation_id"]:
            contract_id = str(row.get("contract_id") or "")
            operation_rows.append({"source_id": contract_id, "contract_id": contract_id, **base, "runtime_evidence_refs": []})
            trace_rows.append(
                {
                    "source_id": contract_id,
                    "contract_id": contract_id,
                    "operation_id": base["operation_id"],
                    "implementation_decision_id": authority.get("decision_id"),
                    "implementation_decision_digest": authority.get("decision_digest"),
                    "status": "review-bound",
                    "trace_status": "review-bound",
                    "reason": (
                        "P3-S3 Agentic code authoring is incomplete; execution and Trace confirmation are deferred"
                        if base["binding_status"] == "authoring-required"
                        else "P3-S3 generated code/tests only; execution and Trace confirmation are intentionally deferred"
                    ),
                    "implementation_targets": base["implementation_targets"],
                    "test_targets": base["test_targets"],
                }
            )
        else:
            non_operation_rows.append(base)

    bindings = {
        "artifact_kind": "phase3-implementation-bindings.v3",
        "authority_mode": "accepted-host-agent-implementation-authority",
        "decision_id": authority.get("decision_id"),
        "decision_digest": authority.get("decision_digest"),
        "rows": operation_rows,
        "non_operation_rows": non_operation_rows,
        "authoring_status": authoring_status,
        "execution_status": "not-executed-by-design",
    }
    write_json_atomic(output_dir / "implementation-bindings.json", bindings)
    trace = {
        "artifact_kind": "phase3-trace-registry-final.v1",
        "authority_mode": "exact-tuple-review-bound-until-evidence-executes",
        "rows": trace_rows,
        "execution_status": "not-executed-by-design",
    }
    write_json_atomic(output_dir / "phase3-trace-registry-final.json", trace)

    receipt = {
        "schema_version": S3_REALIZATION_SCHEMA,
        "status": "authoring-required" if unresolved_blocks else "code-and-tests-generated-not-executed",
        "phase_id": "P3",
        "internal_substage": "S3",
        "decision_id": authority.get("decision_id"),
        "decision_digest": authority.get("decision_digest"),
        "component_coverage": authority.get("component_coverage", {}),
        "slice_count": len(rows),
        "operation_slice_count": len(operation_rows),
        "non_operation_slice_count": len(non_operation_rows),
        "declared_implementation_target_count": len(declared_impl),
        "declared_test_target_count": len(declared_tests),
        "generated_implementation_targets": implementation_records,
        "generated_test_targets": test_records,
        "support_paths": [
            str(support_path.relative_to(output_dir)),
            str(kernel_test_path.relative_to(output_dir)),
        ],
        "missing_declared_targets": [],
        "generation_order": "declared-test-files-before-implementation-targets",
        "authoring": {
            "status": authoring_status,
            "agentic_block_count": sum(len(record.get("agentic_blocks", [])) for record in ownership_records),
            "unresolved_block_count": len(unresolved_blocks),
            "materialized_block_count": sum(
                1 for record in ownership_records for block in record.get("agentic_blocks", []) if block.get("status") == "materialized"
            ),
            "unresolved_blocks": unresolved_blocks,
            "boundary": "Host Agent may edit only @wff:agentic blocks; Workflow owns the surrounding template shell.",
            "authorship_claim_ceiling": "The runner proves bounded block materialization and template-shell integrity, not writer identity or semantic correctness; Host-Agent/session evidence and later verification own those claims.",
        },
        "execution": {
            "tests_executed": False,
            "tdd_red_proven": False,
            "runtime_started": False,
            "trace_confirmed": False,
            "status": "not-executed-by-design",
        },
        "claim_ceiling": (
            "P3-S3 requires Host-Agent executable-body authoring before code realization can be claimed."
            if unresolved_blocks
            else "P3-S3 code and test files were assembled from accepted S2 authority and completed Agentic blocks; no test/runtime/Trace evidence was executed."
        ),
    }
    receipt["content_digest"] = canonical_digest(receipt)
    write_json_atomic(output_dir / "p3-s3-code-realization-receipt.json", receipt)
    projection = {
        "artifact_kind": "phase3-agentic-implementation-projection.v2",
        "decision_id": authority.get("decision_id"),
        "decision_digest": authority.get("decision_digest"),
        "generated_paths": sorted(declared_impl + declared_tests),
        "support_paths": receipt["support_paths"],
        "binding_count": len(operation_rows),
        "non_operation_binding_count": len(non_operation_rows),
        "authoring_status": authoring_status,
        "trace_status": "review-bound",
        "execution_status": "not-executed-by-design",
        "claim_ceiling": authority.get("claim_ceiling", ""),
    }
    write_json_atomic(output_dir / "p3-agentic-implementation-projection.json", projection)
    return {"bindings": bindings, "trace": trace, "projection": projection, "receipt": receipt}
