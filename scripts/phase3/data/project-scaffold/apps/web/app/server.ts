import { createHmac, randomUUID, scryptSync, timingSafeEqual } from "node:crypto";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { URL } from "node:url";

const host = process.env.HOST ?? "0.0.0.0";
const port = Number.parseInt(process.env.WEB_PORT ?? "3100", 10);
const apiBaseUrl = process.env.WEB_API_BASE_URL ?? "http://localhost:3000";
const normalizedApiBaseUrl = apiBaseUrl.replace(/\/$/, "");

const distDir = join(process.cwd(), "dist");
const sessionCookieName = "wff_product_session";
const runtimeTraffic = {
  api_request_count: 0,
  authorized_api_request_count: 0,
  browser_authorization_header_request_count: 0,
  phase3_auth_context_request_count: 0,
  frozen_backend_auth_context_request_count: 0,
};

const frozenBackendAuthAdapter = process.env.WFF_FROZEN_BACKEND_AUTH_ADAPTER === 'phase3-header';

type FrozenBackendSession = {
  subject_id: string;
  tenant_id: string;
  roles: string[];
  session_id: string;
  preferred_username: string;
  exp: number;
};

type LocalAuthUser = {
  username: string;
  password_hash: string;
  subject_id: string;
  tenant_id: string;
  roles: string[];
};

async function buildRuntimeProof(): Promise<Record<string, unknown>> {
  const checks = await Promise.allSettled([
    fetch(`${normalizedApiBaseUrl}/healthz`),
    fetch(`${normalizedApiBaseUrl}/readyz`),
  ]);
  const [healthz, readyz] = checks;
  return {
    ok: healthz.status === 'fulfilled' && readyz.status === 'fulfilled' && healthz.value.ok && readyz.value.ok,
    api_base_url: normalizedApiBaseUrl,
    healthz: healthz.status === 'fulfilled' ? { status: healthz.value.status, ok: healthz.value.ok } : { error: String(healthz.reason) },
    readyz: readyz.status === 'fulfilled' ? { status: readyz.value.status, ok: readyz.value.ok } : { error: String(readyz.reason) },
    frontend_api_traffic: { ...runtimeTraffic },
    auth_adapter_mode: frozenBackendAuthAdapter ? 'frozen-backend-phase3-header' : 'api-session-bearer',
    checked_at: new Date().toISOString(),
  };
}

function parseCookies(request: import("node:http").IncomingMessage): Record<string, string> {
  const raw = String(request.headers.cookie || '');
  const cookies: Record<string, string> = {};
  for (const part of raw.split(';')) {
    const [name, ...rest] = part.trim().split('=');
    if (!name || rest.length === 0) continue;
    cookies[name] = decodeURIComponent(rest.join('='));
  }
  return cookies;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function roleList(value: unknown): string[] {
  if (Array.isArray(value)) return value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0).map((item) => item.trim());
  if (typeof value === 'string' && value.trim()) return [value.trim()];
  return [];
}

function localAuthUsers(): LocalAuthUser[] {
  const raw = String(process.env.PHASE3_AUTH_USERS_JSON || '').trim();
  if (!raw) return [];
  const parsed = JSON.parse(raw) as unknown;
  if (!Array.isArray(parsed)) throw new Error('auth_provider_unavailable:local_auth_users_must_be_array');
  return parsed.map((entry, index) => {
    if (!isRecord(entry)) throw new Error(`auth_provider_unavailable:local_auth_user_invalid:${index}`);
    const user = {
      username: typeof entry.username === 'string' ? entry.username.trim() : '',
      password_hash: typeof entry.password_hash === 'string' ? entry.password_hash.trim() : '',
      subject_id: typeof entry.subject_id === 'string' ? entry.subject_id.trim() : '',
      tenant_id: typeof entry.tenant_id === 'string' ? entry.tenant_id.trim() : '',
      roles: roleList(entry.roles),
    };
    if (!user.username || !user.password_hash || !user.subject_id || !user.tenant_id || user.roles.length === 0) {
      throw new Error(`auth_provider_unavailable:local_auth_user_incomplete:${index}`);
    }
    return user;
  });
}

