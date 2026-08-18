"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useParams } from "next/navigation";
import { Button, Card, EmptyState, Notice, StatusBadge, type StatusTone } from "@/components/ui";
import { PageFrame } from "@/components/shell/page-frame";
import type {
  CreateRiskAcceptanceRequest,
  MeResponse,
  RiskAcceptance,
  RiskAcceptanceState,
  RiskAcceptanceValidity,
} from "@biaice/contracts";

import {
  createRiskAcceptance,
  getCurrentIdentity,
  listRiskAcceptances,
  newIdempotencyKey,
  revokeRiskAcceptance,
} from "./api";
import styles from "./approvals.module.css";

type LoadState = "loading" | "ready" | "empty" | "unauthorized" | "error";

const STATE_TONE: Record<RiskAcceptanceState, StatusTone> = {
  ACTIVE: "success",
  REVOKED: "critical",
  EXPIRED: "warning",
};

const VALIDITY_TONE: Record<RiskAcceptanceValidity, StatusTone> = {
  CURRENT: "success",
  STALE: "warning",
  EXPIRED: "warning",
  INVALIDATED: "critical",
};

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "请求失败，请稍后重试。";
}

function isUnauthorized(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "status" in error &&
    [401, 403].includes((error as { status: number }).status)
  );
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

