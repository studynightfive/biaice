"use client";

import styles from "../styles/feature-simulation.module.css";

export interface SnapshotWatermarkProps {
  caption?: string;
  children?: React.ReactNode;
  testId?: string;
}

export function SnapshotWatermark({ caption, children, testId }: SnapshotWatermarkProps) {
  return (
    <div className={styles.watermark} data-testid={testId ?? "snapshot-watermark"}>
      <div className={styles.watermarkOverlay} aria-hidden="true">
        <span>SHADOW · MVP-B · NOT APPROVABLE</span>
      </div>
      <div className={styles.watermarkBody}>{children}</div>
      {caption ? <p className={styles.watermarkCaption + " " + styles.caption}>{caption}</p> : null}
    </div>
  );
}

export default SnapshotWatermark;
