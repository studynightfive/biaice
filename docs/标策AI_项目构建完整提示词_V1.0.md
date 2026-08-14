# 标策 AI 项目构建完整提示词

> 用于七人研发小组从现有 PRD 与前端 Demo 构建“应用与数据本地自托管、局域网可访问、商家自配模型 API Key”的标策 AI 项目

| 文档项 | 内容 |
| --- | --- |
| 文档版本 | V1.0（终审修订版） |
| 生成日期 | 2026-08-13 |
| 最终复核日期 | 2026-08-14 |
| 需求基线 | `标策AI_产品需求文档_PRD_V1.3.md` |
| 交互参考 | `标策AI_前端设计文档_V1.0.md` 与当前前端 Demo |
| 开发团队 | 7 人，成员 1 为组长与集成负责人 |
| 部署方式 | 应用、数据库、文件与治理服务完全本地自托管；Docker Compose 单机编排；局域网共享访问；不使用 Sites、Cloudflare 或云托管应用；生成式 AI 仅通过商家自配 API Key 调用受控外部 API |
| 数据约束 | 安全 Gate 完成前只允许合成或脱敏测试数据 |
| 使用方式 | 先把“总提示词”交给全体成员统一上下文，再分别把对应的“成员提示词”交给每名成员或其编码智能体 |

---

## 1. 使用说明与权威顺序

### 1.1 权威顺序

开发时出现冲突，严格按以下顺序裁决：

1. 组长最新书面决定与用户最新要求；
2. `docs/标策AI_产品需求文档_PRD_V1.3.md`；
3. 本提示词中已明确锁定的架构、接口、分工和歧义处理规则；
4. 当前前端 Demo 的视觉、布局和交互意图；
5. `docs/标策AI_前端设计文档_V1.0.md`；
6. PRD V1.2、V1.1、V1.0 仅作历史参考，不得覆盖 V1.3。

当前 Demo 只作为 UI、文案风格和操作流程参考，不作为正式业务逻辑、算法、数据结构、接口或部署架构的权威来源。

### 1.2 已锁定的本地化含义

- 应用、数据库、对象存储、缓存、队列、OCR、身份系统、日志和监控都运行在组内电脑或局域网设备上；不部署 Ollama、vLLM 等本地生成式/大语言模型服务。ClamAV、本地 OCR 引擎和确定性裁判仍属于本地基础能力。
- 运行期间不得依赖 Sites、Cloudflare Worker Runtime、D1、R2、Wrangler、ChatGPT 身份头、外部 CDN、远程字体或第三方遥测；本地 Celery 异步 Worker 必须保留。唯一允许的业务出网是经服务端受控网关调用商家已配置并通过治理 Gate 的模型 API。
- 默认允许在首次安装阶段下载经批准的开源依赖和容器镜像；交付时必须锁定版本、镜像摘要和依赖清单，并能够制作离线安装包。若组长要求“安装阶段也完全断网”，应把离线镜像仓库和依赖缓存升级为 M0 阻断项。
- 开发模式可在受信局域网使用 HTTP，但只能处理合成或脱敏数据，并且必须硬禁真实 API Key 写入、连接测试和 Provider 出网；仅允许空配置或明确无价值且永不出网的假 Key fixture。任何真实 API Key 输入前必须通过第 20.2 节 `BYOK_SECRET_GATE`；任何真实投标资料或个人信息进入前，必须通过第 20.1 节完整 `REAL_DATA_MODE` 启动 Gate。TLS、MFA、全存储面隔离、存储加密、密钥隔离、加密备份/恢复、审计、文件扫描、PIA/DSR、保留删除、事件演练和漏洞门槛缺一不可。
- “本地化部署”只描述应用、身份、业务数据和基础设施的承载位置，不等于模型推理离线。浏览器不得直连模型服务；只有 `provider-egress-gateway` 可按租户激活配置访问批准的 HTTPS 域名。未配置 API Key、密钥失效或 ProviderPolicy/PIA/跨境 Gate 未通过时，模型能力显示不可用并回退人工录入，确定性规则流程不得伪造模型结果。
- 系统只登记外部采购平台上的人工提交结果，不自动连接或操作采购平台。

### 1.3 开始开发前必须完成的动作

全体成员先共同确认并冻结以下产物，未完成不得并行写正式业务代码：

- 需求追踪矩阵；
- 统一术语、枚举和状态映射表；
- API operation 目录、Pydantic stub router、由其导出的 OpenAPI 快照与错误码目录；
- 领域对象和数据库范围图；
- 角色权限与 maker-checker 矩阵；
- 事件、血缘和失效传播矩阵；
- Stage Gate 与功能开关矩阵；
- 七人目录所有权与依赖顺序。

---

# 第一部分：全体成员统一总提示词

## 2. 可直接使用的总提示词

你是“标策 AI”项目的高级产品工程师、领域架构师和质量负责人。你需要在现有仓库基础上，按照 PRD V1.3 构建一个应用与数据本地自托管、供七人小组在局域网内共同访问和测试的 Web 决策辅助系统；生成式模型不在本地部署，只能由商家/租户管理员自行配置 API Key 后通过服务端受控调用。

你的工作目标不是复刻当前 Demo 的假数据逻辑，而是保留其视觉语言和主要交互意图，建立可追溯、可复现、可审核、可测试的真实工程基础。所有正式功能必须由真实后端状态支持；任何尚未实现的能力都必须显示“演示、探索、待审核或不可用”，不得通过动画、固定模板或前端内存状态伪装成已经完成。

### 2.1 项目目标

系统围绕一个 `DecisionUnit` 完成以下闭环：

创建项目与决策单元 → 安全文档摄入 → 制度与流程范围确认 → 规则抽取和人工发布 → 本公司证据匹配与固定响应画像 → 资格/响应预审 → 成本、商业政策与策略就绪 → 竞对/市场先验与未知进入者 → 冻结基线、搜索场景和独立评估场景 → 静态候选校验 → 潜在状态采样与确定性裁判 → 多目标报价搜索 → 独立评估、压力测试和方案合并 → 推荐资格 → 影子审批包与审批 → 提交授权记录 → 外部提交登记和双人核验 → 结果回填、报告、回测和模型治理。

系统只能给出企业内部决策参考，不替代采购人、评标委员会、财务、法务或管理层，不保证中标，不与真实竞对交互，不交换或协调报价。

### 2.2 正式范围

- 一个项目可包含 1–N 个决策单元，但一次正式计算和审批只处理一个决策单元。
- 首期只支持一次性、单轮、密封报价类采购流程。
- 策略搜索只优化合同报价 `b`；技术、服务、人员和资源由已发布的固定响应画像提供。
- 支持 0–N 个实名竞对，并始终保留经主体去重的未知进入者场景。
- 跨标段约束、组合报价、兼投不兼中、共享产能冲突只识别和阻断，状态为 `PORTFOLIO_REVIEW_REQUIRED`。
- 谈判、磋商等多轮报价只识别和阻断，状态为 `MULTI_ROUND_UNSUPPORTED`。
- 首期不做跨标段联合优化，不做多轮策略，不自动制作或提交真实投标文件。

### 2.3 绝对禁止的产品表达与实现

- 不得使用“保证中标、稳妥中标、必然中标”等表达。
- 未建立并验证审查结果概率模型时，不得显示单点“中标概率、胜率、胜出概率”。只能显示部分识别区间及其蒙特卡洛误差，或在 Demo 中明确写“演示性胜出权重”。
- 未建立获授模型时，不得把第一候选频率称为最终获授或签约概率。
- 未批准成本不得输出正式利润结论。
- 资格条件不得自动转成评分项。
- 商业审批拒绝不得描述成采购规则意义上的报价无效。
- 生成式模型只能提出制度、条款、证据和解释候选，不得直接执行确定性资格结论、精确评分、舍入、并列或排名。
- 不得使用未公开底价、拟报价、评委信息、非法取得的商业秘密或未经授权的个人信息。
- 不得把压力测试的主观权重混入概率分母。
- 不得因候选计算失败删除对该候选不利的场景。
- 不得在最终可行集合为空时继续执行最优值函数或伪造方案卡片。

### 2.4 对当前 Demo 的处理

保留：

- 暖灰纸张背景、深绿色主色、纸质卡片、蓝/黄/红状态语义；
- Header、Hero、流程导航、工作区、上传区、规则卡、证据矩阵、竞对卡、方案卡、图表和报告版式；
- 三个项目模板作为合成种子和端到端测试 fixture；
- 本地系统字体与 `public/bid-strategy-social.png`，修正其本地引用和尺寸；
- 桌面、平板、手机的响应式思路。

必须替换或修正：

- 移除 vinext、Sites、Cloudflare Vite Plugin、Wrangler、Cloudflare Worker Runtime、D1、R2、ChatGPT 身份头和公网 Sites URL 的运行依赖；保留本地 Celery Worker；
- 当前 `evaluateScenario`、固定 B/C/D、正弦扰动、Softmax 份额和固定价差区间只能保留为明确标记的 Demo fixture，不能成为正式裁判或概率引擎；
- 初始资格、符合性和低价说明状态不得默认为通过；未完成门禁时禁止显示 GO 或正式方案；
- 任意上传文件不得触发固定匹配或提升竞对置信度；文件内容、来源和审核结果必须真正参与处理；
- 每一条强制规则都必须映射到 Requirement 和 EvidenceMatch；未映射强制项失败关闭；
- 流程步骤、Tab 可用性和徽标必须来自真实生命周期与 Gate，不得固定显示 active；
- 报告必须是不可变快照，包含输入清单、哈希、版本、种子、模型、生成时间和适用性；
- 修复 Tab、进度条、模态框、图表文本替代、小字号和触控目标等可访问性问题。

---

## 3. 统一技术框架

### 3.1 架构形态

采用“模块化单体 + 独立异步 Worker”的单仓库结构，不拆成七个微服务。API 与 Worker 使用同一后端代码和同一容器镜像，通过不同启动命令运行。模块之间通过公开 application port、OpenAPI 契约或 outbox 事件协作，禁止跨模块直接写表。

### 3.2 技术栈

| 层 | 统一选择 | 使用边界 |
| --- | --- | --- |
| Web | 标准 Next.js 16 系列 Node Runtime、React 19、TypeScript 5.9 | 自托管 Node 服务；不得使用 Cloudflare Worker Runtime 或 Sites adapter |
| 样式 | Tailwind CSS 4 + CSS Modules/局部样式；保留现有设计令牌 | 禁止新增远程字体和 CDN 资源 |
| API | Python 3.12、FastAPI、Pydantic v2 | Pydantic stub/handler 是接口源，由其导出只读 OpenAPI 快照 |
| ORM/迁移 | SQLAlchemy 2、Alembic | 所有表变更必须有只前进迁移和审阅记录 |
| 主数据库 | PostgreSQL 16 | 事务、复合租户约束、RLS、JSONB；可选 pgvector |
| 异步任务 | Celery；独立 Redis Broker 与 Redis Cache | Broker 启用持久化、`noeviction`；Cache 使用独立实例和命名空间；业务真状态写 PostgreSQL |
| 对象存储 | 自托管 MinIO | 隔离区、正式原文、派生资产、报告、审计锚点分区；正式载荷应用层信封加密 |
| 身份 | 本地 Keycloak，OIDC Authorization Code + PKCE | 七个测试账户；服务端强制 membership、RBAC、scope 与 MFA |
| 网关 | Caddy（本地 CA） | 局域网唯一入口；反向代理、限流、分块上传和内网 TLS；禁止公网 ACME |
| 文件安全 | ClamAV、MIME 嗅探、受限解析容器、LibreOffice headless、Poppler、PaddleOCR | 上传先隔离，扫描通过后才能进入解析；ClamAV 签名与 OCR 权重/资源离线导入 |
| 密钥与备份 | 自托管 OpenBao + 主机磁盘加密 + restic 加密备份 | 真实 BYOK 或真实数据均禁用 OpenBao dev mode；KEK 与业务数据分离；每个敏感载荷使用独立 DEK；最小权限短期凭据、毁钥与恢复演练 |
| 外部模型接入 | 服务端 Provider Adapter + 商家自配 API Key | 不部署本地 LLM；只支持平台 allowlist 内的 HTTPS Provider/模型；无有效配置时人工录入和规则模板仍可用 |
| 受控出网 | 独立 `provider-egress-gateway` | 先通过第 20.2 节密钥安全 Gate；正式调用只允许 ACTIVE 配置，激活前仅允许第 20.4 节固定合成连接测试；浏览器、Web、API 和普通 Worker 均不得直接出网 |
| 可观测性 | OpenTelemetry、Prometheus、Grafana、Loki | 全部本地；日志不得含正文、个人信息、成本或原始提示词响应 |
| 前端测试 | Vitest、Testing Library、Playwright、axe | 组件、契约、真实 Compose E2E 与可访问性 |
| 后端测试 | Pytest、Hypothesis、Schemathesis | 单元、性质、接口、权限、安全、并发和恢复 |
| 性能测试 | k6 | 绑定冻结的 `LoadProfileVersion` |

表中的大版本只是架构族。M0 必须用 ADR 选择彼此兼容的精确 patch、锁文件和镜像 digest，之后所有成员只使用该冻结版本。替换 Caddy、PaddleOCR、k6 或其他基础组件必须另走 ADR，未经组长批准不得自行更换。

### 3.3 本地部署拓扑

| 服务 | 宿主暴露 | 说明 |
| --- | --- | --- |
| gateway | 合成数据模式 `0.0.0.0:8080`；真实数据模式 `0.0.0.0:8443` | 唯一局域网入口；统一 LAN 地址 `https://biaice.local:8443`，不硬编码成员电脑 IP |
| web | 不直接暴露 | Next.js Node |
| api | 不直接暴露 | FastAPI |
| worker-ingest | 不暴露 | 扫描、OCR、解析、画像预处理 |
| worker-simulation | 不暴露 | 场景、裁判、优化、独立评估 |
| worker-governance | 不暴露 | 失效、保留、删除、报告、回测任务 |
| worker-provider | 不暴露 | 成员 5 独占；消费受治理模型任务、执行逐次 Gate、调用内部 provider-egress、记录 attempt/结果 |
| scheduler | 不暴露 | outbox、到期和协调任务 |
| postgres | 默认不暴露；调试仅绑定 `127.0.0.1` | 业务真值 |
| redis-broker | 不暴露 | Celery broker；AOF、`noeviction`，不得存业务唯一真值 |
| redis-cache | 不暴露 | 缓存、限流、短进度通知；可淘汰，与 broker 隔离 |
| minio | API 不直接暴露；管理台仅组长本机 | 对象与副本 |
| keycloak | 仅经 gateway | 本地账户、角色和 MFA |
| openbao | 不暴露 | KEK、轮换、撤销和密钥审计；真实数据模式必需 |
| clamav | 不暴露 | 文件扫描 |
| provider-egress-gateway | 不对 LAN 暴露；仅连接受控出网网络 | 使用租户配置引用调用外部模型；域名 allowlist、TLS 校验、SSRF 防护、限流与审计 |
| observability | 仅组长本机或受控管理网 | 本地指标、日志和追踪 |

Compose 划分 `front`、`back`、`provider-egress` 和默认禁用的 `maintenance-egress` 网络；只有 gateway 发布宿主端口。数据库、Redis、MinIO、ClamAV、OpenBao 不得映射到局域网；Web、API、普通 Worker 只能访问内部网络。通过第 20.2 节后，`provider-egress-gateway` 才能成为唯一业务出网主体：正式调用只允许 ACTIVE 配置访问已批准 Provider HTTPS 域名/端口；激活前唯一例外是满足第 20.4 节的 `CONNECTION_TEST` 固定合成探针。两种路径都阻断 IP literal、私网/回环/元数据地址、DNS rebinding 和未批准重定向。维护 profile 只用于短时导入镜像、ClamAV 签名或 OCR 资产，导入后关闭。

### 3.4 局域网域名、TLS 与 OIDC

- 组长在局域网 DNS 或七台测试设备 hosts 中统一解析 `biaice.local`；不得给每名成员生成不同 issuer，也不得把某台电脑的临时 IP 写入业务配置。
- Caddy 仅使用本地 CA，为 `biaice.local` 签发含正确 SAN 的证书；组长负责把根证书安全分发并安装到七台设备的受信根，维护签发、续期、吊销和设备移除清单。
- Keycloak 固定 issuer 为 `https://biaice.local:8443/realms/biaice`，回调为同源受控路径；校验 issuer/audience/nonce/state/PKCE。真实数据模式使用 Secure、HttpOnly、SameSite 会话 Cookie。
- 两台以上不同 LAN 设备必须完成“解析域名 → 信任证书 → 登录/MFA → 回调 → 刷新/注销”验收；证书过期、错误 SAN、错误 issuer 或未受信根均失败关闭。

### 3.5 Compose 可运行规范

- 所有长驻服务定义无敏感信息的 healthcheck、合理 restart policy、CPU/内存限制和日志轮转；依赖启动使用 `service_healthy`，不能只靠固定 sleep。
- `migrate`、`seed-synthetic`、`keycloak-init`、`backup`、`restore-verify` 是幂等的一次性 job；迁移成功后 API 才 ready，种子默认只含合成数据和七个首次登录强制改密账户。
- PostgreSQL、两个 Redis、MinIO、Keycloak、OpenBao、审计锚点、Caddy `/data`（本地 CA 私钥/证书状态）和备份目录分别使用命名卷；文档列清“可丢缓存”和“不可丢真值”。Caddy CA 卷属于高敏不可丢恢复材料，使用主机 ACL 与加密备份保护，不能随容器重建换根。
- OpenBao 在纯合成开发模式可使用一次性 dev 配置，但该 profile 必须在网络、API 和 UI 三层禁用真实 credential 写入、连接测试与 provider-egress，只允许不保存、不出网的假 Key fixture。`BYOK_SECRET_GATE` 与 `REAL_DATA_MODE` 均严禁 dev mode、固定/明文 root token、自动打印 unseal key 或把 token/share 放入 Compose、`.env`、Git、镜像、日志和普通备份清单。安全模式执行一次性初始化仪式：Shamir unseal/recovery 份额至少 2-of-3 分持、初始 root token 在建立最小权限 policy/AppRole 和审计后立即撤销或离线双控封存；seal/unseal、份额遗失、紧急恢复和重新换份必须有双人审计运行手册。
- API 配置模块使用短期 AppRole/token，只能 create/update/destroy 当前 tenant/provider/purpose 路径，明确 deny secret read/list；`provider-egress-gateway` 使用另一独立短期身份，只能在收到成员 5 已签名、短 TTL、单次使用且绑定 invocation/config/credential version 的授权后读取精确 secret path/version，并在内存中注入请求，绝不向调用方返回 Key。其他服务、平台管理员和交互式用户均无读取策略；OpenBao audit device 必须启用并纳入独立审计完整性检查。
- 默认 HTTP/dev profile 含核心本地服务，但 credential endpoints、连接测试和 `provider-egress-gateway` 出网均硬禁；只有第 20.2 节 PASS 的安全 profile 才开启真实 Key 能力。没有 ACTIVE 商家配置时不得发送任何业务资料或生成式任务，只有第 20.4 节固定合成连接测试例外。`observability`、`maintenance-egress` 分别显式启用。无 API Key 或 Provider 故障时，人工录入和确定性规则流程仍可用。
- 备份顺序固定为：暂停新冻结命令 → 记录可信时间/版本 → PostgreSQL 一致性备份 → MinIO/审计锚点目录 → OpenBao 与 Caddy `/data` CA 恢复材料 → Keycloak → 加密校验清单；恢复顺序先 OpenBao 密钥与 Caddy 原 CA、再 Keycloak 身份/issuer、数据库/对象、重放 tombstone/outbox，验证七台设备仍信任原根后才开放流量。若 CA 私钥确认丢失，必须走新根安全分发与旧根吊销事件，不得静默生成新根。
- 运行手册覆盖主机可信时间同步、证书轮换、KEK/DEK 轮换、密钥丢失处置、加密备份异机/离线保管和恢复后不可复活删除数据。

