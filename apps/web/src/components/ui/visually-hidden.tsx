import type { HTMLAttributes } from "react";
import styles from "./ui.module.css";

export function VisuallyHidden({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return <span className={[styles.visuallyHidden, className].filter(Boolean).join(" ")} {...props} />;
}
