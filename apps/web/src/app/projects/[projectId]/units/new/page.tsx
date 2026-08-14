import type { Metadata } from "next";
import { NewUnitMount } from "@/features/projects/public";
import styles from "@/app/mount.module.css";

export const metadata: Metadata = {
  title: "新建决策单元",
};

export default function NewUnitPage() {
  return (
    <main className={styles.standalone}>
      <NewUnitMount />
    </main>
  );
}
