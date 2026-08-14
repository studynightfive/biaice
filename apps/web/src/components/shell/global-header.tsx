import Link from "next/link";
import { StatusBadge } from "@/components/ui";
import styles from "./shell.module.css";

export function GlobalHeader() {
  return (
    <header className={styles.siteHeader}>
      <div className={styles.headerInner}>
        <Link className={styles.brand} href="/projects" aria-label="标策 AI 项目列表">
          <span aria-hidden="true" className={styles.brandMark}>
            标
          </span>
          <span className={styles.brandCopy}>
            <strong>标策 AI</strong>
            <small>BID DECISION LAB</small>
          </span>
        </Link>
        <div className={styles.headerContext}>本地自托管 · 可追溯决策工作区</div>
        <div className={styles.headerActions}>
          <StatusBadge tone="warning">工程骨架</StatusBadge>
          <Link className={styles.headerLink} href="/account">
            账户
          </Link>
        </div>
      </div>
    </header>
  );
}
