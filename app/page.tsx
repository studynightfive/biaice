"use client";

import { useEffect, useMemo, useRef, useState } from "react";

const BUDGET = 1200;
const PRICE_MIN = 820;
const PRICE_MAX = 1140;

const WEIGHTS = [
  { key: "tech", label: "技术方案", short: "技术", value: 40, color: "#246b50" },
  { key: "price", label: "投标报价", short: "报价", value: 30, color: "#b7d65b" },
  { key: "service", label: "履约服务", short: "履约", value: 18, color: "#e8a849" },
  { key: "business", label: "商务响应", short: "商务", value: 12, color: "#d3cec3" },
] as const;

type Agent = {
  id: "A" | "B" | "C" | "D";
  company: string;
  role: string;
  quote: number;
  quoteRange: string;
  tech: number;
  service: number;
  business: number;
  total?: number;
  probability?: number;
  strategy: string;
  tone: string;
};

type Scenario = {
  competitorPriceFactor?: number;
  ourTechDelta?: number;
};

const COMPETITORS: Agent[] = [
  {
    id: "B",
    company: "北辰数字",
    role: "价格进攻型",
    quote: 895,
    quoteRange: "¥867–923万",
    tech: 82,
    service: 78,
    business: 84,
    strategy: "低价抢分",
    tone: "amber",
  },
  {
    id: "C",
    company: "云启智能",
    role: "技术领先型",
    quote: 1018,
    quoteRange: "¥984–1,052万",
    tech: 94,
    service: 91,
    business: 90,
    strategy: "技术溢价",
    tone: "blue",
  },
  {
    id: "D",
    company: "经纬系统",
    role: "均衡跟随型",
    quote: 958,
    quoteRange: "¥928–988万",
    tech: 86,
    service: 85,
    business: 83,
    strategy: "均衡跟随",
    tone: "slate",
  },
];

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

const formatMoney = (value: number) =>
  new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 }).format(value);

function getProfitMargin(price: number, cost: number) {
  return ((price - cost) / price) * 100;
}

function getProfitFloor(cost: number, minProfit: number) {
  return cost / (1 - minProfit / 100);
}

function scoreAgents(price: number, scenario: Scenario = {}) {
  const competitorPriceFactor = scenario.competitorPriceFactor ?? 1;
  const ourTechDelta = scenario.ourTechDelta ?? 0;
  const agents: Agent[] = [
    {
      id: "A",
      company: "我方 · 标策科技",
      role: "利润约束型",
      quote: price,
      quoteRange: `当前 ¥${formatMoney(price)}万`,
      tech: 93 + ourTechDelta,
      service: 91,
      business: 89,
      strategy: "推荐策略",
      tone: "green",
    },
    ...COMPETITORS.map((agent) => ({
      ...agent,
      quote: agent.quote * competitorPriceFactor,
    })),
  ];

  const basePrice = Math.min(...agents.map((agent) => agent.quote));
  const totals = agents.map((agent) => {
    const priceScore = clamp((basePrice / agent.quote) * 100, 0, 100);
    const total =
      agent.tech * 0.4 +
      priceScore * 0.3 +
      agent.service * 0.18 +
      agent.business * 0.12;
    return { ...agent, total };
  });

  const maxScore = Math.max(...totals.map((agent) => agent.total));
  const exponentials = totals.map((agent) =>
    Math.exp((agent.total - maxScore) / 2)
  );
  const probabilityTotal = exponentials.reduce((sum, value) => sum + value, 0);

  return totals
    .map((agent, index) => ({
      ...agent,
      probability: (exponentials[index] / probabilityTotal) * 100,
    }))
    .sort((a, b) => (b.probability ?? 0) - (a.probability ?? 0));
}

function getOurMetrics(price: number, scenario: Scenario = {}) {
  return scoreAgents(price, scenario).find((agent) => agent.id === "A")!;
}

function getRecommendedPrice(cost: number, minProfit: number) {
  const floor = getProfitFloor(cost, minProfit);
  const start = clamp(Math.ceil(floor / 2) * 2, PRICE_MIN, PRICE_MAX);
  let bestPrice = start;
  let bestProbability = -1;

  for (let candidate = start; candidate <= PRICE_MAX; candidate += 2) {
    const probability = getOurMetrics(candidate).probability ?? 0;
    if (probability > bestProbability) {
      bestProbability = probability;
      bestPrice = candidate;
    }
  }

  return bestPrice;
}

