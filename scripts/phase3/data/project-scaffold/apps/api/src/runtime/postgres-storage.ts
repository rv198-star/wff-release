import { randomUUID } from "node:crypto";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { Client } from "pg";
import type { S3ExecutionContext, S3SliceBinding, S3StorageAdapter } from "../common/s3-realization.js";

type BindingRow = { source_ref: string; target_field: string; target_table?: string; optional?: boolean };
type ConstantRow = { target_field: string; target_table?: string; value: unknown };
type JoinRow = { table: string; left_table?: string; left_field: string; right_field: string };
type PersistenceStep = {
  step_id: string;
  table: string;
  command_kind: "insert" | "append" | "update" | "upsert" | "select-one" | "select-many";
  predicate_bindings?: BindingRow[];
  predicate_constants?: ConstantRow[];
  value_bindings?: BindingRow[];
  joins?: JoinRow[];
  constant_values?: ConstantRow[];
  conflict_target?: string[];
  conflict_update_fields?: string[];
  conflict_error_code?: string;
  increment_fields?: string[];
  returning_fields?: string[];
  result_role?: "response-source" | "projection-source" | "side-effect-only";
  result_alias?: string;
  when_source_present?: string;
  when_source_absent?: string;
  require_affected_row?: boolean;
  not_found_error_code?: string;
  allow_unfiltered_read?: boolean;
};
type ReplayGuard = {
  table: string;
  predicate_bindings: BindingRow[];
  return_table?: string;
  return_predicate_bindings?: BindingRow[];
  returning_fields: string[];
  projection?: Record<string, string>;
  constants?: Record<string, unknown>;
  pre_service?: boolean;
  return_direct?: boolean;
};
type PersistencePlan = { steps: PersistenceStep[]; transaction: { mode: "single-step" | "atomic" | "ordered-non-atomic" }; replay_guard?: ReplayGuard };

export class S3ReplayExistingError extends Error {
  constructor(readonly result: Record<string, unknown>) { super("persistence_replay_existing"); }
}

function quoteIdentifier(value: string): string {
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(value)) throw new Error(`unsafe persistence identifier:${value}`);
  return `"${value}"`;
}

function qualifiedIdentifier(table: string, field: string): string {
  return `${quoteIdentifier(table)}.${quoteIdentifier(field)}`;
}

function readFromClause(step: PersistenceStep): string {
  let clause = quoteIdentifier(step.table);
  for (const join of step.joins ?? []) {
    const leftTable = join.left_table || step.table;
    clause += ` JOIN ${quoteIdentifier(join.table)} ON ${qualifiedIdentifier(leftTable, join.left_field)} = ${qualifiedIdentifier(join.table, join.right_field)}`;
  }
  return clause;
}

function sourceValue(sourceRef: string, context: S3ExecutionContext, optional = false): unknown {
  if (sourceRef === "generated.uuid") return randomUUID();
  const [root, ...parts] = sourceRef.split(".");
  let value: unknown = root === "input" ? context.input : root === "evidence" ? context.evidence : root === "actor" ? context.actor : root === "currentState" ? context.currentState : undefined;
  for (const part of parts) value = value && typeof value === "object" ? (value as Record<string, unknown>)[part] : undefined;
  if (value === undefined && !optional) throw new Error(`persistence source missing:${sourceRef}`);
  return value;
}

async function loadPlan(sliceId: string): Promise<PersistencePlan> {
  const root = fileURLToPath(new URL("../../../../", import.meta.url));
  const authority = JSON.parse(await readFile(`${root}p3-agentic-implementation-authority.json`, "utf-8")) as {
    slice_decisions?: Record<string, { runtime_realization?: { persistence_realization?: unknown } }>;
  };
  const acceptedPlan = authority.slice_decisions?.[sliceId]?.runtime_realization?.persistence_realization;
  if (acceptedPlan && typeof acceptedPlan === "object") return acceptedPlan as PersistencePlan;
  const document = JSON.parse(await readFile(`${root}.phase3-evidence/p3-authority-delta-ledger.json`, "utf-8")) as { records?: unknown[] };
  for (const raw of document.records ?? []) {
    if (!raw || typeof raw !== "object") continue;
    const row = raw as Record<string, unknown>;
    if (row.source_slice_id !== sliceId) continue;
    const resolution = row.resolution_payload;
    if (!resolution || typeof resolution !== "object") continue;
    const plan = (resolution as Record<string, unknown>).persistence_realization;
    if (plan && typeof plan === "object") return plan as PersistencePlan;
  }
  throw new Error(`persistence_realization_missing:${sliceId}`);
}

