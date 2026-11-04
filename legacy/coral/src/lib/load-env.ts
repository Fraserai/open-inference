/**
 * Loads .env.local then .env for CLI scripts.
 *
 * Next.js does this itself for the running application; standalone scripts do
 * not get it for free, and a sovereignty audit that reads the wrong environment
 * would report the wrong posture. Existing process environment always wins, so
 * real deployment secrets can be injected without a file.
 */

import { existsSync } from "node:fs";

export function loadEnvFiles(): void {
  for (const file of [".env.local", ".env"]) {
    if (!existsSync(file)) continue;
    try {
      process.loadEnvFile(file);
    } catch {
      // Unreadable or malformed file; the caller reports on what it actually has.
    }
  }
}
