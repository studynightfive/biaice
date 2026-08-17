"use client";

import { useState } from "react";

import { Button, Notice } from "@/components/ui";

import { createSearchSpace, newIdempotencyKey } from "./api";
import styles from "./styles/feature-simulation.module.css";
import type { CandidateSearchSpaceVersion } from "./types";

export interface RequestSearchSpaceButtonClientProps {
  unitId: string;
  disabled: boolean;
}

export function RequestSearchSpaceButtonClient({ unitId, disabled }: RequestSearchSpaceButtonClientProps) {
  var [open, setOpen] = useState(false);
  var [pending, setPending] = useState(false);
  var [error, setError] = useState<string | null>(null);
  var [lower, setLower] = useState("0");
  var [upper, setUpper] = useState("0");
  var [step, setStep] = useState("0.01");
  var [currency, setCurrency] = useState("CNY");
  var [precision, setPrecision] = useState(2);

  var onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      var result: CandidateSearchSpaceVersion = await createSearchSpace(
        unitId,
        {
          baseline_version_id: unitId,
          lower_bound: lower,
          upper_bound: upper,
          step,
          currency,
          precision,
          rounding_mode: "HALF_UP",
          tax_passthrough: false,
        },
        newIdempotencyKey("create_candidate_search_space", unitId),
      );
      void result.id;
      setOpen(false);
      if (typeof window !== "undefined") {
        window.location.reload();
      }
    } catch (caught) {
      var message = caught instanceof Error ? caught.message : "Request failed";
      setError(message);
    } finally {
      setPending(false);
    }
  };

  if (!open) {
    return (
      <Button
        type="button"
        aria-label="request-new-search-space"
        variant="secondary"
        disabled={disabled || pending}
        onClick={() => setOpen(true)}
      >
        Request a new search space
      </Button>
    );
  }

  return (
    <div className={styles.modalBackdrop} role="dialog" aria-modal="true" aria-label="create-search-space-modal">
      <form className={styles.modalPanel} onSubmit={onSubmit}>
        <h3>Create a candidate search space</h3>
        <p className={styles.caption}>
          The new space must reference the current frozen baseline. All values are submitted as Decimal strings; the backend will not coerce them to Number.
        </p>
        <label>
          Lower bound
          <input
            type="text"
            value={lower}
            onChange={(e) => setLower(e.target.value)}
            inputMode="decimal"
            required
            aria-label="lower-bound-input"
          />
        </label>
        <label>
          Upper bound
          <input
            type="text"
            value={upper}
            onChange={(e) => setUpper(e.target.value)}
            inputMode="decimal"
            required
            aria-label="upper-bound-input"
          />
        </label>
        <label>
          Step
          <input
            type="text"
            value={step}
            onChange={(e) => setStep(e.target.value)}
            inputMode="decimal"
            required
            aria-label="step-input"
          />
        </label>
        <label>
          Currency (ISO 4217)
          <input
            type="text"
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            maxLength={3}
            required
            aria-label="currency-input"
          />
        </label>
        <label>
          Precision
          <input
            type="number"
            value={precision}
            onChange={(e) => setPrecision(Number(e.target.value))}
            min={0}
            max={6}
            aria-label="precision-input"
          />
        </label>
        {error ? (
          <Notice tone="danger" title="Search space request failed">
            {error}
          </Notice>
        ) : null}
        <div className={styles.actions}>
          <Button type="submit" variant="primary" disabled={pending} aria-label="submit-search-space">
            {pending ? "Submitting…" : "Submit"}
          </Button>
          <Button type="button" variant="quiet" disabled={pending} onClick={() => setOpen(false)} aria-label="cancel-search-space">
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}

export default RequestSearchSpaceButtonClient;
