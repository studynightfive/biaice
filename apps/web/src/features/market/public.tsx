"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Button, Card, EmptyState, Notice, StatusBadge } from "@/components/ui";
import { describeM5Problem, newIdempotencyKey, requestM5Json } from "@/features/m5-api";
import styles from "@/features/m5-workbench.module.css";

type Competitor = {
  readonly competitor_id: string;
  readonly legal_name: string;
  readonly canonical_subject_key: string;
  readonly aliases: ReadonlyArray<string>;
  readonly archived_at: string | null;
};

type CompetitorList = { readonly items: ReadonlyArray<Competitor> };
type NoticeState = { readonly title: string; readonly detail: string; readonly danger?: boolean };

function canonicalSubjectKey(value: string): string {
  return value.trim().toLocaleLowerCase().replace(/\s+/g, "");
}

function aliasesFromInput(value: string): ReadonlyArray<string> {
  return [...new Set(value.split(/[,，]/).map((item) => item.trim()).filter(Boolean))];
}

export function MarketMount() {
  const [competitors, setCompetitors] = useState<ReadonlyArray<Competitor>>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [legalName, setLegalName] = useState("");
  const [aliases, setAliases] = useState("");
  const [notice, setNotice] = useState<NoticeState | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    requestM5Json<CompetitorList>("GET", "/api/v1/competitors", {
      signal: controller.signal,
    })
      .then((result) => setCompetitors(result.items))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setNotice({
          title: "竞对清单读取失败",
          detail: describeM5Problem(error, "市场服务暂时不可用，请检查本地身份 BFF 与 API 配置。"),
          danger: true,
        });
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  async function createCompetitor(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const subjectKey = canonicalSubjectKey(legalName);
    if (subjectKey.length < 3) return;
    setBusy(true);
    setNotice(null);
    try {
      const created = await requestM5Json<Competitor>("POST", "/api/v1/competitors", {
        idempotencyKey: newIdempotencyKey("competitor"),
        body: {
          legal_name: legalName.trim(),
          canonical_subject_key: subjectKey,
          aliases: aliasesFromInput(aliases),
        },
      });
      setCompetitors((current) => [created, ...current]);
      setLegalName("");
      setAliases("");
      setNotice({
        title: "竞对草稿已创建",
        detail: "记录已通过 FR-05 真实写入接口保存；来源审核、画像与发布仍按各自门禁推进。",
      });
    } catch (error) {
      const detail = describeM5Problem(error, "创建竞对失败，请根据错误码检查权限与字段。");
      setNotice({ title: "写入被拒绝", detail, danger: true });
    } finally {
      setBusy(false);
    }
  }

  const subjectKey = canonicalSubjectKey(legalName);

  return (
    <div className={styles.page}>
      <Card className={styles.hero}>
        <div>
          <p className={styles.eyebrow}>FR-05 · MEMBER 5</p>
          <h1>竞对与市场治理</h1>
          <p>
            竞对写入已接入真实 API。来源必须完成合法基础、保留期和隐私审核，未经批准的市场先验只能用于压力探索。
          </p>
        </div>
        <StatusBadge tone="success">写入已启用</StatusBadge>
      </Card>

      {notice ? (
        <Notice title={notice.title} tone={notice.danger ? "danger" : "info"}>
          {notice.detail}
        </Notice>
      ) : null}

      <Card eyebrow="WRITE" title="新建竞对草稿">
        <form className={styles.form} onSubmit={(event) => void createCompetitor(event)}>
          <label className={styles.field}>
            法定名称
            <input
              autoComplete="organization"
              maxLength={300}
              onChange={(event) => setLegalName(event.target.value)}
              placeholder="输入至少三个非空白字符"
              required
              value={legalName}
            />
          </label>
          <label className={styles.field}>
            别名
            <input
              maxLength={1200}
              onChange={(event) => setAliases(event.target.value)}
              placeholder="多个别名用逗号分隔"
              value={aliases}
            />
          </label>
          <div className={styles.formActions}>
            <Button disabled={busy || subjectKey.length < 3} type="submit">
              {busy ? "正在写入…" : "创建竞对"}
            </Button>
            <span className={styles.hint}>租户和数据域由服务端会话注入，前端不能覆盖。</span>
          </div>
        </form>
      </Card>

      <Card eyebrow="REGISTRY" title="当前竞对">
        {loading ? <p className={styles.hint}>正在读取真实竞对清单…</p> : null}
        {!loading && competitors.length === 0 ? (
          <EmptyState description="使用上方表单创建第一条竞对草稿。" title="暂无竞对" />
        ) : null}
        {competitors.length > 0 ? (
          <ul className={styles.list}>
            {competitors.map((competitor) => (
              <li className={styles.item} key={competitor.competitor_id}>
                <div>
                  <strong>{competitor.legal_name}</strong>
                  <small>{competitor.canonical_subject_key} · {competitor.competitor_id}</small>
                </div>
                <StatusBadge tone={competitor.archived_at ? "neutral" : "info"}>
                  {competitor.archived_at ? "ARCHIVED" : "DRAFT"}
                </StatusBadge>
              </li>
            ))}
          </ul>
        ) : null}
      </Card>
    </div>
  );
}
