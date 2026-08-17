# M0 成员 3 交接说明：文档摄入（FR-02）

状态：`IMPLEMENTED / HUMAN_GATES_PENDING`

本次交付覆盖 FR-02 P0 的 25 个 operation：上传会话、分块校验、隔离扫描、
审核/放行、下载、解析 Job、派生资产、副本登记、以及项目→单元 document-links。
前端 `features/documents` 消费真实 API，进度只来自持久化 ParseJob。

## 交付范围

- `biaice.modules.documents`：冻结 Pydantic 模型、In-memory 仓储/对象存储、
  解析器（stdlib PDF/DOCX/XLSX/zip）、ClamAV TCP INSTREAM（不可达时回落 EICAR 门）。
- `biaice.api.documents`：25 个真实 handler，注册于 contract_stubs 之前。
- 权限：`fr-02:read/create/put/complete/cancel/review/release/quarantine/inherit/override/resolve/detach/retry`。
- 事件：上传、放行、隔离、parse_completed/failed、derived_asset_registered。
- 删除：`LocalReplicaDeletionAdapter`（`member3-local` / `MEMBER_3_LOCAL_REPLICA`），
  保全时返回 `DELETION_BLOCKED_BY_LEGAL_HOLD` receipt，从不完成 DeletionJob。
- 只读端口：`DocumentReadService`（`app.state.document_read_port`）供成员 2/4/5
  读取已放行文档的 content hash、parse 状态与 fragment_ref。
- Worker：`biaice.ingest.parse_document` / `biaice.ingest.scan_document` 已加入
  `worker.py` imports；M0 解析在 API 进程内执行并持久化 Job 进度。
- 迁移：`m3_documents_0001`（独立 Alembic head，含 parse/derived/replica/link 表）。
- 前端：`apps/web/src/features/documents`，覆盖 loading/empty/ready/unauthorized/expired/error。

## 架构约束

1. **禁止直连 MinIO**：浏览器只走 gateway → API；对象 key 由服务端生成。
2. **哈希门**：complete 校验分块集合、总大小和声明的 SHA-256。
3. **内容嗅探**：不信任扩展名/浏览器 MIME。
4. **下载**：`SCAN_FAILED` / `QUARANTINED` 禁止正文。
5. **解析**：仅干净扫描后的文档；图片无锁定 OCR 时返回 `NO_MANUAL_ENTRY_REQUIRED`。
6. **Links**：继承不复制文件；覆盖必须有原因；冲突禁止 last-write-wins。
7. **去重**：同一租户/域 content_hash 复用已有 SourceDocument。

## 已知限制

- In-memory 仓储用于 M0；SQLAlchemy/MinIO 由成员 1 锁文件后接入。
- ClamAV 在本地测试环境通常不可达，回落 EICAR 内联门。
- `worker.py` / `core/auth.py` / `core/errors.py` / `main.py` / `contract_stubs.py`
  有平台接线，请组长在合并时确认。

## 验证命令

```powershell
uv run --project apps/backend --extra test pytest apps/backend/tests/unit/test_document_intake.py apps/backend/tests/unit/test_replica_deletion_adapter.py apps/backend/tests/contract/test_documents_api.py -v
uv run --project apps/backend --extra test ruff check apps/backend/src/biaice/modules/documents apps/backend/src/biaice/api/documents.py apps/backend/src/biaice/workers/ingest
python packages/contracts/scripts/generate_contracts.py --check
```

## 回滚方法

1. `git revert <commit>` 回滚本 PR；不重写共享历史。
2. 数据库只追加 `m3_documents_0001`；多 head 由成员 1 合并。
3. 临时关闭真实路由：移除 `main.py` 中 `app.include_router(documents.router)`
   并恢复 contract_stubs 跳过集合。
