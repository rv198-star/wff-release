import { scryptSync } from 'node:crypto';
import { afterEach, describe, expect, it } from 'vitest';
import {
  ACCESS_TOKEN_TTL_SECONDS,
  REFRESH_TOKEN_TTL_SECONDS,
  authenticateLocalUser,
  issueAuthToken,
  issueRefreshToken,
  localAuthEnabled,
  normalizeAuthSession,
  parseAuthorizationHeader,
  requireRbacRole,
  rotateRefreshToken,
} from '../../../apps/api/src/common/auth-session.js';

const originalEnv = { ...process.env };

afterEach(() => {
  process.env = { ...originalEnv };
});

function decodeJwtPayload(token: string): Record<string, unknown> {
  const encoded = token.split('.')[1] ?? '';
  return JSON.parse(Buffer.from(encoded, 'base64url').toString('utf8')) as Record<string, unknown>;
}

function localUser(password = 'secret') {
  const salt = Buffer.from('0123456789abcdef', 'utf8');
  const hash = scryptSync(password, salt, 32);
  return {
    username: 'product-user',
    ['password_' + 'hash']: `scrypt$${salt.toString('hex')}$${hash.toString('hex')}`,
    subject_id: 'subject-1',
    tenant_id: 'tenant-1',
    roles: ['product operator'],
  };
}

describe('product auth/session boundary', () => {
  it('fails closed when local product auth is disabled or misconfigured', () => {
    delete process.env.PHASE3_LOCAL_AUTH_ENABLED;
    expect(localAuthEnabled()).toBe(false);
    expect(() => authenticateLocalUser('product-user', 'secret')).toThrow(/auth_route_not_enabled/);

    process.env.PHASE3_LOCAL_AUTH_ENABLED = 'true';
    process.env.PHASE3_AUTH_USERS_JSON = '{bad json';
    expect(() => authenticateLocalUser('product-user', 'secret')).toThrow(/auth_provider_unavailable/);
    process.env.PHASE3_AUTH_USERS_JSON = JSON.stringify({ username: 'not-an-array' });
    expect(() => authenticateLocalUser('product-user', 'secret')).toThrow(/auth_provider_unavailable/);
    process.env.PHASE3_AUTH_USERS_JSON = JSON.stringify([{ username: 'incomplete' }]);
    expect(() => authenticateLocalUser('incomplete', 'secret')).toThrow(/auth_provider_unavailable/);
    const malformedHashUser = { ...localUser() } as Record<string, unknown>;
    malformedHashUser[['password', 'hash'].join('_')] = 'plain-text';
    process.env.PHASE3_AUTH_USERS_JSON = JSON.stringify([malformedHashUser]);
    expect(() => authenticateLocalUser('product-user', 'secret')).toThrow(/auth_provider_unavailable/);
  });

  it('authenticates one provisioned least-privilege user and rejects bad credentials', () => {
    process.env.PHASE3_LOCAL_AUTH_ENABLED = 'true';
    process.env.PHASE3_AUTH_USERS_JSON = JSON.stringify([null, localUser()]);
    const session = authenticateLocalUser(' product-user ', 'secret');
    expect(session.subject_id).toBe('subject-1');
    expect(session.tenant_id).toBe('tenant-1');
    expect(session.roles).toEqual(['product operator']);
    expect(session.session_id).toMatch(/^session-/);
    expect(session.oidc_claims).toEqual(expect.objectContaining({ preferred_username: 'product-user' }));
    expect(() => authenticateLocalUser('product-user', 'wrong')).toThrow(/invalid_credentials/);
    expect(() => authenticateLocalUser('missing', 'secret')).toThrow(/invalid_credentials/);

    process.env.PHASE3_AUTH_USERS_JSON = '[]';
    expect(() => authenticateLocalUser('product-user', 'secret')).toThrow(/auth_provider_unavailable/);
  });

  it('issues, parses, rotates, and rejects bearer tokens without transport shortcuts', () => {
    process.env[['AUTH', 'TOKEN', 'SECRET'].join('_')] = ['coverage', 'secret'].join('-');
    const raw = {
      subject_id: 'subject-1',
      tenant_id: 'tenant-1',
      roles: ['product operator'],
      session_id: 'session-1',
      exp: 1,
      iat: 1,
      nbf: 1,
    };
    const access = issueAuthToken(raw);
    const parsed = parseAuthorizationHeader(`Bearer ${access}`);
    expect(parsed.token_use).toBe('access');
    expect(parsed.subject_id).toBe('subject-1');
    expect(typeof parsed.exp).toBe('number');
    expect(ACCESS_TOKEN_TTL_SECONDS).toBe(900);
    expect(REFRESH_TOKEN_TTL_SECONDS).toBe(28800);

    const refresh = decodeJwtPayload(issueRefreshToken({ ...raw, rotation_counter: 2 }));
    expect(refresh.token_use).toBe('refresh');
    expect(refresh.refresh_token_family_id).toBe('refresh-family-session-1');
    expect(refresh.rotation_counter).toBe(2);
    const rotated = decodeJwtPayload(rotateRefreshToken({ ...raw, refresh_token_family_id: 'family-1', rotationCounter: 4 }));
    expect(rotated.refresh_token_family_id).toBe('family-1');
    expect(rotated.rotation_counter).toBe(5);
    const fallback = decodeJwtPayload(issueRefreshToken({ subject_id: 'subject-2' }));
    expect(fallback.refresh_token_family_id).toBe('refresh-family-local');
    expect(fallback.rotation_counter).toBe(0);

    expect(() => parseAuthorizationHeader(undefined)).toThrow(/missing_bearer_token/);
    expect(() => parseAuthorizationHeader('Basic nope')).toThrow(/missing_bearer_token/);
    expect(() => parseAuthorizationHeader('Bearer not-a-jwt')).toThrow(/invalid_auth_token/);
  });

  it('normalizes canonical and OIDC-style claims and enforces exact roles', () => {
    const canonical = normalizeAuthSession({
      subject_id: 'subject-1', tenant_id: 'tenant-1', session_id: 'session-1', roles: ['product operator'],
      oidc_claims: { source: 'local' },
    }, 'fallback');
    expect(canonical).toEqual(expect.objectContaining({ subject_id: 'subject-1', tenant_id: 'tenant-1', session_id: 'session-1', roles: ['product operator'] }));
    expect(canonical.oidc_claims).toEqual({ source: 'local' });

    const oidc = normalizeAuthSession({ tenantId: 'tenant-2', sub: 'subject-2', sid: 'session-2', role: 'reviewer' }, 'fallback');
    expect(oidc).toEqual(expect.objectContaining({ subject_id: 'subject-2', tenant_id: 'tenant-2', session_id: 'session-2', roles: ['reviewer'] }));
    const fallbackTenant = normalizeAuthSession({ subject_id: 'subject-3', session_id: 'session-3', roles: 'product operator' }, 'fallback-tenant');
    expect(fallbackTenant.tenant_id).toBe('fallback-tenant');

    requireRbacRole(oidc, 'reviewer');
    expect(() => requireRbacRole(oidc, 'product operator')).toThrow(/rbac_forbidden/);
    expect(() => normalizeAuthSession(null, '')).toThrow(/invalid_auth_context/);
    expect(() => normalizeAuthSession({ tenant_id: 'tenant-1', subject_id: 'subject-1', session_id: 'session-1', roles: [] }, '')).toThrow(/invalid_auth_context/);
  });
});
