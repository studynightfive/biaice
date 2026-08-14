export type FeatureOwner = 1 | 2 | 3 | 4 | 5 | 6 | 7;

export type NavigationGroup = "prepare" | "evaluate" | "decide" | "govern";

export type UnitRouteDefinition = {
  gateSummary: string;
  group: NavigationGroup;
  label: string;
  owner: FeatureOwner;
  shortLabel: string;
  suffix: `/${string}`;
};

export const UNIT_ROUTE_GROUPS: ReadonlyArray<{
  id: NavigationGroup;
  label: string;
}> = [
  { id: "prepare", label: "01 · 准备与规则" },
  { id: "evaluate", label: "02 · 评估与仿真" },
  { id: "decide", label: "03 · 决策闭环" },
  { id: "govern", label: "04 · 治理" },
];

export const UNIT_ROUTES: readonly UnitRouteDefinition[] = [
  {
    suffix: "/overview",
    label: "决策单元概览",
    shortLabel: "概览",
    owner: 2,
    group: "prepare",
    gateSummary: "未选择有效单元时只提供只读引导。",
  },
  {
    suffix: "/documents",
    label: "资料摄入",
    shortLabel: "资料",
    owner: 3,
    group: "prepare",
    gateSummary: "隔离或扫描未完成的资料不得进入下游。",
  },
  {
    suffix: "/scope-rules",
    label: "制度、范围与规则",
    shortLabel: "规则",
    owner: 2,
    group: "prepare",
    gateSummary: "规则未发布时只显示草稿与阻断原因。",
  },
  {
    suffix: "/evidence-precheck",
    label: "证据、响应与预审",
    shortLabel: "预审",
    owner: 4,
    group: "prepare",
    gateSummary: "未映射的强制要求按未知处理并失败关闭。",
  },
  {
    suffix: "/commercial-readiness",
    label: "商业政策与就绪",
    shortLabel: "就绪",
    owner: 4,
    group: "prepare",
    gateSummary: "未批准成本只能用于带边界说明的探索。",
  },
  {
    suffix: "/market",
    label: "竞对与市场",
    shortLabel: "市场",
    owner: 5,
    group: "prepare",
    gateSummary: "来源、用途或处理基础缺失时不得用于计算。",
  },
  {
    suffix: "/baseline-scenarios",
    label: "决策基线与场景",
    shortLabel: "基线",
    owner: 6,
    group: "evaluate",
    gateSummary: "就绪门禁未通过时只展示原因。",
  },
  {
    suffix: "/simulation",
    label: "仿真与方案",
    shortLabel: "仿真",
    owner: 6,
    group: "evaluate",
    gateSummary: "没有正式先验时只能进行无概率意义的压力探索。",
  },
  {
    suffix: "/eligibility",
    label: "推荐资格",
    shortLabel: "资格",
    owner: 6,
    group: "evaluate",
    gateSummary: "推荐资格与商业审批结论保持分离。",
  },
  {
    suffix: "/approvals",
    label: "审批中心",
    shortLabel: "审批",
    owner: 7,
    group: "decide",
    gateSummary: "Pilot 前不开放写动作；影子运行必须明确标记。",
  },
  {
    suffix: "/reports-submissions",
    label: "报告与提交",
    shortLabel: "报告",
    owner: 7,
    group: "decide",
    gateSummary: "仅按 Stage Gate 开放对应报告；系统不自动外部提交。",
  },
  {
    suffix: "/outcomes",
    label: "结果与复盘",
    shortLabel: "复盘",
    owner: 7,
    group: "decide",
    gateSummary: "未经独立核验的结果不得进入正式回测。",
  },
  {
    suffix: "/governance/access-audit",
    label: "访问、审计与处置",
    shortLabel: "访问审计",
    owner: 1,
    group: "govern",
    gateSummary: "审计写入不可用时，敏感操作失败关闭。",
  },
  {
    suffix: "/governance/privacy-models",
    label: "隐私与模型治理",
    shortLabel: "隐私模型",
    owner: 5,
    group: "govern",
    gateSummary: "外部调用必须同时满足配置、用途与治理门禁。",
  },
];

export function buildUnitPath(projectId: string, unitId: string, suffix: string) {
  return `/projects/${encodeURIComponent(projectId)}/units/${encodeURIComponent(unitId)}${suffix}`;
}
