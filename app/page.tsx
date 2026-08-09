"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Objective = "win" | "expected" | "balanced";
type Tab = "cockpit" | "rules" | "evidence" | "report";
type GateStatus = "pass" | "warn" | "fail";
type Method = "综合评分法" | "最低评标价法";

type Dimension = {
  id: string;
  label: string;
  points: number;
  color: string;
};

type GateDefinition = {
  label: string;
  evidence: string;
};

type EvidenceRow = {
  item: string;
  dimension: string;
  points?: number;
  evidence: string;
  location: string;
  basePct: number;
  gap?: string;
};

type CompetitorSeed = {
  id: "B" | "C" | "D";
  name: string;
  strategy: string;
  quoteRatio: number;
  pressure: number;
  nonPricePct: Record<string, number>;
  qualificationIssue?: string;
  complianceIssue?: string;
  lowPriceEvidence: boolean;
  accent: string;
};

type ProjectTemplate = {
  id: string;
  name: string;
  shortName: string;
  code: string;
  category: string;
  method: Method;
  budget: number;
  maxPrice: number;
  defaultBid: number;
  defaultCost: number;
  defaultMargin: number;
  lowPriceReviewRate: number;
  priceWeight: number;
  dimensions: Dimension[];
  qualifications: GateDefinition[];
  compliance: GateDefinition[];
  evidenceRows: EvidenceRow[];
  competitors: CompetitorSeed[];
  priceRule: string;
  decisionNote: string;
};

type AgentResult = {
  id: "A" | "B" | "C" | "D";
  name: string;
  strategy: string;
  quote: number;
  qualification: GateStatus;
  qualificationDetail: string;
  compliance: GateStatus;
  complianceDetail: string;
  abnormalLow: boolean;
  abnormalDetail: string;
  valid: boolean;
  priceScore: number;
  nonPriceScore: number;
  totalScore: number;
  rank: number | null;
  winProbability: number;
  accent: string;
};

type Evaluation = {
  agents: AgentResult[];
  basePrice: number | null;
  validCount: number;
};

