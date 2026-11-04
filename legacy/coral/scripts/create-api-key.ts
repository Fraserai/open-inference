/**
 * Issues an API key to an organisation, creating the organisation if needed.
 *
 *   npx tsx scripts/create-api-key.ts --org "Acme Pty Ltd" --name "production"
 *
 * The plaintext key is printed ONCE and never stored. If it is lost, revoke it
 * and issue another.
 */

import { loadEnvFiles } from "@/lib/load-env";

loadEnvFiles();

import { randomUUID } from "node:crypto";
import { eq } from "drizzle-orm";
import { getDb } from "@/lib/db/client";
import { runMigrations } from "@/lib/db/migrate";
import { apiKeys, organisations } from "@/lib/db/schema";
import { generateApiKey } from "@/lib/auth/apiKeys";

function arg(flag: string, fallback?: string): string {
  const i = process.argv.indexOf(flag);
  const value = i >= 0 ? process.argv[i + 1] : undefined;
  if (value === undefined) {
    if (fallback !== undefined) return fallback;
    throw new Error(`Missing required argument ${flag}`);
  }
  return value;
}

function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

runMigrations();

const orgName = arg("--org");
const keyName = arg("--name", "default");
const abn = arg("--abn", "");
const email = arg("--email", "");
const slug = slugify(orgName);

const db = getDb();

let org = db.select().from(organisations).where(eq(organisations.slug, slug)).limit(1).all()[0];
if (!org) {
  const row = {
    id: randomUUID(),
    name: orgName,
    slug,
    country: "AU",
    abn: abn || null,
    contactEmail: email || null,
    status: "active" as const,
    createdAt: new Date(),
  };
  db.insert(organisations).values(row).run();
  org = row;
  console.log(`Created organisation "${orgName}" (${org.id})`);
} else {
  console.log(`Using existing organisation "${org.name}" (${org.id})`);
}

const generated = generateApiKey();
db.insert(apiKeys)
  .values({
    id: generated.id,
    organisationId: org.id,
    name: keyName,
    keyPrefix: generated.keyPrefix,
    keyHash: generated.keyHash,
    lastFour: generated.lastFour,
    status: "active",
    createdAt: new Date(),
  })
  .run();

console.log("");
console.log("  API key (shown once — store it now):");
console.log(`  ${generated.key}`);
console.log("");
