import { FeaturePlaceholder } from "@/components/shell";

export function PrivacyModelsMount() {
  return (
    <FeaturePlaceholder
      contract="PIA、DSR、事件、ProviderPolicy、跨境评估与模型治理契约"
      description="承载个人信息、外部处理、事件响应、Provider 政策与模型治理状态。"
      gate="配置、用途、精确模型、区域、保留和审批任一不匹配时，外部调用失败关闭。"
      owner={5}
      title="隐私与模型治理"
    />
  );
}

export function AiProviderSettingsMount() {
  return (
    <FeaturePlaceholder
      contract="ProviderCatalog、AIProviderConfigurationVersion、只写 credential 与调用记录"
      description="商家在平台允许的 Provider 与模型中配置、测试、轮换、暂停或撤销自己的 API Key。"
      gate="Key 永不回显；BYOK_SECRET_GATE、MFA 与独立隐私审批未通过时禁用写动作。"
      owner={5}
      title="AI 服务商配置"
    />
  );
}
