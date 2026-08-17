# 标策 AI 前端设计文档

> 页面信息架构、状态模型、组件规范、交互流程与正式版接口建议

**版本：**V1.0

**状态：**与 2026-08-11 前端 Demo 对齐

**目标：**帮助产品、设计和研发快速理解并继续实现

**线上 Demo：**https://bid-agent-lab-20260806.breezy-toad-2233.chatgpt.site

> **设计主线**
>
> 第一屏解释“项目规则不是统一表”；第一个工作区完成文件上传与证据匹配；只有通过门槛后，用户才进入多智能体竞标与报价优化。

## 快速索引

- 页面结构：Header + 项目 Hero + 七步流程 + 五个工作区 Tab。

- 首要任务：上传招标方文件和公司材料，执行模拟解析并查看匹配矩阵。

- 决策任务：设置成本、毛利、证据成熟度和竞争强度，运行四方竞演。

- 解释任务：查看规则门槛、评分证据和最终决策报告。

- 当前实现：单页面 React 客户端状态；正式版需拆分领域模块并接入后端任务。

# 1. 设计目标与原则

| **原则** | **前端表达** | **避免** |
|:---|:---|:---|
| 合规优先 | 门槛状态始终先于分数和概率出现 | 只展示“最优报价”而隐藏废标风险 |
| 项目专属 | 项目模板切换后规则、权重、证据与公式同步变化 | 固定通用权重 |
| 可追溯 | 规则和证据显示页码、章节、置信度与版本 | 无来源的模型结论 |
| 渐进披露 | 先给结论与缺口，再展开公式、矩阵和解释 | 第一屏堆满专业细节 |
| 不确定性诚实 | 概率标注“模拟”，异常低价标注“待审查” | 使用保证性语言 |
| 协作导向 | 缺口可以转为待办并回流模拟 | 仅生成静态报告 |

# 2. 信息架构

```text
全局 Header：品牌 / 当前项目状态 / 方法边界 / 报告导出
└─ 项目 Hero：价值主张 + 项目模板 + 文件处理状态 + 上传入口
   └─ 七步流程：解析 → Bid/No-Bid → 资格 → 符合性 → 评分 → 报价 → 报告
      ├─ Tab 1 文档上传与解析（默认）
      ├─ Tab 2 决策驾驶舱
      ├─ Tab 3 规则与门槛
      ├─ Tab 4 评分证据
      └─ Tab 5 决策报告
```

## 2.1 导航规则

- 首次进入默认打开“文档上传与解析”，确保核心能力可被发现。

- Hero 中的“上传并解析招标文件”可回到文档工作区。

- 解析结果中的“将结果带入竞标模拟”切换到决策驾驶舱，并注入门槛和成熟度状态。

- 项目模板切换会重置文件、解析结果、竞标参数和规则版本，避免跨项目污染。

- “方法与边界”使用模态框，持续解释模型与法律边界。

# 3. 页面全局结构

| **区域**  | **内容**                       | **主要操作**         | **状态**     |
|:----------|:-------------------------------|:---------------------|:-------------|
| Header    | 品牌、规则引擎状态、项目编号   | 方法说明、报告导出   | 固定顶部     |
| Hero      | 主张、原则、当前项目模板与预算 | 切换模板、进入上传   | 项目级       |
| Workflow  | 七阶段业务流程                 | 当前版本只做进度表达 | 全局         |
| Tabbar    | 五个工作区及数量徽标           | 切换工作区           | 粘性心智导航 |
| Workspace | 上传、规则、竞演、证据或报告   | 完成具体任务         | 随 Tab 切换  |
| Footer    | Demo 边界与免责声明            | 无                   | 全局         |

# 4. 工作区 1：文档上传与解析

## 4.1 目标

让用户明确区分“招标方规则源”和“本公司证据源”，完成双向上传、解析进度查看、规则确认和证据缺口判断。

## 4.2 页面模块

