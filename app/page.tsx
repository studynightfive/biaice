"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Objective = "win" | "expected" | "balanced" | "margin";
type Tab = "documents" | "cockpit" | "rules" | "evidence" | "report";
type GateStatus = "pass" | "warn" | "fail";
type Method = "综合评分法" | "最低评标价法";
type ParseState = "idle" | "parsing" | "done";
type MatchStatus = "matched" | "partial" | "missing";
type RequirementKind = "资格门槛" | "实质性要求" | "技术评分" | "商务评分" | "服务评分";
type OpponentId = "B" | "C" | "D";
type UploadTarget = "tender" | "company" | OpponentId;

type UploadedDocument = {
  id: string;
  name: string;
  size: number;
  type: string;
};

type DocumentMatch = {
  id: string;
  kind: RequirementKind;
  requirement: string;
  mandatory: boolean;
  tenderSource: string;
  requiredEvidence: string;
  companySource: string;
  status: MatchStatus;
  confidence: number;
};

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
  id: OpponentId;
  name: string;
  strategy: string;
  quoteRatio: number;
  pressure: number;
  nonPricePct: Record<string, number>;
  qualificationIssue?: string;
  complianceIssue?: string;
  lowPriceEvidence: boolean;
  accent: string;
  quoteSpread?: number;
  sourceConfidence?: number;
};

type CompetitorProfile = {
  id: OpponentId;
  name: string;
  strategy: string;
  predictedQuote: number;
  quoteLow: number;
  quoteHigh: number;
  predictedScore: number;
  scoreLow: number;
  scoreHigh: number;
  confidence: number;
  sourceCount: number;
  historySamples: number;
  behavior: string;
  risk: string;
  accent: string;
};