### 3.6 可靠性约束

- API 在同一数据库事务中写业务对象和 `outbox_event`，dispatcher 再投递任务。
- Celery 采用至少一次投递；所有任务以 `job_id + input_hash` 幂等，重试不得重复生成正式版本。
- Job 真状态写 PostgreSQL；Redis 消息丢失后由 reconciliation job 重发。
- OCR、仿真、治理、Provider 调用使用四个独立队列和独立并发/预算限制；`worker-provider` 重启后从 PostgreSQL Job/Outbox 恢复，Redis 不保存唯一调用事实。
- 仿真只能读取冻结 typed input manifest，运行期间不得回读可变业务表。
- 所有正式金额使用定点 decimal 字符串和 ISO 货币代码，禁止二进制浮点承担财务和正式评分计算。
- 所有业务时间使用服务器可信 UTC，另保存采购文件指定的 IANA 时区；截止时间边界必须统一。
- PostgreSQL 保存场景索引、正式聚合指标、可查询摘要和哈希；海量逐场景明细使用版本化压缩 Parquet 保存到 MinIO 并登记 `DerivedDataAssetVersion`，不能让 10,000×200 结果无限膨胀主表。
- 报告、审批包、导出和敏感快照使用独立 DEK 信封加密；删除时销毁相应 DEK 并保留最小墓碑。密钥、密文和备份不得位于同一信任域。

---

## 4. 推荐仓库结构与文件所有权

正式工程按以下结构迁移：

```text
/
├─ apps/
│  ├─ web/
│  │  ├─ src/app/
│  │  ├─ src/features/{projects,rules,documents,evidence,commercial,market,simulation,approvals,reports,access-audit,privacy-models}/
│  │  ├─ src/components/ui/
│  │  ├─ src/lib/api/{generated,client}/
│  │  ├─ src/lib/{auth,telemetry}/
│  │  └─ tests/
│  └─ backend/
│     ├─ src/biaice/main.py
│     ├─ src/biaice/core/{config,auth,db,errors,jobs,outbox,audit,storage,telemetry}/
│     ├─ src/biaice/modules/{projects,rules,documents,evidence,commercial,market,model_governance,simulation,approvals,reports,governance}/
│     ├─ src/biaice/workers/{ingest,simulation,governance,provider}/
│     ├─ migrations/versions/
│     └─ tests/{unit,integration,contract,security,performance}/
├─ packages/
│  ├─ contracts/{openapi.generated.json,events,error-catalog.yaml,generated-typescript}/
│  └─ test-fixtures/{synthetic-documents,golden-rules,scenarios}/
├─ infra/{compose,gateway,provider-egress,keycloak,openbao,postgres,minio,clamav,observability}/
├─ docs/{adr,api,traceability,runbooks,security,stage-gates}/
├─ scripts/{dev.ps1,test.ps1,backup.ps1,restore.ps1}/
├─ compose.yaml
├─ compose.override.yaml
├─ CODEOWNERS
└─ .env.example
```

每个后端业务模块内部统一分为：`api`、`application`、`domain`、`infrastructure`、`schemas`、`tests` 和 `traceability.yaml`。前端 feature 只能导入公共 UI、生成 API 类型和对方公开入口，不能导入其他 feature 的内部文件。

### 4.1 前端路由、壳层与 Demo 迁移

进入具体单元后的业务路由都带稳定上下文 `/projects/{project_id}/units/{unit_id}`；刷新、深链、前进/后退必须从 URL 与后端恢复状态。成员 1 独占 `apps/web/src/app/**`、应用 Shell、顶栏/阶段导航/面包屑、`styles/tokens.css`、`public/**` 和跨域 E2E；成员 2–7 只在各自 feature 内实现页面块并从 `public.ts` 导出。成员 1 只建立空挂载和公共原子组件，不进入 feature 编写业务。

无项目/单元上下文的入口固定为：`/login`（只发起 Keycloak OIDC，不承载密码表单）、`/account`（成员 1）、`/settings/ai-providers`（成员 5，仅商家/租户 AI 管理员与隐私审批角色）、`/projects` 与 `/projects/new`（成员 2）、`/projects/{project_id}` 与 `/projects/{project_id}/units`、`/projects/{project_id}/units/new`（成员 2）。选择或创建单元后才进入双 ID 前缀；非法/无权 ID 返回不泄露存在性的 404/403 页面，登录后只回跳经校验的本地路径。

| 正式路由后缀 | 页面/原 Demo 区域 | feature 单一 owner | Gate 行为 |
| --- | --- | --- | --- |
| `/overview` | Hero、项目概况、阶段、缺口、下一步 | 成员 2 projects | 未选单元时只读引导 |
| `/documents` | 原“资料上传与画像”中的通用摄入 | 成员 3 documents | 无权限只读；隔离中禁止下游使用 |
| `/scope-rules` | 原“规则与门槛” | 成员 2 rules | 未发布时显示草稿/阻断原因 |
| `/evidence-precheck` | 原证据匹配与 evidence Tab | 成员 4 evidence | 未映射强制项失败关闭 |
| `/commercial-readiness` | 成本、政策、条件、就绪 | 成员 4 commercial | 未批准成本只显示探索态 |
| `/market` | 原竞争者上传/画像 | 成员 5 market | 复用成员 3 的 `DocumentIntake` 公共 port；禁止复制上传状态机 |
| `/baseline-scenarios` | 决策基线、搜索/评估/压力场景 | 成员 6 simulation | Readiness 未过仅只读原因 |
| `/simulation` | 原 cockpit、规则裁判、前沿、方案 | 成员 6 simulation | 无正式先验只显示压力探索 |
| `/eligibility` | 推荐资格 | 成员 6 simulation | 与审批分离 |
| `/approvals` | 审批、风险接受、条件核验 | 成员 7 approvals | Pilot 前隐藏写动作；SHADOW 水印 |
| `/reports-submissions` | 原 report、导出、提交核验 | 成员 7 reports | 按 Stage Gate 仅开放对应报告 |
| `/outcomes` | 结果与复盘 | 成员 7 reports | 未核验不能正式回测 |
| `/governance/access-audit` | 审计、血缘、失效、保留、保全、删除 | 成员 1 `features/access-audit/**` | 敏感 sink 失败关闭 |
| `/governance/privacy-models` | PIA/DSR/事件、Provider 政策与模型治理 | 成员 5 `features/privacy-models/**` | 外部调用需有效商家配置与治理 Gate |

`features/access-audit/**` 与 `features/privacy-models/**` 是两个顶级 feature，不共享父级 `public.ts`、样式或测试；两者只由成员 1 在 `src/app/**` 路由壳层组合，CODEOWNERS 分别唯一指向成员 1、成员 5。

- 项目/单元切换前若存在未保存草稿，必须显示“保存草稿 / 放弃 / 取消切换”，不能静默丢失；可复制草稿到新版本，但不得跨项目偷带 scope。
- 上传保留点击/拖拽键盘等价、多选、去重、逐文件状态、取消、重试和移除；长列表不得用 `slice(0,3)` 隐藏不可移除文件。竞对为动态 0–N，每份资料明确 subject、purpose、processing basis。
- 缺口必须支持责任人、截止、补证、独立复核和重跑；保留“方法与边界”、复制摘要和分阶段导出入口。
- 全局令牌以当前 Demo 为基线：ink `#1d2b26`、paper `#fffdf7`、canvas `#f1eee6`、green `#315c4d`、blue `#3568a8`、amber `#d28c3c`、rust `#c76b4f`、danger `#a8483e`、shadow `0 12px 40px rgba(29,43,38,.07)`；M0 归一现有 1240/1180/1040/960/780/650/480 断点，并在 1440、1024、768、390 视口建立正常/空/阻断/错误/长内容黄金截图。
- `bid-strategy-social.png` 的真实尺寸为 1731×909，迁入 `apps/web/public` 并只用本地相对 URL；favicon 按品牌替换，未使用 SVG 和死 CSS 经视觉回归后清理。
- 当前三个公网法规链接改为受版本控制的本地法规索引/镜像，显示来源、版本与生效日；断网点击不得外联。

---

## 5. 产品页面与功能实现要求

### 5.1 全局页面

| 页面 | 主要功能 | Gate/注意事项 |
| --- | --- | --- |
| 登录与账户 | Keycloak 登录、首次改密、MFA、会话退出 | 不能把局域网视为可信身份 |
| AI 服务商配置 | 商家选择平台允许的 Provider/模型，写入、验证、轮换、暂停或撤销自己的 API Key；查看脱敏状态和调用记录 | Key 只写不读；仅服务端调用；激活需 ProviderPolicy/PIA/跨境等 Gate |
| 项目列表 | 创建、搜索、归档项目；显示阶段、风险、缺口和下一步 | 角色与租户范围过滤 |
| 项目/决策单元总览 | 1–N 单元、预算、限价、截止、时区、范围、生命周期 | 一次只进入一个单元的正式计算 |
| 资料摄入中心 | 招标方、本公司、竞对三类资料；上传、扫描、隔离、解析、版本和错误恢复 | 扫描前不得解析；真实状态来自 Job |
| 制度、范围与规则 | 制度建议、ScopeAssessment、规则条款、原文定位、冲突、合规复核、发布 | 模型只建议；人工发布；超范围阻断 |
| 证据、响应与预审 | 证据库、双向匹配、固定响应画像、条件任务、Precheck | 无证据不判满足；预审不检查利润或市场 |
| 成本、政策与就绪 | 成本编制/批准、商业政策、就绪检查 | maker-checker；未批成本仅探索 |
| 竞对与市场 | 0–N 竞对、来源审核、主体去重、市场先验、未知进入者 | 无合法来源不得使用；无先验仅压力测试 |
| 基线与场景 | 冻结输入、搜索空间、搜索集、独立评估集、随机种子 | 概率集与压力集分离 |
| 仿真与方案 | Job 进度、静态校验、场景裁判、区间、经济代理、压力、0–4 个方案 | 无可行解显示原因；不造方案 |
| 推荐资格 | 预审、就绪、静态、场景、条件、风险的聚合 Gate | 不包含商业审批结论 |
| 审批中心 | 不可变审批包、工作流、条件、风险接受、决定 | 仅 Pilot 影子模式；上游变化立即失效 |
| 报告与提交 | 预审报告、模拟快照、决策报告、外部提交登记、双人核验 | 按阶段开放；系统不自动外部提交 |
| 结果与复盘 | Outcome、来源核验、前瞻/事后区分、回测 | 仅 VERIFIED 前瞻结果可正式评估 |
| 治理与管理 | 血缘、失效、审计、保留、删除、保全、DSR、事件、模型治理 | 敏感操作 fail closed |

### 5.2 文档摄入

- 支持 PDF、DOCX、XLSX、图片和受控压缩包；是否兼容旧 DOC/XLS 由安全评审决定，不能只因 Demo 接受扩展名就默认放行。
- 创建 project 或 decision-unit scope 的上传会话后，浏览器只走 `gateway → API 流式分块端点 → MinIO quarantine`；支持断点续传，服务端验证每块和整文件哈希。MinIO 不向浏览器或 LAN 暴露，complete 命令只有在字节数、哈希和隔离对象一致时成功。
- ClamAV、宏/脚本禁用、目录穿越、压缩炸弹、递归归档、伪装类型和资源限制必须在解析前执行。
- 解析任务提供 queued/running/succeeded/failed/cancelled/stale、进度、阶段、可重试性、原因码和人工录入路径。
- OCR 文本、页图、切片、向量、索引、临时文件、提示词、模型响应和导出都登记为派生资产及副本。
- 关键文件持续失败时，不允许通过“排除该文件”绕过规则确认。
- 项目级文件可被单元显式继承；单元覆盖必须写关联/优先级/冲突理由和人工确认，禁止复制文件或 last-write-wins。

### 5.3 制度、范围与规则

- 创建项目只能得到初步范围提示；安全解析足够材料后才允许发布正式 `ScopeAssessmentVersion`。
- Scope 状态为 `SUPPORTED / REVIEW_REQUIRED / UNSUPPORTED`，包含多原因码、影响范围、原文、确认人和确认时间。
- 只有 `SUPPORTED + CURRENT` 才放行正式策略。
- 条款必须记录原文、文件、页码、章节、优先级、覆盖关系、生效区间、结构化表达、置信度和人工确认。
- 项目级文件继承和决策单元覆盖采用确定性优先级解析，不得使用最后写入覆盖；冲突必须人工确认。
- 规则合规复核 `BLOCKING` 时只能探索；“按原文探索”和“合规风险情景”不能同时成为正式规则集。

### 5.4 企业证据、响应和预审

- 资质、案例、人员、技术、服务和承诺形成不可变证据版本。
- RuleClause/Requirement 与 Evidence 双向链接，状态为满足、部分满足、不满足或未知；每一强制规则必须有匹配行，缺行视为未知并阻断。
- 固定响应画像包含资格准备、响应方案、客观非价格输入、主观变量区间、证据和有效期。
- Precheck 只检查制度/规则可用、主体资格、实质响应、证据和截止前闭环能力；不得读取成本、利润和竞对数据做结论。
- 条件必须生成责任人、独立复核人、截止时间、证据和阻断阶段明确的任务。

### 5.5 成本、商业政策和就绪

- 成本基线统一币种、税口径、进项税、周期、履约成本、获授后费用、投标准备成本和现金流。
- 成本编制人与批准人必须不同；未批准只能探索。
- 商业政策版本化利润、现金流、产能、风险、覆盖率、最小获授质量、目标权重、合并容差和例外权限。
- 就绪检查分别列出规则、预审、响应、成本、政策、市场、用途、模型和场景协议状态，不得用一个布尔值代替。
- 商业约束失败只表示“公司政策下不可推荐”，不能标记为采购规则意义上的投标无效。

### 5.6 竞对、市场和模型/API Key

- 支持 0–N 实名竞对；竞对来源必须审核合法来源、允许用途、期限、个人信息基础和主体身份。
- 主体不明的文件保持隔离；同一企业不得同时出现在实名与未知进入者中。
- 画像只生成潜在参与、报价、证据/响应状态、主观变量和数据质量；客观非价格得分必须由确定性裁判计算。
- 没有批准的竞对画像或 `MarketPriorVersion` 时只允许运行无概率意义的压力测试，不能生成正式排名区间或推荐资格。
- Sampler 协议必须联合生成“本场景实名竞对参与集合 + 未知进入者数量”，保存联合分布/相关结构、去重规则、版本和金标；不得把各竞对独立参与与固定未知人数拼接成联合场景。
- 不部署本地生成式模型。平台维护 Provider/模型 allowlist 和版本化 adapter；商家/租户 AI 管理员可选择允许项并自行写入 API Key，不得任意填写 URL。自定义 Provider 域名必须先由平台安全管理员审查 adapter、TLS 域名、区域和 SSRF 风险，再进入 allowlist。
- `AIProviderConfigurationVersion` 必须遵循第 6.2 节的正交状态契约，不能把草稿生命周期、激活、密钥有效性、Provider 健康和适用性压成一个枚举。API Key 为 write-only secret：浏览器经内网 TLS 提交一次，后端立即写入 OpenBao；业务库只存 secret reference、末四位/指纹、创建人、轮换日和状态，任何 GET、日志、审计、导出、备份清单或错误均不得返回明文。写入的新 Key 先是 UNVERIFIED，只有固定合成连接测试成功才变为 VALID。
- 任何真实 Key 写入前先通过第 20.2 节 `BYOK_SECRET_GATE`；连接测试只能再走第 20.4 节 `CONNECTION_TEST` Gate，使用服务端固定合成载荷。成功不等于允许处理真实资料。ACTIVE 还必须满足当前 ProviderProcessingPolicy、处理基础、适用 PIA、跨境判定、用途/精确模型 ID 与能力/区域/保留匹配、调用预算和独立审批。`ProviderProcessingPolicyVersion` 必须明确 Provider 法人、API 域名、获批 provider_model_id/模型能力、允许用途/数据等级/区域、子处理者清单、`training_use=DISABLED` 及 opt-out/合同证明、精确保留天数、协议与安全措施、终止后的返还/删除方式及删除证明要求；仅声明 zero-retention 不能单独放行。正式真实项目或个人信息绝不允许用于 Provider 训练；无法证明禁用训练即阻断。合成或不可逆匿名数据若未来用于训练评估，必须另立非 `REAL_DATA_MODE` 流程与审批，不属于本期正式能力。
- 规则、证据、竞对等领域模块只能调用成员 5 暴露的 `GovernedModelInvocationPort`，传入 typed purpose、项目/单元、input asset refs、prompt template/output schema 和预算类别，不能直接访问低层 egress 或传入 Key/URL。成员 5 在执行逐次 Gate 并创建 `ProviderInvocationRecord` 后，才可通过成员 1 仅授予该模块的低层 `ProviderEgressPort` 发送最小必要、已脱敏/裁剪的输入；记录 provider/model、配置版本、prompt template hash、参数、请求/响应派生资产引用、耗时、token/费用、`invocation_state`、reason code、attempt 关系和删除/保留信息，但不保存 API Key。
- Provider 输出只能形成候选抽取、解释或画像建议，必须人工复核后发布；不得执行确定性资格、评分、舍入、并列或排名。无 API Key、配置未激活、429/超时/5xx、预算耗尽或撤销时，模型功能明确降级到人工录入，不能返回伪造结果。
- ACTIVE 配置不得原地覆盖 Key。计划轮换必须创建链接旧版本的 DRAFT successor，写入新 credential version（UNVERIFIED）→通过第 20.4 节连接测试（VALID/VERIFIED）→复核全部调用 Gate→在事务中原子切换 current config/credential 指针。切换前旧 ACTIVE/Key 继续服务；切换后旧版本禁止新调用，已开始请求仍绑定旧 config/credential version并完整记账，待有界 drain/回滚窗口结束后销毁本地旧 Key并提示商家撤销 Provider 端 Key。测试或复核失败不影响旧 ACTIVE。疑似泄露采用 COMPROMISE 模式：旧配置立即 SUSPENDED、禁止回滚并提示 Provider 端紧急撤销，宁可人工降级也不得继续使用。

### 5.7 场景、裁判、优化和评估

