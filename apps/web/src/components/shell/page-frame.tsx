import type { ReactNode } from "react";
import styles from "./page-frame.module.css";

type PageFrameProps = {
  children: ReactNode;
  description: ReactNode;
  eyebrow: string;
  narrow?: boolean;
  title: ReactNode;
};

export function PageFrame({ children, description, eyebrow, narrow = false, title }: PageFrameProps) {
  return (
    <main className={[styles.frame, narrow && styles.narrow].filter(Boolean).join(" ")}>
      <header>
        <p className={styles.eyebrow}>{eyebrow}</p>
        <h1 className={styles.title}>{title}</h1>
        <p className={styles.description}>{description}</p>
      </header>
      <div className={styles.content}>{children}</div>
    </main>
  );
}
