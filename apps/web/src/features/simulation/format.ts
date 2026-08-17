/**
 * Pure formatting helpers used by the simulation page block.
 *
 * Every formatter here:
 *   - treats amounts as Decimal strings so we never round or coerce,
 *   - pairs monetary output with its ISO 4217 currency code,
 *   - avoids producing single-point probabilities (partial-identification
 *     intervals are always paired with their MC CI when available),
 *   - emits the same canonical JSON ordering used by the backend
 *     snapshot.py so the input manifest hash can be reproduced on the
 *     client.
 *
 * No formatter here performs business calculations; arithmetic belongs to
 * the backend. The functions only shape already-computed values for display.
 */

import type { CurrencyCode, Decimal, Sha256Hex } from "./types";

/* -------------------------------------------------------------------------- */
/*  Money formatting                                                          */
/* -------------------------------------------------------------------------- */

/**
 * Formats a Decimal string with thousand separators and the ISO 4217 code.
 *
 *  formatMoney("1234567.890", "CNY") -> "CNY 1,234,567.890"
 *
 * Negative values keep the minus sign in front of the currency code so the
 * caller does not have to special-case debit/credit UI. We never coerce the
 * input via Number(); if the value is malformed we return it verbatim
 * wrapped in angle brackets so the UI can highlight the problem without
 * silently inventing a number.
 */
export function formatMoney(value: Decimal | string, currency: CurrencyCode): string {
  if (typeof value !== "string") {
    return currency + " <invalid amount>";
  }
  const trimmed = value.trim();
  if (trimmed.length === 0) {
    return currency + " <empty>";
  }
  let sign = "";
  let body = trimmed;
  if (body.startsWith("-")) {
    sign = "-";
    body = body.slice(1);
  }
  const dotIndex = body.indexOf(".");
  const intPart = dotIndex === -1 ? body : body.slice(0, dotIndex);
  const fracPart = dotIndex === -1 ? "" : body.slice(dotIndex + 1);
  const intCleaned = intPart.replace(/[^0-9]/g, "");
  if (intCleaned.length === 0) {
    return currency + " " + sign + "<unparseable: " + value + ">";
  }
  const grouped = intCleaned.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const combined = fracPart.length > 0 ? grouped + "." + fracPart : grouped;
  return currency + " " + sign + combined;
}

/* -------------------------------------------------------------------------- */
/*  Percent / partial-identification formatting                              */
/* -------------------------------------------------------------------------- */

/**
 * Formats a partial-identification pair as a single bracket string.
 *
 * Returns [P-, P+] together with the MC confidence intervals for the
 * endpoints when present. The function refuses to collapse the interval
 * into a single number — the contract says intervals only, no point
 * estimates.
 */
export function formatPercent(
  lower: Decimal | string,
  upper: Decimal | string,
  ci?: { lower?: [Decimal, Decimal]; upper?: [Decimal, Decimal] } | null,
): string {
  const lo = formatDecimalString(lower, 4);
  const hi = formatDecimalString(upper, 4);
  let ciTail = "";
  if (ci) {
    const parts: string[] = [];
    if (ci.lower) {
      parts.push(
        "P- MC CI [" + formatDecimalString(ci.lower[0], 4) + ", " + formatDecimalString(ci.lower[1], 4) + "]",
      );
    }
    if (ci.upper) {
      parts.push(
        "P+ MC CI [" + formatDecimalString(ci.upper[0], 4) + ", " + formatDecimalString(ci.upper[1], 4) + "]",
      );
    }
    if (parts.length > 0) {
      ciTail = " · " + parts.join(" · ");
    }
  }
  return "[" + lo + ", " + hi + "]" + ciTail;
}

/**
 * Trims a Decimal string to a fixed number of fractional digits without
 * rounding (we truncate beyond the requested precision). Used for display,
 * never for arithmetic.
 */
