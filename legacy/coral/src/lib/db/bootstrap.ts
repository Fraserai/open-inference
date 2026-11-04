/**
 * Applies migrations lazily, on the first request that needs the database.
 * Deliberately not run at module load so that `next build` never touches the
 * filesystem database.
 */

import { runMigrations } from "./migrate";

let applied = false;

export function ensureDatabase(): void {
  if (applied) return;
  runMigrations();
  applied = true;
}
