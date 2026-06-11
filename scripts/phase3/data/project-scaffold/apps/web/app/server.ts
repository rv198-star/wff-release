import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { URL } from "node:url";

const host = process.env.HOST ?? "0.0.0.0";
const port = Number.parseInt(process.env.WEB_PORT ?? "3100", 10);
const apiBaseUrl = process.env.WEB_API_BASE_URL ?? "http://localhost:3000";
const normalizedApiBaseUrl = apiBaseUrl.replace(/\/$/, "");

const distDir = join(process.cwd(), "dist");

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
    checked_at: new Date().toISOString(),
  };
}

function buildUpstreamHeaders(request: import("node:http").IncomingMessage): Headers {
  const headers = new Headers();
  for (const [key, value] of Object.entries(request.headers)) {
    if (value == null || key === 'host' || key === 'connection' || key === 'content-length') {
      continue;
    }
    if (Array.isArray(value)) {
      headers.set(key, value.join(', '));
      continue;
    }
    headers.set(key, value);
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

  if (url.pathname === '/api' || url.pathname.startsWith('/api/')) {
    const upstream = `${normalizedApiBaseUrl}${url.pathname}${url.search}`;
    try {
      const requestBody = await new Promise<string>((resolve, reject) => {
        let data = '';
        req.setEncoding('utf-8');
        req.on('data', (chunk) => { data += chunk; });
        req.on('end', () => resolve(data));
        req.on('error', reject);
      });
      const headers = buildUpstreamHeaders(req);
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
