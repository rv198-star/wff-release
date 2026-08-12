import { basename, join } from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";
import { readFile } from "node:fs/promises";
import type { S3ExecutionContext, S3PolicyPort, S3RepositoryPort } from "../common/s3-realization.js";
import { PostgresS3StorageAdapter, S3ReplayExistingError } from "./postgres-storage.js";

type P3Decision = { implementation_targets?: string[] };
type P3PlanRow = { operation_id?: string; slice_id?: string };
type P3Authority = { decisions?: Record<string, P3Decision>; exact_realization_plan?: P3PlanRow[] };
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
  async authorize(_binding: Parameters<S3PolicyPort["authorize"]>[0], context: S3ExecutionContext): Promise<void> {
    const actor = context.actor ?? {};
    if (Object.keys(actor).length === 0) throw new Error("runtime_auth_context_required");
    const inputTenant = String(context.input?.tenant_id ?? context.input?.tenantId ?? "").trim();
    const actorTenant = String(actor.tenant_id ?? actor.tenantId ?? "").trim();
    if (inputTenant && actorTenant && inputTenant !== actorTenant) throw new Error("tenant_boundary_violation");
  }
}

class RuntimeRepository implements S3RepositoryPort {
  constructor(private readonly storage = new PostgresS3StorageAdapter()) {}
  realize(binding: Parameters<S3RepositoryPort["realize"]>[0], context: S3ExecutionContext) {
    return this.storage.realize(binding, context);
  }
}

function unconfiguredDependency(): Record<string, unknown> {
  return new Proxy({}, { get: () => async () => { throw new Error("integration_not_configured"); } });
}

export async function checkS3OperationRuntimeReadiness(operationIds: string[]): Promise<{ ready: boolean; readyOperationCount: number; missingOperationIds: string[] }> {
  const [authority, ledger] = await Promise.all([loadAuthority(), loadDeltaLedger()]);
  const plannedSlices = new Set((ledger.records ?? []).filter((row) => row.resolution_payload?.persistence_realization).map((row) => row.source_slice_id).filter(Boolean));
  const missing = operationIds.filter((operationId) => {
    const decision = authority.decisions?.[operationId];
    const serviceTargets = (decision?.implementation_targets ?? []).filter((target) => target.endsWith(".service.ts"));
    const slices = (authority.exact_realization_plan ?? []).filter((row) => row.operation_id === operationId && row.slice_id);
    return serviceTargets.length !== 1 || slices.length !== 1 || !plannedSlices.has(slices[0]?.slice_id);
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
  const preexisting = await new PostgresS3StorageAdapter().lookupExisting(sliceId, context, true);
  if (preexisting) return preexisting;
  const args: unknown[] = [new RuntimePolicy(), new RuntimeRepository()];
  while (args.length < Service.length) args.push(unconfiguredDependency());
  const service = Reflect.construct(Service, args) as RuntimeService;
  try { return await service.execute(sliceId, context); }
  catch (error) { if (error instanceof S3ReplayExistingError) return error.result; throw error; }
}

export function extractEvidence(input: Record<string, unknown>): Record<string, unknown> {
  return isRecord(input.evidence) ? input.evidence : {};
}
