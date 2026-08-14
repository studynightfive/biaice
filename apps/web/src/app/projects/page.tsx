import type { Metadata } from "next";
import { ProjectListMount } from "@/features/projects/public";
import styles from "@/app/mount.module.css";

export const metadata: Metadata = {
  title: "项目",
};

export default function ProjectsPage() {
  return (
    <main className={styles.standalone}>
      <ProjectListMount />
    </main>
  );
}
