import { Client } from "pg";

export interface DatabaseReadiness {
  ready: boolean;
  reason?: string;
  provider?: string;
}

function databaseConnectionTimeoutMillis(): number {
  return Number.parseInt(process.env.PHASE3_DB_CONNECT_TIMEOUT_MS || '3000', 10);
}

function databaseStatementTimeoutMillis(): number {
  return Number.parseInt(process.env.PHASE3_DB_STATEMENT_TIMEOUT_MS || '5000', 10);
}

function createDatabaseClient(connectionString: string): Client {
  return new Client({
    connectionString,
    connectionTimeoutMillis: databaseConnectionTimeoutMillis(),
    statement_timeout: databaseStatementTimeoutMillis(),
    query_timeout: databaseStatementTimeoutMillis(),
  });
}

export async function checkDatabaseReadiness(): Promise<DatabaseReadiness> {
  const connectionString = process.env.DATABASE_URL || "";
  if (!connectionString) {
    return { ready: false, reason: "database_url_missing" };
  }
  const client = createDatabaseClient(connectionString);
  try {
    await client.connect();
    await client.query("select 1 as ok");
    return { ready: true, provider: "postgresql" };
  } catch (error) {
    return { ready: false, reason: error instanceof Error ? error.message : "db_probe_failed" };
  } finally {
    await client.end().catch(() => undefined);
  }
}

export async function runMigrations(sqlDocuments: string[]): Promise<{ applied: number }> {
  const connectionString = process.env.DATABASE_URL || "";
  if (!connectionString) {
    throw new Error("DATABASE_URL is required for migrations");
  }
  const client = createDatabaseClient(connectionString);
  await client.connect();
  try {
    await client.query("CREATE SCHEMA IF NOT EXISTS public");
    await client.query("SET search_path TO public");
    for (const document of sqlDocuments) {
      if (document.trim()) {
        await client.query(document);
      }
    }
    return { applied: sqlDocuments.length };
  } finally {
    await client.end();
  }
}
