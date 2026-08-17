"use client";

import { useState } from "react";

import { Button, Notice } from "@/components/ui";

import { downloadSnapshot } from "./api";
import styles from "./styles/feature-simulation.module.css";

export interface SnapshotDownloadClientProps {
  snapshotId: string;
  payloadUrl: string;
}

/**
 * Client island that fetches the immutable snapshot payload from the backend
 * and renders it verbatim inside a code block. The component never parses the
 * payload for probabilities; it only displays what the backend returned so
 * the MVP-B SHADOW watermark remains the only authoritative read.
 */
export function SnapshotDownloadClient({ snapshotId, payloadUrl }: SnapshotDownloadClientProps) {
  var [pending, setPending] = useState(false);
  var [error, setError] = useState<string | null>(null);
  var [payload, setPayload] = useState<string | null>(null);

  var onDownload = async () => {
    setPending(true);
    setError(null);
    try {
      var body = await downloadSnapshot(snapshotId);
      var text = typeof body === "string" ? body : JSON.stringify(body, null, 2);
      setPayload(text);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Download failed");
    } finally {
      setPending(false);
    }
  };

  return (
    <div>
      <div className={styles.actions}>
        <Button type="button" variant="secondary" disabled={pending} aria-label="download-snapshot-payload" onClick={onDownload}>
          {pending ? "Downloading…" : "Download snapshot payload"}
        </Button>
        <a href={payloadUrl} download aria-label="download-snapshot-url">Backend URL</a>
      </div>
      {error ? (
        <Notice tone="danger" title="Snapshot download failed">
          {error}
        </Notice>
      ) : null}
      {payload ? (
        <pre className={styles.payloadPre + " " + styles.gapSm} aria-label="snapshot-payload-preview">{payload}</pre>
      ) : null}
    </div>
  );
}

export default SnapshotDownloadClient;
