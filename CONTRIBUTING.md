# 协作规范

## 分支与提交

- 分支名：`feature/m{成员号}-{domain}-{short-name}`。
- 每个提交只处理一个主题，提交信息使用祈使句并说明结果。
- 禁止直接 push、force-push 或删除 `main`；通过 PR 和 squash merge 集成。
- 契约变更先提交独立的“契约 PR”，由成员 1 导出 OpenAPI 并重新生成客户端，功能 PR 才可依赖。

## 目录所有权

成员只能修改自己的模块。跨模块需求通过公开 application port、OpenAPI 契约或 outbox 事件完成，禁止访问其他模块的 repository、ORM model 或表。精确范围见 `docs/architecture/ownership.yaml`。

成员 1 独占根配置、依赖锁、Compose、`infra/**`、后端 `core/**`、FR-11、App Shell、公共原子 UI、生成目录、CI 和 Alembic 多 head 合并。成员 1 不替成员 2–7 实现领域业务。

## PR 最低交付

每个功能 PR 同时包含：

- 实现与对应迁移；
- 单元/集成/契约测试；
- 权限、跨租户和失败关闭负向用例；
- 审计断言；
- traceability 更新；
- 前端正常、空、加载、错误、无权和过期状态；
- 新依赖的用途、安全影响和无依赖替代方案。

## 数据库与依赖

- 每名成员只追加自己的 Alembic revision，不修改已经共享的迁移历史。
- 多 head 由成员 1 使用独立 merge revision 处理。
- 新依赖由成员 1 更新锁文件；禁止在功能分支绕过锁文件或使用浮动生产版本。

## 完成定义

代码格式、类型检查、测试、OpenAPI 漂移、敏感信息扫描和 Compose 静态验证均通过；所有未实现能力明确显示为不可用/探索，不能用固定动画或前端内存状态伪装完成。
