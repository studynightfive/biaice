"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Button, Card, EmptyState, Notice, StatusBadge } from "@/components/ui";
import { describeM5Problem, newIdempotencyKey, requestM5Json } from "@/features/m5-api";
import styles from "@/features/m5-workbench.module.css";

type ResourceDefinition = { readonly path: string; readonly label: string };
type MarketResourceRecord = {
  readonly resource_id: string;
  readonly resource_type: string;
  readonly state: string;
  readonly state_version: number;
  readonly updated_at: string;
};
type MarketResourcePage = {
  readonly items: ReadonlyArray<MarketResourceRecord>;
  readonly has_more: boolean;
  readonly next_cursor: string | null;
};
type LifecycleAction = {
  readonly action: string;
  readonly label: string;
  readonly body?: Readonly<Record<string, string>>;
};
type NoticeState = { readonly title: string; readonly detail: string; readonly danger?: boolean };

const RESOURCES: ReadonlyArray<ResourceDefinition> = [
  { path: "processing-records", label: "处理活动记录" },
  { path: "legal-basis-evidence", label: "处理基础证据" },
  { path: "notice-consent-records", label: "告知与同意记录" },
  { path: "pia-records", label: "PIA 记录" },
  { path: "cross-border-assessments", label: "跨境评估" },
  { path: "provider-policies", label: "服务商处理政策" },
  { path: "dsr-policies", label: "DSR 政策" },
  { path: "load-profiles", label: "负载档案" },
  { path: "data-subject-requests", label: "数据主体请求" },
  { path: "incident-policies", label: "事件政策" },
  { path: "incidents", label: "安全事件" },
];

const INCIDENT_NEXT_STATE: Readonly<Record<string, string>> = {
  OPEN: "TRIAGED",
  TRIAGED: "CONTAINED",
  CONTAINED: "REMEDIATING",
  REMEDIATING: "RESOLVED",
};

function resourceActions(path: string, state: string): ReadonlyArray<LifecycleAction> {
  if (path === "pia-records") {
    if (state === "DRAFT") return [{ action: "approve", label: "批准" }];
    if (state === "APPROVED") return [{ action: "revoke", label: "撤销" }];
  }
  if (path === "cross-border-assessments" || path === "provider-policies") {
    if (state === "DRAFT") {
      return [
        { action: "approve", label: "批准" },
        {
          action: "mark-not-required",
          label: "标记不适用",
          body: { reason_code: "VERIFIED_NOT_REQUIRED" },
        },
      ];
    }
    if (state === "APPROVED" || state === "NOT_REQUIRED") {
      return [
        { action: "revoke", label: "撤销" },
        { action: "expire", label: "失效" },
      ];
    }
  }
  if (path === "dsr-policies") {
    if (state === "DRAFT") return [{ action: "publish", label: "发布" }];
    if (state === "PUBLISHED") return [{ action: "archive", label: "归档" }];
  }
  if (path === "load-profiles" && state === "DRAFT") {
    return [{ action: "freeze", label: "冻结" }];
  }
  if (path === "data-subject-requests") {
    if (state === "RECEIVED") return [{ action: "verify-identity", label: "核验身份" }];
    if (state === "IDENTITY_VERIFIED") {
      return [{ action: "transition", label: "开始处理", body: { target_state: "IN_PROGRESS" } }];
    }
    if (state === "IN_PROGRESS") {
      return [
        {
          action: "transition",
          label: "准备完成",
          body: { target_state: "READY_TO_COMPLETE" },
        },
        { action: "complete", label: "完成" },
      ];
    }
    if (state === "READY_TO_COMPLETE") return [{ action: "complete", label: "完成" }];
  }
  if (path === "incident-policies" && state === "DRAFT") {
    return [{ action: "approve", label: "批准" }];
  }
  if (path === "incidents") {
    const targetState = INCIDENT_NEXT_STATE[state];
    if (targetState) {
      return [
        {
          action: "transition",
          label: `推进至 ${targetState}`,
          body: { target_state: targetState },
        },
      ];
    }
    if (state === "RESOLVED") return [{ action: "close", label: "关闭事件" }];
  }
  return [];
}

