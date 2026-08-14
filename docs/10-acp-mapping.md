# ACP 内容映射——task-brief 的协议化传输

> 关联决策：[ADR 0006](references/0006-inter-agent-protocol-selection.md)
> （编排者/看护者 → 执行者派活走 ACP）。
> 本文定义 task-brief 契约内容如何映射为 ACP content blocks。
> 简体中文正文，RFC 2119 关键词保留英文。

## 1. 背景

编排者 → 执行者的派活接缝，当前实现是自研契约：task-brief 以 markdown
文件（`templates/task-brief/task-brief.md.example`）形式存在，经
`opencode run "<任务>"` 字符串命令派发。ADR 0006 决定改用 ACP 协议传输。

**核心原则：传输升级，字段设计保留。** 契约内容（Objective/Scope/验收标准）
不变，只是从「一个 md 文本」升级为「结构化 ACP content block 列表」。
task-brief.md.example 模板保留为：① ACP 化之前当前实现形态的契约；
② 人类可读的完整版（`tasks/<TASK-ID>.md` 仍是执行者的工作文档）。

## 2. ACP 内容块模型（0.9.0，官方 SDK 验证）

`session/prompt` 请求的 `prompt` 字段是 content block 列表：

| Block 类型 | type 值 | 关键字段 | 语义 |
|:--|:--|:--|:--|
| `TextContentBlock` | `text` | `text: str` | 文本载荷 |
| `ImageContentBlock` | `image` | `data`(base64), `mimeType` | 图片 |
| `AudioContentBlock` | `audio` | — | 音频 |
| `ResourceContentBlock` | `resource_link` | `uri`, `name`, `description?`, `mimeType?`, `size?` | 资源链接（引用，不内嵌） |
| `EmbeddedResourceContentBlock` | `resource` | 内嵌资源内容 | 资源内嵌（避免额外往返） |

- **MUST**：Agent 基线支持 `text` 与 `resource_link`；其余变体按
  `PromptCapabilities` 协商启用。
- **MAY**：宿主以 `resource_link` 或 `resource` 引用上下文；**当可用时
  `resource` 优先**——避免额外往返，且允许包含 Agent 无法直接访问的
  上下文源（schema 原文语义）。
- **MAY**：`_meta` 字段（block 级 + 请求级）供宿主/Agent 附加元数据，
  实现不得假设其值——task-brief Metadata 的天然落点。

## 3. task-brief → content blocks 映射

| task-brief 字段 | → ACP 表达 | 理由 |
|:--|:--|:--|
| Metadata（Task ID / Orchestrator / Executor / Target repo / Branch / Dates） | **`_meta`** + `sessionId` 关联 | 路由/归属信息，不是执行者阅读内容；`_meta` 专为此设计 |
| §1 Objective | **`TextContentBlock`**（一段话：WHAT + WHY） | 自然语言目标，text 直接承载 |
| §2 Scope | **`TextContentBlock`**（in/out 结构化文本） | 执行者必须读到全文；单 block 保留 in/out 对比结构 |
| §3 Stopping Conditions | **`TextContentBlock`**（per-task 内容 inline） | 停止条件是 per-task 的，随 brief 走；通用纪律已由 AGENTS.md 指令层覆盖 |
| §4 Acceptance Criteria | **每命令一个 `TextContentBlock`** | 验收命令要逐条可执行/可路由——单 block 承载一条命令 + 预期结果，宿主/执行者可逐条处理、逐条重跑 |
| §5 Hand-off（deliverables / decision record / verification） | **不进 prompt**——结果方向，走 `session/update` + 任务报告 | 输入/输出分离：prompt 是输入契约，hand-off 是输出契约 |
| §6 Definition of Done | 并入 Objective 尾部（作为验收标准的前置声明） | 避免重复；DoD 是验收标准的汇总语义 |
| AGENTS.md 指令层 | **`ResourceContentBlock`**（uri 指向仓库内 AGENTS.md）⚠️ 待验证 | schema 推荐 resource 引用；OpenCode ACP server 是否支持 resource 注入需实测 |

## 4. 派发时序（ACP 化后的调用形态）

```
编排者（ACP client）
  │  1. session/new            → sessionId
  │  2. session/prompt         → [Objective, Scope, Stopping, 验收命令×N] (+_meta)
  │  3. session/update         ← 执行者中间结果（可选）
  │  4. session/cancel / 中断  （停止条件触发时）
  │  5. 完成 → 编排者重跑验收 + diff 审查（04 §2 纪律不变）
  ▼
执行者（ACP server，OpenCode）
```

- **MUST**：验收命令逐条可重放——编排者重跑（05 §3）不依赖执行者自报。
- **MUST**：`_meta` 含 Task ID，使审计（05 §5.1）可经 Task ID 关联
  ACP 会话与执行者 session JSONL（输入完整性：模型可见输入可追溯）。
