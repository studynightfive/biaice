"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Card, EmptyState, Notice, StatusBadge, type StatusTone } from "@/components/ui";
import styles from "./commercial.module.css";

type LoadState = "loading" | "ready" | "empty" | "unauthorized" | "error";

type Cost = {
  cost_baseline_id: string;
  exploration_only: boolean;
  lifecycle_state: string;
  currency: string;
};

type ReadinessItem = {
  code: string;
  decision: string;
  reason_code: string;
  commercial_not_procurement: boolean;
};

type Readiness = {
  decision: string;
  exploration_watermark: boolean;
  items: ReadinessItem[];
};

function toneFor(value: string): StatusTone {
  if (value === "READY" || value === "PUBLISHED") return "success";
  if (value === "CONDITIONAL" || value === "UNKNOWN") return "warning";
  return "critical";
}

export function CommercialReadinessMount() {
  const params = useParams<{ unitId: string }>();
  const unitId = params.unitId;
  const [state, setState] = useState<LoadState>("loading");
  const [costs, setCosts] = useState<Cost[]>([]);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [message, setMessage] = useState("正在读取成本、政策与策略就绪。");

  useEffect(() => {
    if (!unitId) {
      setState("error");
      setMessage("缺少决策单元上下文。");
      return;
    }
    let cancelled = false;
    async function load() {
      try {
        const [costRes, readyRes] = await Promise.all([
          fetch(`/api/v1/decision-units/${unitId}/cost-baselines`, { credentials: "include" }),
          fetch(`/api/v1/decision-units/${unitId}/readiness-assessments`, { credentials: "include" }),
        ]);
        if (cancelled) return;
        if (costRes.status === 401 || costRes.status === 403 || readyRes.status === 401 || readyRes.status === 403) {
          setState("unauthorized");
          setMessage("当前角色无权查看成本或就绪。系统管理员默认无成本权限。");
          return;
        }
        if (!costRes.ok || !readyRes.ok) {
          setState("error");
          setMessage("商业就绪接口不可用。未批准成本只能探索，不会输出正式利润结论。");
          return;
        }
        const costJson = (await costRes.json()) as { items: Cost[] };
        const readyJson = (await readyRes.json()) as { items: Readiness[] };
        setCosts(costJson.items);
        setReadiness(readyJson.items.at(-1) ?? null);
        setState(costJson.items.length === 0 && readyJson.items.length === 0 ? "empty" : "ready");
      } catch {
        if (!cancelled) {
          setState("error");
          setMessage("无法连接商业就绪服务。");
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [unitId]);

  return (
    <div className={styles.page}>
      <Card className={styles.hero}>
        <div>
          <p className={styles.eyebrow}>FR-04 · MEMBER 4</p>
          <h1>成本、政策与就绪</h1>
          <p>
            成本编制人与批准人必须不同。未批准成本只显示探索态。商业政策不通过只表示“公司政策下不可推荐”，不能写成采购规则意义上的投标无效。
          </p>
        </div>
        <StatusBadge tone={readiness?.exploration_watermark ? "warning" : "info"}>
          {readiness?.exploration_watermark ? "探索水印" : "就绪检查"}
        </StatusBadge>
      </Card>

      <Notice title="语义分离" tone="warning">
        采购规则预审结果与公司商业基线是不同子结果。市场先验由成员 5 提供；缺失时就绪项为 UNKNOWN，不得伪造正式排名输入。
      </Notice>

      {state === "loading" && (
        <p className={styles.muted} role="status" aria-live="polite">
          {message}
        </p>
      )}
      {state === "unauthorized" && (
        <Notice title="无权限" tone="warning">
          {message}
        </Notice>
      )}
      {state === "error" && (
        <Notice title="接口不可用" tone="danger">
          {message}
        </Notice>
      )}
      {state === "empty" && (
        <EmptyState
          title="还没有成本或就绪记录"
          description="先编制成本基线，并由独立财务批准人批准后才能离开探索态。"
        />
      )}

      <div className={styles.grid}>
        <Card eyebrow="COST" title="成本基线">
          {costs.length === 0 ? (
            <EmptyState title="无成本版本" description="未批准成本禁止正式利润结论。" />
          ) : (
            <ul className={styles.list}>
              {costs.map((item) => (
                <li key={item.cost_baseline_id}>
                  <span>{item.currency}</span>
                  <StatusBadge tone={item.exploration_only ? "warning" : "success"}>
                    {item.exploration_only ? "仅探索" : item.lifecycle_state}
                  </StatusBadge>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card eyebrow="READINESS" title="策略就绪分项">
          {readiness ? (
            <ul className={styles.list}>
              {readiness.items.map((item) => (
                <li key={item.code}>
                  <span>
                    {item.code}
                    {item.commercial_not_procurement ? " · 商业" : " · 采购/上游"}
                  </span>
                  <StatusBadge tone={toneFor(item.decision)}>
                    {item.decision}
                  </StatusBadge>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="尚未评估就绪" description="就绪检查分项列出规则、预审、响应、成本、政策、市场、用途、模型和场景协议。" />
          )}
        </Card>
      </div>
    </div>
  );
}