function verifyScryptPassword(password: string, encodedHash: string): boolean {
  const parts = encodedHash.split('$');
  if (parts.length !== 3 || parts[0] !== 'scrypt') throw new Error('auth_provider_unavailable:unsupported_password_hash');
  const salt = Buffer.from(parts[1] || '', 'hex');
  const expected = Buffer.from(parts[2] || '', 'hex');
  if (salt.length < 8 || expected.length < 16) throw new Error('auth_provider_unavailable:malformed_password_hash');
  const actual = scryptSync(password, salt, expected.length);
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}

function sessionSigningSecret(): string {
  return process.env.AUTH_TOKEN_SECRET || 'phase3-local-dev-secret';
}

function signFrozenBackendSession(claims: FrozenBackendSession): string {
  const body = Buffer.from(JSON.stringify(claims), 'utf-8').toString('base64url');
  const signature = createHmac('sha256', sessionSigningSecret()).update(body).digest('base64url');
  return `${body}.${signature}`;
}

function readFrozenBackendSession(token: string | undefined): FrozenBackendSession | null {
  if (!token) return null;
  const [body, signature, extra] = token.split('.');
  if (!body || !signature || extra) return null;
  const expected = createHmac('sha256', sessionSigningSecret()).update(body).digest();
  const actual = Buffer.from(signature, 'base64url');
  if (actual.length !== expected.length || !timingSafeEqual(actual, expected)) return null;
  try {
    const parsed = JSON.parse(Buffer.from(body, 'base64url').toString('utf-8')) as unknown;
    if (!isRecord(parsed)) return null;
    const roles = roleList(parsed.roles);
    const claims: FrozenBackendSession = {
      subject_id: typeof parsed.subject_id === 'string' ? parsed.subject_id : '',
      tenant_id: typeof parsed.tenant_id === 'string' ? parsed.tenant_id : '',
      roles,
      session_id: typeof parsed.session_id === 'string' ? parsed.session_id : '',
      preferred_username: typeof parsed.preferred_username === 'string' ? parsed.preferred_username : '',
      exp: typeof parsed.exp === 'number' ? parsed.exp : 0,
    };
    if (!claims.subject_id || !claims.tenant_id || !claims.session_id || claims.roles.length === 0 || claims.exp <= Math.floor(Date.now() / 1000)) return null;
    return claims;
  } catch {
    return null;
  }
}

function authenticateFrozenBackendUser(username: string, password: string): FrozenBackendSession {
  const users = localAuthUsers();
  if (users.length === 0) throw new Error('auth_provider_unavailable:no_local_product_users');
  const user = users.find((entry) => entry.username === username.trim());
  if (!user || !password || !verifyScryptPassword(password, user.password_hash)) throw new Error('invalid_credentials');
  const ttl = Math.max(60, Number.parseInt(process.env.WFF_PRODUCT_SESSION_TTL_SECONDS || '900', 10) || 900);
  return {
    subject_id: user.subject_id,
    tenant_id: user.tenant_id,
    roles: [...user.roles],
    session_id: `session-${randomUUID()}`,
    preferred_username: user.username,
    exp: Math.floor(Date.now() / 1000) + ttl,
  };
}

function publicFrozenBackendSession(session: FrozenBackendSession): Record<string, unknown> {
  return {
    subject_id: session.subject_id,
    tenant_id: session.tenant_id,
    roles: session.roles,
    session_id: session.session_id,
    preferred_username: session.preferred_username,
    expires_in: Math.max(0, session.exp - Math.floor(Date.now() / 1000)),
  };
}

async function readRequestBody(request: import("node:http").IncomingMessage): Promise<string> {
  return await new Promise<string>((resolve, reject) => {
    let data = '';
    request.setEncoding('utf-8');
    request.on('data', (chunk) => { data += chunk; });
    request.on('end', () => resolve(data));
    request.on('error', reject);
  });
}

function sessionCookie(token: string, maxAgeSeconds: number): string {
  const secure = process.env.WFF_SESSION_COOKIE_SECURE === 'true' ? '; Secure' : '';
  return `${sessionCookieName}=${encodeURIComponent(token)}; HttpOnly; SameSite=Strict; Path=/; Max-Age=${Math.max(0, maxAgeSeconds)}${secure}`;
}