- **MUST NOT**：凭证进 prompt 或 `_meta`（凭证只经环境变量注入，
  05 §5.1 MUST NOT 条款延伸至 ACP 传输层）。

## 5. 与既有机制的关系

| 机制 | 关系 |
|:--|:--|
| task-brief.md.example | 保留：当前实现契约 + 人类可读完整版；ACP 化后其字段设计是 content blocks 的生成源 |
| AGENTS.md 指令层 | 从「prompt 里贴文本」改为 ResourceLink 引用（待验证后定稿） |
| 05 审计 | `_meta` Task ID 打通 ACP 会话 ↔ 执行者 JSONL ↔ 门禁审计事件（05 §5.2 ref 关联） |
| 04 纪律传导 | 停止条件/验收重跑/范围审查纪律不因传输升级而改变 |

## 6. 验证记录（2026-08-14，OpenCode 1.18.15 双机实测：dev host + build host）

**结论：OpenCode ACP server 模式完全可用，映射设计全部协议前提实测通过。**

| 验证点 | 结果 |
|:--|:--|
| `opencode acp`（stdio 模式）存在 | ✅ 双机 1.18.15 一致 |
| initialize 握手 | ✅ `agentInfo: OpenCode 1.18.15` |
| session/new | ✅ 返回 sessionId（`cwd` + `mcpServers` 为必填参数） |
| **promptCapabilities** | ✅ **`{embeddedContext: true, image: true}`**——Resource/Image block 支持 |
| session/prompt 多 text block + `_meta` | ✅ task-brief 映射 7-block 派发成功，模型消费并 end_turn |
| **resource_link 注入（AGENTS.md 指令层）** | ✅ 协议接受，模型消费无错误——指令层可走 ResourceContentBlock |
| 异步事件流 | ✅ `available_commands_update` → `agent_thought_chunk` → `agent_message_chunk` → `usage_update` → RESP（stopReason + usage） |
| 跨机 stdio（SSH tunnel） | ✅ `ssh -T` 完成远程握手，promptCapabilities 与本地一致 |
| 事件捕获要点 | RESP 只含 stopReason+usage；**模型回复内容在 `agent_message_chunk` 通知流**（client 必须订阅通知，不能只等响应） |
| 权限坑（headless） | ⚠️ `external_directory: ask` 挂起——task-brief 文件必须入 workdir（8-10 已记录），ACP 场景同样成立 |

### 验证后定稿的映射调整

- **AGENTS.md 指令层 → `ResourceContentBlock`（resource_link）**：实测通过，从「待验证」升级为**定稿**。URI 指向工作目录内 AGENTS.md（`file://` 相对 workdir），MIME `text/markdown`。
- **`_meta` 的 Task ID 关联**：实测 block 级 `_meta` 被协议接受，审计关联设计成立。
- **client 端要求**：编排者（ACP client）必须持续消费 `session/update` 通知流——回复正文、进度、用量都在通知里，RESP 只是终态标记。

### 编排者侧：Hermes 原生 ACP client（2026-08-14 实测，决定性发现）

**Hermes 原生具备 ACP client 能力，无需自研业务封装**——`agent/copilot_acp_client.py`
的 `CopilotACPClient` 是完整 ACP client（OpenAI-compatible shim），通过 provider
机制配置即可指向任意 ACP server：

```bash
# 环境变量配置（provider runtime 解析，_resolve_command/_resolve_args）
export HERMES_COPILOT_ACP_COMMAND="ssh"
export HERMES_COPILOT_ACP_ARGS="-T -p 2222 <BUILD_HOST> opencode acp --cwd <WORKDIR> --pure"
hermes chat --provider copilot-acp --model copilot-acp -q "<task>"
```

**完整链路实测通过**（build host 远程）：
`Hermes chat --provider copilot-acp` → `CopilotACPClient`（原生 client，spawn
`ssh`）→ SSH stdio 透传 → 远程 `opencode acp` → 模型回复（9s，0 工具调用）。
Hermes 内部路径：`agent.acp_command` ← `runtime.get("command")` ←
`HERMES_COPILOT_ACP_COMMAND`/`HERMES_COPILOT_ACP_ARGS`（或 config.yaml
`providers.copilot-acp`，schema 支持 command/args 则持久化）。

**关键兼容性**：CopilotACPClient 消费 `session/update` 通知中的
`agent_message_chunk`（源码 682-691 行）——与 OpenCode 实测事件流完全一致，
这是「配置即用」成立的协议基础。

**原「业务封装脚本（acp-dispatch.py）」方案已废弃**——Hermes 原生 client
覆盖同一能力，零代码。

### 执行者能力差异（映射设计的适配维度，2026-08-14 查证 + 2026-08-14 实测）