- 决策基线冻结规则、响应、成本、政策、竞对/先验/未知进入者、模型、时间点和完整 typed input manifest。
- 搜索集与独立评估集在搜索前冻结，具有独立种子；优化器永远不能看到评估集。
- 所有候选共享同一搜索场景、权重和共同随机数。
- 静态校验拆分展示“采购规则静态结果”和“商业基线结果”，禁止混淆。
- 采样器只生成潜在状态；资格、符合性、政策调整、客观得分、主观档位、异常低价、候选人产生、舍入、并列和排名由确定性裁判统一执行。
- 每场景输出 `awardable`、`eligible_for_award`、每个参与者的确定有效/待审查/确定无效/不可确定以及全部合法待审查结果空间。
- 第一候选指示必须同时满足 `awardable=true`、我方有效、我方位于可授予集合且排名第一。
- 待审查组合的精确枚举上限由版本化协议固定。超过上限时只能使用有证明的保守界算法，或返回 `INDETERMINATE`；不得静默抽样冒充精确上下界。
- 基础设施失败按协议重试，超限后整批 `SIMULATION_FAILED`；候选自身错误保留在共同分母并阻断正式发布。
- 无审查结果概率模型时只显示部分识别上下界和上下界各自的蒙特卡洛置信区间，不产生单点概率。
- 只有审查结果模型能为每个合法结果给出有效概率、通过独立验证，并且另有时间隔离的校准产物时，才显示校准第一候选概率。
- 未建立获授模型时，不输出正式期望收益点值。经济结果使用明确标注的第一候选情景代理区间。
- “尾部损失保护”在代理 CVaR 的样本空间、权重和获授代理事件经产品/算法/财务共同批准前，只能作为带水印压力保护探索方案，不得成为正式推荐目标。
- 生成 0–4 个不同且可行的方案；完全链接合并必须同时满足报价差、状态、审查类别、推荐资格、跳点、指标距离和可行集合连通条件。
- 算法规范以 PRD V1.3 §10.1–10.7 为逐字权威，不得凭记忆重写。M0 必须冻结变量字典、集合、分母、数值精度和 `B0 / B_proxy / B_cal` 谓词；重要性采样记录 `p/g`；覆盖率、`N_eff`、上下界、零分母、`Q_award`、会计利润、项目 NPV、投标决策 NPV、`E[Y]`、CVaR、风险效用和代理区间完整乘积分别建手算金标。平衡目标中 `P_candidate/Value/RobustMargin/ReviewRisk`、Z 的零方差/边界及所有权重在运行前由政策版本冻结；不得与 Bernoulli 获授变量复用符号。

### 5.8 推荐、审批、报告和提交

- 推荐资格聚合当前预审、就绪、静态校验、场景评估、条件和风险接受，不含商业审批结论。
- MVP-B 只生成不可审批、带水印的 `SimulationAssessmentSnapshot`。
- Pilot 中所有审批和授权记录必须带 `mode=SHADOW`，界面、下载和审计均标记“影子运行，不构成正式运营授权”。只有 Production Gate 后才允许生产模式授权。
- 审批包不可变，包含输入清单与哈希、方案、独立评估、压力测试、限制、条件、风险接受和报告草稿。
- 审批提交在一个事务内重查包适用性、条件、权限和截止时间；任一上游变化立即使包失效并终止当前流程。
- 仅补充证明既有事实且不改变规则、响应、成本、政策、报价或风险评估的条件，可在独立复核后沿用原附条件批准；其他变化必须重新生成审批包。
- 正式报告是不可变快照。提交记录保存平台、提交人、时间/时区、回执、实际报价、文件哈希和独立核验人。
- 无有效回执只能为 `DECLARED`；实际报价/文件/响应与审批包不同必须为 `MISMATCH`。
- `MISMATCH/FAILED` 后的修正必须追加新提交尝试并重新校验授权，不覆盖原记录。
- Outcome 冲突通过追加式 conflict-resolution 事件处理，不覆盖冲突来源。
- SubmissionRecord 生命周期必须完整包含 `DRAFT / DECLARED / VERIFIED / MISMATCH / FAILED / WITHDRAWN`；DRAFT 冻结待提交报价、响应和 `SubmissionArtifact` 文件清单，授权前逐字段/哈希比对审批包，差异立即 BLOCKED。

---

## 6. 核心状态与业务不变量

### 6.1 数据对象正交状态

所有版本化资料和衍生物必须分开保存：

- `lifecycle_state`：DRAFT / PUBLISHED / ARCHIVED / DELETED；
- `review_state`：PENDING / APPROVED / NOT_REQUIRED / REJECTED / QUARANTINED；
- `validity_state`：CURRENT / STALE / INVALIDATED；
- `retention_state`：RETAIN / DISPOSITION_DUE / DISPOSITION_RUNNING / DISPOSED；
- `effective_from/effective_to`；
- `superseded_by_id` 与追加式 SupersessionEvent；
- 0–N 个 LegalHoldRecord。

不得把这些维度合并成一个大枚举。`DELETED` 表示逻辑不可用，`DISPOSED` 表示所需副本处置完成；只保留不含正文和非必要个人信息的墓碑。

正式输入准入谓词统一命名为 `FormalInputAllowed`，必须同时满足：已发布、as-of 时刻生效、审核通过或无需审核、当前有效、处于保留状态、用途和授权当前有效。任一失败都阻断正式计算；所有模块必须调用同一 policy，不得复制判断。

### 6.2 评估与审批状态

| 对象 | 决策状态 | 独立适用性状态 |
| --- | --- | --- |
| PrecheckAssessmentVersion | PASS / CONDITIONAL / BLOCKED / UNKNOWN | CURRENT / STALE / INVALIDATED |
| StrategyReadinessAssessmentVersion | READY / CONDITIONAL / NOT_READY / UNKNOWN | CURRENT / STALE / INVALIDATED |
| StaticCandidateValidationVersion | VALID / INVALID / INDETERMINATE | CURRENT / STALE / INVALIDATED |
| ScenarioStrategyAssessmentVersion | ASSESSED / PARTIALLY_IDENTIFIED / INDETERMINATE | CURRENT / STALE / INVALIDATED |
| RecommendationEligibilityVersion | ELIGIBLE / ELIGIBLE_WITH_ACCEPTED_RISK / ELIGIBLE_WITH_CONDITIONS / INELIGIBLE / INDETERMINATE | CURRENT / STALE / INVALIDATED |
| ApprovalWorkflowInstance | PENDING / RUNNING / CANCELLED / TIMED_OUT / COMPLETED | CURRENT / EXPIRED / INVALIDATED |
| ApprovalDecisionEvent | APPROVED / CONDITIONAL / REJECTED | CURRENT / EXPIRED / INVALIDATED |
| AIProviderConfigurationVersion | activation_state：INACTIVE / VERIFIED / ACTIVE / SUSPENDED / REVOKED | CURRENT / STALE / INVALIDATED |
| ProviderInvocationRecord | invocation_state：QUEUED / RUNNING / SUCCEEDED / FAILED / BLOCKED / TIMED_OUT / CANCELLED | 追加式事实记录，不覆盖 |

历史决定永不覆盖。生命周期状态名称必须始终带对象域，不能把工作流 CANCELLED、决策单元 CANCELLED 和提交 WITHDRAWN 混为一个枚举。

Provider 配置还必须独立保存 `credential_state=MISSING/UNVERIFIED/VALID/INVALID/EXPIRED/REVOKED`、`credential_usage_scope=NONE/TEST_ONLY/BUSINESS_AND_DELETION/DELETION_ONLY` 与 `provider_health=UNKNOWN/HEALTHY/DEGRADED/UNAVAILABLE`，并继续使用第 6.1 节统一的 lifecycle/review/validity/retention/effective 状态。写入/轮换 Key 将 credential_state 置为 UNVERIFIED、usage_scope 置为 TEST_ONLY；固定载荷验证成功才转 VALID/VERIFIED，401/403 转 INVALID；全部治理 Gate 通过并 ACTIVE 后才转 BUSINESS_AND_DELETION。撤销先降为 DELETION_ONLY，收齐 Provider 副本 receipt 后毁钥并转 REVOKED/NONE；COMPROMISE 立即 REVOKED/NONE，后续删除改用独立渠道。Key 失效、Policy/PIA 撤销、目录失配或 Provider 故障分别更新对应维度并按规则进入 SUSPENDED/失败关闭，不得伪装成一个通用 ERROR。

每个 `ProviderInvocationRecord` 保存独立 `attempt_no`、`parent_invocation_id`、开始/结束时间、稳定 reason code 和审计引用。429 只作为 `PROVIDER_RATE_LIMITED` reason code，不新增状态；任何重试都创建新的 attempt/记录并关联原调用，绝不把 FAILED/TIMED_OUT/CANCELLED 历史原地改成 SUCCEEDED。

### 6.3 条件与风险

- 条件状态：OPEN / SATISFIED / WAIVED / FAILED / EXPIRED。
- 每个条件记录责任人、独立复核人、证据、截止日和阻断阶段；成员 4 是 Condition 唯一写入者，成员 7 只能调用其公开 satisfy/waive/fail command port，审批模块不得直接写条件表。
- 阻断阶段采用固定矩阵：COMPUTE / FREEZE / APPROVAL / AUTHORIZATION / SUBMISSION。
- 每个强制 Gate 必须是版本化 `StageGateAssessmentVersion`，绑定阶段、适用制度、负责人、证据、协议、结果与 `waiver_policy=PROHIBITED/ALLOWED`。法定资格缺失、确定性无效、跨租户、审计绕过、违规数据、无处理基础、无证据判满足、硬规则错误和财务计算错误均为 `PROHIBITED`；允许豁免项保存补偿控制、独立批准人、有效期和到期复验。
- 人工覆盖使用追加式 `ManualOverrideEvent`，完整保存 before/after、理由、操作者、独立批准人、适用范围、有效期和撤销事件；不能原地改写机器结果。
- 风险接受必须记录接受范围、授权人、有效期和撤销事件，方案制表人不得自行接受自己的风险。

### 6.4 决策单元生命周期

生命周期必须覆盖：草稿、解析、制度/范围、规则确认、证据、预审、补救、就绪、计算、仿真失败、无可行策略、推荐资格、审批包、审批、条件关闭、授权、冻结、外部提交待处理、提交声明/核验/不一致/失败/撤回、结果待回填/未核验/冲突/已核验、获授/落标/否决、取消/采购失败、关闭和归档。

采购取消可从任意非终态进入 CANCELLED。补遗、截止延期或采购恢复通过追加的 `REOPENED` 事件回到“最早受影响阶段”，并触发依赖传播；不得覆盖历史。NO_BID、WITHDRAWN 和 CANCELLED 是合法终态，不强迫回到 REWORK。

---

## 7. 核心数据对象

所有租户业务持久化对象、索引、对象键、队列消息、缓存、审计和血缘边都必须携带 `tenant_id` 与 `data_domain_id`。`scope_type` 固定为 `PLATFORM / TENANT / DATA_DOMAIN / PROJECT / DECISION_UNIT`；项目级或企业级对象使用明确的 `scope_type/scope_id`，不能为了方便伪造 decision_unit_id。

`ProviderCatalogVersion` 是唯一首期 `scope_type=PLATFORM` 的业务配置例外：其 `tenant_id/data_domain_id` 必须为 NULL，不得伪造“系统租户”，存放在独立 schema/表并使用独立 RLS/授权策略。只有平台安全管理员可创建草稿，独立隐私批准人可发布/撤销；普通已认证租户只能读取 PUBLISHED/CURRENT 的最小投影。租户 `AIProviderConfigurationVersion` 只能通过受控外键引用已发布 catalog ID/hash，不能反向写平台对象。除这项显式例外外，任一缺失 tenant/data-domain 的租户数据都失败关闭；跨租户或跨 scope 引用由复合外键、RLS 和服务层策略共同阻断。

| 对象组 | 对象 |
| --- | --- |
| 项目与规则 | ProcurementProject、DecisionUnit、ApplicableRegimeVersion、ScopeAssessmentVersion、RuleSetVersion、RuleClauseVersion、RuleComplianceReviewVersion、CrossLotConstraintVersion |
| 文件与派生物 | SourceDocumentVersion、DerivedDataAssetVersion、ReplicaLocation、ParseJobVersion |
| 公司响应 | RequirementVersion、CompanyEvidenceVersion、EvidenceMatchVersion、CompanyResponseProfileVersion、PrecheckAssessmentVersion、ConditionRequirementVersion |
| 商业输入 | CostBaselineVersion、CommercialPolicyVersion、StrategyReadinessAssessmentVersion |
| 竞争输入 | Competitor、CompetitorSourceVersion、CompetitorProfileVersion、MarketPriorVersion、UnknownEntrantProfileVersion |
| 搜索与评估 | DecisionBaselineVersion、CandidateSearchSpaceVersion、ScenarioSetVersion、SimulationBatchVersion、OptimizationRunVersion、CandidateStrategyVersion、StaticCandidateValidationVersion、ScenarioOutcome、ScenarioStrategyAssessmentVersion、StressTestAssessmentVersion、StrategyMergeAssessmentVersion |
| 决策与审批 | RiskAcceptanceVersion、RecommendationEligibilityVersion、SimulationAssessmentSnapshot、ApprovalWorkflowVersion、ApprovalRequestVersion、ApprovalWorkflowInstance、ApprovalStepInstance、ApprovalPackageSnapshot、ApprovalDecisionEvent、ApprovalApplicabilityEvent、SubmissionAuthorizationVersion |
| 提交与结果 | SubmissionRecordVersion、ProcurementOutcomeVersion、DecisionUnitLifecycleEvent、PrecheckReportSnapshot、DecisionReportSnapshot、ReportLifecycleEvent、ReportRevocationEvent |
| 模型与 Provider 治理 | ProviderCatalogVersion、AIProviderConfigurationVersion、ProviderCredentialReference、ProviderInvocationRecord、DatasetSnapshotVersion、FeatureSchemaVersion、ModelArtifactVersion、CalibrationArtifactVersion、EvaluationProtocolVersion、ModelApprovalVersion、ModelDeploymentVersion、ModelMonitoringSnapshot、ModelIncidentEvent、RollbackEvent |
| 隐私与安全 | PersonalDataProcessingRecord、LegalBasisEvidence、NoticeConsentRecord、ConsentWithdrawalEvent、PIARecordVersion、CrossBorderTransferAssessment、ProviderProcessingPolicyVersion、DataSubjectRequest、DSRPolicyVersion、IncidentPolicyVersion、IncidentEvent、LoadProfileVersion、StageGateAssessmentVersion、ManualOverrideEvent |
| 血缘与处置 | InputManifestItem、DataLineageEdge、InvalidationEvent、SupersessionEvent、RetentionDispositionJob、LegalHoldRecord、LegalHoldOverride、DeletionJob、DeletionReceipt、AuditEvent、TombstoneRecord |
| 技术支撑对象 | Tenant、DataDomain、UserMembership、RoleBinding、ProjectAccess、Job、OutboxEvent、IdempotencyRecord、Notification、ExportArtifact、SubmissionArtifact、AuditAnchor、EncryptedBackupManifest、KeyVersion |

跨标段和多轮后续对象只预留 ADR，不得在首期作为可用功能：PortfolioDecisionContextVersion、AwardAllocationScenarioVersion、PortfolioStrategyVersion、ProjectApprovalPackageSnapshot、ProcurementRoundVersion、OfferVersion。

为兼容 PRD V1.3，保留 `ModelArtifactVersion` 与 `ModelDeploymentVersion` 名称，但本项目中的含义固定为“外部 Provider/模型版本引用、adapter 与提示词/参数的可审计配置映射及其启停记录”，绝不表示下载模型权重、启动本地推理服务或在局域网部署生成式模型。

---

## 8. API 契约与一一对应规则

### 8.1 全局契约

- 业务 API 基础路径统一为 `/api/v1`；不泄密、无需业务鉴权的探针固定为 `/health/live` 和 `/health/ready`，不放在 `/api/v1`。
- JSON 字段统一 `snake_case`。
- ID 使用 UUID；时间使用 UTC RFC3339，业务截止时间另存 IANA 时区。
- 金额使用十进制定点字符串和 ISO 4217 币种。
- 错误使用 RFC 7807，并包含稳定 `code`、`request_id`、字段错误和可恢复提示。
- 创建、命令和异步任务使用 `Idempotency-Key`。
- 可变草稿使用 ETag/If-Match；已发布版本不可 PATCH。
- 列表统一 cursor pagination、稳定排序和权限过滤。
- 异步请求返回 202、job_id、status_url 和 events_url；SSE 为主、轮询降级；必须定义取消和有限重试语义。
- tenant、data_domain 和访问 scope 从服务端身份上下文获取，客户端字段不能覆盖。
- 所有敏感命令在事务中做权限、状态、截止时间和上游适用性复核，并写审计。
- 采用 code-first：M0 先审阅并冻结 `method + path + operationId + 权限 + Pydantic 请求/响应 stub`，再由 FastAPI 导出 OpenAPI 快照并生成 TypeScript 客户端。所谓“冻结 OpenAPI”是冻结这份可运行 stub 的导出物，不另维护一份 design-first Schema；任何人不得手改导出物或生成目录。

### 8.2 资源动作约定

版本化资源默认具有：列表、创建草稿、读取、修改草稿、发布、归档/撤销（若业务允许）。发布后更正必须创建新版本或追加事件。命令动作使用显式动词路径，不用含义不明的 PATCH 改最终状态。M0 表中每个 P0 操作必须进一步冻结完整 HTTP 方法/path/operationId、字段、枚举、权限、ETag/幂等要求、业务错误与页面字段映射；在该行 traceability 完成前，对应 feature 只能实现静态壳，不得自行发明 mock Schema。

### 8.3 FR—页面—接口—对象一一对应矩阵