| **模块** | **说明** | **关键交互** | **验收重点** |
|:---|:---|:---|:---|
| 处理边界提示 | 说明 Demo 不读取真实正文 | 无 | 不能误导用户已真实解析 |
| 招标方文件区 | 主文件、需求、评分办法、附件、更正 | 点击/拖拽、批量、移除 | 显示类型、大小、处理状态 |
| 公司材料区 | 资质、业绩、团队、技术、服务 | 点击/拖拽、批量、移除 | 与招标文件视觉区分 |
| 解析流水线 | 五类文档智能体及进度 | 开始、重新解析、载入演示 | 禁用态和阶段文案准确 |
| 规则提取卡 | 方法、限价、硬门槛、评分结构 | 进入完整规则页 | 显示来源与模拟置信度 |
| 匹配摘要 | 预计是否过门、四类覆盖率 | 模拟补齐、带入竞演 | 强制缺口必须为红色阻断 |
| 匹配矩阵 | 要求、证据、材料定位、状态、置信度 | 横向滚动 | 行级可追溯 |

## 4.3 上传状态模型

```text
EMPTY ──选择/拖拽──> READY ──开始解析──> PARSING ──成功──> DONE
  ↑                         │                    ├─重新解析──> PARSING
  └────移除全部文件─────────┘                    └─规则变更──> STALE

正式版补充：UPLOADING / SCANNING / FAILED / CANCELED / STALE
```

## 4.4 文件交互规范

- 接受 PDF、DOC/DOCX、XLS/XLSX、PNG/JPG；正式版需要展示单文件和项目总量限制。

- 拖入时边框、底色和文案变化；离开或放下后恢复。

- 同名同大小文件在当前 Demo 去重；正式版应以哈希去重并保留版本。

- 解析中禁止重复提交；允许用户继续浏览其他工作区，但项目状态持续可见。

- 失败必须显示可操作原因：格式不支持、密码保护、扫描质量差、解析超时或权限不足。

# 5. 工作区 2：决策驾驶舱

## 5.1 左侧模拟输入

| **输入** | **控件** | **业务含义** | **联动** |
|:---|:---|:---|:---|
| 我方投标总价 | 滑杆 + 数字输入 | 当前拟报价 | 重算价格分、利润、排名和概率 |
| 履约成本 | 数字输入 | 公司内部预计成本 | 重算利润底价和期望利润 |
| 最低毛利率 | 滑杆 | 公司硬约束 | 限定优化搜索区间 |
| 优化目标 | 三段按钮 | 胜率/期望利润/稳健收益 | 改变推荐报价 |
| 证据成熟度 | 滑杆 | 非价格项可验证程度 | 影响我方非价格得分 |
| 市场竞争强度 | 滑杆 | 竞争者报价压力 | 扰动 B/C/D 报价 |
| 门槛开关 | 三组开关 | 资格、★ 条款、低价说明 | 决定有效性与 Bid/No-Bid |

## 5.2 结果层级

- **第一层：**GO / REVIEW / NO BID、建议报价、模拟胜率和预计毛利。

- **第二层：**A/B/C/D 四方卡片，展示报价、有效性、分项得分、排名和胜率。

- **第三层：**报价—胜率—期望利润前沿图，标记当前价和建议价。

- **解释层：**规则裁判执行顺序和每个智能体的淘汰/得分原因。

> **视觉优先级**
>
> 废标/不可行状态必须压过分数与胜率。无可行解时，建议报价、胜率和毛利显示空状态，不伪造数值。

# 6. 工作区 3–5

| **工作区** | **用户问题** | **核心模块** | **主要出口** |
|:---|:---|:---|:---|
| 规则与门槛 | 这个项目到底怎么评？ | 规则画像、资格/符合性清单、评分结构、公式、四方门槛矩阵 | 回到证据或模拟 |
| 评分证据 | 我方为什么能拿这些分？ | 证据成熟度、评分项—材料—页码—预测得分—缺口 | 提高成熟度、创建补缺任务 |
| 决策报告 | 管理层应该如何决策？ | Bid/No-Bid、建议报价、依据、封标动作、风险边界 | 复制摘要、导出 JSON/正式报告 |