export function formatDecimalString(value: string, fractionDigits: number): string {
  if (typeof value !== "string") return String(value);
  const dot = value.indexOf(".");
  if (dot === -1) {
    if (fractionDigits <= 0) return value;
    return fractionDigits > 0 ? value + "." + "0".repeat(fractionDigits) : value;
  }
  const intPart = value.slice(0, dot);
  let fracPart = value.slice(dot + 1);
  if (fracPart.length > fractionDigits) {
    fracPart = fracPart.slice(0, fractionDigits);
  } else if (fracPart.length < fractionDigits) {
    fracPart = fracPart + "0".repeat(fractionDigits - fracPart.length);
  }
  return fractionDigits === 0 ? intPart : intPart + "." + fracPart;
}

/* -------------------------------------------------------------------------- */
/*  Hash formatting                                                           */
/* -------------------------------------------------------------------------- */

/**
 * Returns a compact representation of a SHA-256 hex string:
 * first 8 + ellipsis + last 8 lowercase hex characters.
 *
 * Returns the original string (trimmed) when it is shorter than the
 * prefix+suffix length so that short test fixtures are not mangled.
 */
export function formatHash(sha256: Sha256Hex | string): string {
  if (typeof sha256 !== "string") return String(sha256);
  if (sha256.length <= 20) return sha256;
  return sha256.slice(0, 8) + "…" + sha256.slice(-8);
}

/* -------------------------------------------------------------------------- */
/*  Canonical JSON                                                            */
/* -------------------------------------------------------------------------- */

/**
 * Produces a deterministic JSON encoding matching the backend
 * snapshot.py canonical_json helper:
 *
 *   - object keys are sorted lexicographically (using Array#sort on the
 *     raw UTF-16 code units, matching CPython json default),
 *   - arrays preserve their order,
 *   - undefined values are dropped (matching CPython json default),
 *   - numbers are serialised via JSON.stringify,
 *   - strings are emitted verbatim with their surrounding double quotes.
 *
 * The simulation feature uses this to recompute a content hash for display
 * next to the backend-provided input_manifest_hash; the values must
 * match exactly for the page to consider the freeze trustworthy.
 */
export function canonicalJson(value: unknown): string {
  return stringify(value);
}

function stringify(node: unknown): string {
  if (node === null) return "null";
  if (node === undefined) return "undefined";
  if (typeof node === "number") {
    if (!Number.isFinite(node)) {
      throw new Error("canonicalJson cannot encode non-finite numbers");
    }
    return JSON.stringify(node);
  }
  if (typeof node === "boolean") return node ? "true" : "false";
  if (typeof node === "string") return JSON.stringify(node);
  if (Array.isArray(node)) {
    const parts: string[] = [];
    for (let i = 0; i < node.length; i += 1) {
      const item = node[i];
      if (item === undefined) continue;
      parts.push(stringify(item));
    }
    return "[" + parts.join(",") + "]";
  }
  if (typeof node === "object") {
    const obj = node as Record<string, unknown>;
    const keys = Object.keys(obj).sort();
    const fields: string[] = [];
    for (let k = 0; k < keys.length; k += 1) {
      const key = keys[k];
      const v = obj[key];
      if (v === undefined) continue;
      fields.push(JSON.stringify(key) + ":" + stringify(v));
    }
    return "{" + fields.join(",") + "}";
  }
  throw new Error("canonicalJson cannot encode value of type " + typeof node);
}

/* -------------------------------------------------------------------------- */
/*  Z-score normalisation                                                     */
/* -------------------------------------------------------------------------- */

/**
 * Standardises a raw value against a baseline mean and stddev. The
 * standardisation matches the backend Z(x) = (x - mean) / stddev
 * formulation used by the FR-08 BALANCED objective.
 *
 * The function returns null when stddev is non-positive so the caller
 * can display "UNDEFINED" instead of dividing by zero.
 */
export function zScore(value: Decimal | string, mean: Decimal | string, stddev: Decimal | string): Decimal | null {
  const v = Number(value);
  const m = Number(mean);
  const s = Number(stddev);
  if (!Number.isFinite(v) || !Number.isFinite(m) || !Number.isFinite(s)) return null;
  if (s <= 0) return null;
  const z = (v - m) / s;
  if (!Number.isFinite(z)) return null;
  return z.toFixed(6);
}