function toLocalInput(date: Date): string {
  return [
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`,
    `${pad(date.getHours())}:${pad(date.getMinutes())}`,
  ].join("T");
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function initialForm(): CreateRiskAcceptanceRequest {
  const from = new Date();
  const until = new Date(from.getTime() + 30 * 24 * 60 * 60 * 1000);
  return {
    risk: "",
    metric: "",
    acceptance_scope: "",
    rationale: "",
    independent_approver_id: "",
    valid_from: toLocalInput(from),
    valid_until: toLocalInput(until),
  };
}

export function ApprovalsMount() {
  const params = useParams<{ projectId: string; unitId: string }>();
  const unitId = params.unitId;
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [message, setMessage] = useState("正在读取当前决策单元的风险接受记录。");
  const [items, setItems] = useState<RiskAcceptance[]>([]);
  const [identity, setIdentity] = useState<MeResponse | null>(null);
  const [form, setForm] = useState<CreateRiskAcceptanceRequest>(initialForm);
  const [createPending, setCreatePending] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!unitId) return;
    const [riskAcceptances, me] = await Promise.all([
      listRiskAcceptances(unitId),
      getCurrentIdentity(),
    ]);
    return { riskAcceptances, me };
  }, [unitId]);

  const refresh = useCallback(async () => {
    try {
      const result = await load();
      if (!result) return;
      setItems(result.riskAcceptances);
      setIdentity(result.me);
      setLoadState(result.riskAcceptances.length === 0 ? "empty" : "ready");
      setMessage("风险接受已同步当前后端状态。");
    } catch (caught) {
      if (isUnauthorized(caught)) {
        setLoadState("unauthorized");
        setMessage("当前角色无权查看或变更风险接受。系统管理员默认不能读取审批内容。");
      } else {
        setLoadState("error");
        setMessage(errorMessage(caught));
      }
    }
  }, [load]);

  useEffect(() => {
    let cancelled = false;
    void load().then(
      (result) => {
        if (cancelled || !result) return;
        setItems(result.riskAcceptances);
        setIdentity(result.me);
        setLoadState(result.riskAcceptances.length === 0 ? "empty" : "ready");
        setMessage("风险接受已同步当前后端状态。");
      },
      (caught: unknown) => {
        if (cancelled) return;
        if (isUnauthorized(caught)) {
          setLoadState("unauthorized");
          setMessage("当前角色无权查看或变更风险接受。系统管理员默认不能读取审批内容。");
        } else {
          setLoadState("error");
          setMessage(errorMessage(caught));
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, [load]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!unitId) return;
    setCreatePending(true);
    setCreateError(null);
    try {
      await createRiskAcceptance(
        unitId,
        {
          ...form,
          valid_from: new Date(form.valid_from).toISOString(),
          valid_until: new Date(form.valid_until).toISOString(),
        },
        newIdempotencyKey("create_risk_acceptance", unitId),
      );
      setForm(initialForm());
      await refresh();
    } catch (caught) {
      setCreateError(errorMessage(caught));
    } finally {
      setCreatePending(false);
    }
  }

  const mfaReady = identity?.mfa_verified === true;

  return (
    <PageFrame
      eyebrow="FR-09b · MEMBER 7"
      title="审批与风险接受"
      description="风险接受由独立授权人完成并受有效期约束；商业审批、提交授权和完整报告在 Pilot Gate 前保持关闭。"
    >
      <div className={styles.page}>
        <Notice title="Pilot 前关闭审批" tone="warning">
          本页面只开放 RiskAcceptance 创建与撤销，不构成商业批准或正式提交许可。影子审批不会在 MVP-B 暴露写入口。
        </Notice>

        {loadState === "loading" && (
          <Card title="正在加载">
            <p className={styles.muted} role="status" aria-live="polite">
              {message}
            </p>
          </Card>
        )}
        {loadState === "unauthorized" && (
          <Notice title="无权限" tone="warning">
            {message}
          </Notice>
        )}
        {loadState === "error" && (
          <Notice title="接口不可用" tone="danger">
            {message}
          </Notice>
        )}

        <div className={styles.grid}>
          <Card eyebrow="CREATE" title="创建风险接受">
            <form className={styles.form} onSubmit={handleCreate}>
              <label className={styles.field}>
                <span>风险</span>
                <input
                  required
                  maxLength={200}
                  value={form.risk}
                  onChange={(event) => setForm({ ...form, risk: event.target.value })}
                  placeholder="例如：压力场景下目标区间超出政策容忍"
                />
              </label>
              <label className={styles.field}>
                <span>指标</span>
                <input
                  required
                  maxLength={200}
                  value={form.metric}
                  onChange={(event) => setForm({ ...form, metric: event.target.value })}
                  placeholder="例如：Scenario CVaR"
                />
              </label>
              <label className={styles.field}>
                <span>接受范围</span>
                <input
                  required
                  maxLength={400}
                  value={form.acceptance_scope}
                  onChange={(event) =>
                    setForm({ ...form, acceptance_scope: event.target.value })
                  }
                  placeholder="该风险接受覆盖哪些决策单元或方案范围"
                />
              </label>
              <label className={styles.field}>
                <span>理由</span>
                <textarea
                  required
                  maxLength={2000}
                  value={form.rationale}
                  onChange={(event) => setForm({ ...form, rationale: event.target.value })}
                  placeholder="独立授权人接受的依据"
                />
              </label>
              <label className={styles.field}>
                <span>独立授权人 ID</span>
                <input
                  required
                  value={form.independent_approver_id}
                  onChange={(event) =>
                    setForm({ ...form, independent_approver_id: event.target.value })
                  }
                  placeholder="UUID，不能与创建人相同"
                />
              </label>
              <div className={styles.field}>
                <label htmlFor="valid-from">有效起始</label>
                <input
                  id="valid-from"
                  required
                  type="datetime-local"
                  value={form.valid_from}
                  onChange={(event) => setForm({ ...form, valid_from: event.target.value })}
                />
              </div>
              <div className={styles.field}>
                <label htmlFor="valid-until">有效截止</label>
                <input
                  id="valid-until"
                  required
                  type="datetime-local"
                  value={form.valid_until}
                  onChange={(event) => setForm({ ...form, valid_until: event.target.value })}
                />
              </div>
              {createError ? (
                <Notice title="创建失败" tone="danger">
                  {createError}
                </Notice>
              ) : null}
              <Button type="submit" disabled={!mfaReady || createPending}>
                {createPending ? "提交中…" : "创建风险接受"}
              </Button>
              {!mfaReady ? (
                <p className={styles.hint}>创建与撤销都需要当前会话完成 MFA 验证。</p>
              ) : null}
            </form>
          </Card>

          <Card eyebrow="LIST" title="风险接受记录">
            {loadState === "empty" ? (
              <EmptyState
                title="还没有风险接受"
                description="当前决策单元没有可用的风险接受版本。创建后，成员 6 才能读取当前风险状态参与资格判断。"
              />
            ) : (
              <ul className={styles.rows}>
                {items.map((item) => (
                  <li key={item.risk_acceptance_id}>
                    <RiskAcceptanceRow item={item} mfaReady={mfaReady} onChanged={refresh} />
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </PageFrame>
  );
}

function RiskAcceptanceRow({
  item,
  mfaReady,
  onChanged,
}: {
  readonly item: RiskAcceptance;
  readonly mfaReady: boolean;
  readonly onChanged: () => Promise<void>;
}) {
  const [reason, setReason] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const revocable = item.state === "ACTIVE" && item.validity === "CURRENT";

  async function handleRevoke(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!reason.trim()) return;
    setPending(true);
    setError(null);
    try {
      await revokeRiskAcceptance(
        item.risk_acceptance_id,
        { revocation_reason: reason.trim() },
        newIdempotencyKey("revoke_risk_acceptance", item.risk_acceptance_id),
      );
      setReason("");
      await onChanged();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setPending(false);
    }
  }

  return (
    <article className={styles.row}>
      <div className={styles.rowMeta}>
        <StatusBadge tone={STATE_TONE[item.state]}>{item.state}</StatusBadge>
        <StatusBadge tone={VALIDITY_TONE[item.validity]}>{item.validity}</StatusBadge>
        <span className={styles.shortId}>{item.risk_acceptance_id}</span>
      </div>
      <h3 className={styles.rowTitle}>{item.risk}</h3>
      <p className={styles.muted}>
        指标：{item.metric}；范围：{item.acceptance_scope}
      </p>
      <p className={styles.muted}>
        有效 {formatDateTime(item.valid_from)} 至 {formatDateTime(item.valid_until)}；独立授权人{" "}
        {item.independent_approver_id}
      </p>
      {item.revocation_reason ? (
        <p className={styles.muted}>撤销：{item.revocation_reason}</p>
      ) : null}
      {revocable ? (
        <form className={styles.revoke} onSubmit={handleRevoke}>
          <input
            required
            maxLength={1000}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="撤销原因"
          />
          <div className={styles.actions}>
            <Button variant="danger" type="submit" disabled={!mfaReady || pending || !reason.trim()}>
              {pending ? "撤销中…" : "撤销"}
            </Button>
          </div>
          {error ? (
            <Notice title="撤销失败" tone="danger">
              {error}
            </Notice>
          ) : null}
        </form>
      ) : null}
    </article>
  );
}
