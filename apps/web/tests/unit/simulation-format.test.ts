import { describe, expect, it } from "vitest";

import {
  canonicalJson,
  formatDecimalString,
  formatHash,
  formatMoney,
  formatPercent,
  zScore,
} from "@/features/simulation/format";

describe("simulation formatters", () => {
  it("formats exact decimal money values", () => {
    expect(formatMoney("1234567.89", "CNY")).toBe("CNY 1,234,567.89");
    expect(formatMoney("-1500", "USD")).toBe("USD -1,500");
    expect(formatMoney("abc1234def.5", "CNY")).toBe("CNY 1,234.5");
  });

  it("reports invalid and empty money inputs", () => {
    expect(formatMoney(123 as unknown as string, "CNY")).toContain("invalid amount");
    expect(formatMoney("", "CNY")).toContain("empty");
  });

  it("formats partial-identification intervals and optional Monte Carlo bounds", () => {
    const value = formatPercent("0.3", "0.6", {
      lower: ["0.28", "0.32"],
      upper: ["0.58", "0.62"],
    });
    expect(value).toContain("[0.3000, 0.6000]");
    expect(value).toContain("P- MC CI [0.2800, 0.3200]");
    expect(value).toContain("P+ MC CI [0.5800, 0.6200]");
    expect(formatPercent("0", "1")).toBe("[0.0000, 1.0000]");
  });

  it("truncates and pads decimals without hidden rounding", () => {
    expect(formatDecimalString("0.123456789", 4)).toBe("0.1234");
    expect(formatDecimalString("0.1", 3)).toBe("0.100");
    expect(formatDecimalString("123.45", 0)).toBe("123");
  });

  it("compacts SHA-256 hashes", () => {
    const hash = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789";
    expect(formatHash(hash)).toBe("abcdef01…23456789");
    expect(formatHash("deadbeef")).toBe("deadbeef");
  });

  it("canonicalizes nested JSON and preserves array order", () => {
    expect(canonicalJson({ b: 2, a: 1 })).toBe('{"a":1,"b":2}');
    expect(canonicalJson({ input_manifest: { as_of: "2026-08-14", rule_set: "v3" } })).toBe(
      '{"input_manifest":{"as_of":"2026-08-14","rule_set":"v3"}}',
    );
    expect(canonicalJson({ a: 1, b: undefined })).toBe('{"a":1}');
    expect(canonicalJson([3, 1, 2])).toBe("[3,1,2]");
    expect(() => canonicalJson(Number.POSITIVE_INFINITY)).toThrow(/non-finite/);
  });

  it("computes a z-score only for finite values and positive deviation", () => {
    expect(zScore("12", "10", "2")).toBe("1.000000");
    expect(zScore("12", "10", "0")).toBeNull();
    expect(zScore("12", "10", "-1")).toBeNull();
    expect(zScore("NaN", "10", "2")).toBeNull();
  });
});