function buildUpstreamHeaders(request: import("node:http").IncomingMessage): Headers {
  const headers = new Headers();
  for (const [key, value] of Object.entries(request.headers)) {
    if (
      value == null
      || key === 'host'
      || key === 'connection'
      || key === 'content-length'
      || key === 'cookie'
      || key === 'authorization'
      || key === 'x-phase3-auth-context'
    ) {
      continue;
    }
    if (Array.isArray(value)) {
      headers.set(key, value.join(', '));
      continue;
    }
    headers.set(key, value);
  }
  const token = parseCookies(request)[sessionCookieName];
  if (frozenBackendAuthAdapter) {
    const session = readFrozenBackendSession(token);
    if (session) {
      headers.set('x-phase3-auth-context', encodeURIComponent(JSON.stringify({
        tenant_id: session.tenant_id,
        subject_id: session.subject_id,
        session_id: session.session_id,
        roles: session.roles,
      })));
    }
  } else if (token) {
    headers.set('authorization', `Bearer ${token}`);
  }
  return headers;
}

function copyUpstreamHeaders(upstreamResponse: Response, response: import("node:http").ServerResponse): void {
  for (const [key, value] of upstreamResponse.headers.entries()) {
    if (key === 'content-length' || key === 'transfer-encoding' || key === 'connection') {
      continue;
    }
    response.setHeader(key, value);
  }
}

