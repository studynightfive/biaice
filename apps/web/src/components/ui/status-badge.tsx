import type { HTMLAttributes } from "react";
import styles from "./ui.module.css";

export type StatusTone = "neutral" | "info" | "success" | "warning" | "critical";

type StatusBadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: StatusTone;
};

export function StatusBadge({ children, className, tone = "neutral", ...props }: StatusBadgeProps) {
  return (
    <span className={[styles.statusBadge, styles[tone], className].filter(Boolean).join(" ")} {...props}>
      {children}
    </span>
  );
}
