import type { Metadata } from "next";
import { NewProjectMount } from "@/features/projects/public";
import styles from "@/app/mount.module.css";

export const metadata: Metadata = {
  title: "新建项目",
};

export default function NewProjectPage() {
  return (
    <main className={styles.standalone}>
      <NewProjectMount />
    </main>
  );
}