| 需求 | 页面/动作 | 必备接口资源 | 核心对象/事件 | 负责人 |
| --- | --- | --- | --- | --- |
| 公共 | 登录、当前用户、任务进度、健康、Gate/覆盖 | `/me`、`/jobs/{id}`、events/cancel/retry、根 `/health/*`、stage-gates、manual-overrides | Membership、Job、Gate、Override、AuditEvent | 成员 1 |
| FR-01 | 项目/单元、范围、制度、规则、合规复核、生命周期 | projects、decision-units、scope-assessments、applicable-regimes、rule-sets、rule-clauses、compliance-reviews、cross-lot-constraints、lifecycle-events | Project、DecisionUnit、Scope、RuleSet、RuleClause、LifecycleEvent | 成员 2（生命周期唯一 writer） |
| FR-02 | 项目/单元上传、继承、隔离、扫描、解析、派生资产 | document-upload-sessions、upload chunks、document-links、documents、document-reviews、parse-jobs、derived-assets、replicas | SourceDocument、ParseJob、DerivedAsset、Replica | 成员 3 |
| FR-03 | Requirement、证据、匹配、响应画像、预审、条件 | requirements、evidence、evidence-matches、response-profiles、precheck-assessments、condition-requirements | Requirement、Evidence、Match、ResponseProfile、Precheck、Condition | 成员 4（条件唯一 writer） |
| FR-04 | 成本、商业政策、就绪 | cost-baselines、commercial-policies、readiness-assessments | CostBaseline、CommercialPolicy、Readiness | 成员 4 |
| FR-05 | 竞对、来源、画像、市场先验、未知进入者 | competitors、competitor-sources、competitor-profiles、market-priors、unknown-entrant-profiles、subject-deduplication | Competitor、MarketPrior、UnknownEntrant | 成员 5 |
| FR-06 | 决策基线、搜索空间、场景集 | decision-baselines、candidate-search-spaces、scenario-sets、freeze 命令 | DecisionBaseline、SearchSpace、ScenarioSet | 成员 6 |
| FR-07 | 仿真任务、静态校验、裁判结果、评估 | simulation-batches、candidates、static-validations、scenario-outcomes、scenario-assessments | Batch、Candidate、Validation、Outcome、Assessment | 成员 6 |
| FR-08 | 多目标搜索、压力测试、方案合并 | optimization-runs、stress-tests、strategy-plans、merge-assessments | CandidateStrategy、Stress、MergedPlan | 成员 6 |
| FR-09a | 推荐资格、模拟快照 | recommendation-eligibilities、simulation-assessment-snapshots | Eligibility、SimulationSnapshot | 成员 6（快照唯一 writer；只读成员 7 的 RiskAcceptance） |
| FR-09b | 风险接受、工作流版本、审批包、请求、步骤、决定、授权 | risk-acceptances、approval-workflow-versions、approval-packages、approval-requests、workflow-instances、approval-steps、approval-decisions、submission-authorizations | RiskAcceptance、WorkflowVersion、Package、DecisionEvent、Authorization | 成员 7（风险接受唯一 writer） |
| FR-10 | 预审报告、决策报告、提交草稿/制品/核验、结果、复盘 | precheck-reports、decision-reports、submission-records、submission-artifacts、submission-attempts、procurement-outcomes、outcome-conflicts、report-events | Report、Submission、Outcome | 成员 7（报告唯一 writer；生命周期只提交 transition command） |
| FR-11 | 血缘、替代、失效、保留、保全、删除编排、墓碑、审计 | lineage、input-manifests、supersession-events、invalidations、retention-jobs、legal-holds、deletion-jobs、deletion-receipts、tombstones、audit-events | LineageEdge、Invalidation、Deletion、Audit、Tombstone | 成员 1（领域/API/编排唯一 owner）；成员 3 只实现本地文件/MinIO/解析副本 adapter，成员 5 只实现 Provider 外部副本 adapter；二者只返回 receipt |
| FR-12 | 处理基础、告知/同意、PIA、跨境、服务商政策、DSR policy/request、事件 | processing-records、legal-basis-evidence、notice-consent-records、pias、cross-border-assessments、provider-policies、dsr-policies、data-subject-requests、consent-withdrawals、incident-policies、incidents | Privacy/Security 对象 | 成员 5；平台中间件由成员 1 |
| FR-13 | Provider 目录、商家 API Key 配置、调用记录、数据集、特征、模型、校准、部署、监控、回滚 | ai-provider-catalog、ai-provider-configurations、provider-invocations、datasets、feature-schemas、model-artifacts、calibrations、evaluation-protocols、model-approvals、model-deployments、monitoring-snapshots、model-incidents、rollbacks | Provider/模型治理对象 | 成员 5；SecretStore/egress 基座由成员 1 |

### 8.4 关键接口清单

以下 operation 必须存在，具体请求和响应字段由对应模块的 Pydantic Schema 固定，并由生成客户端供前端使用。

#### 公共与任务

