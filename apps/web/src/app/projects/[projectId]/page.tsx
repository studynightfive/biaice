import type { Metadata } from "next";
import { ProjectOverviewMount } from "@/features/projects/public";
import styles from "@/app/mount.module.css";

export const metadata: Metadata = {
  title: "项目总览",
};

export default function ProjectOverviewPage() {
  return (
    <main className={styles.standalone}>
      <ProjectOverviewMount />
    </main>
  );
}
