import { describe, expect, it } from "vitest";
import { extractBearerToken, generateApiKey, hashApiKey, KEY_PREFIX } from "@/lib/auth/apiKeys";

describe("api keys", () => {
  it("generates prefixed, high-entropy, unique keys", () => {
    const a = generateApiKey();
    const b = generateApiKey();
    expect(a.key.startsWith(KEY_PREFIX)).toBe(true);
    expect(a.key).not.toBe(b.key);
    expect(a.key.length).toBeGreaterThan(40);
  });

  it("stores a hash, never the key itself", () => {
    const generated = generateApiKey();
    expect(generated.keyHash).toBe(hashApiKey(generated.key));
    expect(generated.keyHash).not.toContain(generated.key);
    expect(generated.keyPrefix.length).toBeLessThan(generated.key.length);
  });

  it("parses bearer tokens and rejects anything else", () => {
    expect(extractBearerToken("Bearer abc123")).toBe("abc123");
    expect(extractBearerToken("bearer abc123")).toBe("abc123");
    expect(extractBearerToken("abc123")).toBeNull();
    expect(extractBearerToken("Bearer ")).toBeNull();
    expect(extractBearerToken(null)).toBeNull();
  });
});
