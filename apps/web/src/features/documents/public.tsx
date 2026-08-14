import { FeaturePlaceholder } from "@/components/shell";

export function DocumentsMount() {
  return (
    <FeaturePlaceholder
      contract="上传会话、分块校验、隔离扫描、解析 Job、派生资产与版本状态"
      description="承载招标方、本公司及受控市场资料的安全摄入入口；真实进度必须来自持久化 Job。"
      gate="资料先隔离、扫描再解析；扫描未通过时禁止查看正文或供下游使用。"
      owner={3}
      title="资料摄入中心"
    />
  );
}
