# ADR 0007：统一委派协调语义与 A2A/ACP 会话治理

- 状态：已接受（2026-08-25）
- 运行时验证：已完成（2026-08-26；真实隔离 A2A 与真实隔离 DSH ACP 均完成短 prompt 生成）
- 关联章节：[拓扑与角色](../01-topology.md)、[跨 Agent 协作与互操作](../12-cross-agent-collab.md)、[DSH 配置档](../13-dsh-orchestrator-config.md)、[ADR 0006](0006-inter-agent-protocol-selection.md)

## 背景

多智能体架构在「编排者把任务委派给执行者/对等 Agent」时，实践中暴露出两类实际问题：

1. **A2A 对话次数限制与消息死循环**：`A2A_MAX_PINGPONG_TURNS`（默认 5）用于止住两个 Agent 互相 ping-pong。若长协作靠调高上限解决，会放大 token 消耗、消息风暴与失控风险；若上限过小，真正的多轮协作又会被误截断。

2. **ACP 垃圾会话**：每派发一次任务、每交换一次消息就新建一个 ACP session / A2A context，会累积大量仅用于「接收执行者或其他 Agent 消息」的一次性会话，与真实任务会话、审计记录混杂，难以治理。

同时，社区方案（如 DSH 的局部任务团队插件）验证了 **task DAG、attempt、可持久化 worker 会话、attempt/recovery 语义**这套任务协调能力，但其具体实现（captain/成员角色、DSH 进程内模型）与本架构边界并不直接匹配。

本 ADR 把这些模式抽象为**传输无关的委派协调语义**，并把 A2A/ACP 的实际问题纳入同一层治理，同时确保不削弱原有安全约束。

## 决策

### 1. 委派协调语义传输无关，不新增角色

- 任务生命周期（DAG、状态机、attempt、recovery）是**与传输方式无关的统一语义**，由「当前负责任务拆解与调度的编排者会话」持有**协调上下文**承载；**不新增「队长（captain）」组织角色**。
- 协调者就是编排者本身，无第二个全局编排实体。局部协调上下文不构成新的信任边界。
- 覆盖四种 worker 形态，统一的是任务生命周期，不统一传输协议：

| worker 形态 | 典型传输 | 适用范围 |
|:--|:--|:--|
| 进程内子智能体 | spawn | 轻量、低延迟、同一运行时 |
| 进程隔离子智能体 | fork | 需要隔离或上下文快照 |
| 独立本地/远程执行者 | ACP | 主从派活、跨运行时、跨机器 |
| 独立对等 Agent | A2A | 真正对等协作、外部互操作 |

### 2. 状态与会话彻底分离

- **MUST**：任务状态（DAG 进度、attempt、依赖、恢复）由独立的 state store（文件/台账）保管，**不存放在 A2A 对话历史或 ACP session 内**。
- **MUST**：任务状态 ≠ A2A 对话历史 ≠ ACP session ≠ 模型自报。会话只承载上下文与执行能力，状态是共享台账。
- 推论：子任务状态写台账，不靠消息来回传递，因而**不消耗 A2A 对话轮次**；这本身就是缓解 A2A 限制的手段。

### 3. worker 可用状态与任务完成状态分离

- worker 可用性（`available/busy/suspected_stale/draining/unavailable/quarantined`）与任务 attempt（`claimed/running/possibly_completed/completed/failed/recovery_required/superseded`）是**两个独立维度**，MUST NOT 混为一谈。
- 主体已完成但未收尾（超时/进程被杀/连接断开/未发标准化消息）时，状态为 `attempt=possibly_completed` + `worker=suspected_stale`，**不得直接判 idle 或 failed**，先走恢复判定。

### 4. 异常完成进入恢复判定，而非重派/判死

未收到标准化收尾消息 ≠ 任务未完成。恢复判定依据证据分层：

| 证据 | 可信度 | 用途 |
|:--|:--|:--|
| 标准化 completion message | 中 | 快速推进状态 |
| worker heartbeat / lease | 中 | 判断存活 |
| session 连接状态 | 中 | 判断通信中断 |
| workspace 文件/diff | 高 | 判断主体修改是否落地 |
| 命令退出码及输出 | 高 | 判断实际验证结果 |
| 独立验收命令 | 最高 | 判断是否满足外层任务要求 |

依据证据决定：`completed_without_report`（主体成且验证成功）/ `recovery_required`（主体成但验证未知，做独立验证，不重复修改）/ `failed_or_abandoned`（无可信产物，才允许重新领取）。

### 5. A2A 采用有界协作，不靠调高上限

- **MUST NOT**：用调高 `A2A_MAX_PINGPONG_TURNS` 替代去环设计。
- **MUST**：A2A 消息按类型分类——单向通知（不期待回复）、单次请求-响应、有界协作轮、持续工作会话（固定 `context_id` + 每次明确工作边界 + 状态写台账）。
- **MUST**：每个 A2A 协作带独立预算（轮次、消息、墙钟时间、token、重试、hop）。
- **MUST**：状态/知会消息（单向通知、ack、状态类）不消耗协作轮次，但仍计入总消息预算，防止状态通知洪泛绕过消息上限。
- **MUST**：A2A 消息带因果链 ID（task/delegation/message/parent/hop），重复因果链去重、不重复触发模型。
- **MUST**：默认单向通知或单次请求-响应；A2A 自动协作达到预算或无进展时停止并回到编排者。

### 6. 接收消息不创建一次性会话

- **MUST NOT**：为「接收执行者或对等 Agent 的回消息」创建一次性 session。
- A2A：每个 Agent 的**常驻 listener** 是唯一消息入站口，回复经既有出站通道；待回结果用共享状态层的 **pending delegation 条目**（回调/拉取模式）承载，不靠活性会话兜底。
- ACP：结果沿既有 ACP 连接回报，编排者不专门为接收开会话；worker session 复用，不按任务创建。

