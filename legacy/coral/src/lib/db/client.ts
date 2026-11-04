/**
 * Database connection.
 *
 * SQLite on the application host. This is a deliberate MVP choice that fits the
 * product: sovereignty means we run on our own Australian infrastructure rather
 * than someone else's serverless platform, so a local durable file is coherent.
 * Drizzle keeps the move to Postgres a dialect change rather than a rewrite.
 */

import { existsSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";
import Database from "better-sqlite3";
import { drizzle, type BetterSQLite3Database } from "drizzle-orm/better-sqlite3";
import { databaseUrl } from "@/lib/config";
import * as schema from "./schema";

let db: BetterSQLite3Database<typeof schema> | null = null;
let sqlite: Database.Database | null = null;

export function getSqlite(): Database.Database {
  if (!sqlite) {
    const url = databaseUrl();
    if (url !== ":memory:") {
      const dir = dirname(url);
      if (dir && dir !== "." && !existsSync(dir)) mkdirSync(dir, { recursive: true });
    }
    sqlite = new Database(url);
    sqlite.pragma("journal_mode = WAL");
    sqlite.pragma("foreign_keys = ON");
  }
  return sqlite;
}

export function getDb(): BetterSQLite3Database<typeof schema> {
  if (!db) db = drizzle(getSqlite(), { schema });
  return db;
}

/** Test helper — drops the cached connection so a new DATABASE_URL takes effect. */
export function resetDb(): void {
  sqlite?.close();
  sqlite = null;
  db = null;
}

export { schema };