function stateTone(state: string): "success" | "warning" | "critical" | "info" | "neutral" {
  if (["APPROVED", "PUBLISHED", "COMPLETED", "CLOSED", "CURRENT", "FROZEN"].includes(state)) {
    return "success";
  }
  if (["REVOKED", "EXPIRED", "REJECTED"].includes(state)) return "critical";
  if (["DRAFT", "RECEIVED", "OPEN"].includes(state)) return "warning";
  return "info";
}

export function PrivacyModelsMount() {
  const [resourcePath, setResourcePath] = useState(RESOURCES[0].path);
  const [records, setRecords] = useState<ReadonlyArray<MarketResourceRecord>>([]);
  const [loading, setLoading] = useState(true);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [subjectScope, setSubjectScope] = useState("synthetic-ui");
  const [justificationRef, setJustificationRef] = useState("ui://fr12/manual-entry");
  const [retentionDays, setRetentionDays] = useState("30");
  const [withdrawalRef, setWithdrawalRef] = useState("");
  const [notice, setNotice] = useState<NoticeState | null>(null);
  const selectedResource = useMemo(
    () => RESOURCES.find((resource) => resource.path === resourcePath) ?? RESOURCES[0],
    [resourcePath],
  );

  useEffect(() => {
    const controller = new AbortController();
    requestM5Json<MarketResourcePage>("GET", `/api/v1/${resourcePath}`, {
      signal: controller.signal,
    })
      .then((page) => setRecords(page.items))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setNotice({
          title: "隐私记录读取失败",
          detail: describeM5Problem(error, "隐私服务暂时不可用，请检查本地身份 BFF 与 API 配置。"),
          danger: true,
        });
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [resourcePath]);

  async function createRecord(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsedRetentionDays = Number(retentionDays);
    if (!Number.isInteger(parsedRetentionDays) || parsedRetentionDays < 0 || parsedRetentionDays > 36500) return;
    setBusyKey("create");
    setNotice(null);
    try {
      const created = await requestM5Json<MarketResourceRecord>("POST", `/api/v1/${resourcePath}`, {
        idempotencyKey: newIdempotencyKey("fr12-create"),
        body: {
          subject_scope: subjectScope.trim(),
          justification_ref: justificationRef.trim(),
          retention_days: parsedRetentionDays,
        },
      });
      setRecords((current) => [created, ...current]);
      setNotice({
        title: `${selectedResource.label}已创建`,
        detail: "仅保存合成/去标识元数据；真实个人信息仍受 REAL_DATA_MODE、PIA 与 DSR 门禁阻断。",
      });
    } catch (error) {
      const detail = describeM5Problem(error, "写入失败，请检查权限、幂等键与合成元数据字段。");
      setNotice({ title: "写入被拒绝", detail, danger: true });
    } finally {
      setBusyKey(null);
    }
  }

  async function runLifecycle(record: MarketResourceRecord, action: LifecycleAction) {
    const key = `${record.resource_id}:${action.action}`;
    setBusyKey(key);
    setNotice(null);
    try {
      const updated = await requestM5Json<MarketResourceRecord>(
        "POST",
        `/api/v1/${resourcePath}/${encodeURIComponent(record.resource_id)}/${action.action}`,
        {
          idempotencyKey: newIdempotencyKey(`fr12-${action.action}`),
          body: action.body ?? {},
        },
      );
      setRecords((current) => current.map((item) => (item.resource_id === updated.resource_id ? updated : item)));
      setNotice({
        title: "状态已更新",
        detail: `${selectedResource.label}已进入 ${updated.state}；批准类动作仍由服务端执行 MFA 与 maker-checker。`,
      });
    } catch (error) {
      const detail = describeM5Problem(error, "状态更新失败，请检查 MFA、maker-checker 与当前状态。");
      setNotice({ title: "状态动作被拒绝", detail, danger: true });
    } finally {
      setBusyKey(null);
    }
  }

  async function appendWithdrawal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!withdrawalRef.trim()) return;
    setBusyKey("withdrawal");
    setNotice(null);
    try {
      await requestM5Json<MarketResourceRecord>("POST", "/api/v1/consent-withdrawals", {
        idempotencyKey: newIdempotencyKey("consent-withdrawal"),
        body: { notice_ref: withdrawalRef.trim() },
      });
      setWithdrawalRef("");
      setNotice({
        title: "同意撤回事件已追加",
        detail: "事件采用追加写入；后续限制处理、删除与下游传播由 DSR 流程继续跟踪。",
      });
    } catch (error) {
      const detail = describeM5Problem(error, "追加撤回失败，请检查权限与告知记录引用。");
      setNotice({ title: "撤回事件被拒绝", detail, danger: true });
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <div className={styles.page}>
      <Card className={styles.hero}>
        <div>
          <p className={styles.eyebrow}>FR-12 · MEMBER 5</p>
          <h1>隐私与外部处理治理</h1>
          <p>
            11 类隐私资源的创建、查询和生命周期动作已接入真实 API；租户隔离、MFA、maker-checker、幂等与审计由服务端强制执行。
          </p>
        </div>
        <StatusBadge tone="success">合成元数据写入已启用</StatusBadge>
      </Card>

      <Notice title="真实数据仍然失败关闭" tone="warning">
        当前页面只接受合成或去标识元数据。M0、REAL_DATA_MODE、PIA/DSR 与事件演练未全部通过时，不得录入真实个人信息。
      </Notice>
      {notice ? (
        <Notice title={notice.title} tone={notice.danger ? "danger" : "info"}>
          {notice.detail}
        </Notice>
      ) : null}

      <Card eyebrow="WRITE" title="创建治理记录">
        <form className={styles.form} onSubmit={(event) => void createRecord(event)}>
          <label className={styles.field}>
            资源类型
            <select
              onChange={(event) => {
                setLoading(true);
                setNotice(null);
                setRecords([]);
                setResourcePath(event.target.value);
              }}
              value={resourcePath}
            >
              {RESOURCES.map((resource) => (
                <option key={resource.path} value={resource.path}>{resource.label}</option>
              ))}
            </select>
          </label>
          <label className={styles.field}>
            合成主体范围
            <input
              maxLength={400}
              onChange={(event) => setSubjectScope(event.target.value)}
              required
              value={subjectScope}
            />
          </label>
          <label className={styles.field}>
            依据引用
            <input
              maxLength={500}
              onChange={(event) => setJustificationRef(event.target.value)}
              required
              value={justificationRef}
            />
          </label>
          <label className={styles.field}>
            保留天数
            <input
              max={36500}
              min={0}
              onChange={(event) => setRetentionDays(event.target.value)}
              type="number"
              value={retentionDays}
            />
          </label>
          <div className={styles.formActions}>
            <Button
              disabled={
                busyKey !== null ||
                !subjectScope.trim() ||
                !justificationRef.trim() ||
                !/^\d+$/.test(retentionDays) ||
                Number(retentionDays) > 36500
              }
              type="submit"
            >
              {busyKey === "create" ? "正在写入…" : `创建${selectedResource.label}`}
            </Button>
          </div>
        </form>
      </Card>

      <Card eyebrow="REGISTRY" title={`${selectedResource.label}清单`}>
        {loading ? <p className={styles.hint}>正在读取真实服务状态…</p> : null}
        {!loading && records.length === 0 ? (
          <EmptyState description="当前作用域内还没有该类记录。" title="暂无记录" />
        ) : null}
        {records.length > 0 ? (
          <ul className={styles.list}>
            {records.map((record) => {
              const actions = resourceActions(resourcePath, record.state);
              return (
                <li className={styles.item} key={record.resource_id}>
                  <div>
                    <strong>{record.resource_type}</strong>
                    <small>v{record.state_version} · {record.resource_id}</small>
                  </div>
                  <div className={styles.actions}>
                    <StatusBadge tone={stateTone(record.state)}>{record.state}</StatusBadge>
                    {actions.map((action) => (
                      <Button
                        disabled={busyKey !== null}
                        key={action.action}
                        onClick={() => void runLifecycle(record, action)}
                        variant="secondary"
                      >
                        {busyKey === `${record.resource_id}:${action.action}` ? "处理中…" : action.label}
                      </Button>
                    ))}
                  </div>
                </li>
              );
            })}
          </ul>
        ) : null}
      </Card>

      <Card eyebrow="APPEND-ONLY" title="追加同意撤回">
        <form className={styles.form} onSubmit={(event) => void appendWithdrawal(event)}>
          <label className={styles.fieldWide}>
            告知/同意记录引用
            <input
              maxLength={500}
              onChange={(event) => setWithdrawalRef(event.target.value)}
              placeholder="notice://tenant/reference"
              required
              value={withdrawalRef}
            />
          </label>
          <div className={styles.formActions}>
            <Button disabled={busyKey !== null || !withdrawalRef.trim()} type="submit" variant="danger">
              {busyKey === "withdrawal" ? "正在追加…" : "追加撤回事件"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

type GateAssessment = {
  readonly status: "PASS" | "FAIL" | "UNKNOWN";
  readonly validity: "CURRENT" | "STALE";
  readonly expires_at: string;
  readonly reason_codes: ReadonlyArray<string>;
};

function gateIsPassCurrent(gate: GateAssessment): boolean {
  return gate.status === "PASS" && gate.validity === "CURRENT" && Date.parse(gate.expires_at) > Date.now();
}

export function AiProviderSettingsMount() {
  const [gate, setGate] = useState<GateAssessment | null>(null);
  const [gateLoading, setGateLoading] = useState(true);
  const [configId, setConfigId] = useState("");
  const [credential, setCredential] = useState("");
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [notice, setNotice] = useState<NoticeState | null>(null);
  const byokEnabled = gate !== null && gateIsPassCurrent(gate);

  useEffect(() => {
    const controller = new AbortController();
    requestM5Json<GateAssessment>("GET", "/api/v1/stage-gates/BYOK_SECRET_GATE", {
      signal: controller.signal,
    })
      .then(setGate)
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setNotice({
          title: "BYOK 门禁不可验证",
          detail: describeM5Problem(error, "门禁服务不可用，请检查本地身份 BFF 与 API 配置。"),
          danger: true,
        });
      })
      .finally(() => {
        if (!controller.signal.aborted) setGateLoading(false);
      });
    return () => controller.abort();
  }, []);

  async function runProviderAction(
    action:
      | "successors"
      | "credential"
      | "test-connection"
      | "activate"
      | "suspend"
      | "revoke"
      | "revoke-credential",
  ) {
    const normalizedId = configId.trim();
    if (!normalizedId) return;
    const protectedAction = ["successors", "credential", "test-connection", "activate"].includes(action);
    if (protectedAction && !byokEnabled) return;
    setBusyAction(action);
    setNotice(null);
    try {
      const encodedId = encodeURIComponent(normalizedId);
      const method = action === "credential" ? "PUT" : action === "revoke-credential" ? "DELETE" : "POST";
      const suffix = action === "revoke-credential" ? "credential" : action;
      const body =
        action === "credential"
          ? { api_key: credential }
          : action === "successors"
            ? { rotation_mode: "PLANNED", reason_code: "USER_REQUESTED_ROTATION" }
            : ["activate", "suspend", "revoke"].includes(action)
              ? { reason_code: `USER_REQUESTED_${action.toUpperCase()}` }
              : undefined;
      await requestM5Json<unknown>(method, `/api/v1/ai-provider-configurations/${encodedId}/${suffix}`, {
        idempotencyKey: newIdempotencyKey(`provider-${action}`),
        body,
      });
      setNotice({ title: "Provider 动作已受理", detail: `${action} 已由服务端按当前门禁执行。` });
    } catch (error) {
      const detail = describeM5Problem(error, "Provider 动作失败，请根据门禁与配置状态处理。");
      setNotice({ title: "Provider 动作被拒绝", detail, danger: true });
    } finally {
      if (action === "credential") setCredential("");
      setBusyAction(null);
    }
  }

  const hasConfig = configId.trim().length > 0;

  return (
    <div className={styles.page}>
      <Card className={styles.hero}>
        <div>
          <p className={styles.eyebrow}>BYOK · MEMBER 5</p>
          <h1>AI 服务商配置</h1>
          <p>
            Key 只写不回显。页面只消费平台公开门禁状态；无法证明 BYOK_SECRET_GATE 为 PASS/CURRENT 时，写 Key、连接测试、后继轮换和激活均保持失败关闭。
          </p>
        </div>
        <StatusBadge tone={byokEnabled ? "success" : "critical"}>
          {gateLoading ? "正在核验门禁" : byokEnabled ? "BYOK PASS/CURRENT" : "BYOK BLOCKED"}
        </StatusBadge>
      </Card>

      {!byokEnabled && !gateLoading ? (
        <Notice title="真实凭据能力未放行" tone="warning">
          {gate?.reason_codes.length
            ? `原因：${gate.reason_codes.join("、")}`
            : "未取得可验证且未过期的 PASS/CURRENT 证据。紧急撤销仍可调用，其他敏感动作已禁用。"}
        </Notice>
      ) : null}
      {notice ? (
        <Notice title={notice.title} tone={notice.danger ? "danger" : "info"}>
          {notice.detail}
        </Notice>
      ) : null}

      <Card eyebrow="WRITE-ONLY" title="凭据与生命周期动作">
        <div className={styles.form}>
          <label className={styles.fieldWide}>
            配置 ID
            <input
              onChange={(event) => setConfigId(event.target.value)}
              placeholder="AIProviderConfigurationVersion UUID"
              value={configId}
            />
          </label>
          <label className={styles.fieldWide}>
            新 API Key（只写）
            <input
              aria-describedby="credential-hint"
              autoComplete="new-password"
              className={styles.secretInput}
              disabled={!byokEnabled}
              onChange={(event) => setCredential(event.target.value)}
              spellCheck={false}
              type="password"
              value={credential}
            />
          </label>
          <p className={`${styles.hint} ${styles.fieldWide}`} id="credential-hint">
            页面不保存、记录或回显 Key；提交完成后立即清空输入。服务端必须在解析 secret body 前再次校验门禁。
          </p>
          <div className={styles.formActions}>
            <Button
              disabled={!byokEnabled || !hasConfig || busyAction !== null}
              onClick={() => void runProviderAction("successors")}
              variant="secondary"
            >
              创建轮换后继版本
            </Button>
            <Button
              disabled={!byokEnabled || !hasConfig || !credential || busyAction !== null}
              onClick={() => void runProviderAction("credential")}
            >
              写入新 Key
            </Button>
            <Button
              disabled={!byokEnabled || !hasConfig || busyAction !== null}
              onClick={() => void runProviderAction("test-connection")}
              variant="secondary"
            >
              固定载荷连接测试
            </Button>
            <Button
              disabled={!byokEnabled || !hasConfig || busyAction !== null}
              onClick={() => void runProviderAction("activate")}
            >
              激活配置
            </Button>
            <Button
              disabled={!hasConfig || busyAction !== null}
              onClick={() => void runProviderAction("suspend")}
              variant="secondary"
            >
              暂停配置
            </Button>
            <Button
              disabled={!hasConfig || busyAction !== null}
              onClick={() => void runProviderAction("revoke")}
              variant="danger"
            >
              撤销配置
            </Button>
            <Button
              disabled={!hasConfig || busyAction !== null}
              onClick={() => void runProviderAction("revoke-credential")}
              variant="danger"
            >
              紧急撤销 Key
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
