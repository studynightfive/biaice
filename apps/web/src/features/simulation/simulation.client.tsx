"use client";

import { useState } from "react";

import { Button, Notice } from "@/components/ui";

import { cancelBatch, createBatch, newIdempotencyKey, retryBatch } from "./api";
import styles from "./styles/feature-simulation.module.css";
import type { SimulationBatchVersion } from "./types";

export interface BatchActionsClientProps {
  unitId: string;
  latestBatch: SimulationBatchVersion | null;
  disabled: boolean;
}

/**
 * Client island that exposes create / cancel / retry actions for the latest
 * simulation batch. Every action forwards an Idempotency-Key so duplicate
 * clicks or retries never produce duplicate state.
 */
export function BatchActionsClient({ unitId, latestBatch, disabled }: BatchActionsClientProps) {
  const [pending, setPending] = useState<"create" | "cancel" | "retry" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const onCreate = async () => {
    setPending("create");
    setError(null);
    setInfo(null);
    try {
      await createBatch(
        unitId,
        {
          baseline_version_id: latestBatch?.baseline_version_id ?? "",
          search_space_version_id: latestBatch?.search_space_version_id ?? "",
          scenario_set_version_id: latestBatch?.scenario_set_version_id ?? "",
        },
        newIdempotencyKey("create_simulation_batch", unitId),
      );
      setInfo("Batch requested. Reload to follow the new run.");
      if (typeof window !== "undefined") window.location.reload();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Request failed");
    } finally {
      setPending(null);
    }
  };

  const onCancel = async () => {
    if (!latestBatch) return;
    setPending("cancel");
    setError(null);
    try {
      await cancelBatch(latestBatch.id, newIdempotencyKey("cancel_simulation_batch", latestBatch.id));
      setInfo("Cancellation requested.");
      if (typeof window !== "undefined") window.location.reload();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Request failed");
    } finally {
      setPending(null);
    }
  };

  const onRetry = async () => {
    if (!latestBatch) return;
    setPending("retry");
    setError(null);
    try {
      await retryBatch(latestBatch.id, newIdempotencyKey("retry_simulation_batch", latestBatch.id));
      setInfo("Retry requested.");
      if (typeof window !== "undefined") window.location.reload();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Request failed");
    } finally {
      setPending(null);
    }
  };

  return (
    <div className={styles.actions}>
      <Button
        type="button"
        variant="primary"
        disabled={disabled || pending !== null}
        aria-label="create-simulation-batch"
        onClick={onCreate}
      >
        {pending === "create" ? "Creating…" : "Create batch"}
      </Button>
      {latestBatch && (latestBatch.state === "RUNNING" || latestBatch.state === "PENDING") ? (
        <Button
          type="button"
          variant="quiet"
          disabled={disabled || pending !== null}
          aria-label="cancel-simulation-batch"
          onClick={onCancel}
        >
          {pending === "cancel" ? "Cancelling…" : "Cancel batch"}
        </Button>
      ) : null}
      {latestBatch && (latestBatch.state === "FAILED" || latestBatch.state === "CANCELLED" || latestBatch.state === "TIMED_OUT") ? (
        <Button
          type="button"
          variant="secondary"
          disabled={disabled || pending !== null}
          aria-label="retry-simulation-batch"
          onClick={onRetry}
        >
          {pending === "retry" ? "Retrying…" : "Retry batch"}
        </Button>
      ) : null}
      {error ? (
        <Notice tone="danger" title="Action failed">
          {error}
        </Notice>
      ) : null}
      {info ? (
        <Notice tone="info" title="Action submitted">
          {info}
        </Notice>
      ) : null}
    </div>
  );
}

/**
 * Thin wrapper used by the server component as the entry point of the
 * client island. We avoid exporting the richer BatchActionsClient directly
 * so the page block never imports more than one symbol from the client
 * bundle.
 */
export function CreateBatchButtonClient({ unitId, disabled }: { unitId: string; disabled: boolean }) {
  return <BatchActionsClient unitId={unitId} latestBatch={null} disabled={disabled} />;
}

export default BatchActionsClient;
