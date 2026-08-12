// Derived artifact authority: frozen-openapi-plus-p3-implementation-authority
import { randomUUID } from "node:crypto";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import type { IncomingMessage, ServerResponse } from "node:http";
import { checkS3OperationRuntimeReadiness, extractEvidence, invokeS3Operation } from "./runtime/operation-runtime.js";

type RouteDef = {
  operationId: string;
  method: string;
  pathTemplate: string;
  successStatus: number;
  successExample: Record<string, unknown>;
  failureStatusByCode: Record<string, number>;
};
type OpenApiOperation = { operationId?: string; responses?: Record<string, unknown> };
type OpenApiDocument = { paths?: Record<string, Record<string, OpenApiOperation>> };

const root = fileURLToPath(new URL("../../../", import.meta.url));
let routesPromise: Promise<RouteDef[]> | undefined;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function successStatus(operation: OpenApiOperation): number {
  const values = Object.keys(operation.responses ?? {}).map(Number).filter((value) => value >= 200 && value < 300).sort();
  return values[0] ?? 200;
}

function failureStatusByCode(operation: OpenApiOperation): Record<string, number> {
  const result: Record<string, number> = {};
  for (const [statusText, response] of Object.entries(operation.responses ?? {})) {
    const status = Number(statusText);
    if (!Number.isInteger(status) || status < 400 || !isRecord(response)) continue;
    const content = isRecord(response.content) ? response.content : {};
    const appJson = isRecord(content["application/json"]) ? content["application/json"] : {};
    const example = appJson.example;
    if (!isRecord(example)) continue;
    const errorCode = String(example.error_code ?? "").trim();
    if (errorCode) result[errorCode] = status;
  }
  return result;
}

function successExample(operation: OpenApiOperation): Record<string, unknown> {
  const responses = operation.responses ?? {};
  const statuses = Object.keys(responses).filter((value) => /^2\d\d$/.test(value)).sort();
  for (const status of statuses) {
    const response = responses[status];
    if (!isRecord(response)) continue;
    const content = isRecord(response.content) ? response.content : {};
    const appJson = isRecord(content["application/json"]) ? content["application/json"] : {};
    const example = appJson.example;
    if (isRecord(example)) return example;
  }
  return {};
}

async function loadRoutes(): Promise<RouteDef[]> {
  routesPromise ??= readFile(join(root, "contracts/openapi.yaml"), "utf-8").then((raw) => {
    const document = JSON.parse(raw) as OpenApiDocument;
    const rows: RouteDef[] = [];
    for (const [pathTemplate, pathItem] of Object.entries(document.paths ?? {})) {
      for (const [method, operation] of Object.entries(pathItem)) {
        if (!operation?.operationId) continue;
        rows.push({
          operationId: operation.operationId,
          method: method.toUpperCase(),
          pathTemplate,
          successStatus: successStatus(operation),
          successExample: successExample(operation),
          failureStatusByCode: failureStatusByCode(operation),
        });
      }
    }
    return rows;
  });
  return routesPromise;
}

function snakeCase(value: string): string {
  return value.replace(/([a-z0-9])([A-Z])/g, "$1_$2").replace(/-/g, "_").toLowerCase();
}

function matchPath(template: string, actual: string): Record<string, string> | null {
  const expected = template.split("/").filter(Boolean);
  const observed = actual.split("/").filter(Boolean);
  if (expected.length !== observed.length) return null;
  const result: Record<string, string> = {};
  for (let index = 0; index < expected.length; index += 1) {
    const left = expected[index]!;
    const right = decodeURIComponent(observed[index] ?? "");
    if (left.startsWith("{") && left.endsWith("}")) {
      const name = left.slice(1, -1);
      result[name] = right;
      result[snakeCase(name)] = right;
    } else if (left !== right) return null;
  }
  return result;
}

async function readBody(request: IncomingMessage): Promise<Record<string, unknown>> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  if (!chunks.length) return {};
  const raw = Buffer.concat(chunks).toString("utf-8").trim();
  if (!raw) return {};
  const value = JSON.parse(raw) as unknown;
  return isRecord(value) ? value : {};
}