type StrategyPlan = {
  id: Objective;
  label: string;
  tag: string;
  quote: number;
  rangeLow: number;
  rangeHigh: number;
  probability: number;
  grossProfit: number;
  expectedProfit: number;
  margin: number;
  abnormal: boolean;
  rationale: string;
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

const DOCUMENT_MATCH_LIBRARY: Record<string, DocumentMatch[]> = {
  "it-service": [
    { id: "it-q1", kind: "资格门槛", requirement: "依法设立并具备独立承担民事责任能力", mandatory: true, tenderSource: "招标文件 P18 §3.1", requiredEvidence: "营业执照、法定代表人身份证明", companySource: "营业执照与基础资质.pdf · P1", status: "matched", confidence: 98 },
    { id: "it-q2", kind: "资格门槛", requirement: "财务、纳税和社会保障记录符合要求", mandatory: true, tenderSource: "招标文件 P19 §3.2", requiredEvidence: "审计报告、纳税及社保凭证", companySource: "财务与社保材料.pdf · P3–16", status: "matched", confidence: 95 },
    { id: "it-q3", kind: "资格门槛", requirement: "近三年无重大违法记录", mandatory: true, tenderSource: "招标文件 P19 §3.3", requiredEvidence: "无重大违法记录书面声明", companySource: "未找到对应声明", status: "missing", confidence: 99 },
    { id: "it-c1", kind: "实质性要求", requirement: "投标有效期不少于 90 日", mandatory: true, tenderSource: "招标文件 P24 ★2.1", requiredEvidence: "投标函明确承诺有效期", companySource: "投标函模板.docx · §2", status: "matched", confidence: 96 },
    { id: "it-c2", kind: "实质性要求", requirement: "SLA 可用性不低于 99.9%", mandatory: true, tenderSource: "采购需求 P41 ★4.2", requiredEvidence: "服务承诺、监控与赔付机制", companySource: "技术方案-v12.docx · P88", status: "matched", confidence: 93 },
    { id: "it-c3", kind: "实质性要求", requirement: "120 日内迁移且跨域兼容无负偏离", mandatory: true, tenderSource: "采购需求 P43 ★4.6", requiredEvidence: "实施计划、兼容性测试证明", companySource: "技术方案-v12.docx · P46（缺兼容性测试附件）", status: "partial", confidence: 91 },
    { id: "it-t1", kind: "技术评分", requirement: "总体架构、接口集成与灾备切换方案", mandatory: false, tenderSource: "评分办法 P67 · 技术 10 分", requiredEvidence: "架构图、接口清单、灾备时序", companySource: "技术方案-v12.docx · P20–38", status: "partial", confidence: 88 },
    { id: "it-b1", kind: "商务评分", requirement: "提供 3 个同类运维项目业绩及验收证明", mandatory: false, tenderSource: "评分办法 P69 · 商务 8 分", requiredEvidence: "合同关键页、验收证明", companySource: "近三年运维业绩汇编.pdf · 2/3 份验收完整", status: "partial", confidence: 94 },
    { id: "it-s1", kind: "服务评分", requirement: "驻场排班、培训与季度应急演练", mandatory: false, tenderSource: "评分办法 P70 · 服务 15 分", requiredEvidence: "排班表、课程、演练记录", companySource: "技术方案-v12.docx · P91–108", status: "matched", confidence: 90 },
  ],
  equipment: [
    { id: "eq-q1", kind: "资格门槛", requirement: "具备独立承担民事责任能力", mandatory: true, tenderSource: "招标文件 P14 §2.1", requiredEvidence: "营业执照、授权材料", companySource: "营业执照与基础资质.pdf · P1", status: "matched", confidence: 98 },
    { id: "eq-q2", kind: "资格门槛", requirement: "制造商或合法渠道针对本项目授权", mandatory: true, tenderSource: "招标文件 P16 §2.4", requiredEvidence: "原厂项目授权函", companySource: "原厂授权函-草稿.pdf（项目编号缺失）", status: "partial", confidence: 97 },
    { id: "eq-c1", kind: "实质性要求", requirement: "CPU、内存、存储等 ★ 参数无负偏离", mandatory: true, tenderSource: "技术参数 P31–36", requiredEvidence: "规格响应表、产品彩页、检测材料", companySource: "服务器规格响应表.xlsx · 42/42 项", status: "matched", confidence: 95 },
    { id: "eq-c2", kind: "实质性要求", requirement: "交货期不超过 45 日", mandatory: true, tenderSource: "采购需求 P38 ★5.1", requiredEvidence: "供货计划与承诺", companySource: "供货与安装方案.docx · P4", status: "matched", confidence: 94 },
    { id: "eq-c3", kind: "实质性要求", requirement: "原厂质保不少于 3 年", mandatory: true, tenderSource: "采购需求 P39 ★5.4", requiredEvidence: "制造商售后服务承诺", companySource: "未找到盖章版售后承诺", status: "missing", confidence: 99 },
  ],
  construction: [
    { id: "gc-q1", kind: "资格门槛", requirement: "电子与智能化工程专业承包资质符合要求", mandatory: true, tenderSource: "资格条件 P12 §2.2", requiredEvidence: "有效资质证书", companySource: "施工资质及安全许可.pdf · P1–4", status: "matched", confidence: 98 },
    { id: "gc-q2", kind: "资格门槛", requirement: "具备有效安全生产许可证", mandatory: true, tenderSource: "资格条件 P12 §2.3", requiredEvidence: "安全生产许可证", companySource: "施工资质及安全许可.pdf · P5", status: "matched", confidence: 98 },
    { id: "gc-q3", kind: "资格门槛", requirement: "项目经理资格、社保及无在建状态符合要求", mandatory: true, tenderSource: "资格条件 P13 §2.5", requiredEvidence: "注册证、安考证、社保、无在建承诺", companySource: "项目团队材料.pdf（缺无在建承诺）", status: "partial", confidence: 96 },
    { id: "gc-c1", kind: "实质性要求", requirement: "工期不超过 240 日历天", mandatory: true, tenderSource: "投标须知 P21 ★1.7", requiredEvidence: "工期承诺、网络进度计划", companySource: "施工组织设计-v8.docx · P12", status: "matched", confidence: 94 },
    { id: "gc-c2", kind: "实质性要求", requirement: "工程量清单完整且不可竞争费未违规调整", mandatory: true, tenderSource: "清单说明 P6 ★3", requiredEvidence: "已标价工程量清单", companySource: "工程量清单-投标版.xlsx · 复核待完成", status: "partial", confidence: 87 },
    { id: "gc-t1", kind: "技术评分", requirement: "关键工序、系统联调、雨季施工措施", mandatory: false, tenderSource: "评分办法 P48 · 施工组织 30 分", requiredEvidence: "专项施工、联调与季节措施", companySource: "施工组织设计-v8.docx · P28–66", status: "partial", confidence: 89 },
    { id: "gc-b1", kind: "商务评分", requirement: "同类智能化工程合同及竣工验收证明", mandatory: false, tenderSource: "评分办法 P51 · 业绩 10 分", requiredEvidence: "合同、竣工验收、金额证明", companySource: "工程业绩汇编.pdf · 3 个项目", status: "matched", confidence: 93 },
  ],
};

const DEMO_DOCUMENTS: Record<string, { tender: UploadedDocument[]; company: UploadedDocument[] }> = {
  "it-service": {
    tender: [
      { id: "demo-it-t1", name: "政企云平台运维服务项目-招标文件.pdf", size: 6840000, type: "application/pdf" },
      { id: "demo-it-t2", name: "采购需求及评分办法.docx", size: 1280000, type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" },
    ],
    company: [
      { id: "demo-it-c1", name: "营业执照与基础资质.pdf", size: 2380000, type: "application/pdf" },
      { id: "demo-it-c2", name: "财务与社保材料.pdf", size: 4120000, type: "application/pdf" },
      { id: "demo-it-c3", name: "近三年运维业绩汇编.pdf", size: 8950000, type: "application/pdf" },
      { id: "demo-it-c4", name: "技术方案-v12.docx", size: 15700000, type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" },
    ],
  },
  equipment: {
    tender: [{ id: "demo-eq-t1", name: "数据中心服务器采购-招标文件.pdf", size: 5280000, type: "application/pdf" }],
    company: [
      { id: "demo-eq-c1", name: "营业执照与基础资质.pdf", size: 2380000, type: "application/pdf" },
      { id: "demo-eq-c2", name: "原厂授权函-草稿.pdf", size: 880000, type: "application/pdf" },
      { id: "demo-eq-c3", name: "服务器规格响应表.xlsx", size: 640000, type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
      { id: "demo-eq-c4", name: "供货与安装方案.docx", size: 3250000, type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" },
    ],
  },
  construction: {
    tender: [
      { id: "demo-gc-t1", name: "园区智能化改造工程-招标文件.pdf", size: 12400000, type: "application/pdf" },
      { id: "demo-gc-t2", name: "工程量清单及评分办法.xlsx", size: 3680000, type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
    ],
    company: [
      { id: "demo-gc-c1", name: "施工资质及安全许可.pdf", size: 4720000, type: "application/pdf" },
      { id: "demo-gc-c2", name: "项目团队材料.pdf", size: 7850000, type: "application/pdf" },
      { id: "demo-gc-c3", name: "施工组织设计-v8.docx", size: 18600000, type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" },
      { id: "demo-gc-c4", name: "工程业绩汇编.pdf", size: 10800000, type: "application/pdf" },
    ],
  },
};

const DEMO_COMPETITOR_DOCUMENTS: Record<string, Record<OpponentId, UploadedDocument[]>> = {
  "it-service": {
    B: [
      { id: "demo-it-b1", name: "锐价科技-近5次投标报价与结果.xlsx", size: 486000, type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
      { id: "demo-it-b2", name: "锐价科技-资质与产品能力.pdf", size: 3280000, type: "application/pdf" },
    ],
    C: [
      { id: "demo-it-cp1", name: "深维数科-历史中标公告汇编.pdf", size: 4620000, type: "application/pdf" },
      { id: "demo-it-cp2", name: "深维数科-技术方案公开材料.docx", size: 7250000, type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" },
    ],
    D: [
      { id: "demo-it-d1", name: "安联智服-近3年投标记录.xlsx", size: 392000, type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
      { id: "demo-it-d2", name: "安联智服-服务与案例材料.pdf", size: 5140000, type: "application/pdf" },
    ],
  },
  equipment: {
    B: [{ id: "demo-eq-b1", name: "竞速硬件-渠道报价历史.xlsx", size: 512000, type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }],
    C: [{ id: "demo-eq-cp1", name: "原厂集成-中标公告与服务能力.pdf", size: 3880000, type: "application/pdf" }],
    D: [{ id: "demo-eq-d1", name: "联采供应-历史投标清单.xlsx", size: 428000, type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }],
  },
  construction: {
    B: [{ id: "demo-gc-b1", name: "城建智能-同类工程报价样本.xlsx", size: 625000, type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }],
    C: [{ id: "demo-gc-cp1", name: "科筑工程-技术标与中标业绩.pdf", size: 8420000, type: "application/pdf" }],
    D: [{ id: "demo-gc-d1", name: "智联建设-投标与项目经理记录.xlsx", size: 538000, type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }],
  },
};

const OBJECTIVES: Record<Objective, { label: string; helper: string }> = {
  win: { label: "胜率优先", helper: "在自动识别的利润底线内优先提高模拟胜出概率" },
  expected: { label: "利润最优", helper: "优先提高中标概率 × 中标后预计毛利" },
  balanced: { label: "均衡推荐", helper: "兼顾模拟胜率、期望利润与异常低价风险" },
  margin: { label: "利润保护", helper: "在仍具竞争力的前提下提高单项目毛利安全垫" },
};

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const roundTo = (value: number, digits = 1) => Number(value.toFixed(digits));
const money = (value: number) => `¥${Math.round(value).toLocaleString("zh-CN")}万`;
const fileSize = (bytes: number) => bytes >= 1024 * 1024
  ? `${roundTo(bytes / 1024 / 1024)} MB`
  : `${Math.max(1, Math.round(bytes / 1024))} KB`;
const fileKind = (name: string) => name.split(".").pop()?.toUpperCase().slice(0, 4) || "FILE";
const matchWeight = (status: MatchStatus) => status === "matched" ? 1 : status === "partial" ? 0.5 : 0;

function matchStatusLabel(status: MatchStatus) {
  if (status === "matched") return "已满足";
  if (status === "partial") return "部分满足";
  return "缺失";
}

function scoreForA(project: ProjectTemplate, readiness: number) {
  const factor = readiness / 88;
  const grouped: Record<string, number> = {};
  for (const row of project.evidenceRows) {
    if (!row.points || row.dimension === "gate") continue;
    grouped[row.dimension] = (grouped[row.dimension] ?? 0) + row.points * clamp(row.basePct * factor, 0, 0.98);
  }
  return grouped;
}

function competitorQuote(project: ProjectTemplate, seed: CompetitorSeed, pressure: number, run: number, sourceCount = 0) {
  const pressureDelta = (pressure - 50) * seed.pressure;
  const uncertainty = sourceCount ? Math.max(0.0025, 0.009 - sourceCount * 0.0015) : 0.018;
  const jitter = Math.sin((run + 1) * (seed.id.charCodeAt(0) + 11)) * uncertainty;
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
  competitorSourceCounts?: Record<OpponentId, number>;
}): Evaluation {
  const { project, ourBid, readiness, qualificationReady, complianceReady, lowPriceEvidence, marketPressure, run, competitorSourceCounts } = args;
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
      const quote = competitorQuote(project, seed, marketPressure, run, competitorSourceCounts?.[seed.id] ?? 0);
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
  const [tab, setTab] = useState<Tab>("documents");
  const [run, setRun] = useState(0);
  const [showMethod, setShowMethod] = useState(false);
  const [copied, setCopied] = useState(false);
  const [tenderFiles, setTenderFiles] = useState<UploadedDocument[]>([]);
  const [companyFiles, setCompanyFiles] = useState<UploadedDocument[]>([]);
  const [competitorFiles, setCompetitorFiles] = useState<Record<OpponentId, UploadedDocument[]>>({ B: [], C: [], D: [] });
  const [parseState, setParseState] = useState<ParseState>("idle");
  const [competitorParseState, setCompetitorParseState] = useState<ParseState>("idle");
  const [parseProgress, setParseProgress] = useState(0);
  const [parseStage, setParseStage] = useState("等待上传招标文件");
  const [competitorParseProgress, setCompetitorParseProgress] = useState(0);
  const [competitorParseStage, setCompetitorParseStage] = useState("等待竞争者历史资料");
  const [dragZone, setDragZone] = useState<UploadTarget | null>(null);
  const [gapsClosed, setGapsClosed] = useState(false);
  const analysisTimers = useRef<number[]>([]);
  const competitorTimers = useRef<number[]>([]);

  useEffect(() => () => {
    analysisTimers.current.forEach((timer) => window.clearTimeout(timer));
    competitorTimers.current.forEach((timer) => window.clearTimeout(timer));
  }, []);

  const competitorSourceCounts = useMemo(() => ({
    B: competitorFiles.B.length,
    C: competitorFiles.C.length,
    D: competitorFiles.D.length,
  }), [competitorFiles]);

  const currentProfit = ourBid - cost;
  const currentMargin = ourBid > 0 ? (currentProfit / ourBid) * 100 : -100;
  const profitPass = currentProfit >= 0 && currentMargin >= minMargin;
  const minimumFeasibleBid = minMargin >= 100 ? Infinity : cost / (1 - minMargin / 100);
  const automaticMarketPressure = useMemo(() => {
    const loadedSources = Object.values(competitorSourceCounts).reduce((sum, value) => sum + value, 0);
    const lowPriceShare = project.competitors.filter((seed) => seed.quoteRatio < 0.84).length / project.competitors.length;
    return Math.round(clamp(38 + lowPriceShare * 36 + Math.min(loadedSources, 6) * 2, 32, 88));
  }, [project, competitorSourceCounts]);
  const effectiveMarketPressure = competitorParseState === "done" ? automaticMarketPressure : marketPressure;

  const evaluation = useMemo(
    () => evaluateScenario({ project, ourBid, readiness, qualificationReady, complianceReady, lowPriceEvidence, marketPressure: effectiveMarketPressure, run, competitorSourceCounts }),
    [project, ourBid, readiness, qualificationReady, complianceReady, lowPriceEvidence, effectiveMarketPressure, run, competitorSourceCounts],
  );

  const ourResult = evaluation.agents.find((agent) => agent.id === "A")!;

  const strategyPlans = useMemo(() => {
    if (!qualificationReady || !complianceReady || minimumFeasibleBid > project.maxPrice) return [] as StrategyPlan[];
    const start = Math.max(minimumFeasibleBid, project.maxPrice * 0.5);
    const step = Math.max(1, project.maxPrice / 180);
    const candidates: Array<{ quote: number; probability: number; expectedProfit: number; grossProfit: number; margin: number; abnormal: boolean }> = [];
    for (let quote = start; quote <= project.maxPrice + 0.01; quote += step) {
      const scenario = evaluateScenario({ project, ourBid: quote, readiness, qualificationReady, complianceReady, lowPriceEvidence, marketPressure: effectiveMarketPressure, run, competitorSourceCounts });
      const ours = scenario.agents.find((agent) => agent.id === "A")!;
      if (!ours.valid) continue;
      const grossProfit = quote - cost;
      const expectedProfit = (ours.winProbability / 100) * (quote - cost);
      candidates.push({ quote: Math.round(quote), probability: ours.winProbability, expectedProfit, grossProfit, margin: grossProfit / quote * 100, abnormal: ours.abnormalLow });
    }
    if (!candidates.length) return [] as StrategyPlan[];

    const pick = (objectiveId: Objective) => [...candidates].sort((a, b) => {
      const score = (item: typeof a) => {
        const abnormalPenalty = item.abnormal ? Math.max(9, item.expectedProfit * 0.24) : 0;
        if (objectiveId === "win") return item.probability - (item.abnormal ? 9 : 0);
        if (objectiveId === "expected") return item.expectedProfit - abnormalPenalty * 0.35;
        if (objectiveId === "margin") return item.margin * 1.7 + item.probability * 0.35 - (item.abnormal ? 16 : 0);
        return item.expectedProfit * (0.68 + 0.32 * item.probability / 100) - abnormalPenalty;
      };
      return score(b) - score(a);
    })[0];

    const metadata: Record<Objective, Pick<StrategyPlan, "label" | "tag" | "rationale" | "accent">> = {
      win: { label: "稳妥中标方案", tag: "胜率优先", rationale: "在自动识别的利润底线之上压低报价，优先争取排名，同时避开异常低价预警。", accent: "#315c4d" },
      expected: { label: "利润最大方案", tag: "期望利润峰值", rationale: "不追求最低报价，以中标概率与单项目毛利乘积最大为目标。", accent: "#3568a8" },
      balanced: { label: "均衡推荐方案", tag: "默认建议", rationale: "兼顾胜率、利润与报价波动，对竞争者画像误差更稳健。", accent: "#d28c3c" },
      margin: { label: "利润保护方案", tag: "安全垫优先", rationale: "保留更高毛利与履约风险准备金，适合资源紧张或成本不确定场景。", accent: "#8a735a" },
    };
    return (["balanced", "win", "expected", "margin"] as Objective[]).map((objectiveId) => {
      const result = pick(objectiveId);
      const spread = project.maxPrice * (competitorParseState === "done" ? 0.012 : 0.026);
      return {
        id: objectiveId,
        ...metadata[objectiveId],
        quote: result.quote,
        rangeLow: Math.round(Math.max(minimumFeasibleBid, result.quote - spread)),
        rangeHigh: Math.round(Math.min(project.maxPrice, result.quote + spread)),
        probability: result.probability,
        grossProfit: result.grossProfit,
        expectedProfit: result.expectedProfit,
        margin: result.margin,
        abnormal: result.abnormal,
      };
    });
  }, [project, cost, readiness, qualificationReady, complianceReady, lowPriceEvidence, effectiveMarketPressure, run, minimumFeasibleBid, competitorSourceCounts, competitorParseState]);

  const selectedPlan = strategyPlans.find((plan) => plan.id === objective) ?? strategyPlans[0] ?? null;
  const optimization = selectedPlan ? {
    quote: selectedPlan.quote,
    probability: selectedPlan.probability,
    expectedProfit: selectedPlan.expectedProfit,
    abnormal: selectedPlan.abnormal,
  } : null;

  const chartPoints = useMemo(() => {
    const start = Math.max(project.maxPrice * 0.5, Math.min(minimumFeasibleBid, project.maxPrice));
    const count = 52;
    return Array.from({ length: count }, (_, index) => {
      const quote = start + ((project.maxPrice - start) * index) / (count - 1);
      const scenario = evaluateScenario({ project, ourBid: quote, readiness, qualificationReady, complianceReady, lowPriceEvidence, marketPressure: effectiveMarketPressure, run, competitorSourceCounts });
      const ours = scenario.agents.find((agent) => agent.id === "A")!;
      return {
        quote,
        probability: ours.valid ? ours.winProbability : 0,
        expectedProfit: ours.valid ? Math.max(0, (ours.winProbability / 100) * (quote - cost)) : 0,
      };
    });
  }, [project, cost, readiness, qualificationReady, complianceReady, lowPriceEvidence, effectiveMarketPressure, run, minimumFeasibleBid, competitorSourceCounts]);

  const competitorProfiles = useMemo<CompetitorProfile[]>(() => project.competitors.map((seed) => {
    const sourceCount = competitorSourceCounts[seed.id];
    const predictedQuote = competitorQuote(project, seed, effectiveMarketPressure, run, sourceCount);
    const spreadRate = sourceCount ? Math.max(0.018, 0.06 - sourceCount * 0.014) : 0.095;
    const nonPriceScore = project.dimensions.reduce(
      (sum, dimension) => sum + dimension.points * (seed.nonPricePct[dimension.id] ?? 0),
      0,
    );
    const expectedBase = Math.min(predictedQuote, ...project.competitors.map((item) => competitorQuote(project, item, effectiveMarketPressure, run, competitorSourceCounts[item.id])));
    const priceScore = project.method === "综合评分法"
      ? expectedBase / predictedQuote * project.priceWeight
      : expectedBase / predictedQuote * 100;
    const predictedScore = project.method === "综合评分法" ? nonPriceScore + priceScore : priceScore;
    const confidence = sourceCount ? clamp(61 + sourceCount * 12, 61, 91) : 38;
    return {
      id: seed.id,
      name: seed.name,
      strategy: seed.strategy,
      predictedQuote,
      quoteLow: Math.round(predictedQuote * (1 - spreadRate)),
      quoteHigh: Math.round(Math.min(project.maxPrice, predictedQuote * (1 + spreadRate))),
      predictedScore,
      scoreLow: Math.max(0, predictedScore - (sourceCount ? 2.8 : 6.5)),
      scoreHigh: Math.min(100, predictedScore + (sourceCount ? 2.2 : 5.2)),
      confidence,
      sourceCount,
      historySamples: sourceCount ? sourceCount * 3 + seed.id.charCodeAt(0) % 4 : 0,
      behavior: seed.id === "B" ? "报价通常贴近历史低分位，价格敏感" : seed.id === "C" ? "以技术与服务得分换取报价溢价" : "多采用跟随定价，报价波动较小",
      risk: seed.qualificationIssue ?? seed.complianceIssue ?? (sourceCount ? "未发现明确门槛缺陷，需持续核验" : "资料不足，区间较宽"),
      accent: seed.accent,
    };
  }), [project, competitorSourceCounts, effectiveMarketPressure, run]);

  const competitorDataReady = competitorParseState === "done" && Object.values(competitorSourceCounts).some((count) => count > 0);
  const competitorConfidence = Math.round(competitorProfiles.reduce((sum, profile) => sum + profile.confidence, 0) / competitorProfiles.length);

  const rankedAgents = [...evaluation.agents].sort((a, b) => {
    if (a.rank === null && b.rank === null) return a.id.localeCompare(b.id);
    if (a.rank === null) return 1;
    if (b.rank === null) return -1;
    return a.rank - b.rank;
  });

  const documentMatches = useMemo(() => {
    const rows = DOCUMENT_MATCH_LIBRARY[project.id] ?? [];
    if (!companyFiles.length) {
      return rows.map((row) => ({ ...row, companySource: "尚未上传公司证明材料", status: "missing" as MatchStatus, confidence: 100 }));
    }
    if (gapsClosed) {
      return rows.map((row) => row.status === "matched" ? row : {
        ...row,
        status: "matched" as MatchStatus,
        companySource: `${row.companySource.replace(/（.*?）/g, "")} · 已补充复核材料`,
        confidence: Math.max(row.confidence, 94),
      });
    }
    return rows;
  }, [project.id, companyFiles.length, gapsClosed]);

  const hardGateMatches = documentMatches.filter((row) => row.mandatory);
  const hardGateGaps = hardGateMatches.filter((row) => row.status !== "matched");
  const qualificationMatches = documentMatches.filter((row) => row.kind === "资格门槛");
  const complianceMatches = documentMatches.filter((row) => row.kind === "实质性要求");
  const scoringMatches = documentMatches.filter((row) => !row.mandatory);
  const coverageOf = (rows: DocumentMatch[]) => rows.length
    ? Math.round(rows.reduce((sum, row) => sum + matchWeight(row.status), 0) / rows.length * 100)
    : 100;
  const qualificationCoverage = coverageOf(qualificationMatches);
  const complianceCoverage = coverageOf(complianceMatches);
  const scoringCoverage = coverageOf(scoringMatches);
  const overallDocumentCoverage = coverageOf(documentMatches);
  const analysisGatePass = hardGateGaps.length === 0 && companyFiles.length > 0;

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

  const clearAnalysisTimers = () => {
    analysisTimers.current.forEach((timer) => window.clearTimeout(timer));
    analysisTimers.current = [];
  };

  const clearCompetitorTimers = () => {
    competitorTimers.current.forEach((timer) => window.clearTimeout(timer));
    competitorTimers.current = [];
  };

  const resetDocumentAnalysis = () => {
    clearAnalysisTimers();
    setParseState("idle");
    setParseProgress(0);
    setParseStage(tenderFiles.length ? "文件已就绪，等待开始解析" : "等待上传招标文件");
    setGapsClosed(false);
  };

  const addDocuments = (target: UploadTarget, files: FileList | File[]) => {
    const incoming = Array.from(files).map((file, index) => ({
      id: `${target}-${file.name}-${file.lastModified}-${index}`,
      name: file.name,
      size: file.size,
      type: file.type || "application/octet-stream",
    }));
    const update = (current: UploadedDocument[]) => {
      const existing = new Set(current.map((file) => `${file.name}-${file.size}`));
      return [...current, ...incoming.filter((file) => !existing.has(`${file.name}-${file.size}`))];
    };
    if (target === "tender") {
      setTenderFiles(update);
      clearAnalysisTimers();
      setParseState("idle");
      setParseProgress(0);
      setParseStage("文件已就绪，等待开始解析");
      setGapsClosed(false);
    } else if (target === "company") {
      setCompanyFiles(update);
      clearAnalysisTimers();
      setParseState("idle");
      setParseProgress(0);
      setParseStage("文件已就绪，等待开始解析");
      setGapsClosed(false);
    } else {
      setCompetitorFiles((current) => ({ ...current, [target]: update(current[target]) }));
      clearCompetitorTimers();
      setCompetitorParseState("idle");
      setCompetitorParseProgress(0);
      setCompetitorParseStage("竞争者资料已就绪，等待画像解析");
    }
  };

  const removeDocument = (target: UploadTarget, id: string) => {
    if (target === "tender") {
      setTenderFiles((files) => files.filter((file) => file.id !== id));
      resetDocumentAnalysis();
    } else if (target === "company") {
      setCompanyFiles((files) => files.filter((file) => file.id !== id));
      resetDocumentAnalysis();
    } else {
      setCompetitorFiles((current) => ({ ...current, [target]: current[target].filter((file) => file.id !== id) }));
      clearCompetitorTimers();
      setCompetitorParseState("idle");
      setCompetitorParseProgress(0);
      setCompetitorParseStage("资料发生变化，请重新生成竞争者画像");
    }
  };

  const loadDemoDocuments = () => {
    const demo = DEMO_DOCUMENTS[project.id];
    setTenderFiles(demo?.tender ?? []);
    setCompanyFiles(demo?.company ?? []);
    clearAnalysisTimers();
    setParseState("idle");
    setParseProgress(0);
    setParseStage("演示材料已就绪，点击开始解析");
    setGapsClosed(false);
  };

  const loadDemoCompetitorDocuments = () => {
    setCompetitorFiles(DEMO_COMPETITOR_DOCUMENTS[project.id] ?? { B: [], C: [], D: [] });
    clearCompetitorTimers();
    setCompetitorParseState("idle");
    setCompetitorParseProgress(0);
    setCompetitorParseStage("三家竞争者演示资料已载入，点击生成画像");
  };

  const runCompetitorAnalysis = () => {
    if (!Object.values(competitorFiles).some((files) => files.length) || competitorParseState === "parsing") return;
    clearCompetitorTimers();
    setCompetitorParseState("parsing");
    setCompetitorParseProgress(8);
    setCompetitorParseStage("文档分类：识别投标报价、公告、资质与技术材料");
    const stages = [
      { delay: 420, progress: 28, label: "报价行为智能体：归一化历史项目规模与报价折扣" },
      { delay: 900, progress: 49, label: "能力画像智能体：映射资格、技术、商务和服务证据" },
      { delay: 1380, progress: 69, label: "评分预测智能体：按当前项目规则重算得分区间" },
      { delay: 1840, progress: 86, label: "不确定性智能体：估计样本偏差、缺失信息和置信区间" },
      { delay: 2280, progress: 100, label: "画像完成：已生成三家预测报价与评分区间", done: true },
    ];
    competitorTimers.current = stages.map((stage) => window.setTimeout(() => {
      setCompetitorParseProgress(stage.progress);
      setCompetitorParseStage(stage.label);
      if (stage.done) {
        setCompetitorParseState("done");
        setRun((value) => value + 1);
      }
    }, stage.delay));
  };

  const runDocumentAnalysis = () => {
    if (!tenderFiles.length || parseState === "parsing") return;
    clearAnalysisTimers();
    setParseState("parsing");
    setParseProgress(6);
    setParseStage("文件安全检查与版面识别");
    const stages = [
      { delay: 450, progress: 24, label: "招标规则智能体：定位资格条件与废标条款" },
      { delay: 950, progress: 47, label: "评分智能体：抽取权重、公式与证明要求" },
      { delay: 1450, progress: 69, label: "企业证据智能体：索引资质、业绩与技术材料" },
      { delay: 1950, progress: 88, label: "一致性裁判：执行逐条双向匹配与冲突检查" },
      { delay: 2450, progress: 100, label: "解析完成：已生成可追溯规则与缺口清单", done: true },
    ];
    analysisTimers.current = stages.map((stage) => window.setTimeout(() => {
      setParseProgress(stage.progress);
      setParseStage(stage.label);
      if (stage.done) setParseState("done");
    }, stage.delay));
  };

  const applyAnalysisToSimulation = () => {
    const qualificationPass = qualificationMatches.every((row) => row.status === "matched");
    const compliancePass = complianceMatches.every((row) => row.status === "matched");
    setQualificationReady(qualificationPass);
    setComplianceReady(compliancePass);
    setReadiness(scoringMatches.length ? clamp(Math.round(58 + scoringCoverage * 0.42), 55, 100) : 88);
    const automaticBid = strategyPlans.find((plan) => plan.id === "balanced")?.quote;
    if (automaticBid) setOurBid(automaticBid);
    setTab("cockpit");
    window.requestAnimationFrame(() => document.getElementById("workspace-tabs")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };

  const applyPlan = (plan: StrategyPlan) => {
    setObjective(plan.id);
    setOurBid(plan.quote);
    setTab("cockpit");
  };

  const openDocumentWorkspace = () => {
    setTab("documents");
    window.requestAnimationFrame(() => document.getElementById("workspace-tabs")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };

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
    setTenderFiles([]);
    setCompanyFiles([]);
    setCompetitorFiles({ B: [], C: [], D: [] });
    clearAnalysisTimers();
    clearCompetitorTimers();
    setParseState("idle");
    setCompetitorParseState("idle");
    setParseProgress(0);
    setCompetitorParseProgress(0);
    setParseStage("等待上传招标文件");
    setCompetitorParseStage("等待竞争者历史资料");
    setGapsClosed(false);
  };

  const report = {
    generatedAt: new Date().toISOString(),
    notice: "模拟决策，不构成中标保证；实际结论以招标文件和评标委员会依法评审为准。",
    project: { name: project.name, code: project.code, method: project.method, maxPrice: project.maxPrice },
    assumptions: { cost, minMargin, readiness, marketPressure, objective: OBJECTIVES[objective].label },
    bidDecision,
    current: { bid: ourBid, margin: roundTo(currentMargin), winProbability: roundTo(ourResult.winProbability), valid: ourResult.valid },
    recommendation: optimization ? { bid: optimization.quote, winProbability: roundTo(optimization.probability), expectedProfit: roundTo(optimization.expectedProfit) } : null,
    documentAnalysis: {
      state: parseState,
      tenderFiles: tenderFiles.map((file) => file.name),
      companyFiles: companyFiles.map((file) => file.name),
      coverage: overallDocumentCoverage,
      hardGateGaps: hardGateGaps.map((row) => row.requirement),
    },
    competitorAnalysis: {
      state: competitorParseState,
      confidence: competitorConfidence,
      profiles: competitorProfiles.map(({ id, name, predictedQuote, quoteLow, quoteHigh, predictedScore, scoreLow, scoreHigh, confidence, sourceCount }) => ({ id, name, predictedQuote, quoteLow, quoteHigh, predictedScore: roundTo(predictedScore), scoreLow: roundTo(scoreLow), scoreHigh: roundTo(scoreHigh), confidence, sourceCount })),
    },
    plans: strategyPlans.map(({ id, label, quote, rangeLow, rangeHigh, probability, grossProfit, expectedProfit, margin }) => ({ id, label, quote, rangeLow, rangeHigh, probability: roundTo(probability), grossProfit: roundTo(grossProfit), expectedProfit: roundTo(expectedProfit), margin: roundTo(margin) })),
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
    const planSummary = strategyPlans.map((plan) => `${plan.label}：${money(plan.quote)}（${money(plan.rangeLow)}–${money(plan.rangeHigh)}），模拟胜率 ${roundTo(plan.probability)}%，期望利润 ${money(plan.expectedProfit)}`).join("\n");
    const summary = `${project.name}\n决策：${bidDecision.label}\n竞争者画像置信度：${competitorConfidence}%\n${planSummary || "当前无可行方案"}\n说明：模拟结果不构成中标保证。`;
    await navigator.clipboard.writeText(summary);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  const tabs: Array<{ id: Tab; label: string; count?: number }> = [
    { id: "documents", label: "资料上传与画像", count: tenderFiles.length + companyFiles.length + Object.values(competitorSourceCounts).reduce((sum, value) => sum + value, 0) },
    { id: "cockpit", label: "多方案决策" },
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
            <h1>资料先画像，智能体再对抗；<br />一次生成多套报价方案。</h1>
            <p>上传招标文件、本公司材料及竞争者历史投标信息，系统预测各家报价与评分区间，再自动生成稳妥中标、利润最大、均衡和利润保护方案。</p>
            <div className="hero-note"><span>!</span><p><strong>核心原则</strong> 评分项、权重与公式来自当前项目；资格条件和实质性要求是通过制，不能混入通用加分表。</p></div>
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
            <div className={`document-lock ${parseState}`}><span>01</span><div><strong>{parseState === "done" ? "规则版本已解析并锁定" : parseState === "parsing" ? "文档解析进行中" : "等待上传项目文件"}</strong><small>{parseState === "done" ? `${tenderFiles.length} 份招标文件 · ${companyFiles.length} 份企业材料` : "支持 PDF、Word、Excel 与扫描件"}</small></div><b>{parseState === "done" ? "✓" : "→"}</b></div>
            <button className="project-upload-cta" type="button" onClick={openDocumentWorkspace}><span>上传三类决策资料</span><strong>进入资料工作台 →</strong></button>
          </aside>
        </section>

        <section className="workflow paper-card" aria-label="评标流程">
          {[
            ["01", "规则解析", "招标文件"],
            ["02", "我方画像", "资质 / 成本"],
            ["03", "竞手画像", "历史投标"],
            ["04", "门槛裁判", "通过制"],
            ["05", "多轮对抗", "区间抽样"],
            ["06", "多目标优化", "胜率 / 利润"],
            ["07", "多方案报告", "解释输出"],
          ].map(([num, title, text], index) => (
            <div className={`workflow-step ${index < 6 ? "active" : ""}`} key={num}>
              <span>{num}</span><div><strong>{title}</strong><small>{text}</small></div>{index < 6 && <i>→</i>}
            </div>
          ))}
        </section>

        <nav id="workspace-tabs" className="tabbar" aria-label="工作台视图">
          {tabs.map((item) => (
            <button className={tab === item.id ? "active" : ""} type="button" key={item.id} onClick={() => setTab(item.id)}>
              {item.label}{item.count !== undefined && <span>{item.count}</span>}
            </button>
          ))}
        </nav>

        {tab === "documents" && (
          <div className="documents-view">
            <section className="document-workbench-head paper-card">
              <div>
                <span className="card-kicker">DOCUMENT INTELLIGENCE</span>
                <h2>三类资料进入同一条决策链</h2>
                <p>招标文件决定规则，本公司材料决定门槛与能力，竞争者历史资料用于预测其报价区间、评分区间和策略偏好。</p>
              </div>
              <div className="demo-boundary">
                <span>DEMO 处理边界</span>
                <p>当前版本只登记文件名称和大小，不读取真实正文；解析结果由模拟数据生成。正式版需接入加密存储、OCR、抽取模型、数据授权与人工复核。</p>
              </div>
            </section>

            <div className="upload-grid">
              <section className="upload-card paper-card tender-upload">
                <div className="upload-card-head"><div><span>INPUT A</span><h3>招标方文件</h3><p>用于识别资格门槛、★ 条款、评分项、权重与报价公式</p></div><b>{tenderFiles.length} 份</b></div>
                <div
                  className={`dropzone ${dragZone === "tender" ? "dragging" : ""}`}
                  onDragEnter={(event) => { event.preventDefault(); setDragZone("tender"); }}
                  onDragOver={(event) => event.preventDefault()}
                  onDragLeave={() => setDragZone(null)}
                  onDrop={(event) => { event.preventDefault(); setDragZone(null); addDocuments("tender", event.dataTransfer.files); }}
                >
                  <input id="tender-file-input" type="file" multiple accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg" onChange={(event) => { if (event.target.files) addDocuments("tender", event.target.files); event.currentTarget.value = ""; }} />
                  <label htmlFor="tender-file-input"><span className="upload-symbol">招</span><strong>拖入招标文件，或点击选择</strong><small>建议同时上传主文件、采购需求、评分办法及更正公告</small><b>选择文件</b></label>
                </div>
                <div className="file-list">
                  {tenderFiles.map((file) => <div className="file-item" key={file.id}><span>{fileKind(file.name)}</span><div><strong>{file.name}</strong><small>{fileSize(file.size)} · 待安全扫描</small></div><button type="button" aria-label={`移除 ${file.name}`} onClick={() => removeDocument("tender", file.id)}>×</button></div>)}
                  {!tenderFiles.length && <div className="empty-file-list">尚未添加招标文件</div>}
                </div>
              </section>

              <section className="upload-card paper-card company-upload">
                <div className="upload-card-head"><div><span>INPUT B</span><h3>本公司材料库</h3><p>用于匹配营业执照、资质证书、业绩、人员与技术响应证据</p></div><b>{companyFiles.length} 份</b></div>
                <div
                  className={`dropzone ${dragZone === "company" ? "dragging" : ""}`}
                  onDragEnter={(event) => { event.preventDefault(); setDragZone("company"); }}
                  onDragOver={(event) => event.preventDefault()}
                  onDragLeave={() => setDragZone(null)}
                  onDrop={(event) => { event.preventDefault(); setDragZone(null); addDocuments("company", event.dataTransfer.files); }}
                >
                  <input id="company-file-input" type="file" multiple accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg" onChange={(event) => { if (event.target.files) addDocuments("company", event.target.files); event.currentTarget.value = ""; }} />
                  <label htmlFor="company-file-input"><span className="upload-symbol">企</span><strong>拖入公司材料，或点击选择</strong><small>支持批量添加；正式版将形成可复用的企业证据库</small><b>选择文件</b></label>
                </div>
                <div className="file-list">
                  {companyFiles.map((file) => <div className="file-item" key={file.id}><span>{fileKind(file.name)}</span><div><strong>{file.name}</strong><small>{fileSize(file.size)} · 待建立索引</small></div><button type="button" aria-label={`移除 ${file.name}`} onClick={() => removeDocument("company", file.id)}>×</button></div>)}
                  {!companyFiles.length && <div className="empty-file-list">未上传时可先解析招标规则，但无法判断我方是否满足</div>}
                </div>
              </section>
            </div>

            <section className="competitor-intake paper-card">
              <div className="section-heading">
                <div><span>INPUT C · COMPETITOR INTELLIGENCE</span><h2>竞争公司资料与历史投标信息</h2><p>每家公司单独建档。可加入公开中标公告、历史报价表、资质能力、技术方案摘要及合法取得的内部记录。</p></div>
                <div className="competitor-intake-actions"><button className="button ghost" type="button" onClick={loadDemoCompetitorDocuments} disabled={competitorParseState === "parsing"}>载入竞争者演示资料</button><button className="button dark" type="button" onClick={runCompetitorAnalysis} disabled={!Object.values(competitorFiles).some((files) => files.length) || competitorParseState === "parsing"}>{competitorParseState === "parsing" ? "画像生成中…" : competitorParseState === "done" ? "重新生成画像" : "生成竞争者画像"}</button></div>
              </div>
              <div className="competitor-upload-grid">
                {project.competitors.map((competitor) => (
                  <article className="competitor-upload" key={competitor.id} style={{ "--competitor": competitor.accent } as React.CSSProperties}>
                    <div className="competitor-upload-head"><span>{competitor.id}</span><div><strong>{competitor.name}</strong><small>{competitor.strategy} · {competitorFiles[competitor.id].length} 份资料</small></div></div>
                    <div
                      className={`competitor-dropzone ${dragZone === competitor.id ? "dragging" : ""}`}
                      onDragEnter={(event) => { event.preventDefault(); setDragZone(competitor.id); }}
                      onDragOver={(event) => event.preventDefault()}
                      onDragLeave={() => setDragZone(null)}
                      onDrop={(event) => { event.preventDefault(); setDragZone(null); addDocuments(competitor.id, event.dataTransfer.files); }}
                    >
                      <input id={`competitor-${competitor.id}-input`} type="file" multiple accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.png,.jpg,.jpeg" onChange={(event) => { if (event.target.files) addDocuments(competitor.id, event.target.files); event.currentTarget.value = ""; }} />
                      <label htmlFor={`competitor-${competitor.id}-input`}><strong>添加资料 / 历史投标</strong><small>PDF、Word、Excel、CSV</small></label>
                    </div>
                    <div className="competitor-file-list">
                      {competitorFiles[competitor.id].slice(0, 3).map((file) => <div key={file.id}><span>{fileKind(file.name)}</span><p><strong>{file.name}</strong><small>{fileSize(file.size)}</small></p><button type="button" aria-label={`移除 ${file.name}`} onClick={() => removeDocument(competitor.id, file.id)}>×</button></div>)}
                      {!competitorFiles[competitor.id].length && <p className="competitor-empty">未上传时使用低置信度行业先验</p>}
                    </div>
                  </article>
                ))}
              </div>
              <div className="competitor-progress"><div><span style={{ width: `${competitorParseProgress}%` }} /></div><strong>{competitorParseProgress}%</strong><p>{competitorParseStage}</p></div>
              <div className="data-compliance-note"><span>!</span><p><strong>数据边界：</strong>仅使用公开信息、已获授权或企业合法持有的数据；不得上传通过串标、围标、商业秘密窃取等不当方式获得的材料。预测仅用于内部风险分析。</p></div>
            </section>

            {competitorParseState === "done" && (
              <section className="competitor-profile-panel paper-card">
                <div className="section-heading"><div><span>COMPETITOR PROFILE EXTRACTION</span><h2>竞争者报价与评分预测画像</h2><p>区间宽度由样本数量和匹配程度决定；不是对真实投标行为的确定判断。</p></div><div className="profile-confidence"><span>综合置信度</span><strong>{competitorConfidence}%</strong><small>模拟值 · 数据越多区间越窄</small></div></div>
                <div className="competitor-profile-grid">
                  {competitorProfiles.map((profile) => <article key={profile.id} style={{ "--competitor": profile.accent } as React.CSSProperties}>
                    <div className="profile-head"><span>{profile.id}</span><div><strong>{profile.name}</strong><small>{profile.sourceCount} 份来源 · 约 {profile.historySamples} 个历史样本</small></div><b>{profile.confidence}%</b></div>
                    <div className="profile-forecast"><div><span>预测报价</span><strong>{money(profile.predictedQuote)}</strong><small>{money(profile.quoteLow)} – {money(profile.quoteHigh)}</small></div><div><span>{project.method === "综合评分法" ? "预测总分" : "评标价指数"}</span><strong>{roundTo(profile.predictedScore)}</strong><small>{roundTo(profile.scoreLow)} – {roundTo(profile.scoreHigh)}</small></div></div>
                    <p><strong>行为判断：</strong>{profile.behavior}</p><p><strong>门槛风险：</strong>{profile.risk}</p>
                  </article>)}
                </div>
                <div className="profile-actions"><p>画像已自动带入对抗模型，报价策略将按竞争者区间进行多轮扰动。</p><button className="button dark" type="button" onClick={() => { setTab("cockpit"); window.requestAnimationFrame(() => document.getElementById("workspace-tabs")?.scrollIntoView({ behavior: "smooth", block: "start" })); }}>查看多方案推演 →</button></div>
              </section>
            )}

            <section className="analysis-runner paper-card">
              <div className="analysis-runner-top">
                <div><span>ANALYSIS PIPELINE</span><h2>多智能体文档解析流水线</h2><p>{parseStage}</p></div>
                <div className="analysis-actions"><button className="button ghost" type="button" onClick={loadDemoDocuments} disabled={parseState === "parsing"}>载入演示材料</button><button className="button dark" type="button" onClick={runDocumentAnalysis} disabled={!tenderFiles.length || parseState === "parsing"}>{parseState === "parsing" ? "解析中…" : parseState === "done" ? "重新解析" : "开始解析与匹配"}</button></div>
              </div>
              <div className="parse-progress"><span style={{ width: `${parseProgress}%` }} /><b>{parseProgress}%</b></div>
              <div className="parser-agents">
                {[
                  ["01", "规则智能体", "方法 / 限价", 15],
                  ["02", "资格智能体", "准入 / 废标", 35],
                  ["03", "评分智能体", "权重 / 公式", 55],
                  ["04", "企业证据智能体", "资质 / 技术", 75],
                  ["05", "一致性裁判", "匹配 / 冲突", 95],
                ].map(([num, title, text, threshold]) => <div className={parseProgress >= Number(threshold) ? "active" : ""} key={String(num)}><span>{num}</span><div><strong>{title}</strong><small>{text}</small></div><b>{parseProgress >= Number(threshold) ? "✓" : "·"}</b></div>)}
              </div>
              {!tenderFiles.length && <p className="analysis-hint">请先上传至少一份招标方文件，或载入演示材料。</p>}
            </section>

            {parseState === "done" && (
              <>
                <section className="extraction-panel paper-card">
                  <div className="section-heading"><div><span>TENDER RULE EXTRACTION</span><h2>已抽取的项目规则</h2><p>每条规则保留来源位置；任何人工修改都应产生新版本并重新执行匹配。</p></div><div className="parse-confidence"><span>抽取置信度</span><strong>94.6%</strong><small>模拟值 · 待人工复核</small></div></div>
                  <div className="extraction-grid">
                    <article><span>01 · 评审方法</span><strong>{project.method}</strong><p>{project.decisionNote}</p><small>来源：招标文件“评标办法”章节</small></article>
                    <article><span>02 · 价格边界</span><strong>{money(project.maxPrice)}</strong><p>最高限价；异常低价重点审查线为限价的 {Math.round(project.lowPriceReviewRate * 100)}%。</p><small>来源：投标人须知与报价要求</small></article>
                    <article><span>03 · 硬门槛</span><strong>{project.qualifications.length + project.compliance.length} 项</strong><p>{project.qualifications.length} 项资格条件，{project.compliance.length} 项实质性要求。</p><small>来源：资格条件与 ★ 条款</small></article>
                    <article><span>04 · 详细评分</span><strong>{project.method === "综合评分法" ? `价格 ${project.priceWeight} 分` : "最低评标价排序"}</strong><p>{project.method === "综合评分法" ? project.dimensions.map((item) => `${item.label} ${item.points}`).join(" · ") : "技术参数通过制，不另设主观分值。"}</p><small>来源：评分因素及分值表</small></article>
                  </div>
                  <div className="extracted-formula"><span>报价规则</span><strong>{project.priceRule}</strong><button type="button" onClick={() => setTab("rules")}>查看全部规则 →</button></div>
                </section>

                <section className="matching-panel paper-card">
                  <div className="matching-summary">
                    <div className={`analysis-verdict ${analysisGatePass ? "pass" : "fail"}`}><span>{analysisGatePass ? "GATE PASS" : "GATE GAP"}</span><strong>{analysisGatePass ? "预计可进入详细评审" : "当前预计不能通过门槛"}</strong><p>{analysisGatePass ? "资格和实质性要求均已找到可验证证据，仍需人工逐页复核。" : `发现 ${hardGateGaps.length} 个强制要求未完全满足，不能用技术高分抵消。`}</p></div>
                    <div className="coverage-metrics">
                      <div><span>资格覆盖</span><strong>{qualificationCoverage}%</strong><i><b style={{ width: `${qualificationCoverage}%` }} /></i></div>
                      <div><span>实质响应</span><strong>{complianceCoverage}%</strong><i><b style={{ width: `${complianceCoverage}%` }} /></i></div>
                      <div><span>评分证据</span><strong>{scoringCoverage}%</strong><i><b style={{ width: `${scoringCoverage}%` }} /></i></div>
                      <div><span>综合覆盖</span><strong>{overallDocumentCoverage}%</strong><i><b style={{ width: `${overallDocumentCoverage}%` }} /></i></div>
                    </div>
                    <div className="matching-actions"><button className="button ghost" type="button" onClick={() => setGapsClosed(true)} disabled={analysisGatePass}>模拟补齐缺口</button><button className="button dark" type="button" onClick={applyAnalysisToSimulation}>将结果带入竞标模拟 →</button></div>
                  </div>

                  <div className="match-table-title"><div><span>EVIDENCE MATCH MATRIX</span><h2>招标要求 ↔ 公司证据匹配矩阵</h2></div><div><span className="match-dot matched" />已满足 <span className="match-dot partial" />部分满足 <span className="match-dot missing" />缺失</div></div>
                  <div className="table-scroll"><table className="document-match-table"><thead><tr><th>类型</th><th>招标要求</th><th>要求证据</th><th>公司材料定位</th><th>匹配结果</th><th>置信度</th></tr></thead><tbody>
                    {documentMatches.map((row) => <tr key={row.id}><td><span className={`requirement-kind ${row.mandatory ? "mandatory" : "scored"}`}>{row.kind}{row.mandatory && " · 必须"}</span></td><td><strong>{row.requirement}</strong><small>{row.tenderSource}</small></td><td>{row.requiredEvidence}</td><td><span className={row.status === "missing" ? "missing-source" : "company-source"}>{row.companySource}</span></td><td><span className={`match-status ${row.status}`}>{matchStatusLabel(row.status)}</span></td><td><strong>{row.confidence}%</strong></td></tr>)}
                  </tbody></table></div>
                  <div className="matching-footnote"><span>!</span><p><strong>机器判断不能直接替代投标负责人签字确认。</strong>正式版应允许用户查看原文高亮、纠正规则、指定证据版本，并保留解析与复核审计记录。</p></div>
                </section>
              </>
            )}
          </div>
        )}

        {tab === "cockpit" && (
          <div className="cockpit-main auto-cockpit">
              <section className="auto-baseline paper-card">
                <div className="section-heading"><div><span>AUTO-DERIVED BASELINE</span><h2>模型自动形成决策基线</h2><p>页面不再要求先手工猜报价、毛利率或竞争强度；以下数值由项目规则、本公司材料和竞争者历史资料联合推导。</p></div><button type="button" className="text-button" onClick={() => setTab("documents")}>返回资料工作台 →</button></div>
                <div className="baseline-grid">
                  <div><span>履约成本基线</span><strong>{money(cost)}</strong><small>本公司成本材料 / 模拟财务台账</small></div>
                  <div><span>利润保护线</span><strong>{minMargin}%</strong><small>公司制度与项目风险自动匹配</small></div>
                  <div><span>证据成熟度</span><strong>{readiness}%</strong><small>{companyFiles.length ? `${companyFiles.length} 份公司资料已建索引` : "使用模板先验，置信度较低"}</small></div>
                  <div><span>竞争画像置信度</span><strong>{competitorConfidence}%</strong><small>{competitorDataReady ? "历史资料已解析" : "尚未解析，使用宽区间行业先验"}</small></div>
                  <div><span>市场竞争强度</span><strong>{effectiveMarketPressure}</strong><small>{competitorParseState === "done" ? "根据对手低价倾向与有效样本自动估计" : "尚未解析竞争资料，使用项目模板先验"}</small></div>
                  <div><span>公司利润底价</span><strong>{Number.isFinite(minimumFeasibleBid) ? money(minimumFeasibleBid) : "无可行解"}</strong><small>成本 ÷（1 − 最低毛利率）</small></div>
                </div>
                <div className="baseline-note"><span>!</span><p>这些是解析后的内部假设，不是评标规则。正式版需显示字段来源、版本和财务审批状态，并允许有权限人员纠错。</p></div>
              </section>

              <section className="strategy-plans paper-card">
                <div className="section-heading"><div><span>MULTI-OBJECTIVE STRATEGIES</span><h2>系统生成的四个投标方案</h2><p>每个方案同时满足最高限价和自动识别的利润保护线；点击方案可带入沙盘复核。</p></div><div className="plan-data-status"><span className={competitorDataReady ? "ready" : "prior"}>{competitorDataReady ? "资料驱动" : "行业先验"}</span><small>区间而非单点承诺</small></div></div>
                <div className="strategy-plan-grid">
                  {strategyPlans.map((plan) => <article className={objective === plan.id ? "selected" : ""} key={plan.id} style={{ "--plan": plan.accent } as React.CSSProperties}>
                    <div className="plan-head"><span>{plan.tag}</span>{plan.id === "balanced" && <b>推荐</b>}</div>
                    <h3>{plan.label}</h3>
                    <div className="plan-price"><span>建议报价</span><strong>{money(plan.quote)}</strong><small>论证区间 {money(plan.rangeLow)} – {money(plan.rangeHigh)}</small></div>
                    <div className="plan-metrics"><div><span>模拟胜率</span><strong>{roundTo(plan.probability)}%</strong></div><div><span>预计毛利</span><strong>{money(plan.grossProfit)}</strong></div><div><span>期望利润</span><strong>{money(plan.expectedProfit)}</strong></div></div>
                    <p>{plan.rationale}</p>
                    <button type="button" onClick={() => applyPlan(plan)}>{objective === plan.id ? "已带入沙盘 ✓" : "采用此方案 →"}</button>
                  </article>)}
                  {!strategyPlans.length && <div className="no-plan"><strong>当前没有可行方案</strong><p>资格 / 符合性未通过，或自动识别的利润底价已超过最高限价。</p></div>}
                </div>
              </section>

              <section className="decision-strip">
                <div className={`bid-decision ${bidDecision.tone}`}><span>{bidDecision.code}</span><strong>{bidDecision.label}</strong><small>{bidDecision.reason}</small></div>
                <div className="decision-metric"><span>当前选定方案</span><strong>{selectedPlan?.label ?? "—"}</strong><small>{selectedPlan ? `${money(selectedPlan.rangeLow)} – ${money(selectedPlan.rangeHigh)}` : "无可行报价"}</small></div>
                <div className="decision-metric"><span>模拟胜出概率</span><strong>{optimization ? `${roundTo(optimization.probability)}%` : "—"}</strong><small>对手策略变化将改变结果</small></div>
                <div className="decision-metric"><span>预计毛利</span><strong>{optimization ? money(optimization.quote - cost) : "—"}</strong><small>{optimization ? `${roundTo((optimization.quote - cost) / optimization.quote * 100)}% 毛利率` : "无可行报价"}</small></div>
                <button className="run-button" type="button" onClick={() => setRun((value) => value + 1)}><span>重采样对手区间</span><strong>RUN {String(run + 1).padStart(2, "0")} ↗</strong></button>
              </section>

              <section className="arena-section paper-card">
                <div className="section-heading"><div><span>MULTI-AGENT ARENA</span><h2>资料驱动的多智能体评标沙盘</h2><p>A 使用选定方案；B/C/D 从各自画像的报价与评分区间抽样，规则裁判先淘汰无效投标，再排序。</p></div><div className="valid-summary"><strong>{evaluation.validCount}</strong><span>/ 4 有效投标</span></div></div>
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
              <div className="report-callout"><span>建议</span><p>{selectedPlan ? <>系统基于公司材料与竞争者画像，当前选定<strong>“{selectedPlan.label}”</strong>：重点论证 <strong>{money(selectedPlan.rangeLow)}–{money(selectedPlan.rangeHigh)}</strong> 区间，以 <strong>{money(selectedPlan.quote)}</strong> 作为模拟中心点；对应模拟胜出概率 <strong>{roundTo(selectedPlan.probability)}%</strong>、中标后预计毛利 <strong>{money(selectedPlan.grossProfit)}</strong>。</> : <>当前不存在同时满足资格 / 符合性、最高限价和公司利润底线的报价，请先修复门槛或重新评估是否参与。</>}</p></div>
              <div className="report-grid">
                <div><span>评审方法</span><strong>{project.method}</strong><small>以当前项目规则为准</small></div>
                <div><span>当前报价</span><strong>{money(ourBid)}</strong><small>模拟胜率 {roundTo(ourResult.winProbability)}%</small></div>
                <div><span>公司利润底价</span><strong>{Number.isFinite(minimumFeasibleBid) ? money(minimumFeasibleBid) : "无可行解"}</strong><small>最低毛利率 {minMargin}%</small></div>
                <div><span>有效竞争者</span><strong>{evaluation.validCount} / 4</strong><small>淘汰后才参与排名</small></div>
              </div>
              <div className="report-section"><div className="report-section-title"><span>01</span><h3>多方案比较</h3></div><div className="report-plan-list">{strategyPlans.map((plan) => <div key={plan.id}><span style={{ background: plan.accent }} /><p><strong>{plan.label}</strong>{money(plan.quote)} · 胜率 {roundTo(plan.probability)}% · 毛利 {money(plan.grossProfit)} · 期望利润 {money(plan.expectedProfit)}</p><b>{plan.id === objective ? "已选" : "备选"}</b></div>)}</div></div>
              <div className="report-section"><div className="report-section-title"><span>02</span><h3>主要判断依据</h3></div><ul><li>资格审查：我方{qualificationReady ? "材料齐备，模拟通过" : "存在缺失，模拟不通过"}。</li><li>符合性审查：我方{complianceReady ? "已响应全部实质性条款" : "存在实质性偏离"}，选定方案报价{ourBid <= project.maxPrice ? "未超过" : "已超过"}最高限价。</li><li>竞争者情报：已接入 {Object.values(competitorSourceCounts).reduce((sum, value) => sum + value, 0)} 份资料，画像综合置信度 {competitorConfidence}%。</li><li>评审公式：{project.priceRule}</li><li>竞争态势：{evaluation.agents.filter((agent) => !agent.valid).map((agent) => `${agent.name}因${agent.qualification === "fail" ? agent.qualificationDetail : agent.complianceDetail}被淘汰`).join("；") || "当前四家均进入详细评审"}。</li></ul></div>
              <div className="report-section"><div className="report-section-title"><span>03</span><h3>封标前动作</h3></div><div className="task-list">{project.evidenceRows.filter((row) => row.gap).map((row, index) => <div key={row.item}><span>{index + 1}</span><p><strong>{row.item}</strong>{row.gap}</p><b>待办</b></div>)}{gapCount === 0 && <p>当前模拟证据清单无未闭环项。</p>}</div></div>
              <div className="report-section"><div className="report-section-title"><span>04</span><h3>风险与边界</h3></div><p className="risk-copy">竞争对手不会公开完整成本与待投报价，历史项目与当前项目也不完全可比。模型只输出带置信区间的内部预测，不得用于串通投标、交换敏感报价或规避公平竞争。本报告不构成法律意见、投标承诺或中标保证。</p></div>
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
          <section className="method-modal" role="dialog" aria-modal="true" aria-labelledby="method-title">
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
