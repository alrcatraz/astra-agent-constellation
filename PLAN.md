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
- [x] 执行者 MCP 接入（2026-08-10）— 双执行者（executor-hc01 / executor-susetlearn00）接入统一网关（AIGate）的共享 MCP 服务：**markitdown / pageindex / astra-kb** 经网关 stream 端点（`/api/mcp/servers/<id>/stream` + 各自 API key），**codegraph / graphlint** 为本地开发实用工具（codegraph = OpenCode 本地 MCP `codegraph serve --mcp`；graphlint = CLI + prompt 注入 `~/.config/opencode/AGENTS.md`，双机均装）。skill 工具在无头 CLI 下需 `permission.skill: allow`（否则自动拒）。双机 opencode 权限放行 MCP/skill 工具后实测可用（HC01 本地 + SUSETLearn00 跨机经 netbird 域名各调通 markitdown/pageindex/astra-kb/codegraph）。
- [x] 执行者技能接入（2026-08-10）— 按「执行者 = 开发调试主体、对等通用技能基座」原则：两个执行者均装 **development-skills 全 7**（c-/csharp-/gdscript-/python-programming、coding-workflow、systematic-debugging、toolchain）+ **astra-vcs-assist 全 8**（主 + github/gpg/git-dev/fork/init/release/sync），落地 `~/.config/opencode/skills/<name>/SKILL.md`；SUSETLearn00 作为 Godot 开发机**额外**挂 godot-agentic + godot-marl-dev。技能经 OpenCode `skill` 工具真实加载验证（从技能内容给出规范建议，非模型默认）。
- [x] 技能导入流程验证 + skill 落地（2026-08-10）— 编排者**用自己的 key** 经 AIGate Skill Hub 从外部导入技能的端到端链路跑通：`GET /api/skills/sources`（源清单 8 个）→ `GET /api/skills/sources/<id>/discover`（技能 meta：sourceUrl/commitSha/externalId）→ `POST /api/skills/sources/<id>/install`（注册进 skillRegistry，返回 id）→ `GET /api/skills/artifacts`（消费清单）→ `GET /api/skills/artifacts/<id>?format=agent-plugin`（拉 SKILL.md 包 + sha256 校验）→ 规范化落位。**AIGate 侧 2 缺口待修**（报部署会话）：`gitRepoAdapter` 嵌套技能（如 `git/skills/`）fetch 路径丢中间层（discover 能列但 install ENOENT）；无「整源 tarball 下发接口」（artifacts 只给单技能，无法交整项目给消费方分析附属文件）。7 个 astra-vcs-assist 子技能因此暂从本地源仓库取（内容与 sourceUrl 仓库 commitSha 一致）。运行手册 skill 新增「Importing skills from outside」小节并标记 Verified。
- [x] Godot 开发机部署（2026-08-10）— godot-agentic-toolkits 技能部署至 SUSETLearn00 执行者（OpenCode skills 目录，含 references），executor-susetlearn00 可加载使用；godot-mcp + Godot 引擎已在机。多智能体架构指定 Godot 项目由 SUSETLearn00 开发、该 repo 工具部署于该机并由 executor-susetlearn00 访问（AIGate 已登记该源）。

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