映射设计假定执行者具备 OpenCode 的能力集。换执行者（如实测 dsh）时按此表适配：

| 能力 | OpenCode 1.18.15（实测） | dsh acp server（实测） |
|:--|:--|:--|
| promptCapabilities | `{embeddedContext: true, image: true}` | baseline-only（无 image/audio/embedded-context） |
| resource_link | ✅ 内嵌消费 | ⚠️ 渲染为文本引用 `[resource_link name=… uri=…]`，模型自取 |
| 多 text block | ✅ 逐块消费 | ⚠️ 拼接为一条消息 |
| 权限 | `permission_requested`（headless ask **挂起**） | `session/request_permission` + 沙箱写墙（**自动拒绝 + 清晰错误，不挂起**） |
| 事件流 | agent_message_chunk 流式 | committed-message 一次性输出（非流式，client 兼容） |
| 工具集 | 有限（fs/bash/web/MCP） | 36 工具（含 LSP/子代理/终端/会话记忆/后台任务） |
| MCP 工具 | `<server>_<tool>`（前缀下划线） | `mcp__<server>__<tool>`（与 Hermes 命名一致） |

**适配规则**：执行者 promptCapabilities 无 embeddedContext 时，AGENTS.md 指令层退回「text block 内联」或「URI 文本引用」；dsh 沙箱写墙（workspace-write）自动拒绝 workdir 外写入并返回清晰错误——**无 OpenCode 的 headless ask 挂起问题**，workdir 外读取也自由（读参考材料无需应答）；MCP 工具命名与 Hermes 一致（`mcp__<server>__<tool>`），规则复用无需改名。

### dsh 执行者版实测记录（2026-08-14，dev host + build host）

dsh（DeepSeek Harness，29 插件执行者组合，`~/Projects/dsh/executor/cordis.yml`）经
ACP 被 Hermes 原生 client 驱动，完整验证矩阵：

| 验证项 | 结果 |
|:--|:--|
| 安装 + 29 插件配置 | ✅ clone + pnpm install + build；远程（build host）全量 tar 同步 |
| AIGate 接入 | ✅ `model='aigate/auto/coding'`，llm-pi-ai hand-declared route（配置非代码） |
| ACP server（Hermes 直连，dev host） | ✅ `DSH-EXECUTOR-OK` |
| 工具调用（fs + bash） | ✅ 真实写文件 + 执行命令 + 结果报告 |
| MCP 门禁（AIGate 工具） | ✅ `mcp__pageindex__get_structure` 真实调用成功 |
| 权限模型 | ✅ workspace-write：读自由 + 写 workdir 外被拒（`file access denied ... outside my working directory`，无挂起）；/tmp 临时区可写（设计行为） |
| 多步开发任务 | ✅ 读代码→定位 bug→修复→跑测试→测试通过→结构化报告 |
| **远程复测（SSH → build host）** | ✅ `REMOTE-DSH-OK`，远程执行者 key 隔离正确（两机 key 不同） |

**结论：dsh 执行者版全面验证通过，明确具备替代 OpenCode 的能力**。核心优势：
沙箱写墙权限模型（无 headless ask 挂起）、36 工具集（LSP/子代理/终端/会话记忆）、
MCP 工具命名与 Hermes 一致。部署/配置手册见 `dsh-executor-deployment` skill（与
`opencode-executor-deployment` 对齐：安装、配置、AIGate 接入、权限、MCP、ACP、坑列表）。

### dsh 生产落地（2026-08-15，v0.2.1）

dsh 正式替换 OpenCode 成为生产执行者：

- **编排侧**：Hermes 原生 `copilot-acp` provider 的启动命令持久化在
  `~/.hermes/.env`（`HERMES_COPILOT_ACP_COMMAND` = `bash`、
  `HERMES_COPILOT_ACP_ARGS` = `-c 'cd ~/Projects/dsh && node --import tsx
  packages/examples/acp-demo/src/bin.ts --config executor/cordis.yml'`）。
  源码确认 client 走 `os.getenv` 读取——env 文件即配置，无需 config.yaml 段。
- **执行者 key 按机隔离**：各机 `AIGATE_EXECUTOR_KEY` 只存在于该机
  `~/Projects/dsh/.env`（gitignored，dsh `loadEnv()` 启动时读取）。
  cordis.yml 仅引用变量名（`apiKeyEnv: AIGATE_EXECUTOR_KEY`）。key 不进
  部署 tar（`--exclude='dsh/.env'`）、不进仓库、不进 Hermes 环境——
  编排者不持有执行者身份。
- **严格验证（`env -u AIGATE_EXECUTOR_KEY` 模拟编排侧无 key）**：
  本机 `DSH-STRICT-OK` ✅ / 远程 `REMOTE-DOTENV-OK` ✅。两机 key 哈希
  前缀不同（隔离验证）。
