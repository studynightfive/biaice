import type { ComponentPropsWithoutRef } from "react";
import styles from "./ui.module.css";

type CardProps = ComponentPropsWithoutRef<"section"> & {
  title?: string;
  eyebrow?: string;
};

export function Card({ children, className, eyebrow, title, ...props }: CardProps) {
  return (
    <section
      className={[styles.card, className].filter(Boolean).join(" ")}
      {...props}
    >
      {(eyebrow || title) && (
        <header className={styles.cardHeader}>
          {eyebrow && <span className={styles.cardEyebrow}>{eyebrow}</span>}
          {title && (
            <h2 className={styles.cardTitle}>{title}</h2>
          )}
        </header>
      )}
      {children}
    </section>
  );
}
