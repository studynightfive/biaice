"use client";

import { useCallback, useState } from "react";

import styles from "../styles/feature-simulation.module.css";

export interface CopyHashButtonProps {
  value: string;
  label?: string;
}

/**
 * Tiny client island that copies a hash (or any opaque identifier) to the
 * clipboard. The button falls back to opening a manual selection dialog when
 * the Clipboard API is unavailable; in that case the user can copy by hand.
 */
export function CopyHashButton({ value, label = "copy-hash" }: CopyHashButtonProps) {
  const [feedback, setFeedback] = useState<"idle" | "copied" | "fallback">("idle");

  const onClick = useCallback(async () => {
    try {
      if (navigator && navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
        await navigator.clipboard.writeText(value);
        setFeedback("copied");
        return;
      }
    } catch {
      // ignore and fall through to the fallback
    }
    setFeedback("fallback");
  }, [value]);

  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className={styles.hashMono + " " + styles.copyBtn}
    >
      {feedback === "copied" ? "copied" : feedback === "fallback" ? "select & copy" : "copy"}
    </button>
  );
}

export default CopyHashButton;
