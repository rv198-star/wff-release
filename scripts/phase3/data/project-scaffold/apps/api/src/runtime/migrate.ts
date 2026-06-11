import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { runMigrations } from "./database.js";

async function loadMigrations(): Promise<string[]> {
  const runtimeDir = fileURLToPath(new URL('.', import.meta.url));
  const migrationsDir = join(runtimeDir, '../../../../db/migrations');
  const entries = (await readdir(migrationsDir)).filter((entry) => entry.endsWith('.sql')).sort();
  const documents: string[] = [];
  for (const entry of entries) {
    documents.push(await readFile(join(migrationsDir, entry), 'utf-8'));
  }
  return documents;
}

async function main(): Promise<void> {
  const documents = await loadMigrations();
  const result = await runMigrations(documents);
  process.stdout.write(`phase3 migrations applied: ${result.applied}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 1;
});
