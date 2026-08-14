import type { HTMLAttributes, ReactNode } from "react";
import styles from "./ui.module.css";

type EmptyStateProps = HTMLAttributes<HTMLDivElement> & {
  action?: ReactNode;
  description: ReactNode;
  title: ReactNode;
};

export function EmptyState({ action, className, description, title, ...props }: EmptyStateProps) {
  return (
    <div className={[styles.emptyState, className].filter(Boolean).join(" ")} {...props}>
      <span aria-hidden="true" className={styles.emptyMark}>
        标
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}
