# 双星模式（Gemini Pattern）

双星模式是本蓝图对「主智能体 + 看护者」双子架构的正式化。它回答一个核心问题：**当主智能体所在机器宕机时，谁来恢复它？**

## 1. 定义

- **主星（Primary）**：编排者智能体（主智能体），承担主要工作负荷，并负责维护看护者。
- **看护星（Guardian）**：辅助智能体（看护者），职责是**维护除自己以外所有智能体的更新、恢复等任务**。

<figure class="cn-figure">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 360" font-family="IBM Plex Sans, Noto Sans SC, sans-serif" role="img" aria-labelledby="cn-gemini-title cn-gemini-desc">
  <title id="cn-gemini-title">双星模式</title>
  <desc id="cn-gemini-desc">The primary agent and the guardian synchronise through a shared fact layer (git, KB, agent registry) instead of a live message channel. The guardian lives on a separate physical machine.</desc>
  <rect width="800" height="360" fill="var(--cn-svg-bg)"/>
  <!-- Primary -->
  <rect x="60" y="140" width="280" height="90" fill="var(--cn-svg-surface)" stroke="var(--cn-svg-accent)" stroke-width="2"/>
  <text x="200" y="168" text-anchor="middle" font-size="16" font-weight="600" fill="var(--cn-svg-fg)">主星 Primary</text>
  <text x="200" y="190" text-anchor="middle" font-size="12" fill="var(--cn-svg-fg-sub)">承担主要工作负荷</text>
  <text x="200" y="208" text-anchor="middle" font-size="12" fill="var(--cn-svg-fg-sub)">维护看护者 · 与用户交互</text>
  <!-- Guardian -->
  <rect x="460" y="140" width="280" height="90" fill="var(--cn-svg-surface)" stroke="var(--cn-svg-accent)" stroke-width="2" stroke-dasharray="4 3"/>
  <text x="600" y="168" text-anchor="middle" font-size="16" font-weight="600" fill="var(--cn-svg-fg)">看护星 Guardian</text>
  <text x="600" y="190" text-anchor="middle" font-size="12" fill="var(--cn-svg-fg-sub)">维护除自己外所有智能体</text>
  <text x="600" y="208" text-anchor="middle" font-size="12" fill="var(--cn-svg-fg-sub)">独立物理机 · 恢复者 ≠ 被恢复者</text>
  <!-- Shared fact layer -->
  <rect x="180" y="280" width="440" height="52" fill="var(--cn-svg-surface)" stroke="var(--cn-svg-border)"/>
  <text x="400" y="302" text-anchor="middle" font-size="13" font-weight="600" fill="var(--cn-svg-fg)">共享事实层 Shared Fact Layer</text>
  <text x="400" y="320" text-anchor="middle" font-size="11" fill="var(--cn-svg-fg-sub)">git 仓库 · 知识库 · 凭证库 · agent 注册表</text>
  <!-- User -->
  <rect x="330" y="20" width="140" height="34" fill="var(--cn-svg-accent)"/>
  <text x="400" y="42" text-anchor="middle" font-size="14" font-weight="600" fill="var(--cn-svg-on-accent)">用户 User</text>
  <!-- Arrows -->
  <line x1="400" y1="54" x2="400" y2="90" stroke="var(--cn-svg-fg)" stroke-width="1.5"/>
  <line x1="400" y1="90" x2="200" y2="140" stroke="var(--cn-svg-fg)" stroke-width="1.5"/>
  <line x1="400" y1="90" x2="600" y2="140" stroke="var(--cn-svg-fg)" stroke-width="1.5" stroke-dasharray="4 3"/>
  <line x1="340" y1="185" x2="460" y2="185" stroke="var(--cn-svg-border)" stroke-width="1.5" stroke-dasharray="4 3"/>
  <line x1="200" y1="230" x2="400" y2="280" stroke="var(--cn-svg-border)" stroke-width="1.5"/>
  <line x1="600" y1="230" x2="400" y2="280" stroke="var(--cn-svg-border)" stroke-width="1.5"/>
</svg>
</figure>

## 2. 硬性约束（MUST）

- **MUST**：看护星部署在**独立于主星的物理机**上。
- 理由：如果看护星与主星同机，主星所在机器宕机时，你**同时失去主智能体和看护者**——「恢复」成为空话。恢复者不能与被恢复者同机。
- **MUST**：看护星所在机器**不得承载任何其他本蓝图角色的主职责**（避免单点叠加）。
- **MUST**：看护星的升级轨道独立于主星——跑稳定版、不随主星升级、配置独立（同框架或异构均可，关键是「不与编排者共享故障域」，见 [ADR 0001](references/0001-agent-platform-selection.md) 板块一）。

!!! warning "当前状态"
    截至本版规范，看护星所需的独立物理机**尚未就位**（仍在准备中）。双星模式在物理机到位前处于「设计完成、待部署」状态；此期间编排者直接承担恢复职责（非对称降级）。

