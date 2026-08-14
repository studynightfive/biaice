import { FeaturePlaceholder } from "@/components/shell";

export function ProjectListMount() {
  return (
    <FeaturePlaceholder
      contract="Project 列表、租户范围过滤、cursor pagination 与权限错误契约"
      description="创建、搜索和归档项目，并在后端真实状态就绪后展示阶段、风险、缺口与下一步。"
      gate="没有租户与项目范围授权时，不返回项目是否存在的信息。"
      owner={2}
      title="项目列表"
    />
  );
}

export function NewProjectMount() {
  return (
    <FeaturePlaceholder
      contract="create_project operation、幂等键、字段级错误与初步范围提示"
      description="创建采购项目。创建动作只生成项目与初步范围提示，不代表制度、规则或策略已经可用。"
      gate="服务端校验 tenant/data-domain 权限；未知制度不能默认进入正式流程。"
      owner={2}
      title="新建项目"
    />
  );
}

export function ProjectOverviewMount() {
  return (
    <FeaturePlaceholder
      contract="get_project、list_decision_units、版本元数据与生命周期状态"
      description="查看项目级信息以及 1–N 个决策单元；一次正式计算仍只进入一个决策单元。"
      gate="跨项目和跨租户访问由服务端拒绝；前端不缓存其他 scope 的草稿。"
      owner={2}
      title="项目总览"
    />
  );
}

export function UnitListMount() {
  return (
    <FeaturePlaceholder
      contract="list_decision_units、项目级文件继承关系与生命周期状态"
      description="选择当前项目下的决策单元，进入带稳定 project_id 与 unit_id 的工作区。"
      gate="未授权单元按不泄露存在性的 404/403 契约处理。"
      owner={2}
      title="决策单元"
    />
  );
}

export function NewUnitMount() {
  return (
    <FeaturePlaceholder
      contract="create_decision_unit operation、幂等键与项目 scope 校验"
      description="在当前项目内创建独立授标单元。跨标段约束只登记与阻断，不在首期做联合优化。"
      gate="没有项目写权限或存在 scope 冲突时，创建动作失败关闭。"
      owner={2}
      title="新建决策单元"
    />
  );
}

export function UnitOverviewMount() {
  return (
    <FeaturePlaceholder
      contract="get_decision_unit、生命周期、当前版本引用与缺口摘要"
      description="汇总当前决策单元的阶段、适用范围、缺口与下一步，不重算任何领域结论。"
      gate="未选择有效单元时只读引导；任何门禁未知都不能显示默认 GO。"
      owner={2}
      title="决策单元概览"
    />
  );
}
