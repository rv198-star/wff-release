import { basename, join } from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";
import { readFile } from "node:fs/promises";
import type { S3ExecutionContext, S3PolicyPort, S3RepositoryPort, S3SliceBinding } from "../common/s3-realization.js";
import { PostgresS3StorageAdapter, S3ReplayExistingError } from "./postgres-storage.js";

type RuntimeRealization = { persistence_realization?: unknown };
type AcceptedResultField = { name?: string; type?: string; constraint?: string; nullable?: boolean; required?: boolean; item_fields?: AcceptedResultField[] };
type P3Decision = { implementation_targets?: string[]; runtime_realization?: RuntimeRealization; accepted_result_fields?: AcceptedResultField[] };
type P3PlanRow = { operation_id?: string; slice_id?: string };
type P3SliceDecision = { terminal_roles?: string[]; terminal_role_authority_status?: string; runtime_realization?: RuntimeRealization; accepted_result_fields?: AcceptedResultField[] };
type P3Authority = { decisions?: Record<string, P3Decision>; exact_realization_plan?: P3PlanRow[]; slice_decisions?: Record<string, P3SliceDecision> };
type DeltaRecord = { source_slice_id?: string; resolution_payload?: { persistence_realization?: unknown } };
type DeltaLedger = { records?: DeltaRecord[] };

const root = fileURLToPath(new URL("../../../../", import.meta.url));
let authorityPromise: Promise<P3Authority> | undefined;
let deltaPromise: Promise<DeltaLedger> | undefined;

async function loadAuthority(): Promise<P3Authority> {
  authorityPromise ??= readFile(join(root, "p3-agentic-implementation-authority.json"), "utf-8").then((raw) => JSON.parse(raw) as P3Authority);
  return authorityPromise;
}

async function loadDeltaLedger(): Promise<DeltaLedger> {
  deltaPromise ??= readFile(join(root, ".phase3-evidence/p3-authority-delta-ledger.json"), "utf-8").then((raw) => JSON.parse(raw) as DeltaLedger);
  return deltaPromise;
}

function serviceClassName(target: string): string {
  return basename(target, ".service.ts").split(/[^A-Za-z0-9]+/).filter(Boolean).map((part) => part[0]!.toUpperCase() + part.slice(1)).join("") + "Service";
}

