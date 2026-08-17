"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Card, EmptyState, Notice, StatusBadge, type StatusTone } from "@/components/ui";
import styles from "./evidence.module.css";

type LoadState = "loading" | "ready" | "empty" | "unauthorized" | "error";

type Requirement = {
  requirement_id: string;
  title: string;
  mandatory: boolean;
  lifecycle_state: string;
};

type Match = {
  match_id: string;
  requirement_id: string;
  state: string;
};

type Precheck = {
  decision: string;
  unmapped_mandatory_count: number;
  evidence_coverage: string;
};

type Condition = {
  condition_id: string;
  title: string;
  state: string;
  blocking_stage: string;
};

function toneFor(value: string): StatusTone {
  if (value === "PASS" || value === "SATISFIED" || value === "PUBLISHED") return "success";
  if (value === "CONDITIONAL" || value === "PARTIAL" || value === "OPEN") return "warning";
  if (value === "BLOCKED" || value === "UNSATISFIED" || value === "FAILED") return "critical";
  return "info";
}

export function EvidencePrecheckMount() {
  const params = useParams<{ projectId: string; unitId: string }>();
  const unitId = params.unitId;
  const [state, setState] = useState<LoadState>("loading");
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [precheck, setPrecheck] = useState<Precheck | null>(null);
  const [conditions, setConditions] = useState<Condition[]>([]);
  const [message, setMessage] = useState("正在读取当前决策单元的证据与预审状态。");

  useEffect(() => {
    if (!unitId) {
      setState("error");
      setMessage("缺少决策单元上下文，无法恢复证据工作区。");
      return;
    }
    let cancelled = false;
    async function load() {
      try {
        const [reqRes, matchRes, precheckRes, conditionRes] = await Promise.all([
          fetch(`/api/v1/decision-units/${unitId}/requirements`, { credentials: "include" }),
          fetch(`/api/v1/decision-units/${unitId}/evidence-matches`, { credentials: "include" }),
          fetch(`/api/v1/decision-units/${unitId}/precheck-assessments`, { credentials: "include" }),
          fetch(`/api/v1/decision-units/${unitId}/conditions`, { credentials: "include" }),
        ]);
        if (cancelled) return;
        if ([reqRes, matchRes, precheckRes, conditionRes].some((item) => item.status === 401 || item.status === 403)) {
          setState("unauthorized");
          setMessage("当前角色无权查看证据或预审。系统管理员默认不能读取正文。");
          return;
        }
        if (![reqRes, matchRes, precheckRes, conditionRes].every((item) => item.ok)) {
          setState("error");
          setMessage("证据接口暂时不可用。未映射强制项按未知处理，不会显示默认通过。");
          return;
        }
        const reqJson = (await reqRes.json()) as { items: Requirement[] };
        const matchJson = (await matchRes.json()) as { items: Match[] };
        const precheckJson = (await precheckRes.json()) as { items: Precheck[] };
        const conditionJson = (await conditionRes.json()) as { items: Condition[] };
        setRequirements(reqJson.items);
        setMatches(matchJson.items);
        setPrecheck(precheckJson.items.at(-1) ?? null);
        setConditions(conditionJson.items);
        setState(reqJson.items.length === 0 && matchJson.items.length === 0 ? "empty" : "ready");
      } catch {
        if (!cancelled) {
          setState("error");
          setMessage("无法连接证据服务。预审不会用成本或市场数据补全结论。");
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
          <p className={styles.eyebrow}>FR-03 · MEMBER 4</p>
          <h1>证据、响应与预审</h1>
          <p>
            强制规则必须有匹配行。没有证据不得判满足；预审只检查制度/规则、主体资格、实质响应、证据和截止前闭环，不读取成本、利润或竞对。
          </p>
        </div>
        <StatusBadge tone={state === "ready" ? "success" : state === "empty" ? "warning" : "info"}>
          {state === "loading" ? "加载中" : state === "ready" ? "已接入真实状态" : "待补证据"}
        </StatusBadge>
      </Card>

      <Notice title="失败关闭" tone="danger">
        未映射强制项视为未知并阻断正式预审通过。成员 3 未放行的文档不能作为证据引用。条件任务由本模块唯一写入，审批侧只能调用 satisfy/waive/fail/expire。
      </Notice>

      {state === "loading" && (
        <Card title="正在核对证据映射">
          <p className={styles.muted} role="status" aria-live="polite">
            {message}
          </p>
        </Card>
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
          title="还没有要求或证据"
          description="发布 Requirement 并完成双向匹配后才能生成预审。三个合成项目夹具接入后会显示强制项覆盖缺口。"
        />
      )}

      <div className={styles.grid}>
        <Card eyebrow="REQUIREMENT" title="要求与强制项">
          {requirements.length === 0 ? (
            <EmptyState title="无要求" description="等待成员 2 的已发布条款映射为本模块 Requirement。" />
          ) : (
            <ul className={styles.list}>
              {requirements.map((item) => (
                <li key={item.requirement_id}>
                  <strong>{item.title}</strong>
                  <StatusBadge tone={item.mandatory ? "warning" : "neutral"}>
                    {item.mandatory ? "强制" : "非强制"} · {item.lifecycle_state}
                  </StatusBadge>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card eyebrow="MATCH" title="双向匹配">
          {matches.length === 0 ? (
            <EmptyState title="无匹配行" description="缺行按未知处理，不会自动满足。" />
          ) : (
            <ul className={styles.list}>
              {matches.map((item) => (
                <li key={item.match_id}>
                  <span>{item.requirement_id}</span>
                  <StatusBadge tone={toneFor(item.state)}>{item.state}</StatusBadge>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card eyebrow="PRECHECK" title="资格/响应预审">
          {precheck ? (
            <div className={styles.stack}>
              <StatusBadge tone={toneFor(precheck.decision)}>{precheck.decision}</StatusBadge>
              <p className={styles.muted}>
                未映射强制项 {precheck.unmapped_mandatory_count}；证据覆盖 {precheck.evidence_coverage}。该结论不因成本或市场变化而改变。
              </p>
            </div>
          ) : (
            <EmptyState title="尚未评估" description="创建 PrecheckAssessment 后显示 PASS/CONDITIONAL/BLOCKED/UNKNOWN。" />
          )}
        </Card>
        <Card eyebrow="CONDITION" title="条件任务">
          {conditions.length === 0 ? (
            <EmptyState title="无开放条件" description="阻断或未知只能探索。成员 7 通过命令端口关闭条件，不能直写表。" />
          ) : (
            <ul className={styles.list}>
              {conditions.map((item) => (
                <li key={item.condition_id}>
                  <strong>{item.title}</strong>
                  <StatusBadge tone={toneFor(item.state)}>
                    {item.state} · {item.blocking_stage}
                  </StatusBadge>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