const PROJECTS: ProjectTemplate[] = [
  {
    id: "it-service",
    name: "政企云平台运维与安全服务项目",
    shortName: "IT 运维服务",
    code: "ZC-2026-IT-042",
    category: "服务采购",
    method: "综合评分法",
    budget: 1200,
    maxPrice: 1180,
    defaultBid: 930,
    defaultCost: 760,
    defaultMargin: 18,
    lowPriceReviewRate: 0.65,
    priceWeight: 20,
    dimensions: [
      { id: "technical", label: "技术", points: 45, color: "#315c4d" },
      { id: "business", label: "商务", points: 20, color: "#3568a8" },
      { id: "service", label: "服务", points: 15, color: "#d28c3c" },
    ],
    qualifications: [
      { label: "依法设立并具备独立承担民事责任能力", evidence: "营业执照、法定代表人身份证明" },
      { label: "财务、纳税和社会保障记录符合要求", evidence: "审计报告、近期开票及社保缴纳凭证" },
      { label: "近三年无重大违法记录", evidence: "书面声明及信用查询记录" },
      { label: "具备履约所必需的专业能力", evidence: "人员、工具平台与服务能力说明" },
    ],
    compliance: [
      { label: "投标总价不超过最高限价 1,180 万元", evidence: "开标一览表、分项报价表" },
      { label: "投标有效期不少于 90 日", evidence: "投标函" },
      { label: "SLA 可用性不低于 99.9%", evidence: "技术偏离表、服务承诺" },
      { label: "120 日内完成迁移，全部 ★ 条款无负偏离", evidence: "实施计划、逐条响应表" },
    ],
    evidenceRows: [
      { item: "核心功能与参数", dimension: "technical", points: 20, evidence: "逐条偏离表、演示截图、检测材料", location: "技术册 §3.1–3.6", basePct: 0.93 },
      { item: "总体架构与集成", dimension: "technical", points: 10, evidence: "架构图、接口清单、兼容性说明", location: "技术册 §4", basePct: 0.86, gap: "补充灾备切换时序" },
      { item: "实施迁移方案", dimension: "technical", points: 8, evidence: "WBS、里程碑、回退方案", location: "实施册 §2", basePct: 0.84, gap: "量化割接窗口" },
      { item: "安全与测试", dimension: "technical", points: 7, evidence: "等保映射、测试与验收方案", location: "技术册 §6", basePct: 0.88 },
      { item: "类似项目业绩", dimension: "business", points: 8, evidence: "合同关键页、验收证明、联系人", location: "商务册 §5", basePct: 0.76, gap: "2 份验收证明待归档" },
      { item: "项目团队配置", dimension: "business", points: 12, evidence: "简历、证书、社保证明、分工表", location: "商务册 §6", basePct: 0.82 },
      { item: "SLA 与驻场保障", dimension: "service", points: 8, evidence: "SLA 表、排班与升级机制", location: "服务册 §2", basePct: 0.94 },
      { item: "培训与应急响应", dimension: "service", points: 7, evidence: "课程、演练、应急预案", location: "服务册 §3–4", basePct: 0.87, gap: "补充季度演练样例" },
    ],
    competitors: [
      { id: "B", name: "锐价科技", strategy: "低价进攻", quoteRatio: 0.63, pressure: 0.0012, nonPricePct: { technical: 0.72, business: 0.63, service: 0.68 }, lowPriceEvidence: true, accent: "#c76b4f" },
      { id: "C", name: "深维数科", strategy: "技术溢价", quoteRatio: 0.93, pressure: 0.0003, nonPricePct: { technical: 0.88, business: 0.82, service: 0.86 }, lowPriceEvidence: true, accent: "#3568a8" },
      { id: "D", name: "安联智服", strategy: "均衡跟随", quoteRatio: 0.81, pressure: 0.0007, nonPricePct: { technical: 0.82, business: 0.76, service: 0.79 }, complianceIssue: "★ 数据跨域兼容条款负偏离", lowPriceEvidence: false, accent: "#8a735a" },
    ],
    priceRule: "满足招标文件要求且评标价最低者为评标基准价；价格得分 = 评标基准价 ÷ 本投标评标价 × 20。",
    decisionNote: "资格与符合性均为通过制，不计分；只有有效投标进入详细评审。",
  },
  {
    id: "equipment",
    name: "数据中心通用服务器设备采购项目",
    shortName: "通用设备采购",
    code: "HW-2026-017",
    category: "货物采购",
    method: "最低评标价法",
    budget: 800,
    maxPrice: 780,
    defaultBid: 650,
    defaultCost: 560,
    defaultMargin: 12,
    lowPriceReviewRate: 0.6,
    priceWeight: 100,
    dimensions: [],
    qualifications: [
      { label: "具备独立承担民事责任能力", evidence: "营业执照、授权材料" },
      { label: "财务、税收、社保与信用记录符合要求", evidence: "审计、纳税社保及信用记录" },
      { label: "制造商或合法渠道授权", evidence: "针对本项目的原厂授权函" },
    ],
    compliance: [
      { label: "评标价不超过最高限价 780 万元", evidence: "报价表、政策扣除说明" },
      { label: "CPU、内存、存储等 ★ 参数无负偏离", evidence: "技术规格响应表、检测报告" },
      { label: "交货期不超过 45 日", evidence: "供货计划与承诺函" },
      { label: "原厂质保不少于 3 年", evidence: "制造商售后服务承诺" },
    ],
    evidenceRows: [
      { item: "核心硬件参数", dimension: "gate", evidence: "逐条规格响应表、产品彩页、检测报告", location: "响应册 §2", basePct: 1 },
      { item: "原厂授权与供货", dimension: "gate", evidence: "项目授权函、供货承诺", location: "商务册 §4", basePct: 1, gap: "授权函有效期待复核" },
      { item: "交付与安装", dimension: "gate", evidence: "到货计划、机房上架方案", location: "实施册 §1", basePct: 1 },
      { item: "质保与售后", dimension: "gate", evidence: "原厂服务承诺、备件清单", location: "服务册 §2", basePct: 1 },
    ],
    competitors: [
      { id: "B", name: "竞速硬件", strategy: "渠道底价", quoteRatio: 0.75, pressure: 0.001, nonPricePct: {}, lowPriceEvidence: true, accent: "#c76b4f" },
      { id: "C", name: "原厂集成", strategy: "原厂服务", quoteRatio: 0.91, pressure: 0.0003, nonPricePct: {}, lowPriceEvidence: true, accent: "#3568a8" },
      { id: "D", name: "联采供应", strategy: "均衡报价", quoteRatio: 0.82, pressure: 0.0006, nonPricePct: {}, qualificationIssue: "原厂授权函缺少项目名称", lowPriceEvidence: true, accent: "#8a735a" },
    ],
    priceRule: "不设置主观加分。通过资格和符合性审查后，按经修正、扣除后的评标价由低到高排序。",
    decisionNote: "技术与资质在本模板中是准入条件，不因证书数量多而任意加分。",
  },
  {
    id: "construction",
    name: "园区智能化系统改造工程施工项目",
    shortName: "智能化工程",
    code: "GC-2026-108",
    category: "工程招标",
    method: "综合评分法",
    budget: 5000,
    maxPrice: 4800,
    defaultBid: 4490,
    defaultCost: 3950,
    defaultMargin: 10,
    lowPriceReviewRate: 0.65,
    priceWeight: 50,
    dimensions: [
      { id: "technical", label: "施工组织", points: 30, color: "#315c4d" },
      { id: "team", label: "项目团队", points: 10, color: "#3568a8" },
      { id: "performance", label: "企业业绩", points: 10, color: "#d28c3c" },
    ],
    qualifications: [
      { label: "具有项目要求的电子与智能化工程资质", evidence: "资质证书及有效期核验" },
      { label: "具备有效安全生产许可证", evidence: "安全生产许可证" },
      { label: "项目经理资格及在岗状态符合要求", evidence: "注册证书、安考证、社保与无在建承诺" },
      { label: "信用、财务及类似履约能力符合要求", evidence: "信用记录、财务与业绩证明" },
    ],
    compliance: [
      { label: "投标总价不超过最高限价 4,800 万元", evidence: "投标函、工程量清单" },
      { label: "工期不超过 240 日历天", evidence: "施工进度网络计划" },
      { label: "质量与安全目标响应招标要求", evidence: "质量、安全承诺与专项方案" },
      { label: "工程量清单完整且无不可竞争费违规调整", evidence: "已标价工程量清单" },
    ],
    evidenceRows: [
      { item: "施工总体部署", dimension: "technical", points: 10, evidence: "总平面、关键路径、资源计划", location: "施工组织 §2", basePct: 0.86 },
      { item: "关键工序与系统联调", dimension: "technical", points: 10, evidence: "专项施工、联调与验收方案", location: "施工组织 §3", basePct: 0.91 },
      { item: "质量安全与进度", dimension: "technical", points: 10, evidence: "质量安全体系、进度纠偏机制", location: "施工组织 §4–6", basePct: 0.85, gap: "雨季施工量化措施不足" },
      { item: "项目经理与核心班组", dimension: "team", points: 10, evidence: "证书、履历、社保、分工", location: "商务册 §5", basePct: 0.82 },
      { item: "同类工程业绩", dimension: "performance", points: 10, evidence: "合同、竣工验收、获奖证明", location: "商务册 §6", basePct: 0.78, gap: "1 个项目金额证明不清" },
    ],
    competitors: [
      { id: "B", name: "城建智能", strategy: "价格抢位", quoteRatio: 0.82, pressure: 0.0007, nonPricePct: { technical: 0.75, team: 0.69, performance: 0.72 }, lowPriceEvidence: true, accent: "#c76b4f" },
      { id: "C", name: "科筑工程", strategy: "方案领先", quoteRatio: 0.95, pressure: 0.0002, nonPricePct: { technical: 0.91, team: 0.88, performance: 0.86 }, lowPriceEvidence: true, accent: "#3568a8" },
      { id: "D", name: "智联建设", strategy: "经验均衡", quoteRatio: 0.88, pressure: 0.0005, nonPricePct: { technical: 0.84, team: 0.81, performance: 0.9 }, qualificationIssue: "项目经理存在在建项目冲突", lowPriceEvidence: true, accent: "#8a735a" },
    ],
    priceRule: "本演示按最低有效评标价为基准：价格得分 = 基准价 ÷ 投标评标价 × 50；实际工程项目须以招标文件载明公式为准。",
    decisionNote: "工程资质、安全许可和项目经理条件先审查；评分权重仅代表当前模拟项目。",
  },
];

const OBJECTIVES: Record<Objective, { label: string; helper: string }> = {
  win: { label: "中标概率", helper: "在利润底线内优先提高胜出概率" },
  expected: { label: "期望利润", helper: "中标概率 × 单项目利润" },
  balanced: { label: "稳健收益", helper: "兼顾期望利润、胜率与异常低价风险" },
};

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const roundTo = (value: number, digits = 1) => Number(value.toFixed(digits));
const money = (value: number) => `¥${Math.round(value).toLocaleString("zh-CN")}万`;

function scoreForA(project: ProjectTemplate, readiness: number) {
  const factor = readiness / 88;
  const grouped: Record<string, number> = {};
  for (const row of project.evidenceRows) {
    if (!row.points || row.dimension === "gate") continue;
    grouped[row.dimension] = (grouped[row.dimension] ?? 0) + row.points * clamp(row.basePct * factor, 0, 0.98);
  }
  return grouped;
}

function competitorQuote(project: ProjectTemplate, seed: CompetitorSeed, pressure: number, run: number) {
  const pressureDelta = (pressure - 50) * seed.pressure;
  const jitter = Math.sin((run + 1) * (seed.id.charCodeAt(0) + 11)) * 0.006;
  return Math.round(project.maxPrice * clamp(seed.quoteRatio - pressureDelta + jitter, 0.46, 0.99));
}

