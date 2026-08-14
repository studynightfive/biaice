import styles from "./shell.module.css";

export function SiteFooter() {
  return (
    <footer className={styles.siteFooter}>
      <div className={styles.footerInner}>
        <div>
          <strong>标策 AI · 企业内部决策辅助</strong>
          <p>
            系统不替代采购人、评标委员会、财务、法务或管理层，不保证中标，也不会自动向外部采购平台提交材料。
          </p>
        </div>
        <span className={styles.footerMeta}>M0 · SHELL ONLY</span>
      </div>
    </footer>
  );
}