## 3. 看护者的独立交流渠道

看护者 MUST 拥有**独立于编排者的交流渠道**（如 Matrix 自有 Bot 账户、独立邮箱等），以便编排者失联时用户仍能直接访问看护者进行检查与修复：

- **MUST**：看护者的交流渠道独立于编排者（不同 Bot 账户、不同平台端点），不共享登录态。
- **MUST**：编排者失联期间，用户经看护者的独立渠道下达检查/修复指令；看护者按注册表定义执行恢复。
- **MUST NOT**：看护者的独立渠道暴露编排者的私有记忆与会话内容——看护者只响应维护类操作（健康检查、版本回滚、服务重启、注册表核对）。
- **SHOULD**：看护者的渠道账号、恢复流程入口登记在 agent 注册表中。

## 4. 信息同步（不靠实时对话）

双子之间的同步**不建立实时消息通道**，而是通过共享事实层：

- **共享**：技能 git 仓库、知识库（KB）、凭证库、**agent 注册表**。
- **不共享**：记忆（各管各的会话局部状态）、cron 职责（看护星管全家的更新/恢复 cron）。
- **通信方式**：看护星通过健康检查（ping 服务端口、检查注册表状态）发现主星异常；恢复依据注册表中的部署定义执行。

## 5. Agent 注册表（单一事实源）

agent 注册表是一个 git 仓库，记录每个智能体的：

| 字段 | 说明 | 语义 |
|:-----|:-----|:-----|
| name | 智能体名称（示例：orchestrator-1 / executor-dev / guardian-1） | 自有 |
| role | 编排者 / 执行者 / 看护者 | 自有 |
| host | 部署机器（脱敏：`<HOST-1>`） | **device-ref**：指向设备/连接层（凭证库 connection.paths 多路径），不复制地址 |
| model | 模型档位（standard / light） | **tier-ref**：指向模型配置层（主模型 + 回落链定义在 L2，不复制） |
| channel | 交流渠道（`<CHAN-N>`） | **chan-ref**：指向渠道注册；看护者登记独立渠道（06 §3） |
| owner | 维护者（agent-ref，须指向本注册表内另一智能体） | **agent-ref**：互相守护闭环（06 §8） |
| version | 当前版本（SemVer） | 自有 |
| patches | 本地补丁清单 | 自有 |
| deploy_def | 部署定义引用（文档锚点） | **doc-ref**：恢复流程按此执行（06 §7） |
| health_check | 健康检查方式（端口 / 命令） | 自有 |
| restart | 恢复流程引用 | **doc-ref** |

- **MUST**：注册表只存智能体自身的生命周期事实；归属其他层的事实（机器地址、模型回落链、凭证）一律**引用而非复制**（引用协议：`device-ref` / `tier-ref` / `chan-ref` / `agent-ref` / `doc-ref`，完整定义见 [Reference Protocol](https://github.com/alrcatraz/astra-aiagent-infra/blob/main/docs/reference-protocol.md)），真源保持单一。
- **MUST**：每个智能体的部署、升级、恢复动作都反映在注册表变更中（git 历史即审计轨迹）。
- **MUST**：看护星维护注册表；主星读取注册表。
- **SHOULD**：注册表变更与健康检查结果联动（异常自动记录）。

模板见 [templates/agent-registry/](https://github.com/alrcatraz/astra-agent-constellation/tree/main/templates/agent-registry)。

## 6. 看护星的职责清单

1. **更新**：编排者、执行者、自身之外所有智能体的版本升级（git 拉取 + 依赖更新 + **本地改动评估** + 验证——本地改动分实例专属/修复补丁/功能增强三类逐项处置，见[操作手册](08-guardian-runbook.md) §1.1）。
2. **恢复**：发现异常（健康检查失败）时，按注册表的 restart 流程恢复。
3. **同步**：拉取 dotfiles、技能仓库、知识库更新，检查 AGENTS.md 漂移。
4. **报告**：周期性地（默认静默）向主星或用户汇报维护结果；异常时立即告警。

> 逐条操作步骤、失败分支与纪律自检见[看护者操作手册](08-guardian-runbook.md)——原则在此章，操作在手册，手册随环境更新。

## 7. 非对称降级

| 场景 | 降级行为 |
|:-----|:---------|
| 看护星未部署（物理机未就位） | 编排者直接承担恢复职责（当前状态） |
| 看护星宕机 | 编排者临时接管看护职责，看护星恢复后交还 |
| 主星宕机 | 看护星依据注册表恢复主星（这是双星模式的根本目的） |
| 看护星所在机器也宕机 | 用户手动干预（接受该单点，或未来冗余化看护星） |

## 8. 命名与角色分离

- 双子架构不要求看护星使用独立品牌；角色由**职责**定义，不由名字定义。
- 主星维护看护星 = 看护星本身的更新/恢复由主星负责（互相守护的闭环）。
- 用户只与两个智能体交互：主星为日常入口，看护星默认静默、仅在维护/异常时出现。
