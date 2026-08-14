import { Card, EmptyState, Notice, StatusBadge } from "@/components/ui";
import styles from "./access-audit.module.css";

const governanceSurfaces = [
  {
    eyebrow: "AUDIT",
    title: "审计事件与完整性",
    contract: "AuditWriter、分页查询、可信时间、哈希链与完整性检查结果。",
  },
  {
    eyebrow: "LINEAGE",
    title: "血缘与失效传播",
    contract: "InputManifest、DataLineageEdge、SupersessionEvent 与 InvalidationEvent。",
  },
  {
    eyebrow: "RETENTION",
    title: "保留与法务保全",
    contract: "RetentionDispositionJob、LegalHold、双人 Override 与到期停止使用。",
  },
  {
    eyebrow: "DELETION",
    title: "删除编排与墓碑",
    contract: "DeletionJob、ReplicaCommand、DeletionReceipt 聚合、Tombstone 与恢复重放。",
  },
] as const;

export function AccessAuditMount() {
  return (
    <div className={styles.page}>
      <Card className={styles.hero}>
        <div>
          <p className={styles.eyebrow}>GOVERNANCE · MEMBER 1</p>
          <h1>访问、审计与数据处置</h1>
          <p>
            统一承载 FR-11 的访问记录、血缘、失效、保留、保全、删除编排与完整性检查；当前页面只建立治理壳，不制造审计记录或删除回执。
          </p>
        </div>
        <StatusBadge tone="warning">治理 API 待接入</StatusBadge>
      </Card>

      <Notice title="敏感操作必须失败关闭" tone="danger">
        独立审计写入不可用时，正文查看、下载、导出、发布、审批、授权、解除隔离、保全解除和删除均不得继续。
      </Notice>

      <div className={styles.grid}>
        {governanceSurfaces.map((surface) => (
          <Card eyebrow={surface.eyebrow} key={surface.title} title={surface.title}>
            <div className={styles.cardBody}>
              <p className={styles.contract}>{surface.contract}</p>
              <EmptyState
                description="等待生成客户端与当前租户/项目/单元授权上下文接入。"
                title="暂无可显示记录"
              />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
