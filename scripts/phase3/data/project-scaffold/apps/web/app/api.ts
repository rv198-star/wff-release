export type ProductSessionSummary = {
  subject_id: string;
  tenant_id: string;
  roles: string[];
  session_id: string;
  expires_in?: number;
};

export type ProductSessionResult = {
  status: number;
  body: string;
  session?: ProductSessionSummary;
};

function productSessionFromBody(body: string): ProductSessionSummary | undefined {
  try {
    const payload = JSON.parse(body) as unknown;
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) return undefined;
    const data = (payload as Record<string, unknown>).data;
    if (!data || typeof data !== "object" || Array.isArray(data)) return undefined;
    const source = data as Record<string, unknown>;
    const subjectId = typeof source.subject_id === "string" ? source.subject_id.trim() : "";
    const tenantId = typeof source.tenant_id === "string" ? source.tenant_id.trim() : "";
    const sessionId = typeof source.session_id === "string" ? source.session_id.trim() : "";
    const roles = Array.isArray(source.roles)
      ? source.roles.filter((value): value is string => typeof value === "string" && value.trim().length > 0)
      : [];
    if (!subjectId || !tenantId || !sessionId || roles.length === 0) return undefined;
    const expiresIn = Number(source.expires_in ?? 0);
    return {
      subject_id: subjectId,
      tenant_id: tenantId,
      roles,
      session_id: sessionId,
      ...(Number.isFinite(expiresIn) && expiresIn > 0 ? { expires_in: expiresIn } : {}),
    };
  } catch {
    return undefined;
  }
}

async function productSessionRequest(init: globalThis.RequestInit): Promise<ProductSessionResult> {
  const response = await fetch("/auth/session", { ...init, credentials: "same-origin" });
  const body = await response.text();
  return { status: response.status, body, session: productSessionFromBody(body) };
}

export async function createProductSession(username: string, password: string): Promise<ProductSessionResult> {
  return productSessionRequest({
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

export async function getProductSession(): Promise<ProductSessionResult> {
  return productSessionRequest({ method: "GET" });
}

export async function clearProductSession(): Promise<ProductSessionResult> {
  return productSessionRequest({ method: "DELETE" });
}

export async function callApi(path: string, init?: globalThis.RequestInit): Promise<{ status: number; body: string }> {
  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api";
  const normalizedBase = base.replace(/\/$/, "");
  const requestInit: globalThis.RequestInit = { ...init, headers: new Headers(init?.headers ?? {}) };
  if (path.startsWith("http://") || path.startsWith("https://")) {
    const response = await fetch(path, requestInit);
    const body = await response.text();
    return { status: response.status, body };
  }
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const baseIsAbsolute = /^[a-z]+:\/\//i.test(normalizedBase);
  const hasRelativeBasePrefix = !baseIsAbsolute && normalizedBase.length > 0 && (normalizedPath === normalizedBase || normalizedPath.startsWith(`${normalizedBase}/`));
  const requestTarget = hasRelativeBasePrefix ? normalizedPath : `${normalizedBase}${normalizedPath}`;
  const response = await fetch(baseIsAbsolute ? `${normalizedBase}${normalizedPath}` : requestTarget, requestInit);
  const body = await response.text();
  return { status: response.status, body };
}
