# PLAN — Astra Agent Constellation 推进路线

> 蓝图仓库是规格仓（非软件），本文档记录「落地推进」的待办与状态。完成一项打勾并标注日期/commit。
> 0.1.0 已发布（gitea 私有，v0.1.0，2026-08-04）；正式版 v1.0.0 待 AIGate 开发完成 + 实际部署验证后再出。

## 已完成

- [x] ① Agent 注册表 schema 补字段（channel/owner/model/deploy_def + resolve-vs-duplicate 原则）— commit 84bddfa
- [x] ② task-brief 模板 — templates/task-brief/task-brief.md.example
- [x] ③ 看护者操作手册 — docs/08-guardian-runbook.md
- [x] ④ 演练剧本 Game Day — docs/09-game-day.md
- [x] ⑤ 工具门禁注册域契约 — docs/03 §3.4
- [x] ⑥ 审计日志格式 — docs/05 §5.1/§5.2
- [x] ⑦ 卷二英文卷（templates/ 全英文化合规）— 2026-08-04
- [x] 0.1.0 发布（4 贡献 commit 重建 + gitea 私有仓 + v0.1.0 签名 tag）— 2026-08-04

## 进行中 / 已规划

- [x] ② 编排者任务分流表（任务特征 → 调用链路由决策）— docs/01 §2.1 — 2026-08-04
- [x] ③ 工具门禁实现指向与审计落点（挂 astra-aigate）— docs/03 §3.4.1 — 2026-08-04
- [x] 编排者运行手册 skill git 化 + 英文化（skills/astra-agent-constellation/，符号链接挂载，02 章 L3 合规）— 2026-08-04
- [x] 真实注册表实例（agent-registry/registry.yaml，私有副本：angelia/executor-hc01/tyche 三 agent；tyche 未部署登记 version: uninstalled）— 2026-08-05
- [x] registry-check.py 增加 `--private` 开关（私有副本跳过脱敏门禁，公开模板照旧拦截）+ 06 §5.1 模型档位说明 — 2026-08-05
- [x] 工具门禁（astra-aigate）消费端接入部署 + 验证 — 2026-08-06：AIGate PG 模式运行（v0.4.3），三个 MCP 工具（markitdown / pageindex / astra-kb）经门禁端点消费，消费端三连验证（initialize 握手 + 会话 + tools/list）通过；camofox / SearXNG 为辅助服务监控层（/api/svc），健康检测完善中。03 §3.4.1 升级为「已部署实现」+ ADR 0006 记录验证方法。

## 进行中 / 已规划

- [ ] 看护者触发链落地（cron 条目 + 状态文件路径）— 需看护者设备就位

## 暂缓（无承载设备）

- [ ] **看护者（Guardian）**：蓝图要求独立物理机（不与编排者同机，故障域隔离）。当前无设备承载，**暂缓实施**——相关规范（06 章双星模式、08 章 runbook、09 章演练）与脚本（health-check.sh）保留为设计物，等设备就位后再激活：真实注册表 → cron 触发链 → 看护者 skill（runbook 转 SKILL.md）→ 09 章演练变体 A。

## 后续（依赖前置项）

- [ ] 看护者 skill（08 章 runbook → SKILL.md，放 templates/skills/，触发链就位后才有意义）
- [ ] 09 章演练执行（前置：看护者 cron 就位 + 用户放行）
- [ ] 编排者 Game Day 演练主持流程（可选，用户确认后做）