# 7. 关键交互流程

## 7.1 首次使用

1.  选择或确认项目模板。

2.  上传招标方文件；如需判断我方资格，再上传公司材料。

3.  开始解析，查看规则提取结果与匹配缺口。

4.  人工确认规则；当前 Demo 可用“模拟补齐缺口”体验闭环。

5.  将解析结果带入竞标模拟，设置成本、毛利和目标。

6.  运行竞演，查看报价前沿并导出决策报告。

## 7.2 缺口闭环

```text
缺口发现 → 指定责任人/截止时间 → 上传补充证据 → 重新匹配
        → 人工确认 → 更新资格/符合性状态 → 自动重跑报价模拟
```

## 7.3 项目切换

切换模板会清空当前文件和解析状态，并恢复该模板默认成本、毛利和报价。正式版若存在未保存内容，应先弹出确认并允许复制为新项目。

# 8. 前端状态与数据映射

| **状态域** | **当前变量/对象** | **影响区域** | **正式版来源** |
|:---|:---|:---|:---|
| 项目 | projectId / ProjectTemplate | 全局规则、模板和竞手 | Project API + RuleVersion |
| 文档 | tenderFiles / companyFiles | 上传区与数量徽标 | Document API + 对象存储 |
| 解析 | parseState / progress / stage | 流水线与结果可见性 | ParseJob 轮询/推送 |
| 证据匹配 | DocumentMatch\[\] / gapsClosed | 覆盖率、门槛和矩阵 | EvidenceMatch API |
| 我方约束 | ourBid / cost / minMargin | 利润、可行区间和优化 | Scenario 草稿 |
| 模型假设 | readiness / marketPressure / objective | 得分、竞手和推荐价 | Scenario 参数 |
| 评标结果 | Evaluation / AgentResult\[\] | 卡片、排名、图表和报告 | SimulationJob 结果 |

# 9. 组件设计

| **组件** | **职责** | **关键 Props/事件** | **复用位置** |
|:---|:---|:---|:---|
| ProjectSelector | 切换项目规则上下文 | value, options, onChange | Hero |
| DocumentDropzone | 文件选择、拖拽、校验、列表 | kind, accept, files, onAdd, onRemove | 招标/公司上传 |
| AnalysisPipeline | 展示任务阶段和进度 | status, progress, stage, agents | 文档解析 |
| RuleSummaryCard | 展示方法、限价、门槛或评分 | label, value, source | 解析/规则页 |
| CoverageMetric | 覆盖率与进度条 | label, value, tone | 匹配摘要 |
| EvidenceMatchTable | 逐条要求—证据映射 | rows, filters, onReview | 解析/证据页 |
| ScenarioControls | 报价与内部约束输入 | scenario, onChange | 驾驶舱 |
| AgentCard | 单个投标智能体结果 | agent, method, rank | 竞演沙盘 |
| ScenarioChart | 胜率/收益前沿 | points, current, recommended | 驾驶舱 |
| DecisionReport | 结论、依据、风险与导出 | report, onExport | 报告页 |

# 10. 视觉系统

| **Token**    | **当前值**                         | **用途**                   |
|:-------------|:-----------------------------------|:---------------------------|
| Ink          | \#1D2B26                           | 导航、主文字、深色决策条   |
| Canvas       | \#F1EEE6                           | 全局暖灰背景               |
| Paper        | \#FFFDF7                           | 卡片和文档感表面           |
| Green        | \#315C4D                           | 通过、规则锁定、主曲线     |
| Blue         | \#3568A8                           | 企业证据、期望利润、信息态 |
| Amber        | \#D28C3C                           | 待审查、提醒、部分满足     |
| Rust/Red     | \#C76B4F / \#A8483E                | 缺失、不通过、淘汰         |
| Radius       | 6–12 px                            | 输入、卡片与状态标签       |
| Body font    | Noto Sans SC / 微软雅黑 / 系统字体 | 中文界面正文               |
| Display font | 宋体回退                           | 主标题与决策数字           |