function evaluateScenario(args: {
  project: ProjectTemplate;
  ourBid: number;
  readiness: number;
  qualificationReady: boolean;
  complianceReady: boolean;
  lowPriceEvidence: boolean;
  marketPressure: number;
  run: number;
}): Evaluation {
  const { project, ourBid, readiness, qualificationReady, complianceReady, lowPriceEvidence, marketPressure, run } = args;
  const lowLine = project.maxPrice * project.lowPriceReviewRate;
  const aAbnormal = ourBid < lowLine;
  const aQualification: GateStatus = qualificationReady ? "pass" : "fail";
  let aCompliance: GateStatus = "pass";
  let aComplianceDetail = "最高限价、有效期及 ★ 条款均响应";
  if (ourBid > project.maxPrice) {
    aCompliance = "fail";
    aComplianceDetail = "投标报价超过最高限价";
  } else if (!complianceReady) {
    aCompliance = "fail";
    aComplianceDetail = "存在未响应的实质性 / ★ 条款";
  } else if (aAbnormal && !lowPriceEvidence) {
    aCompliance = "fail";
    aComplianceDetail = "触发异常低价审查且成本说明材料不足";
  } else if (aAbnormal) {
    aCompliance = "warn";
    aComplianceDetail = "触发项目预警线；模拟为说明材料可支撑，待评委审查";
  }

  const aGrouped = scoreForA(project, readiness);
  const raw: Array<Omit<AgentResult, "priceScore" | "totalScore" | "rank" | "winProbability">> = [
    {
      id: "A",
      name: "我方公司",
      strategy: "约束内优化",
      quote: Math.round(ourBid),
      qualification: aQualification,
      qualificationDetail: qualificationReady ? "资格证明文件齐全" : "关键资格证明材料未齐备",
      compliance: aCompliance,
      complianceDetail: aComplianceDetail,
      abnormalLow: aAbnormal,
      abnormalDetail: aAbnormal ? `低于项目设置的 ${Math.round(project.lowPriceReviewRate * 100)}% 重点审查线` : "未触发项目异常低价预警线",
      valid: aQualification !== "fail" && aCompliance !== "fail",
      nonPriceScore: Object.values(aGrouped).reduce((sum, value) => sum + value, 0),
      accent: "#315c4d",
    },
    ...project.competitors.map((seed) => {
      const quote = competitorQuote(project, seed, marketPressure, run);
      const abnormalLow = quote < lowLine;
      const qualification: GateStatus = seed.qualificationIssue ? "fail" : "pass";
      let compliance: GateStatus = seed.complianceIssue ? "fail" : "pass";
      let complianceDetail = seed.complianceIssue ?? "实质性条款响应完整";
      if (abnormalLow && !seed.lowPriceEvidence && compliance !== "fail") {
        compliance = "fail";
        complianceDetail = "异常低价说明材料不足";
      } else if (abnormalLow && compliance !== "fail") {
        compliance = "warn";
        complianceDetail = "异常低价说明进入评委审查，模拟为可支撑";
      }
      const nonPriceScore = project.dimensions.reduce(
        (sum, dimension) => sum + dimension.points * (seed.nonPricePct[dimension.id] ?? 0),
        0,
      );
      return {
        id: seed.id,
        name: seed.name,
        strategy: seed.strategy,
        quote,
        qualification,
        qualificationDetail: seed.qualificationIssue ?? "资格证明文件通过",
        compliance,
        complianceDetail,
        abnormalLow,
        abnormalDetail: abnormalLow ? `低于项目设置的 ${Math.round(project.lowPriceReviewRate * 100)}% 重点审查线` : "未触发项目异常低价预警线",
        valid: qualification !== "fail" && compliance !== "fail",
        nonPriceScore,
        accent: seed.accent,
      };
    }),
  ];

  const valid = raw.filter((agent) => agent.valid);
  const basePrice = valid.length ? Math.min(...valid.map((agent) => agent.quote)) : null;
  const scored: AgentResult[] = raw.map((agent) => {
    const priceScore = agent.valid && basePrice
      ? project.method === "综合评分法"
        ? (basePrice / agent.quote) * project.priceWeight
        : (basePrice / agent.quote) * 100
      : 0;
    const totalScore = agent.valid
      ? project.method === "综合评分法"
        ? priceScore + agent.nonPriceScore
        : priceScore
      : 0;
    return { ...agent, priceScore, totalScore, rank: null, winProbability: 0 };
  });

  const ranked = scored
    .filter((agent) => agent.valid)
    .sort((a, b) => project.method === "最低评标价法" ? a.quote - b.quote : b.totalScore - a.totalScore);
  ranked.forEach((agent, index) => {
    const target = scored.find((item) => item.id === agent.id);
    if (target) target.rank = index + 1;
  });

  if (ranked.length) {
    const temperature = project.method === "最低评标价法" ? 2.4 : 4.2;
    const maxUtility = Math.max(...ranked.map((agent) => agent.totalScore));
    const weights = ranked.map((agent) => Math.exp((agent.totalScore - maxUtility) / temperature));
    const sum = weights.reduce((total, value) => total + value, 0);
    ranked.forEach((agent, index) => {
      const target = scored.find((item) => item.id === agent.id);
      if (target) target.winProbability = (weights[index] / sum) * 100;
    });
  }

  return { agents: scored, basePrice, validCount: valid.length };
}

function statusLabel(status: GateStatus) {
  if (status === "pass") return "通过";
  if (status === "warn") return "待审查";
  return "不通过";
}

function MetricRing({ value, label }: { value: number; label: string }) {
  return (
    <div className="metric-ring" style={{ "--value": `${clamp(value, 0, 100) * 3.6}deg` } as React.CSSProperties}>
      <div><strong>{roundTo(value, 0)}%</strong><span>{label}</span></div>
    </div>
  );
}

