import { FeaturePlaceholder } from "@/components/shell";

export function ApprovalsMount() {
  return (
    <FeaturePlaceholder
      contract="不可变审批包、工作流、条件、风险接受与追加式决定事件"
      description="承载商业审批与风险接受；上游变化时由后端立即使当前审批包失效。"
      gate="Pilot 前隐藏写动作；影子审批不构成正式运营授权。"
      owner={7}
      title="审批中心"
    />
  );
}