## 10.1 状态颜色规则

- 绿色只表示已通过/已满足，不用于“概率较高”这类不确定结论。

- 黄色表示需要审查、部分满足或不确定，不等于失败。

- 红色表示阻断、缺失、不通过或超限；同时提供文字和图标，不只依赖颜色。

- 蓝色表示信息、证据来源和辅助曲线，不参与通过/失败语义。

# 11. 响应式与可访问性

| **断点** | **布局策略** | **注意事项** |
|:---|:---|:---|
| \> 1240 px | 驾驶舱左侧控制栏 + 右侧结果；四张 Agent 卡并排 | 保证图表和矩阵宽度 |
| 960–1240 px | 控制栏转为横向双列；Agent 卡两列 | 工作流和表格可横向滚动 |
| 650–960 px | 上传区、规则卡和摘要改为单列/双列 | 主要操作保持在模块顶部 |
| \< 650 px | 全单列；按钮满宽；表格横向滚动 | 触控目标至少约 44 px |

- 所有输入具备可见 label；文件移除按钮包含文件名 aria-label。

- 拖拽上传必须同时提供键盘可用的文件选择入口。

- Tab、按钮、滑杆、开关和模态框具备可见焦点与合理的 Tab 顺序。

- Canvas 图表提供文本化 aria-label；正式版补充数据表或摘要作为等价替代。

- 支持 prefers-reduced-motion；解析动画不得成为获取信息的唯一方式。

# 12. 当前前端技术结构

| **文件/层** | **当前职责** | **建议演进** |
|:---|:---|:---|
| app/page.tsx | 模板数据、规则函数、状态、全部页面 JSX | 拆分 features/documents、rules、simulation、report |
| app/globals.css | 完整视觉系统和响应式样式 | 拆分 token、layout、component 样式或 CSS Modules |
| app/layout.tsx | 中文元数据与社交预览 | 根据请求 Host 生成绝对 OG URL |
| 前端内存状态 | 文件元数据、解析动画、匹配和模拟 | 服务端持久化 + Query 缓存 + URL/项目状态 |
| 确定性函数 | evaluateScenario、优化搜索、覆盖率 | 提取为共享规则包并增加单元/性质测试 |
| Canvas | 胜率和期望利润曲线 | 封装图表组件并增加键盘/数据表替代 |

## 12.1 推荐目录

```text
app/
├─ page.tsx                  # 页面装配与路由上下文
├─ features/documents/      # 上传、任务进度、规则提取、证据匹配
├─ features/rules/          # RuleVersion、门槛、公式与版本确认
├─ features/simulation/     # 场景输入、Agent 结果、优化和图表
├─ features/report/         # 决策报告、导出和审批
├─ components/ui/           # Button、StatusTag、Card、Table、Modal
├─ lib/contracts/           # API 类型和 Schema
└─ lib/rule-engine/         # 纯函数规则引擎（前后端共享）
```

# 13. 正式版接口建议

| **方法** | **路径** | **用途** | **前端关键状态** |
|:---|:---|:---|:---|
| POST | /projects | 创建投标项目 | creating / ready / failed |
| POST | /projects/{id}/documents | 初始化上传并返回签名地址 | uploading / scanning |
| POST | /projects/{id}/parse-jobs | 发起规则/证据解析 | queued / running / done / failed |
| GET | /parse-jobs/{id} | 查询阶段、进度和错误 | 轮询或 SSE |
| GET | /projects/{id}/rule-versions/latest | 获取当前规则版本 | draft / confirmed / stale |
| PATCH | /requirements/{id} | 人工纠正规则并记录原因 | saving / saved / conflict |
| GET | /projects/{id}/evidence-matches | 获取匹配矩阵 | loading / ready / error |
| POST | /projects/{id}/scenarios | 运行竞标与报价优化 | queued / running / ready |
| POST | /projects/{id}/reports | 生成决策报告 | generating / downloadable |

