import type { Metadata } from "next";
import { UnitListMount } from "@/features/projects/public";
import styles from "@/app/mount.module.css";

export const metadata: Metadata = {
  title: "决策单元",
};

export default function UnitsPage() {
  return (
    <main className={styles.standalone}>
      <UnitListMount />
    </main>
  );
}