- `GET /api/v1/me`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/events`
- `POST /api/v1/jobs/{job_id}/cancel`
- `POST /api/v1/jobs/{job_id}/retry`
- `GET /health/live`
- `GET /health/ready`
- stage-gates：list、assess、get；stage-gates/{id}/waivers：request、decide、expire；manual-overrides：append、list、revoke。

#### FR-01 项目与规则

- projects：list、create、get、update draft、archive；
- projects/{project_id}/decision-units：list、create；decision-units：get、update draft；
- decision-units/{unit_id}/scope-assessments：list、create；scope-assessments：get、update draft、publish；
- decision-units/{unit_id}/applicable-regimes：list、create；applicable-regimes：get、publish；
- decision-units/{unit_id}/rule-sets：list、create；rule-sets：get、publish；
- rule-sets/{rule_set_id}/clauses：list、create；rule-clauses：get、update draft、supersede；
- decision-units/{unit_id}/compliance-reviews：list、create；compliance-reviews：transition；
- decision-units/{unit_id}/cross-lot-constraints：list、create、confirm；
- decision-units/{unit_id}/transition-commands：submit；decision-units/{unit_id}/lifecycle-events：list。只有成员 2 的状态机可校验命令并追加事件，客户端不能直接 append。

#### FR-02 文件

- `POST /api/v1/projects/{project_id}/document-upload-sessions` 与 `POST /api/v1/decision-units/{unit_id}/document-upload-sessions`：创建同一种资源；
- `GET /api/v1/document-upload-sessions/{session_id}`：返回 scope、总大小/哈希、状态、分块大小、已接收 part/offset/块哈希、过期时间和下一步动作，用于断点续传；
- `PUT /api/v1/document-upload-sessions/{session_id}/chunks/{part_number}`：浏览器经 gateway/API 传输二进制块，校验 `Content-Length`、块哈希、offset 和幂等键；
- `POST /api/v1/document-upload-sessions/{session_id}/complete` 与 `/cancel`：complete 校验总大小、分块集合和总哈希后落 quarantine；cancel 幂等并安排临时副本处置。禁止使用 `upload-sessions` 别名；
- projects/{project_id}/documents 与 decision-units/{unit_id}/documents：list；document-links：inherit-to-unit、override、resolve-conflict、detach；
- documents：get、download、review、release-from-quarantine、quarantine；
- projects/{project_id}/parse-jobs 与 decision-units/{unit_id}/parse-jobs：create；parse-jobs：get、retry、cancel；
- documents/{document_id}/derived-assets：list；derived-assets：get；replicas：list。

#### FR-03/04 证据与商业

- decision-units/{unit_id}/requirements：list、create；requirements：get、update draft、publish、supersede；
- decision-units/{unit_id}/evidence：list、create；evidence：get、review、publish、revoke；
- decision-units/{unit_id}/evidence-matches：list、create；evidence-matches：review；
- decision-units/{unit_id}/response-profiles：list、create；response-profiles：get、publish；
- decision-units/{unit_id}/precheck-assessments：list、create；precheck-assessments：get；
- decision-units/{unit_id}/conditions：list、create；conditions：satisfy、waive、fail、expire；
- decision-units/{unit_id}/cost-baselines：list、create；cost-baselines：get、approve、publish；
- decision-units/{unit_id}/commercial-policies：list、create；commercial-policies：get、publish；
- decision-units/{unit_id}/readiness-assessments：list、create；readiness-assessments：get。

#### FR-05/13 市场与模型

- competitors：list、create、get、update draft、archive；
- competitors/{id}/sources：list、create；competitor-sources：review、quarantine；
- competitors/{id}/profiles：list、build、get、publish；
- decision-units/{unit_id}/market-priors：list、create、review、publish；
- decision-units/{unit_id}/unknown-entrant-profiles：list、create、publish；
- decision-units/{unit_id}/subject-deduplication-runs：create、get；
- datasets、feature-schemas、model-artifacts、evaluation-protocols：list、create、get、publish；其中 `model-artifacts` 只登记外部 Provider/model ID、API/adapter 版本、提示词模板与参数 Schema、评估证据和哈希，不接收或保存第三方模型权重；
- model-approvals：create、decide；model-deployments：create、activate、rollback；这里的 deployment 只把已批准的外部模型引用绑定到指定用途和 `AIProviderConfigurationVersion`，不创建本地模型服务；
- calibration-artifacts、monitoring-snapshots、model-incidents、rollback-events：list、create、get。
- `GET /api/v1/ai-provider-catalog`：返回当前已发布目录版本及允许选择的 provider/model ID、能力、区域、用途、最大输入和脱敏政策摘要；不返回平台级凭据、内部网络信息或未发布项；
- `POST /api/v1/platform/ai-provider-catalog-versions` 与 `GET /api/v1/platform/ai-provider-catalog-versions/{catalog_id}`：仅平台安全管理员创建/读取目录版本草稿；
- `POST /api/v1/platform/ai-provider-catalog-versions/{catalog_id}/publish` 与 `POST /api/v1/platform/ai-provider-catalog-versions/{catalog_id}/revoke`：发布/撤销需独立隐私批准；事件带版本/hash，成员 1 的 egress 策略只消费已发布事件，目录与网络 allowlist 的版本/hash 不一致时阻断调用；
- `GET/POST /api/v1/ai-provider-configurations`：按当前 tenant 列表/创建 DRAFT；创建只接受平台 provider/model allowlist ID、用途、预算、超时和保留选项，不接受任意未批准 URL；
- `GET/PATCH /api/v1/ai-provider-configurations/{config_id}`：GET 仅返回 lifecycle、activation、credential、provider_health、validity 等正交状态、Provider/模型、secret 指纹/末四位、轮换日、最近测试和 Gate 原因，永不返回 Key；PATCH 只改 DRAFT 且使用 If-Match；
- `POST /api/v1/ai-provider-configurations/{config_id}/successors`：为 ACTIVE 配置创建 DRAFT successor，保存 supersedes_config_id、rotation_mode=PLANNED/COMPROMISE、原因、旧 current 指针和 ETag；同一配置同时只能有一个待切换 successor；
- `PUT /api/v1/ai-provider-configurations/{config_id}/credential`：先要求 `BYOK_SECRET_GATE=PASS`，再只允许 DRAFT 配置/后继版本写入 API Key；body 为 write-only，服务端立即存 OpenBao并将 credential_state 置为 UNVERIFIED、credential_usage_scope 置为 TEST_ONLY；响应只含 `credential_reference_id/fingerprint/last_four/created_at/credential_state/credential_usage_scope`。对 ACTIVE 配置直接调用返回 409 `PROVIDER_CREDENTIAL_ROTATION_REQUIRES_SUCCESSOR`；HTTP/dev profile 返回 `BYOK_SECRET_GATE_REQUIRED` 且不得读取 body/持久化 secret；
- `DELETE /api/v1/ai-provider-configurations/{config_id}/credential`：立即把配置停用于所有新业务/连接测试并把 `credential_usage_scope` 降为 DELETION_ONLY，同时创建幂等 DeletionJob 并返回 202、job_id/status_url；若存在 Provider 远端副本，仅允许受限 adapter 以短 TTL、精确删除 endpoint 使用该凭据取得 receipt，收齐必需证明后才销毁 OpenBao secret 并把 scope 置 NONE、credential_state 置 REVOKED。它不能撤回已发送的 in-flight 请求，也不等于已在 Provider 控制台撤销原 Key；Job/UI 必须展示阶段和商家端撤销指引。COMPROMISE 模式必须立即在 Provider 端撤销并禁止复用疑似泄露 Key，后续删除通过独立管理凭据、商家操作或合同支持渠道取证；期间 DeletionJob 保持未完成；
- `POST /api/v1/ai-provider-configurations/{config_id}/test-connection`：先要求第 20.2 节 PASS，再只允许第 20.4 节 `CONNECTION_TEST` Gate；服务端生成固定无敏感探针，返回 Provider 可达性/认证/模型存在/限额错误，不回显请求头或 Key；成功原子转为 VERIFIED，失败只更新对应 credential/provider_health 维度和追加调用记录；
- `POST /api/v1/ai-provider-configurations/{config_id}/activate`：原子检查 credential_state=VALID、credential_usage_scope=TEST_ONLY、ProviderPolicy、处理基础、PIA/跨境、allowlist、预算与独立批准后进入 ACTIVE 并把 usage_scope 转为 BUSINESS_AND_DELETION；若为 successor，同时使用 If-Match/事务锁切换 current 指针并使旧配置停止新业务调用，旧 Key 按轮换/删除策略转 DELETION_ONLY，失败保持旧 ACTIVE 不变；
- `POST /api/v1/ai-provider-configurations/{config_id}/suspend`：保留审计与历史引用、停止新调用；重复请求幂等；
- `POST /api/v1/ai-provider-configurations/{config_id}/revoke`：不可逆停止配置的新业务调用并使依赖结果按矩阵失效；本地 secret 处置异步返回 202、deletion_job_id/status_url，遵循“远端副本删除/到期证明 → 必需 receipt 聚合 → 最终毁钥”的顺序，绝不能把本地毁钥当作 Provider 远端删除 receipt；COMPROMISE 例外按上一条立即远端撤销并改走独立删除渠道；
- `GET /api/v1/provider-invocations` 与 `GET /api/v1/provider-invocations/{id}`：仅返回脱敏元数据、派生资产引用、费用、invocation_state、attempt 关系和错误码；正文读取另走受权资产接口并审计。

上述 Provider API 的 operationId 固定为 `list_ai_provider_catalog`、`create_ai_provider_catalog_version`、`get_ai_provider_catalog_version`、`publish_ai_provider_catalog_version`、`revoke_ai_provider_catalog_version`、`list_ai_provider_configurations`、`create_ai_provider_configuration`、`get_ai_provider_configuration`、`update_ai_provider_configuration`、`create_ai_provider_configuration_successor`、`set_ai_provider_credential`、`revoke_ai_provider_credential`、`test_ai_provider_connection`、`activate_ai_provider_configuration`、`suspend_ai_provider_configuration`、`revoke_ai_provider_configuration`、`list_provider_invocations` 和 `get_provider_invocation`。配置、创建后继版本、写入/轮换 Key、连接测试、暂停与撤销配置需要当前 tenant 的 `TENANT_AI_ADMIN` + MFA；激活还需要隐私/数据责任人的独立批准，maker 不得充当 checker。所有 GET/列表 Schema 明确禁止 `api_key/secret/plaintext` 字段。

Provider 专用稳定错误码至少包括：`BYOK_SECRET_GATE_REQUIRED`、`PROVIDER_REAL_DATA_MODE_REQUIRED`、`PROVIDER_CONFIG_NOT_ACTIVE`、`PROVIDER_CREDENTIAL_MISSING`、`PROVIDER_CREDENTIAL_UNVERIFIED`、`PROVIDER_CREDENTIAL_INVALID`、`PROVIDER_CREDENTIAL_REVOKED`、`PROVIDER_CREDENTIAL_USAGE_NOT_ALLOWED`、`PROVIDER_CREDENTIAL_ROTATION_REQUIRES_SUCCESSOR`、`PROVIDER_ROTATION_CONFLICT`、`PROVIDER_POLICY_NOT_CURRENT`、`PROVIDER_CALL_NOT_AUTHORIZED`、`PROVIDER_EGRESS_BLOCKED`、`PROVIDER_RATE_LIMITED`、`PROVIDER_TIMEOUT`、`PROVIDER_UPSTREAM_ERROR`、`PROVIDER_RESPONSE_INVALID` 和 `PROVIDER_BUDGET_EXCEEDED`。这些错误必须映射到配置修复、稍后重试或人工录入，不得泛化为 500，也不得在错误详情中包含请求头、Key、正文或 Provider 原始敏感载荷。

#### FR-06/07/08/09a 仿真

- decision-units/{unit_id}/decision-baselines：list、freeze、get；
- decision-units/{unit_id}/candidate-search-spaces：list、create、get；
- decision-units/{unit_id}/scenario-sets：list、create、freeze、get；
- decision-units/{unit_id}/simulation-batches：create、list；simulation-batches：get、cancel、retry；
- simulation-batches/{id}/candidates、static-validations、scenario-outcomes、scenario-assessments：list/get；
- simulation-batches/{id}/optimization-runs：create、list/get、finalize、invalidate；
- optimization-runs/{id}/stress-test-assessments、strategy-plans、merge-assessments：list/get；strategy-plans：publish/invalidate；
- decision-units/{unit_id}/recommendation-eligibilities：create、list、get；
- decision-units/{unit_id}/simulation-assessment-snapshots：create、list、get、download。

#### FR-09b/10 决策闭环

- approval-workflow-versions：list、create、get、update draft、publish、archive；
- decision-units/{unit_id}/risk-acceptances：create、list；risk-acceptances：get、revoke；
- decision-units/{unit_id}/approval-packages：freeze、list；approval-packages：get；
- approval-packages/{id}/approval-requests：create；approval-requests：get、cancel；
- workflow-instances：get；workflow-instances/{id}/steps：list；approval-steps/{id}/decisions：append；
- approval-packages/{id}/applicability-events：list；
- decision-units/{unit_id}/submission-authorizations：create、list；submission-authorizations：get、block、expire；
- decision-units/{unit_id}/precheck-reports、decision-reports：按 Stage Gate 创建、读取、下载；SimulationAssessmentSnapshot 只使用成员 6 的 `/simulation-assessment-snapshots`，本组不得创建别名；
- decision-units/{unit_id}/submission-records：create-draft、list；submission-records：get、update-draft、declare、verify、mark-mismatch、mark-failed、withdraw；
- submission-records/{id}/artifacts：create、list、freeze、compare-to-approval-package；所有上传仍复用 FR-02 流式端点；
- submission-records/{id}/attempts：append、list；
- decision-units/{unit_id}/procurement-outcomes：create、list；outcomes：get、verify、mark-conflicting；
- outcomes/{id}/conflict-resolution-events：append、list；
- reports/{id}/lifecycle-events、revocation-events：append、list。

#### FR-11/12 治理

- objects/{object_type}/{object_id}/lineage、input-manifest：get；
- supersession-events：append、list；invalidation-events：list、get；retention-jobs：list、create、get、retry；tombstones：受权 list/get；
- legal-holds：list、create、release；legal-hold-overrides：create；
- deletion-jobs：list、create、get、retry；deletion-jobs/{id}/replica-commands、receipts：list；
- audit-events：受权分页查询；audit-integrity-checks：create、get；
- processing-records、legal-basis-evidence、notice-consent-records、pia-records：list、create、get、approve/revoke；
- cross-border-assessments、provider-policies：list、create、get、approve、mark-not-required、revoke、expire；跨境评估只有在已验证处理区域证明不跨境时才能 `NOT_REQUIRED/CURRENT`；涉及或无法排除跨境时必须 `APPROVED/CURRENT`，UNKNOWN/EXPIRED/REJECTED 一律阻断。ProviderPolicy 批准只代表治理条件之一，不能单独激活 API Key 配置；
- dsr-policies：list、create、get、publish、archive；load-profiles：list、create、get、freeze；
- data-subject-requests：list、create、verify-identity、transition、complete；
- consent-withdrawals：append；incident-policies：create、approve；incidents：create、transition、close。

### 8.5 追踪文件和 CI

每个模块的 `traceability.yaml` 至少包含：

`FR/验收编号 → 用例编号 → 页面路由/组件 → operationId → method/path → 请求 Schema → 响应 Schema → 权限 → 审计动作 → handler → 事件/Job → 单元测试 → 契约测试 → E2E 测试`。

CI 必须做到：

1. 导出并固定 OpenAPI 快照；
2. lint 路径、operationId、错误格式、鉴权和幂等头；
3. 自动生成 TypeScript 客户端，发现手改即失败；
4. 检测 breaking change；
5. Schemathesis 对每个 operation 执行正常、无权、非法状态和边界请求；
6. 任一 PRD 验收项没有 UI/API/test 映射即失败；
7. 任一正式 operationId 没有 FR/用例归属即失败；
8. Playwright 在生成 mock 与真实 Compose 环境各运行一次；
9. 输出 FR 总数、已实现、仅探索、被 Gate 阻断、缺失接口和缺失测试的只读报告。

---

# 第二部分：七人分工与成员提示词

## 9. 七人总分工

| 成员 | 角色 | 独立负责功能 | 独占目录/配置 | 主要下游 |
| --- | --- | --- | --- | --- |
| 1（组长） | 架构、治理编排与集成 | 本地平台、身份/隔离、契约、Job/outbox、Shell/原子 UI、OpenBao SecretStore、受控 Provider 出网、FR-11 治理、CI | 根配置、`infra/**`、后端 `core/**`、`governance/{lineage,invalidation,retention,legal_hold,deletion,audit}/**`、`workers/governance/**`、前端 `app/**`/Shell/`components/ui/**`/access-audit、跨域 E2E | 全员 |
| 2 | 项目与规则 | FR-01 项目、决策单元、制度、范围、规则、合规复核；DecisionUnit 生命周期唯一 writer | 后端 `projects/**`、`rules/**`；前端 projects/rules | 4、6、7 |
| 3 | 文档摄入 | FR-02 安全上传、扫描、OCR、解析、派生资产；为成员 1 提供本地文件/MinIO/解析副本删除 adapter/receipt | `documents/**`、`workers/ingest/**`、前端 documents；`documents/infrastructure/deletion_adapters/**` | 2、4、5、1 |
| 4 | 企业响应与商业 | FR-03/04 Requirement、证据、匹配、响应画像、预审、成本、政策、就绪；Condition 唯一 writer | `evidence/**`、`commercial/**`、前端同名 feature | 6、7 |
| 5 | 市场、隐私与模型 | FR-05/12/13 竞对/先验、PIA/DSR/事件、ProviderPolicy、商家 API Key 配置元数据、外部模型异步调用/副本删除 adapter 与模型治理 | `market/**`、`model_governance/**`、`workers/provider/**`、`governance/privacy_external/**`、`model_governance/infrastructure/provider_deletion_adapters/**`、前端 market/privacy-models/AI Provider settings | 2、3、4、6、1 |
| 6 | 仿真算法 | FR-06/07/08/09a 基线、场景、裁判、优化、独立评估、压力、合并、推荐资格；SimulationAssessmentSnapshot 唯一 writer | `simulation/**`、`workers/simulation/**`、前端 simulation/eligibility | 7 |
| 7 | 决策闭环 | FR-09b/10 RiskAcceptance 唯一 writer、审批、授权、所有报告、提交/制品、结果；只请求生命周期迁移 | `approvals/**`、`reports/**`、前端 approvals/reports/outcomes | 最终交付 |

### 9.1 冲突最小化规则

- 除成员 1 外，任何人不得直接修改根 `package.json`、后端依赖锁、Compose、`.env.example`、网关、Keycloak、公共错误格式、公共认证、公共 UI 或生成目录。
- 每人只能修改自己的模块目录；跨模块需求先写契约变更提案，不直接进入对方目录修复。
- 前端不得从另一个 feature 的内部路径导入；后端不得访问另一个模块的 repository、ORM model 或表。
- 新共享接口先合并“契约 PR”，成员 1 重新生成客户端后，功能 PR 才能依赖它。
- 每人只新增自己的 Alembic revision，不修改已合并迁移；多 head 由成员 1 统一 merge。
- 新依赖由成员 1 统一加入锁文件；成员在 PR 描述中说明用途、安全影响和无依赖替代方案。
- 每个功能 PR 同时提交实现、测试、权限负向用例、审计断言、traceability 行和 UI 空/错/加载状态。
- 已发布版本不可修改；使用新版本或追加式事件。
- 分支统一 `feature/m{成员号}-{domain}-{short-name}`，提交保持单一主题；`main` 受保护，禁止直接 push/force-push，必须通过 PR、CI 与 CODEOWNERS 审阅后 squash merge。
- CODEOWNERS 精确映射上表目录；跨域契约 PR 先于实现 PR。迁移冲突在功能 PR 合入前解决：成员只追加自己的 revision，成员 1 单独提交 merge revision，禁止重写已共享历史。
- 成员 1 只拥有公共原子 UI 和 Shell；页面业务、feature 测试与视觉状态由各 feature owner 完成，避免组长承担全部前端实现。跨域 E2E 由成员 1 编排、对应 feature owner 修复。
- `BYOK_SECRET_GATE` 的证据聚合、core guard、敏感路由预解析 middleware、网络开关和公共只读 Gate 状态 API/生成 hook 由成员 1 独占；成员 5 独占 Provider settings feature 与配置业务 handler，只消费该 guard/hook 显示原因并启停控件，不复制 Gate 判定。成员 1 不进入成员 5 feature，成员 5 不修改 core middleware/网络策略。

### 9.2 依赖顺序

成员 1 的平台与契约 stub 是所有工作的前置。成员 2、3、4、5 可在生成的 stub 客户端下并行；成员 6 只能在规则、响应、成本、市场和模型契约冻结后接入正式基线；成员 7 从 MVP-A 起负责报告渲染，但 Pilot Gate 前不能开放审批，并且只能消费成员 6 的不可变评估结果，不能自行重算策略。

---

## 10. 成员 1 提示词：组长、架构与集成负责人

你是七人小组的组长和唯一集成负责人。请先阅读本文件“全体成员统一总提示词”和 PRD V1.3。你的目标是建立所有人可以并行工作的本地工程骨架和强制契约，不替其他成员实现领域业务。

你的独占范围：根配置、Compose、`infra/**`、后端 `core/**`、前端 app Shell/共享原子 UI、认证、API 生成客户端、公共错误、Job/outbox，以及 FR-11 的血缘、失效、保留、保全、删除编排、墓碑、独立审计和治理 Worker；不拥有成员 3 的本地文件/对象副本 adapter，也不拥有成员 5 的 Provider 外部副本 adapter。

必须完成：

1. 把现有 vinext/Sites/Cloudflare Demo 迁移到标准 Next.js Node；明确删除 `.openai/hosting.json`、`build/sites-vite-plugin.ts`、`worker/index.ts`、旧 Cloudflare `vite.config.ts`、`db/index.ts` D1 入口、`app/chatgpt-auth.ts`、Worker 渲染测试，以及 vinext/Wrangler/Cloudflare/Drizzle-D1 依赖与 `.sites-deploy/.vinext/.wrangler/dist` 缓存；仅移除 Cloudflare Worker Runtime，保留本地 Celery Worker。重写根 npm/PowerShell 脚本，Windows 可直接运行。
2. 建立 Next.js、FastAPI、PostgreSQL、两个 Redis、MinIO、Keycloak、OpenBao、ClamAV、四个 Celery Worker（ingest/simulation/governance/provider）、scheduler、Caddy、`provider-egress-gateway` 和本地观测的 Compose 基线；不加入任何本地 LLM 服务；落实 healthcheck、命名卷、资源/restart 策略、migrate/seed job、profile 与备份恢复顺序。
3. 提供 Windows PowerShell 初始化、启动、测试、备份、恢复、停止入口；显示本机 URL、LAN URL 和依赖 readiness，不硬编码 IP。
4. 初始化七个测试账户、角色、项目范围、首次改密和必要 MFA；前端只做 UX 控制，后端才是授权事实来源。
5. 建立 tenant/data-domain/project/unit scope 中间件、PostgreSQL 复合约束/RLS、MinIO key 前缀、Redis key 和 Job payload 的隔离规范。
6. 建立 RFC 7807 错误、request_id、Idempotency-Key、ETag/If-Match、cursor pagination、可信时间和金额类型规范。
7. 建立 Job、outbox、reconciliation、幂等、重试、取消、SSE 和轮询降级；业务真状态只在 PostgreSQL。
8. 建立独立 append-only AuditWriter、可信时间、哈希链和外部锚点；主库管理员不能无痕改写。审计不可用时阻断正文查看、下载、导出、发布、审批、授权、用途审批、解除隔离、保全解除和删除；恢复后验证断点与哈希链。
9. 独占 FR-11：实现 InputManifest、DataLineageEdge、Supersession/Invalidation、RetentionDispositionJob、LegalHold/Override、DeletionJob 跨 adapter 编排、DeletionReceipt 聚合、Tombstone 和 `worker-governance`。必须同时等待成员 3 的本地文件/MinIO/解析副本 receipt 与成员 5 的 Provider 外部副本 receipt；所有必需副本完成前不得发布 `DeletionCompleted`。dependency_type 固定为 COMPUTATIONAL/EVIDENTIAL/POLICY/AUTHORIZATION/PRESENTATIONAL；事件×依赖矩阵幂等传播；`retention_expires_at` 到期立即停止正式使用并传播。快照载荷独立 DEK、毁钥、备份恢复先重放墓碑。
10. 只把 Demo 拆成 app Shell、公共 UI 和各 feature 空挂载点；各 feature owner 迁移业务页面和视觉状态。清理公网资源、旧误导文案和死测试，不进入成员 2–7 目录代写。
11. 建立 OpenAPI 导出、生成 TS 客户端、breaking change、traceability 聚合、Schemathesis、Playwright 和安全检查流水线。
12. 建立 `REAL_DATA_MODE` 统一启动谓词，逐项验证第 20.1 节；任一状态未知或失败即拒绝启动。实现字段/对象信封加密、KEK/DEK 隔离与轮换、加密导出/备份、密钥销毁和恢复时密钥可用性测试。
13. 建立固定 `biaice.local`、Caddy local CA、Keycloak issuer/redirect、安全 Cookie和主机防火墙；实现 `provider-egress-gateway` 的 Provider 域名 allowlist、TLS 证书/主机名校验、DNS pinning/重绑定防护、私网与 metadata IP 拒绝、重定向复核、请求限流和所有非 Provider 出网拒绝。网络 allowlist 只消费成员 5 发布的 `ProviderCatalogPublished/Revoked`，保存并校验 catalog version/hash；同步失败或 hash 不一致时调用失败关闭。设置 `NEXT_TELEMETRY_DISABLED=1`，禁用无关更新/遥测检查。
14. 提供 `SecretStorePort`：API Key 只写入 OpenBao，按 tenant/provider/purpose 隔离；支持写入、轮换、租约/到期、撤销和毁钥，调用方只能持有不透明 reference。平台/系统管理员默认也不能读取商家 Key 明文。低层 `ProviderEgressPort` 只授予成员 5 的模块服务身份，其他领域/Worker 直接调用必须被依赖规则和运行时策略拒绝。
15. 权限基线写死：系统管理员默认不能查看正文、成本或 API Key；只有 `TENANT_AI_ADMIN` 可为本 tenant 写入/轮换 Key，隐私/数据责任人独立批准 ProviderPolicy/PIA/跨境适用性；保全解除和批量导出双人批准，任何角色不能既 maker 又 checker。
16. 在 `infra/openbao/**` 固化非 dev 初始化、2-of-3 unseal/recovery 份额仪式、root token 撤销/离线双控封存、细粒度 policy、短期 AppRole/token、审计设备、seal 后失败关闭和备份恢复；API 身份只写/销毁不读，egress 身份只按已授权 invocation 的精确 path/version 短时读取。任何 root token 或 unseal share 出现在环境变量、Compose、日志或仓库都使 `BYOK_SECRET_GATE` 与 `REAL_DATA_MODE` 同时失败。
17. 独占实现第 20.2 节 `BYOK_SECRET_GATE` 的平台层：聚合/签名 Gate 证据，提供 `RequireBYOKSecretGate` core guard、在解析 secret body 前执行的敏感路由 middleware、宿主防火墙/Compose provider-egress 开关，以及公共只读 Gate 状态 API/生成 hook；只有 PASS/CURRENT 的 HTTPS 安全 profile 才放行。不要进入成员 5 的 Provider settings feature 或配置业务 handler；该 Gate 与 `REAL_DATA_MODE` 分开记录，但复用同一可信 TLS/OpenBao/审计证据。

必须提供给全体成员的公开契约：IdentityContext、TenantScope、PermissionGuard、AuditWriter、StoragePort、JobPort、OutboxPort、Clock、Money、ProblemDetails、VersionMetadata 和生成 API 客户端。`SecretStorePort` 与低层 `ProviderEgressPort` 不是通用领域端口，只能注入成员 5 的 Provider 配置/调用模块；成员 2/3/4/6/7 若需要生成式候选，只能消费成员 5 的 `GovernedModelInvocationPort`。

验收：两台局域网设备通过受信根证书、OIDC/MFA 登录并并发访问；刷新和服务重启不丢数据；只有 gateway 对 LAN 暴露；断互联网时非模型核心流程和人工降级可用；除第 20.3 节 ACTIVE 正式调用和第 20.4 节固定合成连接测试外无公网请求；浏览器从不直连 Provider；跨租户读取配置/secret reference/调用记录全部拒绝；审计断开时模型调用与敏感操作失败关闭；API Key 写入、遮罩、轮换、撤销、毁钥及加密备份恢复演练通过。

禁止：替成员 2–7 编写领域规则、匹配算法、竞对画像、仿真算法或审批决定；不得为赶进度绕过契约和权限。

交付说明必须列出：架构决定、运行方式、服务健康、公共契约版本、待接模块、已知限制、测试结果和回滚方法。

---

## 11. 成员 2 提示词：项目、制度、范围与规则

你负责 FR-01，独占后端 `projects/**`、`rules/**` 和前端对应 feature。不要修改根配置、公共认证、生成客户端或其他模块。

目标：实现 ProcurementProject、DecisionUnit、ApplicableRegimeVersion、ScopeAssessmentVersion、RuleSetVersion、RuleClauseVersion、RuleComplianceReviewVersion、CrossLotConstraintVersion 和 DecisionUnitLifecycleEvent 的完整闭环。

必须完成：

1. 项目及 1–N 决策单元的创建、编辑草稿、归档、列表和详情；保存预算、最高限价、截止时间、时区和跨单元组。
2. 制度、采购方式、评标方法、单/多轮和跨标段约束的候选识别与人工确认。
3. ScopeAssessment 的创建、原文依据、原因码、影响范围、确认、发布和适用性；只有 SUPPORTED/CURRENT 才可正式放行。
4. 跨标段命中产生 PORTFOLIO_REVIEW_REQUIRED；多轮命中产生 MULTI_ROUND_UNSUPPORTED；只输出规则/冲突报告。
5. 规则条款覆盖资格、实质性要求、评分、公式、舍入、并列、候选人、有效供应商数、同品牌、异常低价、合同和提交要求。
6. 每条规则保存原文、文档/页码/章节、优先级、覆盖关系、结构化表达、置信度、确认人、确认时间和生效区间。
7. 实现项目级继承与单元覆盖的确定性解析；冲突不使用 last-write-wins，进入人工确认。
8. 合规复核状态 OPEN/BLOCKING/ACCEPTED_FOR_SIMULATION/RESOLVED/CLOSED；BLOCKING 只能探索。
9. 仅“已发布且已生效”的制度/规则事件触发下游失效；草稿和未来版本不传播。
10. 生命周期事件追加写入，不覆盖历史；REOPENED 保存前态、后态、原因、依据和最早受影响阶段。

必须发布事件：ScopeAssessmentPublished、RegimePublished、RuleSetPublished、RuleSetRevoked、CrossLotConstraintConfirmed、DecisionUnitReopened、DecisionUnitLifecycleAdvanced。所有调用方只提交 transition command，不得直接追加事件。

必须消费：成员 3 的 SourceDocumentReleased、ParseCompleted、DocumentQuarantined；成员 1 的身份、审计、版本和 outbox。

API：严格实现本文件 FR-01 接口组，operationId 和 Schema 先进入契约 PR。已发布条款不可 PATCH，纠正通过新版本或 supersede。

验收：三个合成项目至少覆盖综合评分法、最低评标价法、规则冲突、补遗覆盖、跨标段阻断和多轮阻断；公式、边界、舍入、并列金标 100% 通过；未映射强制规则能够被下游发现并失败关闭；无关草稿不使正式结果过期。

交付：API、迁移、规则金标 fixture、traceability、前端正常/空/冲突/无权/过期状态、事件清单和成员 4/6 的消费说明。

---

## 12. 成员 3 提示词：安全文档摄入、OCR 与副本处置

你负责 FR-02，并为成员 1 的 FR-11 删除编排提供文件派生资产 adapter。独占 `documents/**`、`workers/ingest/**`、前端 documents feature 和 `documents/infrastructure/deletion_adapters/**`；你不拥有 DeletionJob、LegalHold、Retention、Tombstone 或 governance worker。

目标：确保任何文件在进入规则、证据或竞对处理前都经过可审计的本地安全摄入，并确保所有派生副本可追踪、可隔离、可删除、可恢复验证。

必须完成：

1. 项目级和决策单元级上传会话、经 gateway/API 的分块流式上传、断点续传、大小/数量限制、块/整文件 SHA-256、真实 MIME 嗅探和同内容去重；不能信任扩展名或浏览器 MIME，也不能让浏览器直连 MinIO。
2. quarantine → scan → review → released 的真实状态机；前端进度来自 Job，不使用 setTimeout 伪造。
3. ClamAV、EICAR、伪装后缀、宏/脚本、目录穿越、压缩炸弹、递归归档、嵌套层级、解压总大小、文件数、密码保护和加密文件处理。
4. 解析容器只读根文件系统、no-new-privileges、CPU/内存/时间限制、临时目录、禁互联网出口和有限重试。
5. PDF/DOCX/XLSX/图片解析、本地 OCR、页码和章节定位；失败给稳定原因码、是否可重试和人工录入路径。
6. SourceDocument、ParseJob、DerivedDataAsset、ReplicaLocation 全量登记；OCR、页图、切片、向量、缓存、临时文件、提示词、模型响应、导出和备份都不能漏。
7. 隔离、删除和用途撤回事件立即阻断逻辑访问，并通知失效框架。
8. 实现 SourceDocument/DerivedAsset/ReplicaLocation 的 `ReplicaDeletionAdapter`，接收成员 1 的删除命令并返回不可伪造 receipt；全局遍历、状态和完成判定由成员 1 编排，禁止在 documents 内另建 DeletionJob。
9. 执行 adapter 前查询成员 1 的 LegalHold policy；保全时返回 BLOCKED receipt，但不恢复业务使用。备份恢复前由成员 1 重放 tombstone，你负责证明相应文件副本未复活。
10. 上传和下载必须进行权限、范围、审计和路径穿越防护；对象 key 不接受用户拼接路径。

必须发布事件：SourceDocumentUploaded、SourceDocumentReleased、DocumentQuarantined、ParseCompleted、ParseFailed、DerivedAssetRegistered、ReplicaDeletionReceiptProduced。只有成员 1 聚合全部必需 receipt 后可发布全局 `DeletionCompleted`。

必须向成员 2/4/5 提供：稳定文档/页/片段引用、解析状态、内容哈希、来源/用途/审核元数据和只读访问 port。

验收：恶意验收样本 100% 阻断；100MB 接收状态 P95≤5秒、200页原生文本初稿 P95≤10分钟、200 DPI 扫描 OCR 初稿 P95≤20分钟，全部绑定本地 LoadProfile；正常删除、单副本失败重试、保全、解除保全和备份恢复墓碑重放五类演练通过。

禁止：自行判断规则含义、证据是否满足、竞对画像或模型结论；不得让“解析成功”自动等同业务审核通过。

---

## 13. 成员 4 提示词：公司证据、固定响应、预审与商业就绪

你负责 FR-03 和 FR-04，独占 `evidence/**`、`commercial/**` 及前端对应 feature；你是 RequirementVersion、ConditionRequirementVersion 及其命令接口的唯一 writer。

目标：实现“证据与响应事实 → 资格/响应预审 → 成本与政策 → 策略就绪”的无循环链路，并严格区分采购规则有效性和公司商业政策。

必须完成：

1. 资质、案例、人员、技术、服务、承诺等不可变 CompanyEvidenceVersion；来源、有效期、主体和审核完整。
2. RuleClause/Requirement ↔ Evidence 的双向匹配；满足/部分满足/不满足/未知四态；人工复核记录理由和原 ETag。
3. 每条强制规则必须有匹配行。未映射、无证据或证据失效均不得自动判满足。
4. 发布固定 CompanyResponseProfileVersion，包含资格准备、固定技术/服务响应、客观非价格输入、主观变量区间、证据和有效期。
5. Precheck 只读取制度/规则、主体资格、实质响应、证据和截止前闭环能力；不读取成本、利润、市场或竞对结论。
6. 条件任务保存责任人、独立复核人、证据、截止时间和阻断阶段；为成员 7 提供 satisfy/waive/fail/expire command port，成员 7 不得直写条件表。阻断或未知只能探索。
7. CostBaselineVersion 覆盖币种、含税/不含税、进项税、周期、履约成本、获授后成本、准备成本和现金流；使用 decimal。
8. 成本 created_by 必须不等于 approved_by；批准前仅探索。
9. CommercialPolicyVersion 版本化利润、现金流、产能、风险、覆盖率、最小获授质量、权重、合并容差和例外。
10. StrategyReadinessAssessment 分项检查规则、预审、响应、成本、政策、市场、数据用途、模型和场景协议；输出 READY/CONDITIONAL/NOT_READY/UNKNOWN。
11. 将采购规则静态不通过与公司商业基线不通过作为不同子结果和不同 UI 文案。

必须发布事件：EvidencePublished/Revoked、EvidenceMatchReviewed、ResponseProfilePublished、PrecheckAssessed、ConditionChanged、CostBaselinePublished、CommercialPolicyPublished、ReadinessAssessed。

验收：无证据自动满足为 0；证据到期只传播到实际依赖匹配；财务独立复算在规定精度内 100% 一致；maker-checker 负向用例全部拒绝；预审结果不因成本或市场变化而变化；成本/政策变化只使策略链路过期。

禁止：把商业拒绝写成投标无效；把资格当评分；自行生成竞对概率或正式推荐。

---

## 14. 成员 5 提示词：竞对、市场先验、隐私与模型治理

你负责 FR-05、FR-12 和 FR-13，独占 `market/**`、`model_governance/**`、`workers/provider/**`、`governance/privacy_external/**` 及前端对应 feature。

目标：建立合法、可审计、可撤销的 0–N 竞对与市场输入，并实现“平台限定 Provider/模型，商家自行配置 API Key，服务端受控调用”的外部生成式模型能力。项目不部署本地 LLM；API Key 自助配置不能绕过隐私、跨境、用途和模型治理 Gate。

必须完成：

1. Competitor 主体、来源、资料审核、用途、期限、个人信息基础和数据等级；主体不明资料保持隔离。
2. 主体解析与去重；同一企业不能同时作为实名竞对和未知进入者。
3. CompetitorProfile 只表达参与、报价、潜在证据/响应、主观变量、有效性假设、覆盖、偏差、漂移和数据质量；客观得分留给裁判。
4. MarketPriorVersion 和 UnknownEntrantProfileVersion 的创建、审核、发布、有效期和失效。
5. 0 个实名竞对也能建立未知进入者场景；冻结实名参与集合与未知进入者数量的联合分布、相关结构、主体去重和版本协议，不能默认我方是唯一有效参与者。
6. 无批准竞对画像或市场先验时向成员 6 返回 `PRESSURE_ONLY`，明确禁止正式概率分母与 Eligibility。
7. PersonalDataProcessingRecord、LegalBasisEvidence、NoticeConsentRecord、PIA、CrossBorderTransferAssessment、ProviderProcessingPolicyVersion、DSRPolicyVersion、DataSubjectRequest、ConsentWithdrawal、IncidentPolicy/Event 全流程；真实个人信息前必须有 APPROVED/CURRENT 的 DSR Policy 与适用 PIA。ProviderPolicy Schema 强制保存 Provider 法人/API 域名、获批 provider_model_id/能力、用途、数据等级、区域、全部子处理者、`training_use=DISABLED` 及 opt-out/合同证明、精确保留天数、协议/安全措施、终止返还/删除和删除证明；zero-retention 声明只是一项证据，不得绕过其他 Gate。目录新增模型或切换 model ID/能力必须新建/重批 Policy，不能沿用旧批准。
8. 建立版本化 `ProviderCatalogVersion`：固定 adapter、受支持模型、API base domain、区域、能力、最大输入、超时和允许用途；成员 5 是目录数据/API 唯一 writer，成员 1 只把已发布目录同步为 egress 网络策略。商家只能选择 catalog 项并填写 Key；自定义域名先走成员 1/5 联合 ADR 和安全评审，不能把任意 URL 当 OpenAI-compatible endpoint。
9. 独占 `AIProviderConfigurationVersion`、`ProviderInvocationRecord`、Provider 配置 API 业务 handler 与 settings feature；通过成员 1 仅授予本模块的 SecretStorePort 保存 API Key，通过低层 ProviderEgressPort 调用。所有 credential/test/egress handler 声明并消费成员 1 的 `RequireBYOKSecretGate`，settings 页面只读取公共 Gate hook 来禁用/启用表单、按钮并展示原因；不得复制或改写 Gate 判定/middleware。Key 输入 write-only，任何查询只显示末四位/指纹及 activation/credential/provider_health/validity 正交状态；成员 5 也不得读取已保存明文。ACTIVE 配置轮换必须创建 DRAFT successor：新 Key 从 UNVERIFIED 经连接测试转 VALID/VERIFIED后原子切换 current 指针；测试失败不影响旧 ACTIVE。PLANNED 模式保留有界 in-flight/drain/回滚窗口，COMPROMISE 模式立即停旧且禁止回滚。
10. 配置激活采用两阶段：`TENANT_AI_ADMIN` 先通过第 20.2 节，再创建配置、写入 Key并通过第 20.4 节固定合成连接测试；隐私/数据责任人独立批准当前 ProviderPolicy、PIA 与跨境适用性。已验证处理区域明确不跨境时只允许 `NOT_REQUIRED/CURRENT`，涉及或无法排除跨境时必须 `APPROVED/CURRENT`；UNKNOWN/EXPIRED/REJECTED 阻断。事务内全部通过后才 ACTIVE，任一撤销/到期/Key 失效立即 SUSPENDED 并传播下游适用性。
11. 对其他领域独占暴露异步 `GovernedModelInvocationPort`；请求必须是 typed purpose、project/unit、input asset refs、prompt template/output schema 与预算类别，不接受 API Key、任意 URL 或绕过 Gate 标志。submit 在同一事务创建 PostgreSQL Job、QUEUED `ProviderInvocationRecord` 与 outbox，返回 job_id/invocation_id；`worker-provider` 消费专用队列，在真正出网前重新原子执行第 20.3 节，转 RUNNING 后才调用低层 egress，完成后写终态/派生资产。每次调用绑定 tenant、purpose、project/unit、配置版本、处理基础、输入资产、prompt template、provider/model、参数、预算、超时、输出资产和删除/保留策略；只发送最小必要内容，默认去标识、裁剪无关页和移除隐藏元数据，禁止整库/整项目无选择外传。连接测试可在严格短超时下同步执行，但仍只能走第 20.4 节。
12. Prompt、模型响应、错误载荷、缓存和 Provider 返回的 request id 都登记为派生资产/副本；日志只留脱敏指标。Provider 429/401/403/超时/5xx/配额耗尽使用稳定原因码、有限重试和熔断，不得自动换用另一个商家的 Key 或 Provider。取消在发送前可进入 CANCELLED；请求已发出后只能 best-effort 标记取消意图，不能声称已撤回 Provider 处理，返回内容按政策处置且历史 attempt 不覆盖。重试只创建新 attempt。
13. MVP-B 前建立 Dataset、FeatureSchema、外部 ModelArtifact 引用、Approval、Deployment/Provider 配置映射、Monitoring、Incident、Rollback；保存 adapter 代码/镜像摘要、Provider/模型 ID、API 版本（若可得）、提示词模板、参数、依赖锁、随机性和数值协议。不能声称第三方黑盒模型逐位复现，必须保存足够证据并由确定性复核兜底。
14. Pilot 再建立 Calibration、前瞻评估和漂移 Gate。只有审查结果模型和第一候选校准两个独立产物均获批，才向前端开放单点第一候选概率；上下界不得直接校准成唯一概率。
15. 无配置、未激活、撤销或外部服务不可用时，人工录入/规则模板路径完整可用；生成式模型结果永远只是待复核候选，不能直接改变正式规则、证据、评分或排名。
16. 独占 `ProviderReplicaDeletionAdapter`：对 Provider 端提示词、响应、文件、缓存和日志副本按其已批准能力请求删除/到期处置并返回可验证 `DeletionReceipt`；正常撤销时只能使用 `credential_usage_scope=DELETION_ONLY` 的短期、精确删除 endpoint 授权，禁止推理/连接测试；收齐 receipt 后才通知成员 1 毁本地 secret。不支持即时远端删除时，激活前必须有精确保留期限和到期删除证明机制。COMPROMISE 时不得复用泄露 Key，必须改用独立管理凭据、商家控制台或合同支持渠道。逻辑访问先立即断开，但 `DeletionJob` 必须保持 `PENDING_EXTERNAL/RUNNING` 直至到期并取得证明；超期、失败或无法证明都进入重试/升级，绝不能标记 COMPLETE。成员 5 只发布 `ProviderReplicaDeletionReceiptProduced`，全局 `DeletionCompleted` 仍只能由成员 1 在聚合所有必需 receipt 后发布。

必须发布事件：CompetitorProfilePublished/Quarantined、MarketPriorPublished/Expired、UnknownEntrantPublished、ProviderCatalogPublished/Revoked、ProviderConfigurationSuccessorCreated/Superseded、ProviderCredentialSet/Rotated/UsageRestricted/LocalReferenceDestroyed、ProviderRemoteCredentialRevocationReceiptProduced（仅 Provider 支持时）、ProviderConfigurationVerified/Activated/Suspended/Revoked、ProcessingAuthorizationWithdrawn、ProviderPolicyApproved/Expired/Revoked、ProviderInvocationQueued/Started/Succeeded/Failed/Blocked/TimedOut/Cancelled、ProviderReplicaDeletionReceiptProduced、ModelDeploymentActivated、ModelPolicyEffective、ModelRolledBack。

验收：竞对资料来源/用途/处理基础缺一即阻断；主体去重及联合采样金标通过；商家可完成配置、测试、激活、后继版本原子轮换、暂停和撤销；轮换失败不影响旧 ACTIVE，成功仅切一次 current，旧/新 in-flight 归属、PLANNED 回滚窗口和 COMPROMISE 紧急停用均通过并发测试；API Key 不出现在 GET、数据库业务表、前端状态、localStorage、日志、审计、错误、导出或备份清单；跨租户 Key/配置/调用记录 100% 拒绝；成员 2/3/4/6/7 对低层 SecretStore/EgressPort 的直接访问全部拒绝，所有生成式任务均可追溯到 GovernedModelInvocationPort、Job 和唯一 InvocationRecord；`worker-provider` 重启、Redis 消息丢失/reconciliation、发送前/后取消、超时、有限重试和重复投递测试不丢状态、不重复发布结果；仅批准 Provider 域名可出网，SSRF/DNS rebinding/重定向测试全部阻断；目录/egress hash 不一致失败关闭；本地 reference 销毁、Provider 端 Key 撤销和 in-flight 请求三种状态不混淆；Provider 副本删除成功、失败重试、不支持删除、receipt 缺失和全局完成聚合演练通过；断网或 Provider 故障时人工路径可用；未满足校准门槛时 UI/API 均无单点概率。

禁止：把文件数量当画像置信度；从画像直接抽客观总分；在浏览器调用 Provider；把 API Key 放进 `.env`、数据库业务字段或日志；允许商家任填 URL；调用未批准配置；为 Demo 伪造市场先验或模型结果。

---

## 15. 成员 6 提示词：场景、确定性裁判、多目标优化与推荐资格

你负责 FR-06、FR-07、FR-08 和 FR-09a，独占 `simulation/**`、`workers/simulation/**` 和前端 simulation/eligibility feature；你是 RecommendationEligibilityVersion 与 SimulationAssessmentSnapshot 的唯一 writer，只读成员 7 的当前 RiskAcceptanceVersion。

目标：实现可复现、无样本内选择偏差、诚实表达不确定性的报价策略仿真。你只能消费已发布且准入的上游版本，不得自行修补规则、证据、成本或市场数据。

必须完成：

1. DecisionBaselineVersion 原子冻结规则、响应、成本、政策、竞对/先验/未知、模型、as-of 时间和 typed input manifest/hash。
2. CandidateSearchSpaceVersion 纳入报价上下限、精度、规则/舍入/税/异常低价跳点和商业边界。
3. 搜索场景集与独立评估集在搜索前冻结，种子独立；所有候选共享搜索集和共同随机数。
4. 概率场景与压力场景完全分离；压力权重永不进入概率分母。
5. StaticCandidateValidation 分开输出采购规则静态结果和商业基线结果。
6. Sampler 按成员 5 冻结的联合分布共同生成实名参与集合、未知进入者数量、报价、潜在证据/响应、主观变量和公共评委变量；Referee 确定性执行全部客观规则。
7. 每场景输出 awardable、eligible_for_award、四态有效性、全部合法待审查结果；第一候选指标必须包含 eligible_for_award。
8. 实现 Coverage、N_eff、部分识别上下界和两端 MC 置信区间；所有正式概率/经济/风险加权共用冻结 K_calc 和同一分母。
9. 候选错误不得删场景；基础设施失败有限重试后整批失败。
10. 精确待审查组合枚举设协议上限；超限采用有证明的保守界或 INDETERMINATE。
11. 搜索只使用搜索集；候选锁定后用独立评估集复算。评估失败不得反馈当前优化器继续调参。
12. 0–4 个方案：综合平衡、排名下界优先、第一候选经济代理/获授模型后决策价值优先、尾部保护。未批准代理 CVaR 前，尾部保护只作水印探索。
13. 压力测试覆盖成本上浮、竞对降价、响应提升、未知进入、证据失效和规则跳点。
14. 完全链接合并，防止链式合并；无可行集合只输出原因和补救。
15. RecommendationEligibility 聚合当前预审、就绪、静态、场景、条件和风险接受，不包含商业审批。
16. MVP-B 只生成水印 SimulationAssessmentSnapshot，不暴露审批创建入口；成员 7 只能读取/展示该对象，不得创建同名快照。
17. 逐项实现并测试 PRD V1.3 §10.1–10.7：`B0/B_proxy/B_cal`、重要性采样 `p/g`、共同 `K_calc` 分母、Coverage/N_eff、`P-/P+`、零分母 UNDEFINED、`Q_award`、利润/NPV/投标决策价值/CVaR/风险效用、代理经济上下界的完整乘积和多目标 argmax/argmin；变量字典、标准化边界和权重未冻结时阻断正式运行。

必须发布事件：DecisionBaselineFrozen、ScenarioSetsFrozen、SimulationStarted/Failed/Assessed、StrategyPlansFinalized、EligibilityAssessed、SimulationSnapshotCreated。

验收：裁判有效性、候选产生、异常低价、舍入和并列金标 100%；可枚举场景与手算一致；正式方案硬约束违规 0；压力进入概率分母 0；相同冻结环境可复现；Coverage≥99.5%；N_eff 达协议阈值；排名区间端点 MC 95% CI 半宽≤1个百分点；10,000 eval 场景、A+最多10竞对单候选 P95≤60秒，200候选搜索 P95≤5分钟。

Hypothesis 必测性质：awardable=false 不记第一；无效候选不推荐；零分母返回 UNDEFINED；空集合不调用 argmax；待审查上下界有序；评估集不进入搜索；候选错误不改变共同分母；压力集权重不污染概率。

禁止：直接读可变业务表；混用代理和校准指标；把部分识别区间转为单点概率；把排名第一频率称为获授概率。

---

## 16. 成员 7 提示词：审批、报告、提交、结果与生命周期闭环

你负责 FR-09b 和 FR-10，独占 `approvals/**`、`reports/**` 及前端 approvals/reports/outcomes feature。你是 RiskAcceptanceVersion、PrecheckReportSnapshot、DecisionReportSnapshot、审批和提交对象的唯一 writer；你只读成员 6 的 SimulationAssessmentSnapshot，不得自行重算或再次生成它。你从 MVP-A 参与报告交付，但 Pilot Gate 前不开放审批。

目标：把合格策略安全地变成不可变影子审批包、审批决定、提交授权记录、外部提交核验和结果复盘，同时保持所有历史追加不可变。

必须完成：

1. Pilot Entry Gate 后，仅允许 ELIGIBLE、ELIGIBLE_WITH_ACCEPTED_RISK 或政策允许的 ELIGIBLE_WITH_CONDITIONS 冻结审批包。
2. ApprovalPackageSnapshot 包含输入清单与哈希、方案、独立评估、压力、限制、条件、风险接受和报告草稿，创建后不可变。
3. ApprovalWorkflowVersion 定义顺序、并行/串行、金额/风险阈值、角色、maker-checker、超时和升级。
4. Request、WorkflowInstance、StepInstance、DecisionEvent 分离；PENDING/RUNNING/CANCELLED/TIMED_OUT 不能写入最终决定对象。
5. 送审和每步决定在事务内检查包 CURRENT、条件、截止、权限和未发生上游失效。
6. 上游变化使包 INVALIDATED，并原子终止进行中的审批；重新生成新包，不覆盖旧决定。
7. 条件关闭分为“仅证明既有事实”与“改变计算输入”；你只能调用成员 4 的 Condition command port，不能直接写表；后者强制重新审批。
8. SubmissionAuthorizationVersion 使用 ACTIVE/BLOCKED/EXPIRED，并带 `mode=SHADOW`；Pilot UI/报告显示影子授权，不产生可被当作正式提交许可的输出。
9. 按阶段生成：MVP-A `PrecheckReportSnapshot`、Pilot `DecisionReportSnapshot`；MVP-B 只读取成员 6 的 `SimulationAssessmentSnapshot` 并负责受权展示/下载，不创建别名对象。不得提前开放完整报告。
10. SubmissionRecord 从 DRAFT 开始，保存平台、提交人、时间、时区、回执、实际报价、响应和 SubmissionArtifact 文件清单/哈希；冻结后与审批包原子比对，VERIFIED 必须双人且信息齐全。
11. DRAFT、DECLARED、VERIFIED、MISMATCH、FAILED、WITHDRAWN 状态严格；失败或不一致后的重试为新 attempt，重新核验授权。
12. ProcurementOutcome 保存取消/失败、我方有效性、分项分、排名、获授/落标/否决、公开竞对结果、来源和核验状态。
13. 冲突来源不覆盖，通过追加 conflict-resolution 事件处理；仅 VERIFIED 且预测早于结果公开的结果进入正式回测。
14. 报告撤回、失效和替代使用追加事件；旧下载链接根据权限显示“已撤回/不可继续使用”，不静默替换文件。
15. 你把 NO_BID、WITHDRAWN、CANCELLED、SUBMISSION_FAILED、AWARDED、LOST、DISQUALIFIED、PROCUREMENT_FAILED、CLOSED、ARCHIVED 和 REOPENED 作为受控 transition command 发送给成员 2 的生命周期 port；成员 2 是唯一事件追加者。
16. 风险接受与方案生成分权：记录范围、理由、独立授权人、有效期、撤销和 maker-checker；成员 6 只能读取当前版本。

必须发布事件：RiskAccepted/Revoked、ApprovalPackageFrozen/Invalidated、ApprovalRequested/Decided、SubmissionAuthorizationCreated/Blocked、PrecheckReportCreated、DecisionReportCreated/Revoked、SubmissionDrafted/Declared/Verified/Mismatch/Failed/Withdrawn、OutcomeVerified/Conflicting；生命周期变化只发布 `DecisionUnitTransitionRequested`，由成员 2 校验后追加 `DecisionUnitLifecycleAdvanced`。

验收：审批与上游失效并发时只有一个原子结果成立；重复幂等键只产生一个请求或决定；maker-checker、超时、条件过期、包失效和截止到达全部失败关闭；报告包含完整输入哈希与免责声明；Pilot 全链路始终带 SHADOW 水印；完整报告生成 P95≤30秒。

禁止：自动调用采购平台；修改历史审批决定；把商业拒绝改写成投标无效；在 MVP-B 开放审批入口。

---

# 第三部分：集成、测试与验收提示词

## 17. 集成顺序

### M0：迁移与契约基座

成员 1 完成本地骨架、身份、租户、审计/治理、Job/outbox、Pydantic stub/OpenAPI、生成客户端和 Demo app Shell/空挂载拆分。全员共同完成术语、状态、字段级接口和追踪矩阵；其他成员只使用生成客户端在自己的目录开发，不各建 mock Schema。

M0 验收后才允许连接真实模块。现有测试中固定断言“稳妥中标、模拟胜率、期望利润”等旧文案的部分必须先改为 PRD V1.3 合规语义。

### MVP-A：预审闭环

1. 成员 2 提供 Project/DecisionUnit、Scope、Regime、RuleSet；
2. 成员 3 提供安全摄入、扫描、ParseJob 和派生资产；
3. 成员 4 提供证据、响应画像、Precheck、成本、政策和 Readiness；
4. 成员 1/3/5 分别按单写者边界通过权限/审计治理、文件副本 adapter、用途/PIA/DSR/事件 Gate；
5. 成员 7 从本阶段接入，只读取 PrecheckAssessment 生成唯一 `PrecheckReportSnapshot`；不开放审批，也不输出竞对概率建议。

### MVP-B：仿真闭环

1. 成员 5 发布合法竞对/先验/未知进入者和批准模型；
2. 成员 6 冻结基线、搜索集和独立评估集；
3. 完成静态校验、采样、裁判、区间、优化、压力和合并；
4. 如存在可接受风险，成员 7 仅开放 RiskAcceptance 创建/撤销，由独立授权角色处理；本阶段仍不开放审批；
5. 成员 6 读取当前风险接受，完成 RecommendationEligibility；
6. 只输出由成员 6 冻结的带水印 SimulationAssessmentSnapshot，不开放审批。

### Pilot：影子决策闭环

成员 7 接入不可变包、影子审批、条件、影子授权、报告、人工外部提交登记、双人核验、结果和前瞻评估。整个 Pilot 不得被标记为 Production 准入已经完成。

---

## 18. 每个功能的统一完成定义

每一个功能必须同时具备：

- 正常流程；
- 条件/人工复核流程；
- 空状态；
- 加载和长任务进度；
- 可重试与不可重试错误；
- 取消；
- 无权限与跨范围拒绝；
- 过期、失效和并发版本冲突；
- 审计事件；
- 上游依赖和失效传播；
- API Schema 和生成客户端；
- 单元、接口、契约、E2E 和权限负向测试；
- traceability 行；
- 中文可操作错误文案；
- 可访问性和响应式验收。

没有以上任一项，功能不得标记完成。

---

## 19. 强制测试矩阵

### 19.1 业务与算法

- 制度、规则、公式、边界、舍入、并列、候选人产生、同品牌和异常低价金标；
- RuleClause → Requirement → EvidenceMatch 强制项全覆盖；
- 0 个竞对、1 个竞对、10 个竞对、未知进入者和主体去重；
- 实名参与集合与未知进入者数量的联合采样、相关结构、去重与版本复现；
- awardable=false、有效供应商不足、全待审查组合、规则跳点；
- 搜索/评估隔离、共同场景、共同分母、Coverage、N_eff 和 MC 区间；
- 零分母 UNDEFINED、空可行集合、候选自身错误、整批基础设施失败；
- 方案完全链接合并，防链式首尾越界；
- 商业不通过与采购规则无效不混淆；
- 条件只补既有事实与条件改变输入的分支；
- 审批期间上游变化；
- 实际报价/文件哈希与审批包不一致；
- outcome 未核验、冲突和追加解决；
- 相关上游变化传播，无关变化和草稿不传播。
- `B0/B_proxy/B_cal`、重要性权重 `p/g`、Coverage/N_eff/P-/P+、Q_award、零分母、利润/NPV/E[Y]/CVaR/代理完整乘积逐项与 PRD §10 手算一致。

### 19.2 安全与隐私

- 跨租户/数据域/项目/单元的 CRUD、对象、搜索、向量、缓存、队列、导出和血缘请求 100% 拒绝；
- EICAR、类型伪装、宏、目录穿越、zip bomb、递归归档、加密文件、超时和超资源；
- 审计 sink 失效时敏感操作 fail closed；
- 默认拒绝所有外部处理；第 20.2 节密钥安全 Gate 是任一真实 Key/出网的前置；业务调用的唯一例外是当前 tenant 的 ACTIVE Provider 配置通过第 20.3 节逐次 Gate 后由 `provider-egress-gateway` 发起；激活前只允许第 20.4 节不含任何业务/用户数据的固定合成 `CONNECTION_TEST`；
- API Key 明文不得出现在 GET/列表、业务数据库、前端状态/localStorage、环境变量、Git、镜像、日志、trace、审计正文、错误、导出或备份清单；验证写入、遮罩、原子轮换、撤销、毁钥和 OpenBao 恢复；
- Key 撤销/配置撤销先阻断新业务调用，再以 DELETION_ONLY 短期能力完成 Provider 远端副本处置并聚合 receipt，最后毁本地 secret；本地毁钥不得充当远端 receipt。COMPROMISE 立即远端撤销且不得复用泄露 Key，删除改走独立渠道；
- OpenBao 真实模式非 dev、root token 已撤销/离线双控封存、2-of-3 unseal/recovery 份额分离、API write-only 与 egress exact-read 短期策略生效；seal、过期 token、越权 path/version、root/share 泄漏扫描和恢复演练全部失败关闭；
- 跨租户 Provider 配置、secret reference、调用记录和费用 100% 拒绝；系统/平台管理员也不能读取商家 Key 明文；
- `ProviderCatalogVersion` 的 PLATFORM scope 使用独立 RLS：租户只能读 PUBLISHED/CURRENT 最小投影且不能写，平台角色不能借 catalog 权限读取任何租户配置/Key/调用正文；NULL tenant/data-domain 仅此显式对象允许；
- provider-egress SSRF、IP literal、回环/私网/元数据地址、DNS rebinding、未批准 redirect、TLS 主机名/证书错误全部阻断；正式任务只允许 ACTIVE 配置的 Provider host/model，连接测试只允许发布目录中的同一 host/model 和固定合成载荷；
- 测试 401/403/429、超时、5xx、配额/预算耗尽、Key 轮换/撤销与 Provider 故障；有限重试、熔断和人工降级不串用其他 tenant 的 Key；
- DSR、撤回、PIA、跨境和事件桌面演练；
- ProviderPolicy 的精确 model ID/能力、`training_use=DISABLED` 证明、子处理者和保留/删除字段逐项匹配；目录新增/切换模型不得沿用旧 Policy；跨境 `NOT_REQUIRED/CURRENT` 正向用例及 UNKNOWN/EXPIRED/REJECTED 阻断用例；
- BYOK Gate 已通过但 `REAL_DATA_MODE` 失败/未知/过期时，真实资料、个人信息和 UNKNOWN 分类调用全部在出网前阻断；完全合成/经验证不可逆匿名调用及固定连接测试按独立 Gate 可用；
- 正常删除、单副本失败、保全、解除保全、备份恢复墓碑重放；
- Provider 外部副本立即删除、按精确保留期到期删除、receipt 缺失/伪造/超期和不支持删除路径；未收齐证明时 DeletionJob 不得完成；
- secret、依赖、镜像、SAST 和本地主机端口扫描；
- PostgreSQL/MinIO/报告/快照/导出/备份的密文验证，KEK/DEK 隔离、轮换、毁钥和恢复时密钥可用性；
- 系统管理员默认不能查看正文/成本；保全解除与批量导出双人控制；Gate waiver/人工覆盖追加记录；
- 管理员、法务、财务、审批角色 MFA；
- 日志/指标/trace 不泄露正文、个人信息、成本、提示词或模型响应。

### 19.3 局域网、自托管与受控 Provider 出网

- 至少两台不同局域网设备通过 `biaice.local`、受信本地 CA、正确 SAN/issuer 与 MFA 成功登录并并发操作；七台设备均有证书安装/吊销说明；
- Web、SSE/轮询、上传和下载均走 LAN；浏览器不直接访问任何 Provider；
- 刷新、API/Worker/Redis/PostgreSQL 重启后数据和 Job 可恢复；
- 断互联网后非模型核心流程和人工录入仍可运行；模型任务明确显示 Provider 不可达，不伪造结果；
- 浏览器、DNS、代理和防火墙日志除可追溯的批准 Provider 调用外，无 CDN、字体、analytics、chatgpt.site、云 OCR 或其他公网请求；每次允许出网都能关联 tenant/config/invocation/audit id；
- CSP 默认 `self`，不把 Provider 域名加入浏览器 CSP；本地法规、字体、图标、ClamAV 签名和 OCR 资产均已预装；
- gateway 是唯一 LAN 暴露入口，不启用 UPnP 或公网映射。

### 19.4 可访问性与前端

- 按 WCAG 2.2 AA 验收；Tab 使用正确语义、aria-selected 和键盘切换；
- 进度条具备 progressbar 属性，状态变化用 aria-live；
- 模态框支持焦点锁定、Escape、打开聚焦和关闭后焦点恢复；点击内容不关闭，仅真实 backdrop 关闭；
- 图表提供数据表或文本摘要；
- 状态不只依赖颜色；正文对比度 ≥4.5:1，UI/大字 ≥3:1，触控目标原则上 ≥44×44px；
- 支持 reduced motion、200%/400% 缩放与 reflow、桌面/平板/手机和可聚焦横向表格滚动；
- 提供 skip link、landmark、正确标题层级、表单错误摘要/字段关联、Dropzone 键盘等价、隐藏 file input 的可见焦点代理、表格 caption/scope；
- axe serious/critical 为 0，并完成全键盘人工测试；
- 未通过 Gate 的工作区可查看原因，但正式动作不可用且不能显示默认 GO。

### 19.5 观察指标与本地可观测性

- 成员 1 定义本地事件信封、去标识聚合任务和管理页；成员 2–7 在各自业务事件中填充指标所需字段，禁止把正文、个人信息、成本明细或原始提示词写入 telemetry。
- 按 DecisionUnit、阶段和冻结协议聚合：规则核对工时、缺口关闭周期、审批周期、报告采用率、实际贡献利润偏差、No-Bid 质量、数据新鲜度和用户纠错率；中标率不得作为唯一成功指标。
- 观察指标不单独作为 Stage Gate，必须与强制指标分栏展示，并带口径、样本窗口、更新时间、缺失率和适用 `LoadProfileVersion/EvaluationProtocolVersion`。
- 所有指标和仪表板完全本地；Prometheus/Grafana/Loki 未启用时核心业务不受影响，但审计事件不能因此降级。

---

## 20. PRD 阶段验收门槛

### 20.1 `REAL_DATA_MODE` 不可绕过启动 Gate

只有以下全部为机器可验证的 PASS，API/Worker 才允许以真实数据模式启动；任一 UNKNOWN/FAIL 均拒绝启动，且不得 waiver：

1. `biaice.local` TLS、正确 SAN/issuer、Secure Cookie、管理/法务/财务/审批 MFA；
2. tenant/data-domain/project/unit 在 PostgreSQL、MinIO、全文/向量、两个 Redis、队列、缓存、血缘、导出和日志上全部隔离；跨范围负向测试 100% 拒绝；
3. 主机磁盘、PostgreSQL/MinIO 敏感载荷、报告/审批快照、导出和备份加密；OpenBao KEK 与数据分离，DEK 轮换/销毁/恢复验证通过；OpenBao 非 dev、已完成 2-of-3 unseal/recovery 分持、root token 撤销/离线双控封存、API write-only/egress exact-read 短期策略和审计，secret/root/share 未进入 Git、Compose、环境变量、镜像或日志；
4. 独立 append-only 审计、可信时间、哈希链/锚点完整；审计 sink 故障时敏感操作 fail closed；
5. quarantine、MIME、ClamAV、宏/脚本、压缩保护、受限解析和本地 OCR Gate 全过；
6. APPROVED/CURRENT 的处理基础、事件策略及演练；涉及个人信息时另有适用 PIA、DSRPolicyVersion、告知/同意/撤回与 DSR 演练；
7. 保留/到期、LegalHold、全副本删除、receipt、墓碑、加密备份恢复与“删除数据不复活”演练通过；
8. 默认拒绝公网；只有 `provider-egress-gateway` 具备出网能力。第 20.2 节未通过时不得接收真实 Key或启用出网；正式模型任务必须使用 ACTIVE 配置；未激活时唯一例外是第 20.4 节固定合成 `CONNECTION_TEST`，不得包含用户、项目或业务数据。浏览器、Web、API、普通 Worker 和其他容器无直接公网访问；
9. SAST、secret、依赖、镜像和端口扫描无 Critical；RCE、跨租户和数据外泄类 High 不可豁免；
10. 系统管理员默认无正文/成本权限，maker-checker、保全解除双控和批量导出双控测试通过；
11. 加密备份、密钥恢复、服务重启、worker/Redis/数据库故障、事件桌面演练与恢复顺序验证通过；
12. 所有结果绑定冻结 `LoadProfileVersion`、GateAssessment 和审计证据。

`REAL_DATA_MODE` 允许在没有 API Key 的情况下启动并处理真实数据，但所有生成式模型按钮必须禁用或走人工降级。它不等于外部模型调用授权。

### 20.2 `BYOK_SECRET_GATE` 密钥安全 Gate

API Key 本身属于真实高价值 secret，不因业务数据是合成的而降级。任何真实 Key 写入、读取供 egress 使用、连接测试或 Provider 出网前，必须先取得独立、机器可验证且 CURRENT 的 `BYOK_SECRET_GATE=PASS`；它不要求先启用 `REAL_DATA_MODE`，但至少同时满足：

1. 访问固定 `https://biaice.local:8443`，证书/issuer/SAN 受信，Secure/HttpOnly/SameSite Cookie、CSRF 防护、`TENANT_AI_ADMIN` MFA 和会话重认证通过；HTTP 来源在解析 credential body 前即拒绝；
2. OpenBao 非 dev、已正确 seal/unseal，2-of-3 份额分持，root token 已撤销或离线双控封存；API write-only、egress exact-read 的短期 AppRole/token 和 OpenBao audit device 均健康；
3. tenant/data-domain、角色、配置/secret path、credential version 和审计范围隔离通过；系统/平台管理员、其他租户和其他领域模块都无法读取 Key；
4. ProviderCatalog version/hash 与 egress allowlist 一致，TLS/SSRF/DNS rebinding/redirect/私网与 metadata IP 防护、限频、预算和唯一出网主体已验证；
5. Key 不进入业务库、前端状态/localStorage、环境变量、Compose、Git、镜像、日志、trace、错误、导出或普通备份清单；泄漏扫描、seal/过期 token/越权 path 负向测试与恢复演练通过；
6. `StageGateAssessmentVersion` 保存证据、时间、负责人和 hash，`waiver_policy=PROHIBITED`。Gate 变为 UNKNOWN/FAIL/STALE 时立即禁用 credential endpoint、连接测试和 provider-egress，但不影响本地人工/确定性流程。

HTTP/OpenBao-dev profile 只能展示空配置或不保存、不出网的假 Key fixture；UI 必须显示“安全密钥 Gate 未通过”，后端和网络层也必须独立拒绝，不能只靠隐藏按钮。

### 20.3 每次外部模型调用 Gate

每次调用前必须原子验证，不能只在应用启动时检查：

1. 当前 tenant/data-domain 拥有 ACTIVE/CURRENT 的 `AIProviderConfigurationVersion`，目标 provider/model 与平台 allowlist 一致；
2. `BYOK_SECRET_GATE=PASS/CURRENT`；OpenBao 中对应 credential version 存在，`credential_state=VALID` 且 `credential_usage_scope=BUSINESS_AND_DELETION`，未撤销/过期且属于同一 tenant/provider/purpose；UNVERIFIED/TEST_ONLY 只能进入第 20.4 节连接测试，DELETION_ONLY 只能进入 Provider 副本处置，均不能用于正式调用；
3. 当前用户/Job、项目/单元、purpose、数据分类和模型用途被授权；任一输入资产含真实项目资料、个人信息或不能证明不可逆匿名的数据时，必须额外验证 `REAL_DATA_MODE=PASS/CURRENT`。20.1 未通过时只允许标记为完全合成或经验证不可逆匿名的输入；分类 UNKNOWN 一律按真实数据阻断并返回 `PROVIDER_REAL_DATA_MODE_REQUIRED`；
4. 处理基础、ProviderProcessingPolicy 与适用 PIA 均 APPROVED/CURRENT；已验证处理区域证明不跨境时 CrossBorderTransferAssessment 必须为 NOT_REQUIRED/CURRENT，涉及或无法排除跨境时必须为 APPROVED/CURRENT，UNKNOWN/EXPIRED/REJECTED 一律阻断；Provider 法人/API 域名、精确 provider_model_id/能力、用途、数据等级、区域、子处理者、`training_use=DISABLED` 及 opt-out/合同证明、精确保留天数、协议/安全措施、终止返还/删除及删除证明要求与本次调用逐项匹配；目录新增或切换模型必须重批 Policy，zero-retention 不能替代这些检查；
5. 输入已执行最小化、去标识/裁剪和隐藏元数据清理；禁止发送无关页、其他租户数据或整个资料库；
6. 预算、token、并发、速率、超时和熔断未超限；
7. 审计与派生资产登记可用，能够生成 `ProviderInvocationRecord`、请求/响应哈希及删除/保留任务；
8. egress host、解析后的全部 IP、TLS 证书、redirect 和最终 model 仍匹配已批准配置。

任一失败都不得调用 Provider；返回稳定原因码并提供人工路径。Provider 响应只有在安全扫描/结构校验和人工复核后才能发布为正式上游版本。

必须有逐次负向用例：`BYOK_SECRET_GATE=PASS`、配置 ACTIVE、但 `REAL_DATA_MODE=FAIL/UNKNOWN/STALE` 时，任何真实 asset ref、个人信息或 UNKNOWN 分类都必须在出网前 BLOCKED；完全合成/经验证不可逆匿名的受批用途调用及第 20.4 节连接测试仍可按各自 Gate 运行，不能因此被误阻断。

### 20.4 激活前连接测试 Gate

`CONNECTION_TEST` 是 ACTIVE 要求的前置验证，不属于业务模型调用，也不能复用第 20.3 节的业务资料。只有 `BYOK_SECRET_GATE=PASS/CURRENT` 且以下条件全部满足才允许出网：

1. 请求者是当前 tenant 的 `TENANT_AI_ADMIN`，已完成 MFA，且配置 lifecycle 为 DRAFT、activation_state 为 INACTIVE 或 VERIFIED、credential_state 为 UNVERIFIED 或 VALID、credential_usage_scope=TEST_ONLY；ACTIVE 配置必须先创建 DRAFT successor，不能原地换 Key 后测试；
2. provider/model、API host、adapter 和网络 allowlist 来自同一 PUBLISHED/CURRENT `ProviderCatalogVersion`，catalog version/hash 已与 egress 同步；
3. 请求体不接受 prompt、文件、asset ref、project/unit 数据或自定义 URL；探针由服务端按 adapter 生成固定、公开、完全合成且不含个人/投标信息的最小载荷；
4. egress 授权标记为 `purpose=CONNECTION_TEST`，绑定 tenant/config/credential version/host/model，短 TTL、单次使用；仍执行 TLS、SSRF、DNS、redirect 和精确 secret path/version 校验；
5. 使用独立的低 token/费用/并发/频率上限，记录审计和 `ProviderInvocationRecord`，响应仅保留认证、可达性、模型存在和限额的脱敏结果，不保留 Provider 回显正文；
6. 成功时把 credential_state 转为 VALID、activation_state 原子转为 VERIFIED 并更新 provider_health，绝不自动 ACTIVE；401/403 把 credential_state 转为 INVALID，其他失败只更新 provider_health 和稳定 reason code。激活仍必须另行通过 ProviderPolicy、PIA/跨境、训练禁用、预算及独立审批。

必须测试：未登录/MFA 缺失、无 Key、任意 URL、自定义 prompt/文件、目录或 egress hash 失配、跨租户配置、频率/预算超限、SSRF/redirect、401/403/404/429/超时/5xx；全部不得泄露 Key，也不得把 UNVERIFIED、测试失败或仅 VERIFIED 的配置用于业务调用。计划轮换还必须并发验证“旧 ACTIVE 持续服务→后继测试失败不影响旧版本→成功后 current 指针只切一次→旧配置不接新调用→旧 in-flight 仍按旧版本记账→窗口内受控回滚/窗口后销毁”；COMPROMISE 模式验证旧配置立即停用且禁止回滚。

### Demo

- 所有结果明确标记模拟；
- 使用“演示性胜出权重、模拟策略、固定价差演示区间”；
- 上传不暗示已读正文，JSON 不称审批报告；
- 不出现保证性语言。

### MVP-A

- 支持范围内硬条款召回率 ≥98%、准确率 ≥95%、召回 95% CI 下限 ≥95%；
- 原文定位 ≥99%；规则公式、边界、舍入、并列金标 100%；
- 无证据自动判满足 0 次；财务复算 100% 一致；
- MVP-A 基础安全 Gate 全部通过；恶意样本 100% 阻断；
- 跨租户所有存储面负向用例 100% 拒绝；
- 100MB 接收 P95≤5秒，200页文本≤10分钟，200 DPI OCR≤20分钟。

### MVP-B

- 裁判有效性、候选产生、异常低价和并列金标 100%；
- 可枚举场景与手算一致；正式方案硬约束违规 0；
- 压力场景进入概率分母 0；优化 regret 在协议容差；
- 相同冻结环境可复现；Coverage≥99.5%；N_eff 达阈值；
- 排名区间端点 95% MC CI 半宽≤1个百分点；
- 10,000 场景单候选 P95≤60秒，200 候选搜索 P95≤5分钟；
- 未达标只能探索，不能生成推荐资格。

### Pilot

- 预测冻结早于结果公开，训练/测试时间隔离；
- 一个 DecisionUnit 是一个独立评估单元；
- 至少 100 个前瞻独立单元且正负各不少于 20 才可展示点概率；
- Brier 相对基线改善的 95% CI 下限 >0，ECE≤0.08；
- 报价点标准化 MAE 相对预注册基线改善的 95% CI 下限 >0；若采用非劣路径，业务依据和数值 margin 必须在评估前冻结，评估后不得补批；
- 80% 报价区间覆盖 75%–85%，同时报告 CI、WIS 和平均宽度；
- 以 DecisionUnit 为独立单元，按项目/采购人聚类；置信区间使用预注册的 cluster bootstrap。协议预先固定取消/采购失败/缺失结果的处理、样本排除和敏感性分析；
- 完成完整影子采购周期和联合签署；
- 完整影子审批包/报告生成 P95≤30秒。

### Production

- 本七人局域网项目不得自动宣称 Production 达标；
- Production 另需自托管高可用、正式渗透测试、灾备、99.9% 月可用、批准且实测的 RPO/RTO、审计恢复、模型回滚和规模化隔离测试。

---

## 21. 待组长/产品评审决定与默认阻断策略

以下项目不能由成员自行猜测。未决定前采用配置占位并阻断对应正式能力：

1. MVP-A 首个试点制度、行业、采购方式和评标方法；
2. 哪些跨标段规则完全阻断，哪些仅提示；
3. 合法竞对数据和市场先验来源白名单；
4. 预审条件、风险接受和商业审批责任矩阵；
5. 商业政策的覆盖率、最小获授质量、风险阈值、目标权重和合并容差；
6. 未建立获授模型时的经济代理 UI 文案；
7. 首期 Provider/模型 allowlist、各 Provider API base domain、区域/跨境、训练禁用证明、保留、子处理者、预算/配额和是否允许自定义 Provider；真实项目/个人信息的 `training_use=DISABLED` 是不可豁免项，不属于待决策；
8. 副本删除、DSR 和事件响应 SLA；
9. Pilot 独立样本、基线、ECE 和统计非劣协议；
10. Production SLO、RPO、RTO、渗透标准和风险接受权限；
11. 旧 DOC/XLS 是否进入安全支持范围；
12. 安装/维护阶段允许联网的批准源，以及 Provider 调用之外的所有出网封锁策略。
13. M0 中平衡目标变量字典、Z 标准化边界/零方差、精确枚举上限和代理 CVaR 协议；未签署前相关目标仅水印探索。

默认策略：未知、冲突、过期、未审核、未授权、未校准、未通过 Gate 或缺少责任人时，一律失败关闭正式流程，但允许带水印的安全探索或人工录入。

---

# 第四部分：生成后逐步核查记录

## 22. 逻辑自洽与完整性核查

### 第 1 步：来源与版本

- 已以 PRD V1.3 为唯一需求基线；V1.2/V1.1 仅作历史参考。
- 已把前端设计文档降级为交互参考，避免其旧项目级接口覆盖 DecisionUnit 设计。
- 已把 Demo 明确为视觉/fixture，而非正式逻辑。

结论：通过。

### 第 2 步：用户新增的本地部署要求

- 已明确不使用 Sites、Cloudflare Worker Runtime、D1、R2、Wrangler 和 ChatGPT 身份头，同时保留本地 Celery Worker。
- 已给出局域网 Compose 拓扑、唯一入口、Windows 脚本、核心离线降级和“仅批准 Provider 可出网”的验收。
- 已区分开发合成数据模式与真实数据安全 Gate。

结论：通过。

### 第 3 步：七人分工和冲突控制

- 七名成员都有独立功能域、前后端目录、事件、接口、验收和禁止范围。
- 共享根配置、契约、依赖、迁移合并、app Shell 和公共原子 UI 由成员 1 单点负责；feature 页面由成员 2–7 各自负责。
- DecisionUnit 生命周期、Condition、RiskAcceptance、SimulationAssessmentSnapshot、报告及 FR-11 分别只有一个 writer，跨域只走 command port/event。
- 仿真依赖上游冻结契约，审批只消费不可变评估，依赖方向无循环。

结论：通过。

### 第 4 步：FR 功能覆盖

| PRD 功能 | 覆盖章节 | 状态 |
| --- | --- | --- |
| FR-01 | 5.3、8、11 | 完整 |
| FR-02 | 5.2、8、12 | 完整 |
| FR-03 | 5.4、8、13 | 完整 |
| FR-04 | 5.5、8、13 | 完整 |
| FR-05 | 5.6、8、14 | 完整 |
| FR-06 | 5.7、8、15 | 完整 |
| FR-07 | 5.7、8、15 | 完整 |
| FR-08 | 5.7、8、15 | 完整 |
| FR-09a | 5.8、8、15 | 完整 |
| FR-09b | 5.8、8、16 | 完整 |
| FR-10 | 5.8、8、16 | 完整 |
| FR-11 | 6、7、8、10/12、19 | 完整 |
| FR-12 | 3、8、14、19 | 完整 |
| FR-13 | 5.6、8、14、20 | 完整 |

结论：13 个功能域均有页面、后端资源、单一负责人和验收映射；字段级 operation 的冻结被明确设为 M0 业务实现 Gate。

### 第 5 步：关键业务顺序

- 响应画像位于 Precheck 之前，已消除旧版循环。
- Precheck、Readiness、Static Validation、Scenario Assessment、Eligibility、Approval 相互独立。
- 搜索集和独立评估集分离；推荐资格不进入可行集合，避免循环。
- 审批包先冻结，审批时原子复核；上游变化立即失效。

结论：通过。

### 第 6 步：算法歧义处理

- 第一候选指示补入 eligible_for_award；
- 无市场先验固定为压力测试且禁止 Eligibility；
- 未定义代理 CVaR 时只提供水印探索；
- 商业基线结果与采购有效性分离；
- 待审查组合超限返回保守界或 INDETERMINATE；
- Pilot 统一为 SHADOW 模式。
- 已锁定 PRD §10 为算法权威，并补充变量字典、共同分母、重要性权重、财务/风险和零分母金标。

结论：已知高风险歧义均有保守锁定策略；平衡目标变量与代理 CVaR 的产品参数仍在第 21 节失败关闭，不影响 M0。

### 第 7 步：接口一一对应

- 每个 FR 已映射页面、资源、核心对象和负责人。
- 必备资源和关键 operation 已分组列出，补齐上传字节、项目级继承、Requirement、工作流版本、DSR policy、Gate/waiver、治理事件和 SubmissionArtifact。
- traceability 同时做正向“需求必须有接口/测试”和反向“接口必须有需求”检查。

结论：资源级覆盖通过；字段级 `method/path/operationId/schema/permission/UI-field` 必须在 M0 契约 PR 冻结，未冻结的 feature 只能做静态壳，不能开始业务实现。

### 第 8 步：状态与生命周期

- 生命周期、审核、适用性、保留、替代和保全已正交分离。
- 条件阻断阶段、审批状态、提交状态和 DecisionUnit 生命周期按对象域区分。
- No-Bid、撤回、取消、提交失败、获授、落标、否决、冲突和重开均有路径。

结论：通过。

### 第 9 步：安全、删除与本地化风险

- TLS/MFA、复合租户隔离、存储/快照/导出/备份加密、密钥隔离、文件隔离、审计 fail-closed、默认拒绝出网、PIA/DSR、删除全副本和备份墓碑均进入 `REAL_DATA_MODE`；真实 API Key 另由独立 `BYOK_SECRET_GATE` 保护，外部模型再由正式调用/连接测试逐次 Gate 控制。
- 本地部署没有被错误等同于自动安全、自动合规或 Production 高可用。

结论：通过。

### 第 10 步：Demo 与正式版一致性

- 已列出可复用视觉资产和不可复用算法。
- 已处理未上传默认 GO、任意文件触发匹配、固定 B/C/D、假解析、假概率、报告不冻结、流程假 active、五 Tab 到正式路由映射和量化可访问性缺口。

结论：通过。

### 第 11 步：未决项

- PRD 的产品决策、本地化安装边界与算法参数决策已显式列出。
- 未决项统一采用“正式流程失败关闭、可安全探索”的默认策略，不会被成员默认为已批准。

结论：有条件通过；需要组长在对应 Stage Gate 前签署决定，不影响 M0 骨架开发。

### 第 12 步：最终完整性结论

经“需求分析、Demo 审计、架构审计、独立终审、修订后静态复核”五轮检查，本提示词已覆盖：产品边界、框架、本地部署、目录/路由、FR-01 至 FR-13、核心对象、状态、流程、资源级接口、七人单写者职责、冲突控制、集成顺序、测试、安全、性能、Stage Gate、Demo 迁移和未决项。没有阻止 M0 骨架与契约阶段开始的逻辑断裂；M0 字段级契约、试点范围和真实数据 Gate 未签署前，不得宣称业务功能或真实数据模式已完成。

开始业务实现前仍必须由组长完成四项签署：

1. M0 OpenAPI/状态/权限基线；
2. MVP-A 首个试点制度与规则范围；
3. 第 20.1 节 `REAL_DATA_MODE` 全部证据；
4. 平衡目标、代理 CVaR 与 Pilot 统计协议。

---

## 23. 最终交付检查表

- [ ] 七人已确认各自目录所有权和禁止修改范围；
- [ ] 根运行链已彻底移除 Sites/Cloudflare 依赖；
- [ ] Compose 可在组长电脑一键启动并显示 LAN URL；
- [ ] `biaice.local`、本地 CA、七台设备信任、Keycloak issuer/redirect 与证书续期/吊销已验收；
- [ ] HTTP/OpenBao-dev profile 无法接收真实 Key或启用出网；`BYOK_SECRET_GATE` 的 TLS、MFA、非 dev OpenBao、最小权限、审计与泄漏负测全部 PASS；
- [ ] 七个测试账户、角色、MFA 和 maker-checker 用例可用；
- [ ] OpenAPI、错误目录、生成客户端和 traceability CI 已冻结；
- [ ] PRD 13 个 FR 都有 operationId、页面、对象、权限、审计和测试；
- [ ] 所有强制规则都有 Requirement/EvidenceMatch 映射；
- [ ] Demo 误导性文案和默认 GO 已清除；
- [ ] 除 `provider-egress-gateway` 在第 20.2 节 PASS 后执行第 20.3 节 ACTIVE 正式调用或第 20.4 节固定合成连接测试外，无其他外部网络请求；浏览器/Web/API/普通 Worker 无直连；
- [ ] 商家可配置/测试/激活/轮换/暂停/撤销 API Key，且明文从不回显或落入业务库/前端/日志/导出；
- [ ] ACTIVE Key 通过 DRAFT successor 完成 UNVERIFIED→VALID/VERIFIED→原子切换；失败不影响旧配置，PLANNED in-flight/回滚与 COMPROMISE 紧急停用均已测试；
- [ ] 连接测试在 INACTIVE/VERIFIED 配置下只发送服务端固定合成探针，成功不自动 ACTIVE，任意 prompt/文件/URL 或跨租户请求均阻断；
- [ ] ProviderPolicy 精确匹配 model ID/能力、禁用训练证明、区域/跨境、子处理者和保留/删除字段；模型切换必须重批，跨境 NOT_REQUIRED 与 BLOCKED 分支均已测试；
- [ ] `BYOK_SECRET_GATE=PASS` 但 `REAL_DATA_MODE` 非 CURRENT 时，真实/个人/UNKNOWN 数据调用均被阻断，合成或不可逆匿名调用与连接测试未被误阻断；
- [ ] 无 API Key、Key 撤销或 Provider 故障时，模型功能禁用并提供人工降级，非模型核心流程正常；
- [ ] 正式生成式任务由 `worker-provider` 异步执行，Job/Invocation/attempt 可在重启、重复投递、取消、超时和 Redis 消息丢失后正确恢复；连接测试是唯一受限同步例外；
- [ ] Provider 端提示词/响应/文件/缓存副本的处置能力、精确保留期和删除证明已进入 Policy；缺任一必需 receipt 时全局删除不得完成；
- [ ] 正常撤销按“停业务→DELETION_ONLY 远端处置/receipt→毁本地 Key”执行；COMPROMISE 不复用泄露 Key，本地毁钥不冒充远端删除证明；
- [ ] PostgreSQL/MinIO/快照/导出/备份加密，OpenBao 密钥隔离、轮换、毁钥和恢复演练通过；
- [ ] OpenBao 非 dev、2-of-3 份额分持、root token 撤销/离线双控封存、API 只写与 egress 精确短期读取策略及 seal/恢复演练通过；
- [ ] 安全 Gate 前只使用合成/脱敏数据；
- [ ] `REAL_DATA_MODE` 第 20.1 节 12 项全部有机器证据且无 waiver；
- [ ] 搜索/评估集隔离、共同分母和区间语义通过金标；
- [ ] MVP-A/MVP-B/Pilot 输出权限严格分阶段；
- [ ] Pilot 全部审批和授权带 SHADOW 水印；
- [ ] 报告、审批决定和提交/结果历史不可变且可追溯；
- [ ] 局域网两设备并发、重启恢复、备份恢复和删除演练通过；
- [ ] 系统管理员无正文/成本权限，保全解除与批量导出双控通过；
- [ ] 所有未决产品项在对应 Gate 前有签署记录。

---

## 24. 参考依据

- `docs/标策AI_产品需求文档_PRD_V1.3.md`
- `docs/标策AI_前端设计文档_V1.0.md`
- 当前 `app/page.tsx`、`app/globals.css`、`app/layout.tsx` 前端 Demo
- Next.js 官方自托管与 Docker 文档
- FastAPI 官方容器部署文档
- Docker Compose 官方网络文档
- PostgreSQL 官方版本与支持策略