function ScenarioChart({
  points,
  recommended,
  current,
}: {
  points: Array<{ quote: number; probability: number; expectedProfit: number }>;
  recommended: number | null;
  current: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !points.length) return;
    const container = canvas.parentElement;
    if (!container) return;

    const draw = () => {
      const width = container.clientWidth;
      const height = 300;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, width, height);

      const pad = { left: 48, right: 46, top: 22, bottom: 38 };
      const plotW = width - pad.left - pad.right;
      const plotH = height - pad.top - pad.bottom;
      const minQuote = points[0].quote;
      const maxQuote = points[points.length - 1].quote;
      const maxExpected = Math.max(1, ...points.map((point) => point.expectedProfit));
      const x = (quote: number) => pad.left + ((quote - minQuote) / (maxQuote - minQuote || 1)) * plotW;
      const yP = (probability: number) => pad.top + plotH - (probability / 100) * plotH;
      const yE = (expected: number) => pad.top + plotH - (expected / maxExpected) * plotH;

      ctx.strokeStyle = "rgba(29, 43, 38, .10)";
      ctx.lineWidth = 1;
      ctx.font = "11px ui-sans-serif, system-ui";
      ctx.fillStyle = "#7a827d";
      for (let i = 0; i <= 4; i += 1) {
        const yy = pad.top + (plotH / 4) * i;
        ctx.beginPath();
        ctx.moveTo(pad.left, yy);
        ctx.lineTo(width - pad.right, yy);
        ctx.stroke();
        ctx.fillText(`${100 - i * 25}%`, 7, yy + 4);
      }

      const fill = ctx.createLinearGradient(0, pad.top, 0, pad.top + plotH);
      fill.addColorStop(0, "rgba(49, 92, 77, .20)");
      fill.addColorStop(1, "rgba(49, 92, 77, 0)");
      ctx.beginPath();
      points.forEach((point, index) => {
        const xx = x(point.quote);
        const yy = yP(point.probability);
        if (index === 0) ctx.moveTo(xx, yy);
        else ctx.lineTo(xx, yy);
      });
      ctx.lineTo(x(points[points.length - 1].quote), pad.top + plotH);
      ctx.lineTo(x(points[0].quote), pad.top + plotH);
      ctx.closePath();
      ctx.fillStyle = fill;
      ctx.fill();

      ctx.beginPath();
      points.forEach((point, index) => {
        const xx = x(point.quote);
        const yy = yP(point.probability);
        if (index === 0) ctx.moveTo(xx, yy);
        else ctx.lineTo(xx, yy);
      });
      ctx.strokeStyle = "#315c4d";
      ctx.lineWidth = 2.5;
      ctx.stroke();

      ctx.beginPath();
      points.forEach((point, index) => {
        const xx = x(point.quote);
        const yy = yE(point.expectedProfit);
        if (index === 0) ctx.moveTo(xx, yy);
        else ctx.lineTo(xx, yy);
      });
      ctx.strokeStyle = "#3568a8";
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 5]);
      ctx.stroke();
      ctx.setLineDash([]);

      const drawMarker = (quote: number, color: string, text: string, offset: number) => {
        const xx = clamp(x(quote), pad.left, width - pad.right);
        ctx.beginPath();
        ctx.moveTo(xx, pad.top);
        ctx.lineTo(xx, pad.top + plotH);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([3, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = color;
        ctx.font = "600 11px ui-sans-serif, system-ui";
        ctx.fillText(text, clamp(xx + offset, pad.left, width - 104), 14);
      };
      drawMarker(current, "#8a735a", "当前报价", -74);
      if (recommended !== null) drawMarker(recommended, "#c76b4f", "建议报价", 6);

      ctx.fillStyle = "#7a827d";
      ctx.font = "11px ui-sans-serif, system-ui";
      ctx.fillText(`${Math.round(minQuote)}万`, pad.left, height - 12);
      const maxLabel = `${Math.round(maxQuote)}万`;
      ctx.fillText(maxLabel, width - pad.right - ctx.measureText(maxLabel).width, height - 12);
      ctx.fillText(`期望利润峰值 ${Math.round(maxExpected)}万`, width - 142, pad.top + plotH + 25);
    };

    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(container);
    return () => observer.disconnect();
  }, [points, recommended, current]);

  return <canvas ref={canvasRef} role="img" aria-label="报价、中标概率与期望利润关系图" />;
}