function runtimeServiceTarget(target: string): string {
  const sourcePrefix = "apps/api/src/";
  if (!target.startsWith(sourcePrefix) || !target.endsWith(".ts")) return target;
  const runtimePath = fileURLToPath(import.meta.url).replaceAll("\\", "/");
  if (!runtimePath.includes("/apps/api/dist/runtime/")) return target;
  return `apps/api/dist/${target.slice(sourcePrefix.length, -3)}.js`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

class RuntimePolicy implements S3PolicyPort {
  async authorize(binding: Parameters<S3PolicyPort["authorize"]>[0], context: S3ExecutionContext): Promise<void> {
    const actor = context.actor ?? {};
    if (Object.keys(actor).length === 0) throw new Error("runtime_auth_context_required");
    const inputTenant = String(context.input?.tenant_id ?? context.input?.tenantId ?? "").trim();
    const actorTenant = String(actor.tenant_id ?? actor.tenantId ?? "").trim();
    if (inputTenant && actorTenant && inputTenant !== actorTenant) throw new Error("tenant_boundary_violation");
    const authority = await loadAuthority();
    const slice = authority.slice_decisions?.[binding.sliceId];
    if (slice?.terminal_role_authority_status === "not-applicable-system-continuation") {
      if (actor.system_continuation !== true) throw new Error("system_continuation_required");
      return;
    }
    const requiredRoles = (slice?.terminal_roles ?? []).map((role) => String(role).trim().toLowerCase()).filter(Boolean);
    if (requiredRoles.length) {
      if (slice?.terminal_role_authority_status !== "sufficient") throw new Error("runtime_role_authority_not_sufficient");
      const actorRoles = Array.isArray(actor.roles) ? actor.roles.map((role) => String(role).trim().toLowerCase()).filter(Boolean) : [];
      if (!requiredRoles.some((role) => actorRoles.includes(role))) throw new Error("role_permission_denied");
    }
  }
}

class RuntimeRepository implements S3RepositoryPort {
  constructor(private readonly storage = new PostgresS3StorageAdapter()) {}
  realize(binding: Parameters<S3RepositoryPort["realize"]>[0], context: S3ExecutionContext) {
    return this.storage.realize(binding, context);
  }
  lookupExisting(sliceId: string, context: S3ExecutionContext) {
    return this.storage.lookupExisting(sliceId, context, true);
  }
}

function unconfiguredDependency(): Record<string, unknown> {
  return new Proxy({}, { get: () => async () => { throw new Error("integration_not_configured"); } });
}

function resultFieldIsOptional(field: AcceptedResultField): boolean {
  return field.required === false || field.nullable === true || /optional/i.test(String(field.constraint ?? ""));
}

function assertAcceptedResultFields(operationId: string, value: unknown, fields: AcceptedResultField[], path = "data"): void {
  if (!fields.length) return;
  if (!isRecord(value)) throw new Error(`runtime_result_contract_mismatch:${operationId}:${path}:object_required`);
  for (const field of fields) {
    const name = String(field.name ?? "").trim();
    if (!name) continue;
    if (!(name in value)) {
      if (resultFieldIsOptional(field)) continue;
      throw new Error(`runtime_result_contract_mismatch:${operationId}:${path}.${name}:missing`);
    }
    const actual = value[name];
    if (actual == null) {
      if (resultFieldIsOptional(field)) continue;
      throw new Error(`runtime_result_contract_mismatch:${operationId}:${path}.${name}:null`);
    }
    if (String(field.type ?? "").toLowerCase() === "array") {
      if (!Array.isArray(actual)) throw new Error(`runtime_result_contract_mismatch:${operationId}:${path}.${name}:array_required`);
      const itemFields = Array.isArray(field.item_fields) ? field.item_fields : [];
      for (let index = 0; index < actual.length; index += 1) {
        assertAcceptedResultFields(operationId, actual[index], itemFields, `${path}.${name}[${index}]`);
      }
    }
  }
}

function assertAcceptedResultContract(authority: P3Authority, sliceId: string, operationId: string, result: Record<string, unknown>): void {
  const fields = authority.slice_decisions?.[sliceId]?.accepted_result_fields ?? authority.decisions?.[operationId]?.accepted_result_fields ?? [];
  assertAcceptedResultFields(operationId, result, fields);
}

export async function checkS3OperationRuntimeReadiness(operationIds: string[]): Promise<{ ready: boolean; readyOperationCount: number; missingOperationIds: string[] }> {
  const [authority, ledger] = await Promise.all([loadAuthority(), loadDeltaLedger()]);
  const plannedSlices = new Set([
    ...Object.entries(authority.slice_decisions ?? {})
      .filter(([, row]) => row?.runtime_realization?.persistence_realization)
      .map(([sliceId]) => sliceId),
    ...(ledger.records ?? [])
      .filter((row) => row.resolution_payload?.persistence_realization)
      .map((row) => row.source_slice_id)
      .filter((sliceId): sliceId is string => Boolean(sliceId)),
  ]);
  const missing = operationIds.filter((operationId) => {
    const decision = authority.decisions?.[operationId];
    const serviceTargets = (decision?.implementation_targets ?? []).filter((target) => target.endsWith(".service.ts"));
    const slices = (authority.exact_realization_plan ?? []).filter((row) => row.operation_id === operationId && row.slice_id);
    const sliceId = slices[0]?.slice_id;
    return serviceTargets.length !== 1 || slices.length !== 1 || typeof sliceId !== "string" || !plannedSlices.has(sliceId);
  });
  return { ready: missing.length === 0, readyOperationCount: operationIds.length - missing.length, missingOperationIds: missing };
}

export async function invokeS3Operation(
  operationId: string,
  input: Record<string, unknown>,
  actor: Record<string, unknown>,
  evidence: Record<string, unknown> = {},
): Promise<Record<string, unknown>> {
  const authority = await loadAuthority();
  const decision = authority.decisions?.[operationId];
  const serviceTargets = (decision?.implementation_targets ?? []).filter((target) => target.endsWith(".service.ts"));
  const slices = (authority.exact_realization_plan ?? []).filter((row) => row.operation_id === operationId && row.slice_id);
  if (serviceTargets.length !== 1 || slices.length !== 1) throw new Error(`runtime_operation_binding_incomplete:${operationId}`);
  const target = serviceTargets[0]!;
  const moduleTarget = runtimeServiceTarget(target);
  const module = await import(pathToFileURL(join(root, moduleTarget)).href);
  type RuntimeService = { execute(sliceId: string, context: S3ExecutionContext): Promise<Record<string, unknown>> };
  const Service = module[serviceClassName(target)] as ({ new (...args: unknown[]): RuntimeService; length: number }) | undefined;
  if (!Service) throw new Error(`runtime_service_export_missing:${operationId}`);
  const sliceId = String(slices[0]!.slice_id);
  const context: S3ExecutionContext = { input, actor, evidence };
  const bindings = Array.isArray(module.s3Bindings) ? module.s3Bindings as readonly S3SliceBinding[] : [];
  const binding = bindings.find((row) => row.sliceId === sliceId);
  if (!binding) throw new Error(`runtime_service_binding_missing:${operationId}`);
  const policy = new RuntimePolicy();
  const repository = new RuntimeRepository();
  await policy.authorize(binding, context);
  const existing = await repository.lookupExisting(sliceId, context);
  if (existing) {
    assertAcceptedResultContract(authority, sliceId, operationId, existing);
    return existing;
  }
  const namedPortCount = (decision?.implementation_targets ?? []).filter((target) => target.endsWith(".port.ts")).length;
  const args: unknown[] = [policy, repository];
  while (args.length < 2 + namedPortCount) args.push(unconfiguredDependency());
  const service = Reflect.construct(Service, args) as RuntimeService;
  try {
    const result = await service.execute(sliceId, context);
    assertAcceptedResultContract(authority, sliceId, operationId, result);
    return result;
  } catch (error) {
    if (error instanceof S3ReplayExistingError) {
      assertAcceptedResultContract(authority, sliceId, operationId, error.result);
      return error.result;
    }
    throw error;
  }
}

export function extractEvidence(input: Record<string, unknown>): Record<string, unknown> {
  return isRecord(input.evidence) ? input.evidence : {};
}
