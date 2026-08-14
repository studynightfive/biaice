import type { Metadata } from "next";
import { AiProviderSettingsMount } from "@/features/privacy-models/public";
import styles from "@/app/mount.module.css";

export const metadata: Metadata = {
  title: "AI 服务商配置",
};

export default function AiProviderSettingsPage() {
  return (
    <main className={styles.standalone}>
      <AiProviderSettingsMount />
    </main>
  );
}