createServer(async (req, res) => {
  const url = new URL(req.url ?? '/', `http://${host}:${port}`);
  if (url.pathname === '/runtime-proof') {
    const proof = await buildRuntimeProof();
    res.statusCode = (proof.ok as boolean) ? 200 : 503;
    res.setHeader('content-type', 'application/json; charset=utf-8');
    res.end(JSON.stringify(proof));
    return;
  }

  if (url.pathname === '/auth/session' && req.method === 'GET') {
    try {
      if (frozenBackendAuthAdapter) {
        const session = readFrozenBackendSession(parseCookies(req)[sessionCookieName]);
        if (!session) {
          res.statusCode = 401;
          res.setHeader('content-type', 'application/json; charset=utf-8');
          res.end(JSON.stringify({ error_kind: 'auth_error', error_code: 'missing_product_session' }));
          return;
        }
        res.statusCode = 200;
        res.setHeader('content-type', 'application/json; charset=utf-8');
        res.end(JSON.stringify({ data: publicFrozenBackendSession(session) }));
        return;
      }
      const headers = buildUpstreamHeaders(req);
      const authorization = headers.get('authorization');
      if (!authorization) {
        res.statusCode = 401;
        res.setHeader('content-type', 'application/json; charset=utf-8');
        res.end(JSON.stringify({ error_kind: 'auth_error', error_code: 'missing_product_session' }));
        return;
      }
      const upstreamResponse = await fetch(`${normalizedApiBaseUrl}/auth/session`, { method: 'GET', headers });
      const responseText = await upstreamResponse.text();
      res.statusCode = upstreamResponse.status;
      res.setHeader('content-type', upstreamResponse.headers.get('content-type') ?? 'application/json; charset=utf-8');
      res.end(responseText);
    } catch (error) {
      res.statusCode = 502;
      res.setHeader('content-type', 'application/json; charset=utf-8');
      res.end(JSON.stringify({ error_kind: 'system_error', error_code: 'auth_session_status_gateway_failed', detail: String(error) }));
    }
    return;
  }

  if (url.pathname === '/auth/session' && req.method === 'POST') {
    try {
      const requestBody = await readRequestBody(req);
      if (frozenBackendAuthAdapter) {
        const parsed = JSON.parse(requestBody || '{}') as unknown;
        const body = isRecord(parsed) ? parsed : {};
        const username = typeof body.username === 'string' ? body.username : '';
        const password = typeof body.password === 'string' ? body.password : '';
        const session = authenticateFrozenBackendUser(username, password);
        const token = signFrozenBackendSession(session);
        const expiresIn = Math.max(0, session.exp - Math.floor(Date.now() / 1000));
        res.statusCode = 200;
        res.setHeader('content-type', 'application/json; charset=utf-8');
        res.setHeader('set-cookie', sessionCookie(token, expiresIn));
        res.end(JSON.stringify({ data: publicFrozenBackendSession(session) }));
        return;
      }
      const upstreamResponse = await fetch(`${normalizedApiBaseUrl}/auth/session`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: requestBody,
      });
      const responseText = await upstreamResponse.text();
      res.statusCode = upstreamResponse.status;
      res.setHeader('content-type', upstreamResponse.headers.get('content-type') ?? 'application/json; charset=utf-8');
      if (!upstreamResponse.ok) {
        res.end(responseText);
        return;
      }
      const payload = JSON.parse(responseText) as { data?: Record<string, unknown> };
      const data = payload && typeof payload === 'object' && payload.data && typeof payload.data === 'object' ? payload.data : {};
      const token = typeof data.access_token === 'string' ? data.access_token : '';
      const expiresIn = Number(data.expires_in ?? 0);
      if (!token || !Number.isFinite(expiresIn) || expiresIn <= 0) {
        res.statusCode = 502;
        res.end(JSON.stringify({ error_kind: 'system_error', error_code: 'auth_session_response_invalid' }));
        return;
      }
      res.setHeader('set-cookie', sessionCookie(token, expiresIn));
      const publicSession = { ...data };
      delete publicSession.access_token;
      res.end(JSON.stringify({ data: publicSession }));
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const invalidCredentials = message.includes('invalid_credentials');
      const providerUnavailable = message.includes('auth_provider_unavailable');
      res.statusCode = invalidCredentials ? 401 : providerUnavailable ? 503 : 502;
      res.setHeader('content-type', 'application/json; charset=utf-8');
      res.end(JSON.stringify({
        error_kind: invalidCredentials ? 'auth_error' : 'system_error',
        error_code: invalidCredentials ? 'invalid_credentials' : providerUnavailable ? 'auth_provider_unavailable' : 'auth_session_gateway_failed',
      }));
    }
    return;
  }

  if (url.pathname === '/auth/session' && req.method === 'DELETE') {
    res.statusCode = 204;
    res.setHeader('set-cookie', sessionCookie('', 0));
    res.end();
    return;
  }

  if (url.pathname === '/api' || url.pathname.startsWith('/api/')) {
    runtimeTraffic.api_request_count += 1;
    const upstream = `${normalizedApiBaseUrl}${url.pathname}${url.search}`;
    try {
      const requestBody = await readRequestBody(req);
      if (req.headers.authorization !== undefined) {
        runtimeTraffic.browser_authorization_header_request_count += 1;
      }
      const headers = buildUpstreamHeaders(req);
      const authorization = headers.get('authorization');
      if (typeof authorization === 'string' && /^Bearer\s+\S+/i.test(authorization.trim())) {
        runtimeTraffic.authorized_api_request_count += 1;
      }
      if (headers.has('x-phase3-auth-context')) {
        runtimeTraffic.frozen_backend_auth_context_request_count += 1;
      }
      if (req.headers['x-phase3-auth-context'] !== undefined) {
        runtimeTraffic.phase3_auth_context_request_count += 1;
      }
      const method = req.method ?? 'GET';
      const upstreamResponse = await fetch(upstream, {
        method,
        headers,
        body: requestBody.length > 0 && method !== 'GET' && method !== 'DELETE' ? requestBody : undefined,
      });
      const responseText = await upstreamResponse.text();
      res.statusCode = upstreamResponse.status;
      copyUpstreamHeaders(upstreamResponse, res);
      res.setHeader('content-type', upstreamResponse.headers.get('content-type') ?? 'application/json; charset=utf-8');
      res.end(responseText);
    } catch (error) {
      res.statusCode = 502;
      res.setHeader('content-type', 'application/json; charset=utf-8');
      res.end(JSON.stringify({ error: 'bad_gateway', detail: String(error) }));
    }
    return;
  }

  const assetPath = url.pathname === '/' ? '/index.html' : url.pathname;
  try {
    const file = await readFile(join(distDir, assetPath.replace(/^\//, '')));
    if (assetPath.endsWith('.js')) {
      res.setHeader('content-type', 'application/javascript; charset=utf-8');
    } else if (assetPath.endsWith('.css')) {
      res.setHeader('content-type', 'text/css; charset=utf-8');
    } else {
      res.setHeader('content-type', 'text/html; charset=utf-8');
    }
    res.statusCode = 200;
    res.end(file);
    return;
  } catch {
    const indexHtml = await readFile(join(distDir, 'index.html'));
    res.statusCode = 200;
    res.setHeader('content-type', 'text/html; charset=utf-8');
    res.end(indexHtml);
    return;
  }
}).listen(port, host, () => {
  process.stdout.write(`[web] listening on http://${host}:${port}\n`);
});
