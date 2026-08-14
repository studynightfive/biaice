import type { HTMLAttributes, ReactNode } from "react";
import styles from "./ui.module.css";

type NoticeTone = "info" | "warning" | "danger";

type NoticeProps = Omit<HTMLAttributes<HTMLDivElement>, "title"> & {
  children: ReactNode;
  title: ReactNode;
  tone?: NoticeTone;
};

const toneClass: Record<NoticeTone, string> = {
  info: styles.noticeInfo,
  warning: styles.noticeWarning,
  danger: styles.noticeDanger,
};

const toneMark: Record<NoticeTone, string> = {
  info: "i",
  warning: "!",
  danger: "×",
};

export function Notice({ children, className, title, tone = "info", ...props }: NoticeProps) {
  return (
    <div className={[styles.notice, toneClass[tone], className].filter(Boolean).join(" ")} {...props}>
      <span aria-hidden="true" className={styles.noticeIcon}>
        {toneMark[tone]}
      </span>
      <div className={styles.noticeContent}>
        <strong>{title}</strong>
        <p>{children}</p>
      </div>
    </div>
  );
}
