/****
 * Unit tests for the simulation feature's pure formatters.
 *
 * Run with `pnpm vitest apps/web/src/features/simulation/__tests__/format.test.ts`.
 * We intentionally avoid DOM globals here so the suite runs under the
 * default Vitest node environment.
 */

import { describe, expect, it } from "vitest";

import {
  canonicalJson,
  formatDecimalString,
  formatHash,
  formatMoney,
  formatPercent,
  zScore,
} from "../format";

describe("formatMoney", () => {
  it("formats a plain Decimal with thousand separators and currency code", () => {
    expect(formatMoney("1234567.89", "CNY")).toBe("CNY 1,234,567.89");
  });

  it("preserves negative values", () => {
    expect(formatMoney("-1500", "USD")).toBe("USD -1,500");
  });

  it("returns the input verbatim when not a string", () => {
    expect(formatMoney(123 as unknown as string, "CNY")).toContain("invalid amount");
  });

  it("returns an empty sentinel when input is the empty string", () => {
    expect(formatMoney("", "CNY")).toContain("empty");
  });

  it("strips non-numeric junk from the integer part", () => {
    expect(formatMoney("abc1234def.5", "CNY")).toBe("CNY 1,234.5");
  });
});

describe("formatPercent", () => {
  it("renders a partial identification interval with MC CI", () => {
    var out = formatPercent("0.3", "0.6", { lower: ["0.28", "0.32"], upper: ["0.58", "0.62"] });
    expect(out).toContain("[0.3000, 0.6000]");
    expect(out).toContain("P- MC CI [0.2800, 0.3200]");
    expect(out).toContain("P+ MC CI [0.5800, 0.6200]");
  });

  it("renders without CI when none is provided", () => {
    expect(formatPercent("0", "1")).toBe("[0.0000, 1.0000]");
  });
});

describe("formatDecimalString", () => {
  it("truncates to the requested precision without rounding", () => {
    expect(formatDecimalString("0.123456789", 4)).toBe("0.1234");
  });

  it("pads short values to the requested precision", () => {
    expect(formatDecimalString("0.1", 3)).toBe("0.100");
  });

  it("drops the decimal part entirely when fractionDigits=0", () => {
    expect(formatDecimalString("123.45", 0)).toBe("123");
  });
});

describe("formatHash", () => {
  it("returns a compact SHA-256 representation", () => {
    var sample = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789";
    var expected = "abcdef01…" + "23456789";
    expect(formatHash(sample)).toBe(expected);
    expect(formatHash(sample).length).toBeLessThan(sample.length);
    expect(formatHash(sample)).toMatch(/^.{8}….{8}$/);
  });

  it("returns short hashes unchanged", () => {
    expect(formatHash("deadbeef")).toBe("deadbeef");
  });
});

describe("canonicalJson", () => {
  it("sorts object keys lexicographically", () => {
    expect(canonicalJson({ b: 2, a: 1 })).toBe("{\"a\":1,\"b\":2}");
  });

  it("matches the backend snapshot.py ordering for nested objects", () => {
    expect(
      canonicalJson({ input_manifest: { as_of: "2026-08-14", rule_set: "v3" } }),
    ).toBe("{\"input_manifest\":{\"as_of\":\"2026-08-14\",\"rule_set\":\"v3\"}}");
  });

  it("drops undefined properties to mirror Python json", () => {
    expect(canonicalJson({ a: 1, b: undefined })).toBe("{\"a\":1}");
  });

  it("preserves array order", () => {
    expect(canonicalJson([3, 1, 2])).toBe("[3,1,2]");
  });

  it("rejects non-finite numbers", () => {
    expect(() => canonicalJson(Number.POSITIVE_INFINITY)).toThrow(/non-finite/);
  });
});

describe("zScore", () => {
  it("returns the standard deviation multiplier", () => {
    expect(zScore("12", "10", "2")).toBe("1.000000");
  });

  it("returns null when stddev is non-positive", () => {
    expect(zScore("12", "10", "0")).toBeNull();
    expect(zScore("12", "10", "-1")).toBeNull();
  });

  it("returns null when the inputs are not finite", () => {
    expect(zScore("NaN", "10", "2")).toBeNull();
  });
});
