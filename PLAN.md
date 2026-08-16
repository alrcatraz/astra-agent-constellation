# PLAN — Astra Agent Constellation 推进路线

> 蓝图仓库是规格仓（非软件），本文档记录「落地推进」的待办与状态。完成一项打勾并标注日期/commit。
> 0.1.0 已发布（gitea 私有，v0.1.0，2026-08-04）；**v0.2.0（2026-08-14，ACP 化 + dsh 执行者版）**；**v0.2.1（2026-08-15，添加 dsh 作为推荐执行者之一 + A2A 支持核实落地）**；**v0.2.2（2026-08-15，总是知晓保证机制——编排者/看护者架构感知常驻化）**；**v0.2.3（2026-08-16，对外互操作门面——A2A+ANP 分层、泛域子域式暴露、内部 overlay 多级回落）**；正式版 v1.0.0 待 AIGate 开发完成 + 实际部署验证后再出。

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
- [x] Note.md 附带发现处置（2026-08-14）— 三发现辨析：①「技能双份拷贝」= 误报（~/.hermes 为符号链接指向仓库，reference-not-copy 正确落地，无需处理）；②「审计缺输入完整性」= 属实 → docs/05 §5.1 补 SHOULD 条款（模型可见输入可追溯，「Model-visible means logged」不变量）；③「kind 枚举类型混淆」= 实现已解决、蓝图落后 → docs/03 §3.4 kind 对齐 aigate 实现 `builtin|stdio|http`（sse/stream 是 http 端点的传输变体，由 URL 路径选择，不入枚举）。均不牵动 aigate 实现。Note.md 为转交媒介，处置完毕已清理。
- [x] **「总是知晓」保证机制（2026-08-15，v0.2.2）**— docs/11-always-aware.md 定义三层保证：① 常驻注入（Linux drop-in 模式，内容归算子侧，实现见生态元仓 context-anchor v2.2）；② 触发加载（星座 skill 描述扩 dispatch/parallel 触发词）；③ 动态发现（A2A discover 演进接口，当前静态快照 100% 覆盖无需动态）。公开副本仅保留 11.2 思路层，11.3 部署细节私有（插件名/路径/环境变量不公开）。
- [x] **对外互操作门面（2026-08-16，v0.2.3）**— ADR 0006 补充对外接缝分层决策（A2A=任务对话层 / ANP=身份信任层），内部接缝结论不变。对外域采用**子域式** `{agent}.{public-domain}` + 泛域证书，内部转发统一经**团体自有 overlay 域名**多级回落（P0→P1→P2 逐级 failover）。对外互操作全链路已在外部网络**实测通过**（DNS → 对外入口 → HTTPS → 反向代理 → overlay 回程 → 成员端点），端到端验证指挥。（具体部署细节——入口节点身份、机器网络、DNS 记录值——属私有边界，只进私有副本，不进公开版。）

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

- [x] **执行者选型：dsh（DeepSeek Harness）— 添加为推荐执行者（2026-08-15）**（2026-08-14 查证 + 方案定稿 + **HC01/SUSETLearn00 双机实测通过**）— dsh 插件化、**ACP 双向**（`@deepseek-ai/dsh-acp` server + `subagent-acp` client）。**执行者版组合（29 插件，`~/Projects/dsh/executor/cordis.yml`）**：官方 acp-agent 蓝本 18 全保留（sandbox/bash/fs/subprocess/approval/acp-agent/token-meter/compaction/subagent×2/workflow/hooks/todo）+ 新增 11（llm-pi-ai 接 AIGate 替换 llm-deepseek、mcp-client×3 门禁工具、skill-filesystem+tool-skill 技能基座、lsp-stdio+tool-lsp、tool-fs-search、str_replace_editor、code-runtime、tool-jobs、tool-web+web-search-deepseek、tool-terminal+terminal-bash、goal+plan-mode；session-query-sqlite 因 acp-agent 内置服务冲突已移除）。**实测矩阵（全 ✅）**：ACP 直连（DSH-EXECUTOR-OK）、工具调用（fs/bash 真实执行）、MCP 门禁（mcp__pageindex__get_structure）、权限模型（workspace-write 写墙，无 OpenCode ask 挂起）、多步开发任务（bug 修复闭环）、远程复测（SSH→SUSETLearn00，REMOTE-DSH-OK，执行者 key 隔离）。**✅ 已落地**：Hermes `copilot-acp` provider 指向 dsh（`HERMES_COPILOT_ACP_COMMAND/ARGS` 在 `~/.hermes/.env`，见 AGENTS.md）；执行者 key 按机隔离（各机 `~/Projects/dsh/.env`，gitignored，dsh `loadEnv()` 启动读取，不进 tar/仓库/编排者环境）；严格验证双机 PASS（本机 `DSH-STRICT-OK` / 远程 `REMOTE-DOTENV-OK`）。⚠️ 已知差异：baseline-only（resource_link 退化文本引用）、committed-message 非流式（client 兼容）。部署手册 = `dsh-executor-deployment` skill。
- [ ] **编排者版 DSH 设计（长期推进模块）**（2026-08-14 立项）— dsh 插件化可承担编排者（`subagent-acp` client 驱动外部 worker + ACP server 被连），作为 Hermes 编排者的**研究性替代/补充形态**。前置：执行者版 DSH 测试结论 + AIGate 稳定。设计要点：cordis.yml 编排者组合（subagent-acp ×N 驱动执行者、registry/task-brief 集成、纪律传导 hooks）。当前编排者仍为 Hermes（记忆/通道/路由/审计已落地），编排者版 DSH 是长期观察项。
- [x] **编排→执行接缝 ACP 化落地**（2026-08-14 协议选型已定，ADR 0006；**2026-08-15 落地 dsh**）— **选型边界**：编排者/看护者→执行者派活走 **ACP**（host→agent）；编排者↔看护者状态交换走**共享事实层**（无协议）；多个编排者对等协作（未来）走 **A2A**。**✅ 已完成全部核心**：① task-brief→ACP content blocks 映射设计（docs/10-acp-mapping.md）；② OpenCode ACP server 双机实测（1.18.15 全协议前提通过）；③ **Hermes 原生 ACP client 发现 + 远程实测**（CopilotACPClient + `HERMES_COPILOT_ACP_COMMAND/ARGS` 指向 `ssh ... opencode acp`，SUSETLearn00 远程 full-chain 通过 9s；**业务封装脚本方案废弃——零代码配置即用**）；④ **✅ dsh 落地为推荐执行者（2026-08-15）**：`HERMES_COPILOT_ACP_COMMAND/ARGS` 持久化在 `~/.hermes/.env`（非 config.yaml——源码确认走 `os.getenv`，env 文件即配置），指向 dsh ACP server；执行者 key 按机隔离（各机 `~/Projects/dsh/.env`，dsh `loadEnv()` 启动读取）；双机严格验证 PASS（`DSH-STRICT-OK` / `REMOTE-DOTENV-OK`）。**⚠️ 未来切换**：OpenCode 支持官方 ACP Web Transport 时改用官方标准（transport-agnostic，client 零改动）。
- [ ] 看护者 skill（08 章 runbook → SKILL.md，放 templates/skills/，触发链就位后才有意义）
- [ ] 09 章演练执行（前置：看护者 cron 就位 + 用户放行）
- [ ] 编排者 Game Day 演练主持流程（可选，用户确认后做）
