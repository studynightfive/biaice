# Stage Gate 与功能开关矩阵

| 能力 | synthetic | BYOK PASS | REAL_DATA PASS | Pilot | Production |
|---|---:|---:|---:|---:|---:|
| 合成数据 App Shell/人工录入 | 允许 | 允许 | 允许 | 允许 | 另行评审 |
| 合成 fixture 探索 | 允许，必须水印 | 允许 | 允许 | 允许 | 另行评审 |
| 真实 API Key 写入 | 阻断 | 允许（secure HTTPS） | 允许 | 允许 | 另行评审 |
| 固定合成连接测试 | 阻断 | 允许，成功不自动 ACTIVE | 允许 | 允许 | 另行评审 |
| 合成/不可逆匿名正式模型调用 | 阻断 | 逐次 Gate 后允许 | 逐次 Gate 后允许 | 逐次 Gate 后允许 | 另行评审 |
| 真实/个人数据进入系统 | 阻断 | 阻断 | 允许 | 允许 | 另行评审 |
| 真实/个人数据发送 Provider | 阻断 | 阻断 | 逐次全 Gate 后允许 | 逐次全 Gate 后允许 | 另行评审 |
| PrecheckReportSnapshot | 静态壳 | MVP-A Gate 后 | MVP-A Gate 后 | 允许 | 另行评审 |
| SimulationAssessmentSnapshot | 静态壳 | MVP-B Gate 后、水印 | MVP-B Gate 后、水印 | 允许展示 | 另行评审 |
| 审批/提交授权 | 阻断 | 阻断 | 阻断 | SHADOW 水印 | 另行评审 |
| 自动外部采购平台提交 | 永久不在首期范围 | 永久不在首期范围 | 永久不在首期范围 | 永久不在首期范围 | 另行产品立项 |

任一依赖 Gate 为 `UNKNOWN/FAIL/STALE` 时按左侧更严格列执行，不能沿用旧 PASS。
