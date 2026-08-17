import { Card, EmptyState, Notice, StatusBadge } from "@/components/ui";
import styles from "./rules.module.css";

const surfaces = [
  {
    eyebrow: "SCOPE",
    title: "范围评估",
    contract: "ScopeAssessment：SUPPORTED/CURRENT 才可正式放行；多轮命中 MULTI_ROUND_UNSUPPORTED。",
  },
  {
    eyebrow: "REGIME",
    title: "适用制度",
    contract: "ApplicableRegime：制度、采购方式、评标方法；已发布后不可 PATCH。",
  },
  {
    eyebrow: "RULES",
    title: "规则条款",
    contract: "RuleSet/RuleClause：原文、页码、覆盖关系；冲突进入人工确认，禁止 last-write-wins。",
  },
  {
    eyebrow: "COMPLIANCE",
    title: "合规复核",
    contract: "OPEN/BLOCKING/ACCEPTED_FOR_SIMULATION/RESOLVED/CLOSED；BLOCKING 只能探索。",
  },
] as const;

export function ScopeRulesMount() {
  return (
    <div className={styles.page}>
      <Card className={styles.hero}>
        <div>
          <p className={styles.eyebrow}>FR-01 · MEMBER 2</p>
          <h1>制度、范围与规则</h1>
          <p>
            确认制度、流程范围、规则条款、原文定位、覆盖关系与发布状态。只有已发布且已生效的版本才触发下游失效。
          </p>
        </div>
        <StatusBadge tone="warning">未发布不得进入正式策略</StatusBadge>
      </Card>

      <Notice title="冲突必须人工确认" tone="warning">
        项目级继承与单元覆盖若不一致，状态为 CONFLICT_REQUIRES_CONFIRMATION，不会用最后一次写入覆盖。
      </Notice>
      <Notice title="跨标段与多轮只阻断" tone="danger">
        跨标段命中输出 PORTFOLIO_REVIEW_REQUIRED，多轮命中输出 MULTI_ROUND_UNSUPPORTED，首期不做联合优化或多轮策略。
      </Notice>

      <div className={styles.grid}>
        {surfaces.map((surface) => (
          <Card eyebrow={surface.eyebrow} key={surface.title} title={surface.title}>
            <div className={styles.cardBody}>
              <p className={styles.contract}>{surface.contract}</p>
              <EmptyState
                description="等待当前决策单元的已授权版本。草稿、过期或无权对象保持空状态。"
                title="暂无已发布记录"
              />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
