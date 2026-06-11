const STORAGE_KEY = "phase3-role-session";

type RoleSession = {
  currentRole?: string;
};

function readRoleSession(): RoleSession {
  if (typeof window === "undefined" || typeof window.localStorage === "undefined") {
    return {};
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return {};
    }
    const source = parsed as Record<string, unknown>;
    const currentRole = typeof source.currentRole === "string" ? source.currentRole.trim() : "";
    return currentRole ? { currentRole } : {};
  } catch {
    return {};
  }
}

function roleSessionAuthHeader(): string | undefined {
  const currentRole = String(readRoleSession().currentRole || '').trim();
  if (!currentRole) {
    return undefined;
  }
  const slug = currentRole.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "workspace";
  return encodeURIComponent(JSON.stringify({
    sub: `phase3-${slug}`,
    subject_id: `phase3-${slug}`,
    sid: `phase3-${slug}-session`,
    session_id: `phase3-${slug}-session`,
    role: currentRole,
    roles: [currentRole],
    oidc_claims: { role: currentRole },
  }));
}

function withPhase3AuthHeaders(init?: globalThis.RequestInit): globalThis.RequestInit {
  const headers = new Headers(init?.headers ?? {});
  const allowAuthContextHeader = import.meta.env.VITE_PHASE3_ALLOW_AUTH_CONTEXT_HEADER === "true";
  if (allowAuthContextHeader && !headers.has("authorization") && !headers.has("x-phase3-auth-context")) {
    const authContext = roleSessionAuthHeader();
    if (authContext) {
      headers.set("x-phase3-auth-context", authContext);
    }
  }
  return { ...init, headers };
}

export async function callApi(path: string, init?: globalThis.RequestInit): Promise<{ status: number; body: string }> {
  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api";
  const normalizedBase = base.replace(/\/$/, "");
  const requestInit = withPhase3AuthHeaders(init);
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