export default function Home() {
  const [projectId, setProjectId] = useState(PROJECTS[0].id);
  const project = PROJECTS.find((item) => item.id === projectId) ?? PROJECTS[0];
  const [ourBid, setOurBid] = useState(project.defaultBid);
  const [cost, setCost] = useState(project.defaultCost);
  const [minMargin, setMinMargin] = useState(project.defaultMargin);
  const [readiness, setReadiness] = useState(88);
  const [marketPressure, setMarketPressure] = useState(50);
  const [objective, setObjective] = useState<Objective>("balanced");
  const [qualificationReady, setQualificationReady] = useState(true);
  const [complianceReady, setComplianceReady] = useState(true);
  const [lowPriceEvidence, setLowPriceEvidence] = useState(true);
  const [tab, setTab] = useState<Tab>("cockpit");
  const [run, setRun] = useState(0);
  const [showMethod, setShowMethod] = useState(false);
  const [copied, setCopied] = useState(false);

  const evaluateAt = (quote: number) => evaluateScenario({
    project,
    ourBid: quote,
    readiness,
    qualificationReady,
    complianceReady,
    lowPriceEvidence,
    marketPressure,
    run,
  });

  const evaluation = useMemo(
    () => evaluateScenario({ project, ourBid, readiness, qualificationReady, complianceReady, lowPriceEvidence, marketPressure, run }),
    [project, ourBid, readiness, qualificationReady, complianceReady, lowPriceEvidence, marketPressure, run],
  );

  const ourResult = evaluation.agents.find((agent) => agent.id === "A")!;
  const currentProfit = ourBid - cost;
  const currentMargin = ourBid > 0 ? (currentProfit / ourBid) * 100 : -100;
  const profitPass = currentProfit >= 0 && currentMargin >= minMargin;
  const minimumFeasibleBid = minMargin >= 100 ? Infinity : cost / (1 - minMargin / 100);

  const optimization = useMemo(() => {
    if (!qualificationReady || !complianceReady || minimumFeasibleBid > project.maxPrice) return null;
    const start = Math.max(minimumFeasibleBid, project.maxPrice * 0.5);
    const step = Math.max(1, project.maxPrice / 180);
    let best: { quote: number; probability: number; expectedProfit: number; score: number; abnormal: boolean } | null = null;
    for (let quote = start; quote <= project.maxPrice + 0.01; quote += step) {
      const scenario = evaluateScenario({ project, ourBid: quote, readiness, qualificationReady, complianceReady, lowPriceEvidence, marketPressure, run });
      const ours = scenario.agents.find((agent) => agent.id === "A")!;
      if (!ours.valid) continue;
      const expectedProfit = (ours.winProbability / 100) * (quote - cost);
      const riskPenalty = ours.abnormalLow ? Math.max(12, (quote - cost) * 0.18) : 0;
      const score = objective === "win"
        ? ours.winProbability - (ours.abnormalLow ? 6 : 0)
        : objective === "expected"
          ? expectedProfit
          : expectedProfit * (0.72 + 0.28 * (ours.winProbability / 100)) - riskPenalty;
      if (!best || score > best.score) {
        best = { quote: Math.round(quote), probability: ours.winProbability, expectedProfit, score, abnormal: ours.abnormalLow };
      }
    }
    return best;
  }, [project, cost, minMargin, readiness, qualificationReady, complianceReady, lowPriceEvidence, marketPressure, run, objective, minimumFeasibleBid]);

  const chartPoints = useMemo(() => {
    const start = Math.max(project.maxPrice * 0.5, Math.min(minimumFeasibleBid, project.maxPrice));
    const count = 52;
    return Array.from({ length: count }, (_, index) => {
      const quote = start + ((project.maxPrice - start) * index) / (count - 1);
      const scenario = evaluateScenario({ project, ourBid: quote, readiness, qualificationReady, complianceReady, lowPriceEvidence, marketPressure, run });
      const ours = scenario.agents.find((agent) => agent.id === "A")!;
      return {
        quote,
        probability: ours.valid ? ours.winProbability : 0,
        expectedProfit: ours.valid ? Math.max(0, (ours.winProbability / 100) * (quote - cost)) : 0,
      };
    });
  }, [project, cost, readiness, qualificationReady, complianceReady, lowPriceEvidence, marketPressure, run, minimumFeasibleBid]);

  const rankedAgents = [...evaluation.agents].sort((a, b) => {
    if (a.rank === null && b.rank === null) return a.id.localeCompare(b.id);
    if (a.rank === null) return 1;
    if (b.rank === null) return -1;
    return a.rank - b.rank;
  });

  const bidDecision = !qualificationReady || !complianceReady
    ? { code: "NO BID", label: "暂不投标", tone: "danger", reason: "关键门槛尚未闭环" }
    : minimumFeasibleBid > project.maxPrice
      ? { code: "NO BID", label: "不建议投标", tone: "danger", reason: "利润底价高于最高限价" }
      : (optimization?.probability ?? 0) < 20
        ? { code: "REVIEW", label: "谨慎参与", tone: "warning", reason: "利润约束下竞争力偏低" }
        : { code: "GO", label: "建议参与", tone: "success", reason: "门槛可满足且存在可行报价区间" };

  const gapCount = project.evidenceRows.filter((row) => row.gap).length;
  const evidenceScore = project.evidenceRows.length
    ? Math.round(project.evidenceRows.reduce((sum, row) => sum + row.basePct, 0) / project.evidenceRows.length * (readiness / 88) * 100)
    : 100;

  const onProjectChange = (id: string) => {
    const next = PROJECTS.find((item) => item.id === id) ?? PROJECTS[0];
    setProjectId(next.id);
    setOurBid(next.defaultBid);
    setCost(next.defaultCost);
    setMinMargin(next.defaultMargin);
    setReadiness(88);
    setMarketPressure(50);
    setQualificationReady(true);
    setComplianceReady(true);
    setLowPriceEvidence(true);
    setRun(0);
  };

  const report = {
    generatedAt: new Date().toISOString(),
    notice: "模拟决策，不构成中标保证；实际结论以招标文件和评标委员会依法评审为准。",
    project: { name: project.name, code: project.code, method: project.method, maxPrice: project.maxPrice },
    assumptions: { cost, minMargin, readiness, marketPressure, objective: OBJECTIVES[objective].label },
    bidDecision,
    current: { bid: ourBid, margin: roundTo(currentMargin), winProbability: roundTo(ourResult.winProbability), valid: ourResult.valid },
    recommendation: optimization ? { bid: optimization.quote, winProbability: roundTo(optimization.probability), expectedProfit: roundTo(optimization.expectedProfit) } : null,
    agents: evaluation.agents.map(({ id, name, strategy, quote, valid, rank, totalScore, winProbability }) => ({ id, name, strategy, quote, valid, rank, totalScore: roundTo(totalScore), winProbability: roundTo(winProbability) })),
  };

  const exportReport = () => {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json;charset=utf-8" });
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.download = `${project.code}-投标策略模拟报告.json`;
    anchor.click();
    URL.revokeObjectURL(href);
  };

  const copySummary = async () => {
    const summary = `${project.name}\n决策：${bidDecision.label}\n当前报价：${money(ourBid)}，模拟胜率 ${roundTo(ourResult.winProbability)}%\n建议报价：${optimization ? money(optimization.quote) : "无可行解"}\n说明：模拟结果不构成中标保证。`;
    await navigator.clipboard.writeText(summary);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  const tabs: Array<{ id: Tab; label: string; count?: number }> = [
    { id: "cockpit", label: "决策驾驶舱" },
    { id: "rules", label: "规则与门槛", count: project.qualifications.length + project.compliance.length },
    { id: "evidence", label: "评分证据", count: gapCount },
    { id: "report", label: "决策报告" },
  ];

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="标策 AI 首页">
          <span className="brand-mark">标</span>
          <span><strong>标策 AI</strong><small>BID STRATEGY LAB</small></span>
        </a>
        <div className="top-context">
          <span className="live-dot" /> 规则引擎已锁定
          <span className="top-divider" />
          <span>{project.code}</span>
        </div>
        <div className="header-actions">
          <button className="button ghost" type="button" onClick={() => setShowMethod(true)}>方法与边界</button>
          <button className="button dark" type="button" onClick={exportReport}>导出模拟报告</button>
        </div>
      </header>

      <div id="top" className="page-shell">
        <section className="hero-grid">
          <div className="hero-copy">
            <div className="eyebrow"><span>项目专属评标</span><span>多智能体竞演</span><span>利润约束</span></div>
            <h1>先过门，再竞分；<br />先守利，再优化报价。</h1>
            <p>智能体生成投标策略，确定性规则引擎执行资格、符合性与评分公式。系统寻找的是当前招标文件和公司约束下的更优解，而不是“保证中标”。</p>
            <div className="hero-note"><span>!</span><p><strong>核心原则</strong>　评分项、权重与公式来自当前项目；资格条件和实质性要求是通过制，不能混入通用加分表。</p></div>
          </div>

          <aside className="project-card paper-card">
            <div className="card-kicker">当前模拟招标文件</div>
            <label className="project-select-label" htmlFor="project-select">项目模板</label>
            <select id="project-select" value={projectId} onChange={(event) => onProjectChange(event.target.value)}>
              {PROJECTS.map((item) => <option value={item.id} key={item.id}>{item.shortName} · {item.method}</option>)}
            </select>
            <h2>{project.name}</h2>
            <div className="project-meta-grid">
              <div><span>采购类别</span><strong>{project.category}</strong></div>
              <div><span>评审方法</span><strong>{project.method}</strong></div>
              <div><span>项目预算</span><strong>{money(project.budget)}</strong></div>
              <div><span>最高限价</span><strong>{money(project.maxPrice)}</strong></div>
            </div>
            <div className="document-lock"><span>01</span><div><strong>规则版本已锁定</strong><small>模拟解析时间 2026-08-09 09:30</small></div><b>✓</b></div>
          </aside>
        </section>

        <section className="workflow paper-card" aria-label="评标流程">
          {[
            ["01", "文件解析", "识别规则"],
            ["02", "Bid / No-Bid", "内部决策"],
            ["03", "资格审查", "通过制"],
            ["04", "符合性审查", "通过制"],
            ["05", "详细评审", "项目公式"],
            ["06", "报价优化", "利润约束"],
            ["07", "候选与报告", "解释输出"],
          ].map(([num, title, text], index) => (
            <div className={`workflow-step ${index < 6 ? "active" : ""}`} key={num}>
              <span>{num}</span><div><strong>{title}</strong><small>{text}</small></div>{index < 6 && <i>→</i>}
            </div>
          ))}
        </section>

        <nav className="tabbar" aria-label="工作台视图">
          {tabs.map((item) => (
            <button className={tab === item.id ? "active" : ""} type="button" key={item.id} onClick={() => setTab(item.id)}>
              {item.label}{item.count !== undefined && <span>{item.count}</span>}
            </button>
          ))}
        </nav>

        {tab === "cockpit" && (
          <div className="cockpit-layout">
            <aside className="control-panel paper-card">
              <div className="section-heading compact"><div><span>SCENARIO INPUT</span><h2>模拟前提</h2></div><button type="button" className="text-button" onClick={() => setRun((value) => value + 1)}>刷新竞手 ↻</button></div>

              <label className="field-label" htmlFor="our-bid"><span>我方投标总价</span><strong>{money(ourBid)}</strong></label>
              <input id="our-bid" className="range green" type="range" min={Math.round(project.maxPrice * 0.5)} max={Math.round(project.maxPrice * 1.04)} step={1} value={ourBid} onChange={(event) => setOurBid(Number(event.target.value))} />
              <div className="range-ends"><span>{money(project.maxPrice * 0.5)}</span><span>限价 {money(project.maxPrice)}</span></div>
              <div className="input-row">
                <label>报价（万元）<input type="number" value={ourBid} onChange={(event) => setOurBid(Number(event.target.value))} /></label>
                <label>履约成本（万元）<input type="number" value={cost} min={0} onChange={(event) => setCost(Number(event.target.value))} /></label>
              </div>

              <label className="field-label spaced" htmlFor="margin"><span>最低毛利率</span><strong>{minMargin}%</strong></label>
              <input id="margin" className="range blue" type="range" min={0} max={35} value={minMargin} onChange={(event) => setMinMargin(Number(event.target.value))} />
              <div className="constraint-readout">
                <span>公司利润底价</span><strong>{Number.isFinite(minimumFeasibleBid) ? money(minimumFeasibleBid) : "无可行解"}</strong>
              </div>

              <div className="field-label spaced"><span>优化目标</span></div>
              <div className="segmented three">
                {(Object.keys(OBJECTIVES) as Objective[]).map((item) => <button type="button" className={objective === item ? "active" : ""} key={item} onClick={() => setObjective(item)}>{OBJECTIVES[item].label}</button>)}
              </div>
              <p className="field-helper">{OBJECTIVES[objective].helper}</p>

              <label className="field-label spaced" htmlFor="readiness"><span>证据成熟度</span><strong>{readiness}%</strong></label>
              <input id="readiness" className="range amber" type="range" min={55} max={100} value={readiness} onChange={(event) => setReadiness(Number(event.target.value))} />
              <label className="field-label spaced" htmlFor="pressure"><span>市场竞争强度</span><strong>{marketPressure}</strong></label>
              <input id="pressure" className="range rust" type="range" min={0} max={100} value={marketPressure} onChange={(event) => setMarketPressure(Number(event.target.value))} />

              <div className="toggle-stack">
                <label><input type="checkbox" checked={qualificationReady} onChange={(event) => setQualificationReady(event.target.checked)} /><span /><div><strong>资格材料齐全</strong><small>缺失将直接出局</small></div></label>
                <label><input type="checkbox" checked={complianceReady} onChange={(event) => setComplianceReady(event.target.checked)} /><span /><div><strong>★ 条款全部响应</strong><small>实质性偏离直接出局</small></div></label>
                <label><input type="checkbox" checked={lowPriceEvidence} onChange={(event) => setLowPriceEvidence(event.target.checked)} /><span /><div><strong>异常低价可说明</strong><small>成本、效率与供应链证据</small></div></label>
              </div>
            </aside>

            <div className="cockpit-main">
              <section className="decision-strip">
                <div className={`bid-decision ${bidDecision.tone}`}><span>{bidDecision.code}</span><strong>{bidDecision.label}</strong><small>{bidDecision.reason}</small></div>
                <div className="decision-metric"><span>建议报价</span><strong>{optimization ? money(optimization.quote) : "—"}</strong><small>{OBJECTIVES[objective].label}最优 · 模拟</small></div>
                <div className="decision-metric"><span>模拟胜出概率</span><strong>{optimization ? `${roundTo(optimization.probability)}%` : "—"}</strong><small>对手策略变化将改变结果</small></div>
                <div className="decision-metric"><span>预计毛利</span><strong>{optimization ? money(optimization.quote - cost) : "—"}</strong><small>{optimization ? `${roundTo((optimization.quote - cost) / optimization.quote * 100)}% 毛利率` : "无可行报价"}</small></div>
                <button className="run-button" type="button" onClick={() => setRun((value) => value + 1)}><span>运行竞演</span><strong>RUN {String(run + 1).padStart(2, "0")} ↗</strong></button>
              </section>

              <section className="arena-section paper-card">
                <div className="section-heading"><div><span>MULTI-AGENT ARENA</span><h2>多智能体评标沙盘</h2><p>策略智能体提交响应；规则裁判先淘汰无效投标，再对有效投标排序。</p></div><div className="valid-summary"><strong>{evaluation.validCount}</strong><span>/ 4 有效投标</span></div></div>
                <div className="agent-grid">
                  {rankedAgents.map((agent) => (
                    <article className={`agent-card ${agent.id === "A" ? "ours" : ""} ${!agent.valid ? "eliminated" : ""}`} key={agent.id} style={{ "--agent": agent.accent } as React.CSSProperties}>
                      <div className="agent-top"><span className="agent-id">{agent.id}</span><div><strong>{agent.name}</strong><small>{agent.strategy}</small></div><b>{agent.valid ? (agent.rank === 1 ? "领先" : `第 ${agent.rank} 名`) : "已淘汰"}</b></div>
                      <div className="agent-quote"><span>投标报价</span><strong>{money(agent.quote)}</strong></div>
                      <div className="agent-score-row">
                        <div><span>{project.method === "综合评分法" ? "模拟总分" : "评标价指数"}</span><strong>{agent.valid ? roundTo(agent.totalScore) : "—"}</strong></div>
                        <MetricRing value={agent.winProbability} label="胜出概率" />
                      </div>
                      <div className="gate-chips">
                        <span className={agent.qualification}>资格 {statusLabel(agent.qualification)}</span>
                        <span className={agent.compliance}>符合性 {statusLabel(agent.compliance)}</span>
                      </div>
                      <p className="agent-reason">{!agent.valid ? (agent.qualification === "fail" ? agent.qualificationDetail : agent.complianceDetail) : agent.abnormalLow ? agent.abnormalDetail : project.method === "综合评分法" ? `价格 ${roundTo(agent.priceScore)} + 非价格 ${roundTo(agent.nonPriceScore)}` : "通过门槛后按评标价竞争"}</p>
                    </article>
                  ))}
                </div>
                <div className="referee-line"><span>规则裁判</span><p><strong>固定顺序：</strong>资格审查 → 符合性审查 → 异常低价说明审查 → {project.method === "综合评分法" ? "价格与非价格项计分" : "有效评标价排序"}。智能体不能绕过门槛。</p></div>
              </section>

              <section className="chart-card paper-card">
                <div className="section-heading"><div><span>PRICE FRONTIER</span><h2>报价—胜率—收益前沿</h2><p>可行区间从公司利润底价开始；曲线根据当前对手画像和项目公式重算。</p></div><div className={`profit-badge ${profitPass ? "pass" : "fail"}`}><span>当前利润约束</span><strong>{profitPass ? "满足" : "不满足"}</strong></div></div>
                <div className="chart-wrap"><ScenarioChart points={chartPoints} recommended={optimization?.quote ?? null} current={ourBid} /></div>
                <div className="chart-legend"><span><i className="solid" />模拟胜出概率（左轴）</span><span><i className="dashed" />期望利润（归一化）</span><span className="chart-note">当前报价毛利率 {roundTo(currentMargin)}%</span></div>
              </section>
            </div>
          </div>
        )}

        {tab === "rules" && (
          <div className="rules-view">
            <section className="rules-lead paper-card">
              <div><span className="card-kicker">RULE SOURCE</span><h2>当前项目规则画像</h2><p>以下内容来自“模拟招标文件”，切换项目后门槛、权重和公式会随之改变。</p></div>
              <div className="rule-facts"><div><span>方法</span><strong>{project.method}</strong></div><div><span>价格权重</span><strong>{project.method === "综合评分法" ? `${project.priceWeight} 分` : "不计分"}</strong></div><div><span>最高限价</span><strong>{money(project.maxPrice)}</strong></div><div><span>异常低价预警</span><strong>&lt; 限价 {Math.round(project.lowPriceReviewRate * 100)}%</strong></div></div>
            </section>

            <div className="gate-columns">
              <section className="gate-panel paper-card">
                <div className="gate-panel-head"><span>GATE 01</span><h2>资格审查</h2><b>通过制 · 不计分</b></div>
                {project.qualifications.map((item, index) => <div className="rule-row" key={item.label}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{item.label}</strong><small>{item.evidence}</small></div><b>必须</b></div>)}
              </section>
              <section className="gate-panel paper-card">
                <div className="gate-panel-head"><span>GATE 02</span><h2>符合性审查</h2><b>实质响应 · 不计分</b></div>
                {project.compliance.map((item, index) => <div className="rule-row" key={item.label}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{item.label}</strong><small>{item.evidence}</small></div><b>必须</b></div>)}
              </section>
            </div>

            <section className="scoring-panel paper-card">
              <div className="section-heading"><div><span>DETAILED REVIEW</span><h2>{project.method === "综合评分法" ? "项目专属评分结构" : "有效最低评标价排序"}</h2><p>{project.decisionNote}</p></div><span className="method-stamp">{project.method}</span></div>
              {project.method === "综合评分法" ? (
                <>
                  <div className="weight-stack" aria-label="评分权重">
                    <div style={{ width: `${project.priceWeight}%`, background: "#1f2d28" }}><span>价格 {project.priceWeight}</span></div>
                    {project.dimensions.map((dimension) => <div key={dimension.id} style={{ width: `${dimension.points}%`, background: dimension.color }}><span>{dimension.label} {dimension.points}</span></div>)}
                  </div>
                  <div className="dimension-grid">
                    <article><span className="dim-index">P</span><div><strong>价格 · {project.priceWeight} 分</strong><p>严格使用招标文件给定公式，不由模型自行设权。</p></div></article>
                    {project.dimensions.map((dimension, index) => <article key={dimension.id}><span className="dim-index">{index + 1}</span><div><strong>{dimension.label} · {dimension.points} 分</strong><p>{project.evidenceRows.filter((row) => row.dimension === dimension.id).map((row) => row.item).join("、")}</p></div></article>)}
                  </div>
                </>
              ) : (
                <div className="lowest-flow"><div><span>01</span><strong>资格通过</strong><small>不通过即淘汰</small></div><i>→</i><div><span>02</span><strong>实质响应</strong><small>参数与条款无重大偏离</small></div><i>→</i><div><span>03</span><strong>价格修正 / 扣除</strong><small>按招标文件和政策执行</small></div><i>→</i><div><span>04</span><strong>最低评标价</strong><small>由低到高排序</small></div></div>
              )}
              <div className="formula-box"><span>PRICE RULE</span><strong>{project.priceRule}</strong><p>本公式仅用于当前模拟项目。实际项目如采用平均价、区间法或其他合法公式，必须重新解析并锁定版本。</p></div>
            </section>

            <section className="gate-matrix paper-card">
              <div className="section-heading"><div><span>ELIGIBILITY MATRIX</span><h2>四方门槛审查矩阵</h2></div></div>
              <div className="table-scroll"><table><thead><tr><th>投标智能体</th><th>资格审查</th><th>符合性审查</th><th>异常低价</th><th>是否进入评审</th></tr></thead><tbody>
                {evaluation.agents.map((agent) => <tr key={agent.id}><td><span className="mini-agent" style={{ background: agent.accent }}>{agent.id}</span><strong>{agent.name}</strong></td><td><span className={`status-text ${agent.qualification}`}>{statusLabel(agent.qualification)}</span><small>{agent.qualificationDetail}</small></td><td><span className={`status-text ${agent.compliance}`}>{statusLabel(agent.compliance)}</span><small>{agent.complianceDetail}</small></td><td><span className={`status-text ${agent.abnormalLow ? "warn" : "pass"}`}>{agent.abnormalLow ? "触发" : "未触发"}</span><small>{agent.abnormalDetail}</small></td><td><b className={agent.valid ? "yes" : "no"}>{agent.valid ? "进入" : "淘汰"}</b></td></tr>)}
              </tbody></table></div>
            </section>
          </div>
        )}

        {tab === "evidence" && (
          <div className="evidence-view">
            <section className="evidence-summary paper-card">
              <div><span className="card-kicker">BID EVIDENCE GRAPH</span><h2>从评分项反推投标证据</h2><p>{project.method === "综合评分法" ? "预测分数必须能落到招标文件条款、响应材料和页码；没有证据的能力不计入乐观分。" : "最低评标价项目仍需把每个门槛映射到证据；通过参数响应后，价格才有比较意义。"}</p></div>
              <MetricRing value={clamp(evidenceScore, 0, 100)} label="证据成熟度" />
              <div className="evidence-stat"><span>待补缺口</span><strong>{gapCount}</strong><small>建议在封标前闭环</small></div>
            </section>

            <section className="evidence-table paper-card">
              <div className="table-scroll"><table><thead><tr><th>评审 / 响应项</th><th>{project.method === "综合评分法" ? "分值" : "属性"}</th><th>可验证证据</th><th>投标文件定位</th><th>{project.method === "综合评分法" ? "模拟得分" : "响应状态"}</th><th>缺口</th></tr></thead><tbody>
                {project.evidenceRows.map((row) => {
                  const predicted = row.points ? row.points * clamp(row.basePct * (readiness / 88), 0, 0.98) : 0;
                  return <tr key={row.item}><td><strong>{row.item}</strong><small>{row.dimension === "gate" ? "门槛响应" : project.dimensions.find((dim) => dim.id === row.dimension)?.label}</small></td><td><b>{row.points ? `${row.points} 分` : "必须"}</b></td><td>{row.evidence}</td><td><span className="location-tag">{row.location}</span></td><td>{row.points ? <strong className="score-value">{roundTo(predicted)} / {row.points}</strong> : <span className="status-text pass">已映射</span>}</td><td>{row.gap ? <span className="gap-tag">{row.gap}</span> : <span className="clear-tag">已闭环</span>}</td></tr>;
                })}
              </tbody></table></div>
            </section>

            <div className="improvement-grid">
              <section className="paper-card action-card"><span>01 · 先补门槛</span><h3>不能用高分弥补废标风险</h3><p>优先校验授权、签章、有效期、最高限价和 ★ 条款。任何一项实质性不响应，详细评分优势都失去意义。</p><button type="button" onClick={() => setTab("rules")}>查看门槛清单 →</button></section>
              <section className="paper-card action-card"><span>02 · 再补证据</span><h3>技术与资质不是天然加分</h3><p>只有招标文件列为评分因素、且能提供规定证明材料时，技术能力、证书、业绩和团队才产生分值。</p><button type="button" onClick={() => setReadiness(Math.min(100, readiness + 5))}>模拟成熟度 +5 →</button></section>
              <section className="paper-card action-card"><span>03 · 最后定价</span><h3>报价与响应方案联动优化</h3><p>每次调整报价，都重新执行门槛审查、价格公式、对手排序和利润校验，避免只看最低价。</p><button type="button" onClick={() => setTab("cockpit")}>返回报价模拟 →</button></section>
            </div>
          </div>
        )}

        {tab === "report" && (
          <div className="report-view">
            <section className="report-paper paper-card">
              <div className="report-head"><div><span>DECISION MEMO / {project.code}</span><h2>投标策略模拟决策单</h2><p>{project.name}</p></div><div className={`report-verdict ${bidDecision.tone}`}><span>{bidDecision.code}</span><strong>{bidDecision.label}</strong></div></div>
              <div className="report-callout"><span>建议</span><p>{optimization ? <>在“{OBJECTIVES[objective].label}”目标和最低毛利率 {minMargin}% 约束下，建议重点论证 <strong>{money(optimization.quote)}</strong> 附近报价；对应模拟胜出概率 <strong>{roundTo(optimization.probability)}%</strong>、中标后预计毛利 <strong>{money(optimization.quote - cost)}</strong>。</> : <>当前不存在同时满足资格 / 符合性、最高限价和公司利润底线的报价，请先修复门槛或重新评估是否参与。</>}</p></div>
              <div className="report-grid">
                <div><span>评审方法</span><strong>{project.method}</strong><small>以当前项目规则为准</small></div>
                <div><span>当前报价</span><strong>{money(ourBid)}</strong><small>模拟胜率 {roundTo(ourResult.winProbability)}%</small></div>
                <div><span>公司利润底价</span><strong>{Number.isFinite(minimumFeasibleBid) ? money(minimumFeasibleBid) : "无可行解"}</strong><small>最低毛利率 {minMargin}%</small></div>
                <div><span>有效竞争者</span><strong>{evaluation.validCount} / 4</strong><small>淘汰后才参与排名</small></div>
              </div>
              <div className="report-section"><div className="report-section-title"><span>01</span><h3>主要判断依据</h3></div><ul><li>资格审查：我方{qualificationReady ? "材料齐备，模拟通过" : "存在缺失，模拟不通过"}。</li><li>符合性审查：我方{complianceReady ? "已响应全部实质性条款" : "存在实质性偏离"}，当前报价{ourBid <= project.maxPrice ? "未超过" : "已超过"}最高限价。</li><li>评审公式：{project.priceRule}</li><li>竞争态势：{evaluation.agents.filter((agent) => !agent.valid).map((agent) => `${agent.name}因${agent.qualification === "fail" ? agent.qualificationDetail : agent.complianceDetail}被淘汰`).join("；") || "当前四家均进入详细评审"}。</li></ul></div>
              <div className="report-section"><div className="report-section-title"><span>02</span><h3>封标前动作</h3></div><div className="task-list">{project.evidenceRows.filter((row) => row.gap).map((row, index) => <div key={row.item}><span>{index + 1}</span><p><strong>{row.item}</strong>{row.gap}</p><b>待办</b></div>)}{gapCount === 0 && <p>当前模拟证据清单无未闭环项。</p>}</div></div>
              <div className="report-section"><div className="report-section-title"><span>03</span><h3>风险与边界</h3></div><p className="risk-copy">竞争对手报价、评委主观评分、澄清结果与政策性价格扣除均存在不确定性。本报告使用模拟数据，仅用于内部方案比较；不构成法律意见、投标承诺或中标保证。最终必须由项目团队按正式招标文件逐条复核。</p></div>
              <div className="report-actions"><button className="button dark" type="button" onClick={exportReport}>下载 JSON 报告</button><button className="button ghost" type="button" onClick={copySummary}>{copied ? "已复制 ✓" : "复制决策摘要"}</button><button className="text-button" type="button" onClick={() => setShowMethod(true)}>查看模型边界</button></div>
            </section>
          </div>
        )}

        <footer>
          <div><strong>标策 AI · 多智能体投标决策 Demo</strong><span>模拟数据 / 非真实采购项目</span></div>
          <p>提高可解释决策质量，不承诺中标。实际流程、资格、技术、资质和评分要求以每个项目正式招标文件为准。</p>
        </footer>
      </div>

      {showMethod && (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setShowMethod(false)}>
          <section className="method-modal" role="dialog" aria-modal="true" aria-labelledby="method-title" onMouseDown={(event) => event.stopPropagation()}>
            <button className="modal-close" type="button" aria-label="关闭" onClick={() => setShowMethod(false)}>×</button>
            <span className="card-kicker">MODEL & COMPLIANCE</span>
            <h2 id="method-title">这不是“万能评分表”</h2>
            <p className="modal-lead">系统把招标文件视为唯一项目规则源。智能体可以模拟策略、响应质量和竞争行为，但不能修改门槛、权重或公式。</p>
            <div className="method-list">
              <div><span>01</span><p><strong>硬门槛先执行</strong>资格和实质性要求采用通过 / 不通过，不拿额外证书抵消缺失项。</p></div>
              <div><span>02</span><p><strong>详细评分项目化</strong>只有招标文件明确列出的技术、商务、服务因素及证明材料才计分。</p></div>
              <div><span>03</span><p><strong>异常低价不是自动废标</strong>触发审查后需解释成本合理性；是否接受由评标委员会依法判断。</p></div>
              <div><span>04</span><p><strong>优化含公司约束</strong>利润底价是企业内部约束，不属于评委评分项；系统只在可行区间搜索。</p></div>
            </div>
            <div className="legal-note"><strong>Demo 边界</strong><p>概率来自当前模拟对手画像和确定性评分映射，不代表真实投标结果。法规、政策与项目条款可能变化，正式使用前应由采购、法务和项目负责人复核。</p></div>
            <div className="official-links">
              <span>权威规则入口</span>
              <a href="https://www.mof.gov.cn/gp/xxgkml/tfs/201707/t20170718_2652766.htm" target="_blank" rel="noreferrer">财政部令第 87 号 ↗</a>
              <a href="https://m.mof.gov.cn/zcfb/202601/t20260121_3982332.htm" target="_blank" rel="noreferrer">政府采购异常低价审查规则 ↗</a>
              <a href="https://www.ndrc.gov.cn/xwdt/tzgg/202602/t20260210_1403681_ext.html" target="_blank" rel="noreferrer">招标投标制度规则 ↗</a>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
