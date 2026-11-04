import { describe, expect, it } from "vitest";
import {
  evaluateSovereignty,
  isAustralian,
  validateAustralianClaim,
  type SovereigntyClaim,
} from "@/lib/sovereignty";

const auClaim: SovereigntyClaim = {
  inferenceCountry: "AU",
  weightCountry: "AU",
  infrastructureRegion: "au-syd-1",
  infrastructureProvider: "firmus",
  weightLocation: "firmus:au-syd-1:vault/kimi-k3",
};

describe("sovereignty rules", () => {
  it("accepts only AU", () => {
    expect(isAustralian("AU")).toBe(true);
    expect(isAustralian("au")).toBe(true);
    expect(isAustralian("US")).toBe(false);
    expect(isAustralian("NZ")).toBe(false);
    expect(isAustralian(undefined)).toBe(false);
  });

  it("rejects a deployment whose inference runs offshore", () => {
    const errors = validateAustralianClaim({ ...auClaim, inferenceCountry: "US" });
    expect(errors.join(" ")).toContain("inference country");
  });

  it("rejects a deployment whose weights are stored offshore", () => {
    const errors = validateAustralianClaim({ ...auClaim, weightCountry: "SG" });
    expect(errors.join(" ")).toContain("weight country");
  });

  it("does not mark a configured-but-unverified AU deployment as sovereign", () => {
    const result = evaluateSovereignty(auClaim, false);
    expect(result.status).toBe("configured_unverified");
    expect(result.isSovereign).toBe(false);
  });

  it("marks an AU deployment sovereign only with a complete verification record", () => {
    const verified = evaluateSovereignty(
      {
        ...auClaim,
        verification: {
          verifiedBy: "ops@example.com",
          verifiedAt: "2026-09-01",
          method: "provider attestation and contract schedule",
        },
      },
      false,
    );
    expect(verified.status).toBe("verified");
    expect(verified.isSovereign).toBe(true);
  });

  it("treats a partial verification record as no verification", () => {
    const partial = evaluateSovereignty(
      {
        ...auClaim,
        verification: { verifiedBy: "ops@example.com", verifiedAt: "", method: "" },
      },
      false,
    );
    expect(partial.isSovereign).toBe(false);
  });

  it("never marks a development mock as sovereign, whatever it claims", () => {
    const mock = evaluateSovereignty(
      {
        ...auClaim,
        verification: { verifiedBy: "x", verifiedAt: "y", method: "z" },
      },
      true,
    );
    expect(mock.status).toBe("development_mock");
    expect(mock.isSovereign).toBe(false);
  });

  it("treats a missing deployment as not configured", () => {
    expect(evaluateSovereignty(undefined, false).status).toBe("not_configured");
  });
});
