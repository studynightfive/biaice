import { FeaturePlaceholder } from "@/components/shell";

export function ReportsSubmissionsMount() {
  return (
    <FeaturePlaceholder
      contract="预审报告、模拟快照、决策报告、提交授权与外部提交登记"
      description="查看不可变报告快照，冻结待提交内容，并登记、核验外部采购平台上的人工提交。"
      gate="系统不自动外部提交；报告与操作仅按当前 Stage Gate 开放。"
      owner={7}
      title="报告与提交"
    />
  );
}

export function OutcomesMount() {
  return (
    <FeaturePlaceholder
      contract="ProcurementOutcome、来源核验、冲突事件、前瞻/事后标记与回测入口"
      description="登记采购结果与来源，在独立核验后用于复盘、校准和模型治理。"
      gate="只有 VERIFIED 的前瞻结果可以进入正式评估；冲突只能追加事件处理。"
      owner={7}
      title="结果与复盘"
    />
  );
}
