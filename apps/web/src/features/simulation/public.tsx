import { FeaturePlaceholder } from "@/components/shell";

export function BaselineScenariosMount() {
  return (
    <FeaturePlaceholder
      contract="DecisionBaseline、CandidateSearchSpace、ScenarioSet 与冻结 input manifest"
      description="冻结规则、响应、成本、政策、市场、模型、时间点以及相互独立的搜索和评估场景。"
      gate="就绪门禁未通过时只显示阻断原因，不创建正式仿真批次。"
      owner={6}
      title="决策基线与场景"
    />
  );
}

export function SimulationMount() {
  return (
    <FeaturePlaceholder
      contract="SimulationBatch、静态校验、逐场景裁判、优化、压力测试与方案合并"
      description="展示后端真实 Job 进度、可行性、部分识别区间和 0–4 个可行方案。"
      gate="最终可行集合为空时只显示原因；不伪造方案、胜率或利润结论。"
      owner={6}
      title="仿真与方案"
    />
  );
}

export function EligibilityMount() {
  return (
    <FeaturePlaceholder
      contract="RecommendationEligibilityVersion 与 SimulationAssessmentSnapshot"
      description="聚合预审、就绪、静态、场景、条件和风险接受门禁，不包含商业审批决定。"
      gate="任一输入过期、未知或失效时，不得把推荐资格显示为通过。"
      owner={6}
      title="推荐资格"
    />
  );
}