function valuesFor(step: PersistenceStep, context: S3ExecutionContext): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const row of step.value_bindings ?? []) {
    const value = sourceValue(row.source_ref, context, row.optional === true);
    if (value !== undefined) result[row.target_field] = value;
  }
  for (const row of step.constant_values ?? []) result[row.target_field] = row.value;
  return result;
}

function predicateFor(step: PersistenceStep, context: S3ExecutionContext): Record<string, unknown> {
  return Object.fromEntries((step.predicate_bindings ?? []).map((row) => [row.target_field, sourceValue(row.source_ref, context)]));
}

function returning(step: PersistenceStep): string {
  const fields = step.returning_fields ?? [];
  return fields.length ? ` RETURNING ${fields.map(quoteIdentifier).join(", ")}` : "";
}

function whereClause(bindings: BindingRow[], context: S3ExecutionContext, bind: (value: unknown) => string): string {
  return bindings.map((row) => {
    const value = sourceValue(row.source_ref, context, true);
    return value === undefined || value === null ? `${quoteIdentifier(row.target_field)} IS NULL` : `${quoteIdentifier(row.target_field)} = ${bind(value)}`;
  }).join(" AND ");
}

async function lookupReplay(client: Client, guard: ReplayGuard, context: S3ExecutionContext): Promise<Record<string, unknown> | null> {
  const params: unknown[] = [];
  const bind = (value: unknown) => { params.push(value); return `$${params.length}`; };
  const predicate = whereClause(guard.predicate_bindings, context, bind);
  if (!predicate) throw new Error("replay_guard_predicate_missing");
  const hit = await client.query(`SELECT 1 FROM ${quoteIdentifier(guard.table)} WHERE ${predicate} LIMIT 1`, params);
  if ((hit.rowCount ?? 0) === 0) return null;
  params.length = 0;
  const returnPredicate = whereClause(guard.return_predicate_bindings ?? guard.predicate_bindings, context, bind);
  const table = quoteIdentifier(guard.return_table ?? guard.table);
  const row = (await client.query<Record<string, unknown>>(`SELECT ${guard.returning_fields.map(quoteIdentifier).join(", ")} FROM ${table} WHERE ${returnPredicate} LIMIT 1`, params)).rows[0];
  if (!row) throw new Error("replay_result_missing");
  const projected = guard.projection ? Object.fromEntries(Object.entries(guard.projection).map(([output, source]) => [output, row[source]])) : { ...row };
  return { ...projected, ...(guard.constants ?? {}) };
}

async function executeStep(client: Client, step: PersistenceStep, context: S3ExecutionContext): Promise<Record<string, unknown>[]> {
  const table = quoteIdentifier(step.table);
  const params: unknown[] = [];
  const bind = (value: unknown) => { params.push(value); return `$${params.length}`; };
  if (step.command_kind === "select-one" || step.command_kind === "select-many") {
    const predicateBindings = step.predicate_bindings ?? [];
    const predicateConstants = step.predicate_constants ?? [];
    const unfilteredReadAllowed = step.command_kind === "select-many" && step.allow_unfiltered_read === true;
    if (!predicateBindings.length && !predicateConstants.length && !unfilteredReadAllowed) throw new Error(`persistence predicate missing:${step.step_id}`);
    const where = [
      ...predicateBindings.map((row) => {
        const value = sourceValue(row.source_ref, context, row.optional === true);
        const field = qualifiedIdentifier(row.target_table || step.table, row.target_field);
        return value === undefined || value === null ? `${field} IS NULL` : `${field} = ${bind(value)}`;
      }),
      ...predicateConstants.map((row) => {
        const field = qualifiedIdentifier(row.target_table || step.table, row.target_field);
        return row.value === null ? `${field} IS NULL` : `${field} = ${bind(row.value)}`;
      }),
    ].join(" AND ");
    const fields = step.returning_fields ?? [];
    if (!fields.length) throw new Error(`persistence returning missing:${step.step_id}`);
    const selectFields = fields.map((field) => `${qualifiedIdentifier(step.table, field)} AS ${quoteIdentifier(field)}`).join(", ");
    const limit = step.command_kind === "select-one" ? " LIMIT 1" : "";
    const whereSql = where ? ` WHERE ${where}` : "";
    const rows = (await client.query<Record<string, unknown>>(`SELECT ${selectFields} FROM ${readFromClause(step)}${whereSql}${limit}`, params)).rows;
    const requiresRow = Boolean(step.require_affected_row) || (step.command_kind === "select-one" && Boolean(step.not_found_error_code));
    if (requiresRow && rows.length === 0) {
      throw new Error(step.not_found_error_code || "persistence_not_found");
    }
    return rows;
  }
  if (step.command_kind === "update") {
    const values = Object.entries(valuesFor(step, context));
    const predicate = Object.entries(predicateFor(step, context));
    if (!values.length || !predicate.length) throw new Error(`persistence update incomplete:${step.step_id}`);
    const increments = step.increment_fields ?? [];
    const set = [...values.map(([key, value]) => `${quoteIdentifier(key)} = ${bind(value)}`), ...increments.map((key) => `${quoteIdentifier(key)} = ${quoteIdentifier(key)} + 1`)].join(", ");
    const where = predicate.map(([key, value]) => `${quoteIdentifier(key)} = ${bind(value)}`).join(" AND ");
    const result = await client.query<Record<string, unknown>>(`UPDATE ${table} SET ${set} WHERE ${where}${returning(step)}`, params);
    if ((step.require_affected_row || step.not_found_error_code) && (result.rowCount ?? 0) === 0) {
      throw new Error(step.not_found_error_code || "persistence_conflict");
    }
    return result.rows;
  }
  const values = Object.entries(valuesFor(step, context));
  if (!values.length) throw new Error(`persistence values missing:${step.step_id}`);
  const names = values.map(([key]) => quoteIdentifier(key)).join(", ");
  const placeholders = values.map(([, value]) => bind(value)).join(", ");
  let conflict = "";
  if (step.command_kind === "upsert") {
    const target = step.conflict_target ?? [];
    const updates = step.conflict_update_fields ?? [];
    if (!target.length || !updates.length) throw new Error(`persistence upsert conflict incomplete:${step.step_id}`);
    conflict = ` ON CONFLICT (${target.map(quoteIdentifier).join(", ")}) DO UPDATE SET ${updates.map((name) => `${quoteIdentifier(name)} = EXCLUDED.${quoteIdentifier(name)}`).join(", ")}`;
  }
  return (await client.query<Record<string, unknown>>(`INSERT INTO ${table} (${names}) VALUES (${placeholders})${conflict}${returning(step)}`, params)).rows;
}