function authContext(request: IncomingMessage): Record<string, unknown> {
  if (process.env.PHASE3_ALLOW_AUTH_CONTEXT_HEADER !== "true") return {};
  const raw = request.headers["x-phase3-auth-context"];
  const value = Array.isArray(raw) ? raw[0] : raw;
  if (!value) return {};
  try {
    const parsed = JSON.parse(decodeURIComponent(value)) as unknown;
    return isRecord(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function buildSuccessMeta(example: unknown): Record<string, unknown> {
  if (!isRecord(example)) return {};
  const meta: Record<string, unknown> = {};
  for (const key of Object.keys(example)) {
    const normalized = snakeCase(key);
    if (["trace_id", "request_id", "correlation_id"].includes(normalized)) {
      meta[key] = randomUUID();
      continue;
    }
    throw new Error(`runtime_success_meta_not_materialized:${key}`);
  }
  return meta;
}

function buildSuccessEnvelope(route: RouteDef, result: Record<string, unknown>): Record<string, unknown> {
  const expected = route.successExample;
  if (!Object.keys(expected).length) return { data: result };
  const envelope: Record<string, unknown> = {};
  for (const key of Object.keys(expected)) {
    if (key === "data") {
      envelope.data = result;
      continue;
    }
    if (key === "meta") {
      envelope.meta = buildSuccessMeta(expected.meta);
      continue;
    }
    if (["trace_id", "request_id", "correlation_id"].includes(snakeCase(key))) {
      envelope[key] = randomUUID();
      continue;
    }
    if (key in result) {
      envelope[key] = result[key];
      continue;
    }
    throw new Error(`runtime_success_envelope_field_unmaterialized:${key}`);
  }
  return envelope;
}

function fallbackErrorStatus(message: string): number {
  if (/dependency_unavailable|integration_not_configured|provider_unavailable|model_dependency|vision_or_model/i.test(message)) return 503;
  if (/forbidden|permission|tenant_boundary|auth_context/i.test(message)) return 403;
  if (/not_found|missing/i.test(message)) return 404;
  if (/conflict|stale|version/i.test(message)) return 409;
  return 400;
}

function errorStatus(route: RouteDef, errorCode: string): number {
  return route.failureStatusByCode[errorCode] ?? fallbackErrorStatus(errorCode);
}

export async function checkGeneratedRouteReadiness(): Promise<{ ready: boolean; routeCount: number; readyOperationCount: number; missingOperationIds?: string[]; reason?: string }> {
  try {
    const routes = await loadRoutes();
    if (!routes.length) return { ready: false, routeCount: 0, readyOperationCount: 0, reason: "no_compiled_business_routes" };
    const runtime = await checkS3OperationRuntimeReadiness(routes.map((route) => route.operationId));
    return { ready: runtime.ready, routeCount: routes.length, readyOperationCount: runtime.readyOperationCount, missingOperationIds: runtime.missingOperationIds };
  } catch (error) {
    return { ready: false, routeCount: 0, readyOperationCount: 0, reason: error instanceof Error ? error.message : "route_load_failed" };
  }
}

export async function handleGeneratedApiRequest(
  request: IncomingMessage,
  response: ServerResponse,
  helpers: { sendJson: (response: ServerResponse, statusCode: number, payload: Record<string, unknown>) => void },
): Promise<boolean> {
  const method = request.method || "GET";
  const url = new URL(request.url || "/", `http://${request.headers.host || "localhost"}`);
  for (const route of await loadRoutes()) {
    if (route.method !== method) continue;
    const pathParams = matchPath(route.pathTemplate, url.pathname);
    if (!pathParams) continue;
    try {
      const body = await readBody(request);
      const query = Object.fromEntries(url.searchParams.entries());
      const input = { ...query, ...body, ...pathParams };
      const result = await invokeS3Operation(route.operationId, input, authContext(request), extractEvidence(body));
      helpers.sendJson(response, route.successStatus, buildSuccessEnvelope(route, result));
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const errorCode = message.replace(/[^A-Za-z0-9_.:-]+/g, "_");
      helpers.sendJson(response, errorStatus(route, errorCode), { error_kind: "business_error", error_code: errorCode });
    }
    return true;
  }
  return false;
}