function percentDelta(value: number) {
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(1)}pp`;
}

function ProbabilityChart({
  currentPrice,
  recommendedPrice,
  cost,
  minProfit,
  onPriceChange,
}: {
  currentPrice: number;
  recommendedPrice: number;
  cost: number;
  minProfit: number;
  onPriceChange: (price: number) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;

    const rect = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    canvas.width = rect.width * ratio;
    canvas.height = rect.height * ratio;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);

    const width = rect.width;
    const height = rect.height;
    const padding = { top: 18, right: 18, bottom: 34, left: 42 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;
    const x = (price: number) =>
      padding.left + ((price - PRICE_MIN) / (PRICE_MAX - PRICE_MIN)) * plotWidth;
    const y = (probability: number) =>
      padding.top + ((100 - probability) / 100) * plotHeight;

    context.clearRect(0, 0, width, height);
    context.font = '11px "Microsoft YaHei", sans-serif';
    context.textBaseline = "middle";

    const floor = clamp(getProfitFloor(cost, minProfit), PRICE_MIN, PRICE_MAX);
    context.fillStyle = "rgba(216, 103, 75, 0.08)";
    context.fillRect(x(PRICE_MIN), padding.top, x(floor) - x(PRICE_MIN), plotHeight);

    [0, 25, 50, 75, 100].forEach((tick) => {
      context.beginPath();
      context.strokeStyle = tick === 0 ? "rgba(255,255,255,.18)" : "rgba(255,255,255,.08)";
      context.lineWidth = 1;
      context.moveTo(padding.left, y(tick));
      context.lineTo(width - padding.right, y(tick));
      context.stroke();
      context.fillStyle = "rgba(232, 236, 226, .48)";
      context.textAlign = "right";
      context.fillText(`${tick}%`, padding.left - 9, y(tick));
    });

    [820, 900, 980, 1060, 1140].forEach((tick) => {
      context.fillStyle = "rgba(232, 236, 226, .48)";
      context.textAlign = "center";
      context.fillText(`${tick}`, x(tick), height - 12);
    });

    const points: Array<{ price: number; probability: number }> = [];
    for (let chartPrice = PRICE_MIN; chartPrice <= PRICE_MAX; chartPrice += 4) {
      points.push({
        price: chartPrice,
        probability: getOurMetrics(chartPrice).probability ?? 0,
      });
    }

    const area = context.createLinearGradient(0, padding.top, 0, height - padding.bottom);
    area.addColorStop(0, "rgba(183, 214, 91, .28)");
    area.addColorStop(1, "rgba(183, 214, 91, 0)");
    context.beginPath();
    points.forEach((point, index) => {
      const px = x(point.price);
      const py = y(point.probability);
      if (index === 0) context.moveTo(px, py);
      else context.lineTo(px, py);
    });
    context.lineTo(x(PRICE_MAX), y(0));
    context.lineTo(x(PRICE_MIN), y(0));
    context.closePath();
    context.fillStyle = area;
    context.fill();

    context.beginPath();
    points.forEach((point, index) => {
      const px = x(point.price);
      const py = y(point.probability);
      if (index === 0) context.moveTo(px, py);
      else context.lineTo(px, py);
    });
    context.strokeStyle = "#b7d65b";
    context.lineWidth = 2.5;
    context.lineJoin = "round";
    context.lineCap = "round";
    context.stroke();

    context.setLineDash([5, 5]);
    context.beginPath();
    context.strokeStyle = "rgba(232, 168, 73, .8)";
    context.moveTo(x(floor), padding.top);
    context.lineTo(x(floor), height - padding.bottom);
    context.stroke();
    context.setLineDash([]);
    context.fillStyle = "#e8a849";
    context.textAlign = floor > 1060 ? "right" : "left";
    context.fillText(
      "利润红线",
      x(floor) + (floor > 1060 ? -7 : 7),
      padding.top + 9
    );

    const recommendedProbability = getOurMetrics(recommendedPrice).probability ?? 0;
    context.beginPath();
    context.fillStyle = "#b7d65b";
    context.arc(x(recommendedPrice), y(recommendedProbability), 5.5, 0, Math.PI * 2);
    context.fill();
    context.beginPath();
    context.strokeStyle = "rgba(183, 214, 91, .4)";
    context.lineWidth = 5;
    context.arc(x(recommendedPrice), y(recommendedProbability), 9, 0, Math.PI * 2);
    context.stroke();

    const currentProbability = getOurMetrics(currentPrice).probability ?? 0;
    if (currentPrice !== recommendedPrice) {
      context.beginPath();
      context.strokeStyle = "rgba(255,255,255,.48)";
      context.setLineDash([3, 4]);
      context.moveTo(x(currentPrice), padding.top);
      context.lineTo(x(currentPrice), height - padding.bottom);
      context.stroke();
      context.setLineDash([]);
      context.beginPath();
      context.fillStyle = "#f4f2ed";
      context.arc(x(currentPrice), y(currentProbability), 4, 0, Math.PI * 2);
      context.fill();
    }
  }, [currentPrice, recommendedPrice, cost, minProfit]);

  const handlePointer = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const paddingLeft = 42;
    const paddingRight = 18;
    const raw =
      PRICE_MIN +
      ((event.clientX - rect.left - paddingLeft) /
        (rect.width - paddingLeft - paddingRight)) *
        (PRICE_MAX - PRICE_MIN);
    onPriceChange(clamp(Math.round(raw / 2) * 2, PRICE_MIN, PRICE_MAX));
  };

  return (
    <canvas
      ref={canvasRef}
      className="probability-canvas"
      role="img"
      aria-label="报价与中标概率关系曲线，橙色虚线表示最低利润率对应的报价红线"
      onPointerDown={handlePointer}
    />
  );
}

export default function Home() {
  const [cost, setCost] = useState(760);
  const [minProfit, setMinProfit] = useState(18);
  const recommendedPrice = useMemo(
    () => getRecommendedPrice(cost, minProfit),
    [cost, minProfit]
  );
  const [price, setPrice] = useState(928);
  const [isRunning, setIsRunning] = useState(false);
  const [runCount, setRunCount] = useState(1);
  const [showModel, setShowModel] = useState(false);

  const rankedAgents = useMemo(() => scoreAgents(price), [price, runCount]);
  const ourAgent = rankedAgents.find((agent) => agent.id === "A")!;
  const recommendedMetrics = useMemo(
    () => getOurMetrics(recommendedPrice),
    [recommendedPrice]
  );
  const profit = price - cost;
  const profitMargin = getProfitMargin(price, cost);
  const isProfitable = profitMargin >= minProfit;
  const priceDifference = price - recommendedPrice;
  const baseProbability = ourAgent.probability ?? 0;
  const competitorCutProbability =
    getOurMetrics(price, { competitorPriceFactor: 0.97 }).probability ?? 0;
  const techDropProbability =
    getOurMetrics(price, { ourTechDelta: -4 }).probability ?? 0;
  const costUpRecommended = getRecommendedPrice(cost * 1.05, minProfit);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setShowModel(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const runSimulation = () => {
    if (isRunning) return;
    setIsRunning(true);
    window.setTimeout(() => {
      setRunCount((value) => value + 1);
      setIsRunning(false);
    }, 1100);
  };

  const exportPlan = () => {
    const report = {
      project: "智慧园区数字化运维服务项目",
      dataNotice: "前端演示模拟数据",
      recommendedBidWan: recommendedPrice,
      currentBidWan: price,
      predictedWinRate: Number(baseProbability.toFixed(1)),
      estimatedProfitWan: profit,
      estimatedProfitMargin: Number(profitMargin.toFixed(1)),
      minimumProfitMargin: minProfit,
      weights: Object.fromEntries(WEIGHTS.map((weight) => [weight.label, weight.value])),
      agentRanking: rankedAgents.map((agent, index) => ({
        rank: index + 1,
        agent: agent.id,
        company: agent.company,
        bidWan: Math.round(agent.quote),
        totalScore: Number((agent.total ?? 0).toFixed(2)),
        winRate: Number((agent.probability ?? 0).toFixed(1)),
      })),
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: "application/json;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "标策AI-投标决策演示方案.json";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <div className="brand-mark" aria-hidden="true">策</div>
          <div>
            <div className="brand-name">标策 AI</div>
            <div className="brand-en">BID DECISION LAB</div>
          </div>
        </div>

        <nav className="topnav" aria-label="页面导航">
          <a className="active" href="#decision">决策沙盘</a>
          <a href="#agents">智能体竞演</a>
          <a href="#rules">评分规则</a>
        </nav>

        <div className="topbar-actions">
          <span className="demo-badge"><i /> 模拟数据</span>
          <button className="ghost-button" onClick={() => setShowModel(true)}>
            模型说明
          </button>
          <button className="dark-button" onClick={exportPlan}>
            导出方案 <span aria-hidden="true">↗</span>
          </button>
        </div>
      </header>

      <section className="workspace" id="decision">
        <div className="page-heading">
          <div>
            <div className="eyebrow"><span>项目 01</span> · 服务类综合评分</div>
            <h1>多智能体投标决策台</h1>
            <p>在利润红线之上，寻找更有机会胜出的报价。</p>
          </div>
          <div className="project-meta">
            <div className="project-title-row">
              <span className="project-label">当前项目</span>
              <span className="status-dot">推演就绪</span>
            </div>
            <strong>智慧园区数字化运维服务项目</strong>
            <span>项目预算 ¥1,200万 · 4 家模拟投标人</span>
          </div>
        </div>

        <div className="kpi-grid">
          <article className="kpi-card primary-kpi">
            <div className="kpi-label">推荐报价 <span>01</span></div>
            <div className="kpi-value"><small>¥</small>{formatMoney(recommendedPrice)}<em>万</em></div>
            <div className="kpi-foot">
              <span className="positive">最优可行解</span>
              <span>预算占比 {((recommendedPrice / BUDGET) * 100).toFixed(1)}%</span>
            </div>
          </article>
          <article className="kpi-card">
            <div className="kpi-label">预计中标概率 <span>02</span></div>
            <div className="kpi-value">{(recommendedMetrics.probability ?? 0).toFixed(1)}<em>%</em></div>
            <div className="kpi-foot">
              <span className="positive">优势区间</span>
              <span>对手均值 +{((recommendedMetrics.total ?? 0) - 88.6).toFixed(1)} 分</span>
            </div>
          </article>
          <article className="kpi-card">
            <div className="kpi-label">预计项目利润 <span>03</span></div>
            <div className="kpi-value"><small>¥</small>{formatMoney(recommendedPrice - cost)}<em>万</em></div>
            <div className="kpi-foot">
              <span className="positive">满足要求</span>
              <span>利润率 {getProfitMargin(recommendedPrice, cost).toFixed(1)}%</span>
            </div>
          </article>
          <article className="kpi-card confidence-kpi">
            <div className="kpi-label">模型置信度 <span>04</span></div>
            <div className="kpi-value">82<em>%</em></div>
            <div className="confidence-line"><i style={{ width: "82%" }} /></div>
            <div className="kpi-foot">
              <span>基于 10,000 次模拟竞演</span>
            </div>
          </article>
        </div>

        <div className="decision-grid">
          <aside className="control-panel panel">
            <div className="panel-heading compact">
              <div>
                <span className="section-index">01 / 决策变量</span>
                <h2>报价约束</h2>
              </div>
              <span className="live-dot">实时</span>
            </div>

            <div className="field-group quote-field">
              <label htmlFor="price-input">我方投标金额</label>
              <div className="money-input">
                <span>¥</span>
                <input
                  id="price-input"
                  type="number"
                  min={PRICE_MIN}
                  max={PRICE_MAX}
                  value={price}
                  onChange={(event) =>
                    setPrice(clamp(Number(event.target.value) || PRICE_MIN, PRICE_MIN, PRICE_MAX))
                  }
                />
                <small>万元</small>
              </div>
              <input
                className="range-input"
                type="range"
                min={PRICE_MIN}
                max={PRICE_MAX}
                step="2"
                value={price}
                aria-label="我方投标金额"
                onChange={(event) => setPrice(Number(event.target.value))}
                style={{
                  "--range-progress": `${((price - PRICE_MIN) / (PRICE_MAX - PRICE_MIN)) * 100}%`,
                } as React.CSSProperties}
              />
              <div className="range-labels"><span>¥820万</span><span>¥1,140万</span></div>
            </div>

            <div className="split-fields">
              <div className="field-group">
                <label htmlFor="cost-input">预计总成本</label>
                <div className="small-input">
                  <span>¥</span>
                  <input
                    id="cost-input"
                    type="number"
                    min="600"
                    max="920"
                    value={cost}
                    onChange={(event) => setCost(clamp(Number(event.target.value) || 600, 600, 920))}
                  />
                  <small>万</small>
                </div>
              </div>
              <div className="field-group">
                <label htmlFor="profit-input">最低利润率</label>
                <div className="small-input">
                  <input
                    id="profit-input"
                    type="number"
                    min="8"
                    max="30"
                    value={minProfit}
                    onChange={(event) => setMinProfit(clamp(Number(event.target.value) || 8, 8, 30))}
                  />
                  <small>%</small>
                </div>
              </div>
            </div>

            <div className={`constraint-card ${isProfitable ? "safe" : "warning"}`}>
              <div>
                <span>{isProfitable ? "利润约束已满足" : "当前方案低于红线"}</span>
                <strong>{profitMargin.toFixed(1)}%</strong>
              </div>
              <p>
                {isProfitable
                  ? `预计利润 ¥${formatMoney(profit)}万，较最低要求高 ${(profitMargin - minProfit).toFixed(1)}pp。`
                  : `至少需报价 ¥${formatMoney(Math.ceil(getProfitFloor(cost, minProfit)))}万。`}
              </p>
            </div>

            <div className="weight-summary">
              <div className="weight-title"><span>评分权重</span><small>合计 100%</small></div>
              <div className="mini-weight-bar">
                {WEIGHTS.map((weight) => (
                  <i
                    key={weight.key}
                    style={{ width: `${weight.value}%`, backgroundColor: weight.color }}
                    title={`${weight.label} ${weight.value}%`}
                  />
                ))}
              </div>
              <div className="mini-weight-labels">
                {WEIGHTS.map((weight) => (
                  <span key={weight.key}><i style={{ background: weight.color }} />{weight.short} {weight.value}</span>
                ))}
              </div>
            </div>

            <button
              className="recommend-button"
              onClick={() => setPrice(recommendedPrice)}
              disabled={price === recommendedPrice}
            >
              <span>应用推荐报价</span>
              <strong>¥{formatMoney(recommendedPrice)}万</strong>
            </button>
          </aside>

          <section className="chart-panel panel">
            <div className="panel-heading">
              <div>
                <span className="section-index">02 / 报价前沿</span>
                <h2>胜率与利润可行域</h2>
              </div>
              <div className="chart-legend">
                <span><i className="legend-line green" />中标概率</span>
                <span><i className="legend-line amber" />利润红线</span>
              </div>
            </div>

            <div className="chart-summary">
              <div>
                <span>当前方案</span>
                <strong>¥{formatMoney(price)}万</strong>
              </div>
              <div>
                <span>预计胜率</span>
                <strong>{baseProbability.toFixed(1)}%</strong>
              </div>
              <div>
                <span>综合得分</span>
                <strong>{(ourAgent.total ?? 0).toFixed(1)}</strong>
              </div>
              <div className={isProfitable ? "feasible" : "unfeasible"}>
                <span>可行性</span>
                <strong>{isProfitable ? "满足约束" : "不可行"}</strong>
              </div>
            </div>

            <div className="chart-wrap">
              <ProbabilityChart
                currentPrice={price}
                recommendedPrice={recommendedPrice}
                cost={cost}
                minProfit={minProfit}
                onPriceChange={setPrice}
              />
              <div className="chart-note">
                <span>推荐点</span>
                <strong>¥{formatMoney(recommendedPrice)}万</strong>
                <small>{(recommendedMetrics.probability ?? 0).toFixed(1)}% 胜率</small>
              </div>
            </div>

            <div className="insight-strip">
              <span className="insight-icon" aria-hidden="true">↳</span>
              <p>
                <strong>决策洞察：</strong>
                {priceDifference === 0
                  ? "当前已处于利润约束下的胜率峰值；继续降价将触碰公司利润红线。"
                  : priceDifference > 0
                    ? `当前报价比推荐值高 ¥${formatMoney(priceDifference)}万，预计少获得 ${Math.max(0, (recommendedMetrics.probability ?? 0) - baseProbability).toFixed(1)}pp 胜率。`
                    : "当前报价更具价格优势，但未必满足公司设定的最低利润要求。"}
              </p>
            </div>
          </section>

          <aside className="agents-panel panel" id="agents">
            <div className="panel-heading compact">
              <div>
                <span className="section-index">03 / 智能体竞演</span>
                <h2>四方投标沙盘</h2>
              </div>
              <span className="agent-status">4 / 4 在线</span>
            </div>

            <div className={`agent-stack ${isRunning ? "running" : ""}`}>
              {rankedAgents.map((agent, index) => (
                <article className={`agent-card ${agent.id === "A" ? "ours" : ""}`} key={agent.id}>
                  <div className={`agent-avatar ${agent.tone}`}>{agent.id}</div>
                  <div className="agent-info">
                    <div className="agent-title">
                      <strong>{agent.company}</strong>
                      {agent.id === "A" && <span>我方</span>}
                    </div>
                    <p>{agent.role} · {agent.strategy}</p>
                    <div className="agent-score-line">
                      <span>报价 <b>¥{formatMoney(Math.round(agent.quote))}万</b></span>
                      <span>总分 <b>{(agent.total ?? 0).toFixed(1)}</b></span>
                    </div>
                  </div>
                  <div className="agent-probability">
                    <small>#{index + 1}</small>
                    <strong>{(agent.probability ?? 0).toFixed(1)}%</strong>
                    <span>胜出倾向</span>
                  </div>
                </article>
              ))}
            </div>

            <div className="agent-consensus">
              <div className="consensus-head">
                <span className="pulse-icon"><i /><i /><i /></span>
                <strong>{isRunning ? "智能体正在交叉评审…" : "本轮竞演共识"}</strong>
              </div>
              <p>
                {isRunning
                  ? "正在重算报价分、技术优势与利润可行域。"
                  : `A 在 ¥${formatMoney(recommendedPrice)}万附近保持技术优势，同时守住 ${minProfit}% 利润红线。`}
              </p>
            </div>

            <button className="run-button" onClick={runSimulation} disabled={isRunning}>
              <span className="run-symbol" aria-hidden="true">{isRunning ? "···" : "▶"}</span>
              {isRunning ? "正在推演 10,000 次" : "重新运行竞演"}
            </button>
            <div className="run-meta">第 {runCount} 轮 · 模拟数据已脱敏 · 约 1.1 秒</div>
          </aside>
        </div>

        <section className="lower-grid" id="rules">
          <article className="rules-panel panel">
            <div className="panel-heading">
              <div>
                <span className="section-index">04 / 评分模型</span>
                <h2>服务类项目综合评分示例</h2>
              </div>
              <button className="text-button" onClick={() => setShowModel(true)}>查看依据 ↗</button>
            </div>

            <div className="weight-bar" aria-label="评分权重分布">
              {WEIGHTS.map((weight) => (
                <div
                  key={weight.key}
                  style={{ width: `${weight.value}%`, backgroundColor: weight.color }}
                >
                  <strong>{weight.value}%</strong>
                  <span>{weight.label}</span>
                </div>
              ))}
            </div>

            <div className="criteria-grid">
              <div>
                <span className="criteria-number">01</span>
                <strong>技术方案 · 40分</strong>
                <p>方案完整性 16 · 团队能力 9 · 实施计划 9 · 创新与安全 6</p>
              </div>
              <div>
                <span className="criteria-number">02</span>
                <strong>投标报价 · 30分</strong>
                <p>低价优先法：基准价 ÷ 投标报价 × 30；异常低价单独预警</p>
              </div>
              <div>
                <span className="criteria-number">03</span>
                <strong>履约服务 · 18分</strong>
                <p>SLA与响应 7 · 售后保障 6 · 培训及交付 5</p>
              </div>
              <div>
                <span className="criteria-number">04</span>
                <strong>商务响应 · 12分</strong>
                <p>同类履约经验 5 · 合同条款响应 4 · 资源保障 3</p>
              </div>
            </div>

            <div className="gate-row">
              <span className="gate-title">准入门槛（不计分）</span>
              <span>✓ 资格审查</span>
              <span>✓ 实质性响应</span>
              <span>✓ 不超最高限价</span>
              <span>✓ 异常低价可解释</span>
            </div>
          </article>

          <article className="stress-panel panel">
            <div className="panel-heading">
              <div>
                <span className="section-index">05 / 风险压力测试</span>
                <h2>如果外部条件变化</h2>
              </div>
              <span className="scenario-badge">3 个情景</span>
            </div>

            <div className="stress-list">
              <div className="stress-item">
                <span className="stress-icon down">↓</span>
                <div>
                  <strong>对手整体降价 3%</strong>
                  <p>价格竞争加剧</p>
                </div>
                <div className="stress-result negative">
                  <strong>{competitorCutProbability.toFixed(1)}%</strong>
                  <span>{percentDelta(competitorCutProbability - baseProbability)}</span>
                </div>
              </div>
              <div className="stress-item">
                <span className="stress-icon tech">T</span>
                <div>
                  <strong>我方技术评分 -4分</strong>
                  <p>方案优势收窄</p>
                </div>
                <div className="stress-result negative">
                  <strong>{techDropProbability.toFixed(1)}%</strong>
                  <span>{percentDelta(techDropProbability - baseProbability)}</span>
                </div>
              </div>
              <div className="stress-item">
                <span className="stress-icon cost">¥</span>
                <div>
                  <strong>项目成本上浮 5%</strong>
                  <p>利润红线右移</p>
                </div>
                <div className="stress-result neutral">
                  <strong>¥{formatMoney(costUpRecommended)}万</strong>
                  <span>新建议价</span>
                </div>
              </div>
            </div>

            <div className="risk-tip">
              <span aria-hidden="true">!</span>
              <p><strong>关键风险：</strong>云启智能的技术评分最接近我方，若其报价低于 ¥980万，建议强化实施计划与 SLA 证据。</p>
            </div>
          </article>
        </section>

        <footer className="page-footer">
          <p>本页面仅用于前端方案评审，所有公司、报价及概率均为模拟数据，不构成实际投标或法律意见。</p>
          <span>模型版本 DEMO 0.1 · 规则更新时间 2026.08.06</span>
        </footer>
      </section>

      {showModel && (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setShowModel(false)}>
          <section
            className="model-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="model-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <button className="modal-close" onClick={() => setShowModel(false)} aria-label="关闭">×</button>
            <span className="section-index">MODEL NOTE / DEMO 0.1</span>
            <h2 id="model-title">模型口径与评分依据</h2>
            <p className="modal-lead">这是一套用于验证页面和决策流程的可解释模拟模型，不是通用法定评分模板。</p>

            <div className="modal-section">
              <h3>本 Demo 如何计算</h3>
              <ol>
                <li><span>1</span><p><strong>先过准入门槛</strong>：资格、实质性响应、最高限价和异常低价风险单独判断，不混入得分。</p></li>
                <li><span>2</span><p><strong>再算综合得分</strong>：技术 40% + 报价 30% + 履约服务 18% + 商务响应 12%。</p></li>
                <li><span>3</span><p><strong>最后做情景推演</strong>：A 为我方，B/C/D 为竞争对手；根据得分差异映射为模拟胜率。</p></li>
              </ol>
            </div>

            <div className="formula-card">
              <span>报价得分（示例）</span>
              <strong>最低有效报价 ÷ 本方报价 × 30</strong>
              <small>推荐价 = 满足最低利润率约束的可行报价中，模拟胜率最高者</small>
            </div>

            <div className="modal-section sources">
              <h3>权威规则参考</h3>
              <a href="https://tfs.mof.gov.cn/caizhengbuling/201707/t20170718_2652603.htm" target="_blank" rel="noreferrer">
                <span>财政部令第87号</span>
                <p>综合评分因素应与质量相关并细化量化；服务项目价格权重不得低于 10%，价格分采用低价优先法。</p>
              </a>
              <a href="https://fgw.beijing.gov.cn/fgwzwgk/2024zcwj/flfggz/gz/bmgz/202004/t20200416_3727865.htm" target="_blank" rel="noreferrer">
                <span>评标委员会和评标方法暂行规定</span>
                <p>综合评估法应按招标文件明确的量化因素和权重，对技术与商务部分加权比较。</p>
              </a>
              <a href="https://www.mof.gov.cn/gkml/caizhengwengao/2017wg/wg201702/201706/t20170602_2614096.htm" target="_blank" rel="noreferrer">
                <span>财政部履约验收管理指导意见</span>
                <p>采购需求、服务实施与履约验收应完整、明确并形成闭环。</p>
              </a>
            </div>

            <div className="modal-warning">
              正式版本需按具体招标文件、行业规则、公司成本口径和历史中标数据重新训练与校准。
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
