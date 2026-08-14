import { FeaturePlaceholder } from "@/components/shell";

export function MarketMount() {
  return (
    <FeaturePlaceholder
      contract="0–N 竞对、来源审核、主体去重、市场先验与未知进入者契约"
      description="管理合法来源的竞对与市场输入；文件摄入复用 documents 公开端口，不复制上传状态机。"
      gate="无批准先验时只允许压力探索，不能生成正式排名频率或推荐资格。"
      owner={5}
      title="竞对与市场"
    />
  );
}