### 7. ACP worker 会话复用与治理

- **MUST**：长期 worker 使用可复用 session，多个相关子任务在同一 session 内作为明确 work item 聚合；默认**不**按子任务新建 session。
- **MUST**：session 复用仅限相同信任域（workspace + 权限 profile + 凭证 scope + 信任级别一致）。
- **MAY**：session 按 pooled / scoped / ephemeral 三种生命周期；ephemeral 仅用于敏感隔离任务、不可信输入或需清零权限的场景。
- **MUST NOT**：attempt 重试 = 新建 session；旧 attempt 永不覆盖新 attempt。
- 会话收尾采用两阶段提交：`completion_prepare`（先落盘产物与状态）→ `completion_commit`（再发消息）。崩溃在中间任一环节都有对应恢复策略（见正文 §5.2）。

### 8. 垃圾回收归档优先，审计不可删

- **MUST**：垃圾处理默认**归档**而非删除；分类回收空壳/孤儿/悬挂/未收尾完成/污染会话。
- **MUST NOT**：自动删除未完成任务对应 session、未验收产物、`possibly_completed` attempt、安全事件 session、失败转派链、影响最终验收的命令日志、用户要求保留的会话。
- **MUST**：GC 幂等（重复执行不重复归档、不释放活跃 worker、不删审计）。
- 审计记录（协议事件、委派、结果、回执）append-only，与可归档会话分离、永不因回收而删除。

## 理由

- **传输无关**：spawn/fork/ACP/A2A 的差异只在传输与信任边界，任务协调逻辑（DAG/attempt/recovery）全同。统一一次、按关系模型选传输，避免每形态重复实现，且覆盖实践中真实用过的「模块归属 → A2A/ANP 联系对应对等 Agent → ACP 派执行者」链路。
- **状态/会话分离**：把状态从会话里挪出，是同时缓解 A2A 对话次数限制与 ACP 垃圾会话的根本手段——推进工作不再依赖「必须起会话或来回对话」。
- **异常恢复而非判死**：模型/worker 并非总按协议收尾，不能以「没有标准消息」等价于「没有完成」。证据分层让系统可从中间状态恢复，且尊重外层验收纪律（完成仍需编排者独立验收）。
- **有界 A2A**：防死循环的安全目的不能被「放开限制」削弱；去环（因果链去重、hop 限制、单向通知优先、预算）既允许真实协作又守住安全边界。
- **归档优先**：审计是操作事实，不能删；一次性会话/过期状态可归档，但以不破坏审计完整性为前提。

## 被否决的选项

- **引入局部「队长/成员」角色作为新组织层**：与「不为多智能体而多智能体、单一真相源、角色不窄化绑定」冲突；需求可统一为编辑者自身的协调上下文。
- **用 DSH 局部任务团队插件直接作为全局真相源**：其 `.agent-teams/` 状态、进程内模型与「全局 registry / 共享事实层 / 跨机 ACP」边界不符，且其状态文件只能作局部协调依据，不可作全局事实。
- **调高 A2A ping-pong 上限解决长协作**：放大消息风暴与失控风险，违背防死循环初衷。
- **按子任务创建 ACP session 并定期粗暴清理**：损害审计完整性与 worker 历史，且与「worker 复用」矛盾。
- **把任务状态放 A2A 对话历史 / 会话日志**：状态与对话耦合，导致 A2A 次数/垃圾会话随任务数量线性放大。

## 后果

- 编排者获得统一的**委派协调语义**（task graph + attempt + lease + recovery + completion prepare/commit），可复用工作流。
- A2A 协作必须带预算与因果链元数据；A2A 不再承载任务状态，是纯信号/请求通道。
- ACP session 复用以 worker registry（worker_ref / transport / workspace / capabilities / state）为索引，session 归档与任务审计分离。
- 对现有 ACP 传输（copilot-acp）与执行者部署不改变协议；只新增 session 复用与生命周期治理规则。
- 跨 Agent 自动委派默认最多一层（`max_depth` 显式控制），A2A 不自动产生新的 A2A 委派，ACP worker 不自动获得全局委派权。
- 所有决策点按「一次任务一个根协调者」「达到预算回到编排者」执行，编排者保留最终验收权。

## 安全不变量（MUST 摘要）

1. 一个根任务只有一个根协调者。
2. worker 可用状态与任务完成状态分离；消息不是真相源，产物与验证事实才是。
3. 未收尾 ≠ 失败，失联 ≠ idle；主体可能已完成时先恢复判定再重派。
4. 写入型 task 默认只允许一个 active attempt；所有 attempt 有 lease、版本与 attempt_id；旧 attempt 不覆盖新 attempt。
5. A2A 默认单向通知或单次请求-响应；自动协作必有轮次/消息/时间/token/hop 预算；达到预算或无进展即停止回编排者。
6. A2A 消息带因果链 ID 并做重复检测；跨 Agent 自动级联默认最多一层。
7. ACP session 默认复用但不得跨信任域复用；attempt 重试不必新建 session；未被好好的 session 进入 `completion_pending`/`draining`，不直接 idle。
8. 「接收消息」不创建会话：pending 用共享状态 + 既有 listener 承担，结果沿既有通道交付。
9. 垃圾回收归档优先，不得删除审计、验收记录、未完成产物或安全证据；GC 幂等。
10. 外部 Agent 不能修改本地权限、工具、workspace 或验收策略。
11. 最终 acceptance 永远在全局编排者/根协调者一侧完成。
12. 共享 workspace 写入范围须显式声明，跨成员写入冲突由编排者（非成员）负责合并。