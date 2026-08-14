import { Card, EmptyState, Notice, StatusBadge } from "@/components/ui";
import type { FeatureOwner } from "@/lib/navigation/unit-routes";
import styles from "./feature-placeholder.module.css";

type FeaturePlaceholderProps = {
  contract: string;
  description: string;
  gate: string;
  owner: FeatureOwner;
  title: string;
};

export function FeaturePlaceholder({ contract, description, gate, owner, title }: FeaturePlaceholderProps) {
  return (
    <Card className={styles.headerCard}>
      <div className={styles.headerBand}>
        <div>
          <p className={styles.eyebrow}>FEATURE MOUNT · M0</p>
          <h1 className={styles.title}>{title}</h1>
          <p className={styles.description}>{description}</p>
        </div>
        <div className={styles.owner}>
          <span>唯一业务 Owner</span>
          <strong>成员 {owner}</strong>
        </div>
      </div>
      <div className={styles.body}>
        <StatusBadge tone="warning">业务尚未接入</StatusBadge>
        <Notice title="当前仅为安全挂载点" tone="warning">
          这里没有演示数据、固定结论、前端计时器或伪造后端状态。领域实现合并后，页面只能消费冻结的生成客户端与后端真实状态。
        </Notice>
        <div className={styles.contractGrid}>
          <div className={styles.contractItem}>
            <span>接入契约</span>
            <strong>{contract}</strong>
          </div>
          <div className={styles.contractItem}>
            <span>门禁边界</span>
            <strong>{gate}</strong>
          </div>
        </div>
        <EmptyState
          description="等待对应领域成员从 feature 的 public.tsx 导出真实页面块。空状态本身不代表通过、失败或就绪。"
          title="待领域模块接入"
        />
      </div>
    </Card>
  );
}
