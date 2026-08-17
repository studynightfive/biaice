import { Card, EmptyState, Notice, StatusBadge } from "@/components/ui";
import styles from "./projects.module.css";

type Surface = {
  contract: string;
  description: string;
  eyebrow: string;
  title: string;
};

function FeatureShell({
  description,
  surfaces,
  title,
}: {
  description: string;
  surfaces: readonly Surface[];
  title: string;
}) {
  return (
    <div className={styles.page}>
      <Card className={styles.hero}>
        <div>
          <p className={styles.eyebrow}>FR-01 · MEMBER 2</p>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        <StatusBadge tone="warning">未接入真实租户数据</StatusBadge>
      </Card>

      <Notice title="不显示默认 GO 或演示结论" tone="warning">
        列表、草稿和生命周期都以服务端 DecisionUnit 状态为准。未知、无权或冲突时失败关闭，不使用前端内存状态伪装完成。
      </Notice>
      <Notice title="无权访问不泄露是否存在" tone="danger">
        跨租户、跨项目或未授权决策单元按 404/403 处理。系统管理员默认不能查看项目正文。
      </Notice>

      <div className={styles.grid}>
        {surfaces.map((surface) => (
          <Card eyebrow={surface.eyebrow} key={surface.title} title={surface.title}>
            <div className={styles.cardBody}>
              <p className={styles.contract}>{surface.contract}</p>
              <EmptyState description={surface.description} title="当前范围无可显示记录" />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

export function ProjectListMount() {
  return (
    <FeatureShell
      description="创建、搜索和归档采购项目。阶段、缺口和下一步只来自后端真实状态，不预填三个 Demo 模板当正式结果。"
      title="项目列表"
      surfaces={[
        {
          eyebrow: "LIST",
          title: "租户内项目",
          contract: "list_projects：tenant/data-domain 过滤与权限错误契约。",
          description: "没有授权范围时保持空列表，不猜测其他租户是否存在项目。",
        },
        {
          eyebrow: "CREATE",
          title: "新建入口",
          contract: "create_project：幂等键、字段级错误、初步范围提示。",
          description: "创建只生成项目草稿，不代表制度、规则或策略已经可用。",
        },
      ]}
    />
  );
}

export function NewProjectMount() {
  return (
    <FeatureShell
      description="创建采购项目。未知制度不能默认进入正式流程。"
      title="新建项目"
      surfaces={[
        {
          eyebrow: "DRAFT",
          title: "项目草稿",
          contract: "create_project、幂等键、时区/预算/截止时间字段。",
          description: "表单在后端 handler 对当前会话授权后才会提交。",
        },
        {
          eyebrow: "GATE",
          title: "范围提示",
          contract: "服务端校验 tenant/data-domain；无权时不创建。",
          description: "没有写权限时保持空状态，不缓存其他 scope 的草稿。",
        },
      ]}
    />
  );
}

export function ProjectOverviewMount() {
  return (
    <FeatureShell
      description="查看项目级信息以及 1–N 个决策单元。一次正式计算仍只进入一个决策单元。"
      title="项目总览"
      surfaces={[
        {
          eyebrow: "PROJECT",
          title: "项目版本",
          contract: "get_project、VersionMetadata、归档状态。",
          description: "非法或无权 project_id 不展示占位卡片，只保留空/错误边界。",
        },
        {
          eyebrow: "UNITS",
          title: "决策单元",
          contract: "list_decision_units 与生命周期摘要。",
          description: "未选择单元时只读引导，不显示默认通过。",
        },
      ]}
    />
  );
}

export function UnitListMount() {
  return (
    <FeatureShell
      description="选择当前项目下的决策单元，进入带稳定 project_id 与 unit_id 的工作区。"
      title="决策单元"
      surfaces={[
        {
          eyebrow: "SELECT",
          title: "单元列表",
          contract: "list_decision_units、生命周期状态。",
          description: "未授权单元按不泄露存在性的空状态处理。",
        },
        {
          eyebrow: "STALE",
          title: "过期引用",
          contract: "validity_state=STALE 不得当作 CURRENT。",
          description: "过期或已归档单元不会显示为可正式计算。",
        },
      ]}
    />
  );
}

export function NewUnitMount() {
  return (
    <FeatureShell
      description="在当前项目内创建独立授标单元。跨标段约束只登记与阻断，不在首期做联合优化。"
      title="新建决策单元"
      surfaces={[
        {
          eyebrow: "CREATE",
          title: "单元草稿",
          contract: "create_decision_unit、幂等键、项目 scope 校验。",
          description: "没有项目写权限或存在 scope 冲突时，创建动作失败关闭。",
        },
        {
          eyebrow: "PORTFOLIO",
          title: "跨标段提示",
          contract: "命中后只输出 PORTFOLIO_REVIEW_REQUIRED。",
          description: "不把跨标段组解释成已经完成联合优化。",
        },
      ]}
    />
  );
}

export function UnitOverviewMount() {
  return (
    <FeatureShell
      description="汇总当前决策单元的阶段、适用范围、缺口与下一步。成员 2 是生命周期唯一 writer，本页不重算其他领域结论。"
      title="决策单元概览"
      surfaces={[
        {
          eyebrow: "LIFECYCLE",
          title: "当前阶段",
          contract: "get_decision_unit、lifecycle-events 只读列表。",
          description: "未选择有效单元时只读引导；门禁未知时不能显示 GO。",
        },
        {
          eyebrow: "GAPS",
          title: "缺口与下一步",
          contract: "当前制度/规则版本引用，缺失则保持缺口。",
          description: "草稿或未来版本不会把正式结果显示为已就绪。",
        },
      ]}
    />
  );
}