## 13.1 核心响应示例

```typescript
type Requirement = {
  id: string
  kind: string
  text: string
  mandatory: boolean
  score?: number
  formula?: string
  requiredEvidence: string[]
  tenderSource: { documentId: string; page: number; section: string }
  confidence: number
  reviewStatus: string
  ruleVersionId: string
}

type EvidenceMatch = {
  requirementId: string
  evidenceId: string
  status: string
  confidence: number
  rationale: string
  reviewer?: string
}

type ScenarioResult = {
  validBids: unknown[]
  eliminatedBids: unknown[]
  ranking: unknown[]
  recommendation: unknown
  assumptions: string[]
}
```

# 14. 错误与空状态

| **场景** | **页面反馈** | **恢复动作** |
|:---|:---|:---|
| 未上传招标文件 | 解析按钮禁用并提示最低前置条件 | 上传文件或载入演示材料 |
| 只上传招标文件 | 可展示规则；证据矩阵全部标记未匹配 | 上传公司材料 |
| 文件不支持/加密 | 文件行显示错误原因，不进入解析 | 替换文件或输入密码后重传 |
| 解析失败 | 保留已上传文件和失败阶段 | 重试、下载错误详情或人工录入 |
| 规则有冲突 | 黄色阻断，展示冲突来源 | 人工选择有效版本并确认 |
| 强制项缺失 | 红色 GATE GAP，禁止绿色通过结论 | 补充证据或作 NO BID |
| 利润底价高于限价 | NO BID，无推荐报价 | 重估成本/毛利或退出项目 |
| 网络中断 | 保留本地草稿并提示同步状态 | 自动重连或手动重试 |

# 15. 埋点建议

| **事件** | **触发** | **关键属性** |
|:---|:---|:---|
| project_template_changed | 切换项目模板 | from, to |
| document_added | 添加文件 | kind, extension, sizeBucket |
| parse_started/completed/failed | 解析任务状态变化 | projectId, duration, stage, errorCode |
| match_gap_reviewed | 用户查看或确认缺口 | requirementKind, status |
| analysis_applied_to_simulation | 将匹配结果带入竞演 | coverage, hardGapCount |
| scenario_parameter_changed | 调整报价/成本/目标 | field, previous, next |
| simulation_run | 运行竞演 | objective, validCount, recommendation |
| report_exported | 导出报告 | format, bidDecision |

# 16. 前端验收清单

- 首次进入能在首屏和默认 Tab 发现文档上传入口。

- 两类文件区视觉和语义明确，点击、拖拽、批量添加和移除均可用。

- 无招标文件时不能开始解析；解析中按钮状态、阶段和进度一致。

- 完成后展示项目方法、限价、门槛、评分结构和报价公式。

- 公司材料缺失时，匹配结果不得误报已满足；强制缺口使用阻断状态。

- “将结果带入竞标模拟”能同步资格、符合性和证据成熟度。

- 切换项目模板后，文件、解析、规则和场景状态不串线。

- 桌面、平板、手机均可完成核心流程；表格允许横向滚动。

- 键盘焦点清晰、控件有标签、状态不只依赖颜色。

- 所有概率、解析和法律判断均标注模拟/待人工复核边界。

# 附录 A：当前 Demo 页面映射

| **页面元素** | **实现位置** | **备注** |
|:---|:---|:---|
| 五个工作区与业务数据 | app/page.tsx | 单文件实现，便于 Demo，正式版建议拆分 |
| 项目模板与匹配模拟数据 | app/page.tsx | IT 服务、设备采购、智能化工程 |
| 视觉与响应式 | app/globals.css | 暖纸张 + 深绿 + 蓝/黄/红状态 |
| 站点元数据 | app/layout.tsx | 中文标题、描述和社交预览 |
| 社交预览图 | public/bid-strategy-social.png | 四条策略路径汇入规则决策 |