export class PostgresS3StorageAdapter implements S3StorageAdapter {
  async lookupExisting(sliceId: string, context: S3ExecutionContext, preServiceOnly = false): Promise<Record<string, unknown> | null> {
    const plan = await loadPlan(sliceId);
    if (!plan.replay_guard || (preServiceOnly && plan.replay_guard.pre_service !== true)) return null;
    const connectionString = process.env.DATABASE_URL || "";
    if (!connectionString) throw new Error("DATABASE_URL is required for persistence runtime");
    const client = new Client({ connectionString });
    await client.connect();
    try { return await lookupReplay(client, plan.replay_guard, context); } finally { await client.end(); }
  }

  async realize(binding: S3SliceBinding, context: S3ExecutionContext): Promise<Record<string, unknown>> {
    const connectionString = process.env.DATABASE_URL || "";
    if (!connectionString) throw new Error("DATABASE_URL is required for persistence runtime");
    const plan = await loadPlan(binding.sliceId);
    const client = new Client({ connectionString });
    await client.connect();
    const atomic = plan.transaction.mode === "atomic" || Boolean(plan.replay_guard);
    try {
      if (atomic) await client.query("BEGIN");
      if (plan.replay_guard) {
        const lockValues = plan.replay_guard.predicate_bindings.map((row) => sourceValue(row.source_ref, context, true));
        await client.query("SELECT pg_advisory_xact_lock(hashtextextended($1, 0))", [JSON.stringify([plan.replay_guard.table, lockValues])]);
        const existing = await lookupReplay(client, plan.replay_guard, context);
        if (existing) {
          if (atomic) await client.query("COMMIT");
          if (plan.replay_guard.return_direct) throw new S3ReplayExistingError(existing);
          return existing;
        }
      }
      let response: Record<string, unknown> = {};
      const projections: Record<string, unknown> = {};
      for (const step of plan.steps) {
        if (step.when_source_present && sourceValue(step.when_source_present, context, true) === undefined) continue;
        if (step.when_source_absent && sourceValue(step.when_source_absent, context, true) !== undefined) continue;
        let rows: Record<string, unknown>[];
        try {
          rows = await executeStep(client, step, context);
        } catch (error) {
          if ((error as { code?: string }).code === "23505" && step.conflict_error_code) {
            throw new Error(step.conflict_error_code);
          }
          throw error;
        }
        if (step.result_role === "response-source") response = rows[0] ?? {};
        if (step.result_role === "projection-source" && step.result_alias) projections[step.result_alias] = step.command_kind === "select-many" ? rows : rows[0] ?? {};
      }
      if (atomic) await client.query("COMMIT");
      return Object.keys(projections).length ? { ...response, ...projections } : response;
    } catch (error) {
      if (atomic) await client.query("ROLLBACK").catch(() => undefined);
      if ((error as { code?: string }).code === "23505") throw new Error("persistence_conflict");
      throw error;
    } finally {
      await client.end();
    }
  }
}
