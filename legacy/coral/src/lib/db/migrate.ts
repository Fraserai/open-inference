/**
 * Applies the SQL migrations in ./drizzle to the configured database.
 * Idempotent: safe to run on every deploy and on every boot.
 */

import { loadEnvFiles } from "@/lib/load-env";

loadEnvFiles();

import { resolve } from "node:path";
import { migrate } from "drizzle-orm/better-sqlite3/migrator";
import { getDb } from "./client";
import { databaseUrl } from "@/lib/config";

export function runMigrations(): void {
  migrate(getDb(), { migrationsFolder: resolve(process.cwd(), "drizzle") });
}

if (process.argv[1] && process.argv[1].endsWith("migrate.ts")) {
  runMigrations();
  console.log(`Migrations applied to ${databaseUrl()}`);
}
