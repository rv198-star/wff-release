import { createServer } from "node:http";
import { URL, pathToFileURL } from "node:url";
import { handleGeneratedApiRequest } from "./generated-api-router.js";
import { checkDatabaseReadiness } from "./runtime/database.js";

const host = process.env.HOST || "0.0.0.0";
const port = Number.parseInt(process.env.PORT || "3000", 10);

function sendJson(
  response: import("node:http").ServerResponse,
  statusCode: number,
  payload: Record<string, unknown>,
): void {
  response.statusCode = statusCode;
  response.setHeader("content-type", "application/json; charset=utf-8");
  response.end(JSON.stringify(payload));
}

export async function createApiServer() {
  return createServer(async (request, response) => {
    const method = request.method || "GET";
    const url = new URL(request.url || "/", `http://${request.headers.host || "localhost"}`);

    if (method === "GET" && url.pathname === "/healthz") {
      sendJson(response, 200, {
        status: "ok",
        service: "phase3-api",
        startup_mode: "runnable-runtime-baseline",
      });
      return;
    }

    if (method === "GET" && url.pathname === "/readyz") {
      const database = await checkDatabaseReadiness();
      sendJson(response, database.ready ? 200 : 503, {
        status: database.ready ? "ready" : "not_ready",
        database,
      });
      return;
    }

    if (method === "GET" && url.pathname === "/") {
      sendJson(response, 200, {
        service: "phase3-api",
        docs_hint: "use /healthz or /readyz for runtime smoke checks",
      });
      return;
    }

    const handled = await handleGeneratedApiRequest(request, response, { sendJson });
    if (handled) {
      return;
    }

    sendJson(response, 404, {
      error_kind: "system_error",
      error_code: "route_not_found",
    });
  });
}

export async function bootstrapApi(): Promise<import("node:http").Server> {
  const server = await createApiServer();
  await new Promise<void>((resolve) => {
    server.listen(port, host, () => resolve());
  });
  return server;
}

const directRun = (() => {
  const entry = process.argv[1];
  return Boolean(entry && import.meta.url === pathToFileURL(entry).href);
})();

if (directRun) {
  bootstrapApi().then((server) => {
    server.on("listening", () => {
      process.stdout.write(`phase3-api listening on http://${host}:${port}\n`);
    });
  });
}
