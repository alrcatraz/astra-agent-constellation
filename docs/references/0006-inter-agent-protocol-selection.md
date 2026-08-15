# ADR 0006：跨智能体协议选型边界——ACP / A2A / 共享事实层

- 状态：已接受（2026-08-14）
- 关联章节：[拓扑](../01-topology.md)、[同步层](../02-sync-layers.md)、[工具共享](../03-tool-sharing.md)

## 背景

多智能体架构定义四类角色：编排者（orchestrator）、执行者（executor）、
看护者（guardian）、工具门禁（tool gate）。角色之间的接缝需要明确
「用什么协议」：编排者→执行者的派活、编排者↔看护者的状态交换、以及
未来多个编排者之间的协作，语义各不相同，不能一概而论。

候选协议：**ACP**（Agent Client Protocol，host→agent 派活协议）、
**A2A**（Agent2Agent，agent↔agent 对等协作协议，v1.0.0）、**共享事实层**
（git 化的注册表/状态文件/审计，本架构既有机制）。

## 决策

按接缝的**关系模型**选择协议，而非按角色名一刀切：

| 接缝 | 关系模型 | 协议 |
|:--|:--|:--|
| 编排者 → 执行者 | 主从派活（host 驱动 worker，单向控制） | **ACP** |
| 看护者 → 执行者 | 主从派活（同上） | **ACP** |
| 编排者 ↔ 看护者 | 异步状态交换（无实时对话） | **共享事实层**（无协议） |
| 编排者 ↔ 编排者（未来多个） | 对等协作（互相委派/协商） | **A2A**（将来引入） |

判断标准：**这个接缝是「宿主驱动 worker」还是「平级 agent 协商」**。
前者走 ACP，后者走 A2A；既不实时也不对等的状态交换，一律走共享事实层，
不引入协议。

## 理由

- **ACP 匹配主从派活**：ACP 的 client（宿主）→ server（agent）关系、
  会话生命周期（session/prompt）、内容块列表，正好对应「编排者派活给
  执行者」的语义；OpenCode 是 ACP 兼容执行器，Hermes 原生支持 ACP。
- **A2A 是为对等设计的**：A2A v1.0.0 的核心是 AgentCard 能力发现、
  Task 状态机、推送通知、opaque execution（不共享内部状态）——面向
  「独立 agent 系统互操作」。这些机制在我们「禁 agent 直连、走共享
  事实层」的架构里没有落点，且 opaque execution 与「会话可回放」的
  审计不变量（05 §5.1）冲突。
- **编排者↔看护者不需要协议**：两者交换的是注册表变更、健康检查结果、
  状态文件——异步写入共享事实层（git）天然解耦、可审计，引入实时协议
  反而增加握手/协商复杂度，且违背「禁直连」原则。
- **A2A 留给未来**：仅当出现真正对等的协作需求（多个编排者互相协调、
  或看护者升级为主动协商通道）才引入 A2A。当前架构无此需求。

## 被否决的选项

- **编排者↔看护者用 A2A**：两者不是对等关系（看护者服务于系统，不反向
  派活），且 A2A 的实时协商语义与「异步共享事实层 + 全审计」的设计冲突。
- **编排者→执行者用 A2A**：A2A 是 agent↔agent 协议，套在主从派活上语义
  错位（执行者不应发现/委派编排者），且 opaque execution 反审计。
- **编排者→执行者维持自研字符串契约（opencode run 命令拼接）**：作为
  过渡可行，但无协议级结构化保证，执行者增多或引入异厂商 worker 后无法
  规范扩展——这是 ACP 化的动机，不是长期选项。

## 后果

- 编排者→执行者的 task-brief 内容将映射为 ACP content blocks（传输升级，
  字段设计保留）。
- 跨机 ACP 传输方式（stdio / TCP bridge / WebSocket）待定，参考
  remote-acp-connectivity 方案。
- 执行者需支持 ACP server 模式（OpenCode 侧成熟度待验证）。
- A2A 不引入，直到出现多个编排者或对等协作需求。

## 事实注记（2026-08-15 核实）

- **Hermes 原生已支持 A2A v1.0**（插件 `plugins/platforms/a2a`，双向：
  outbound `a2a_call`/`a2a_orchestrate` 等 5 工具 + inbound Agent Card /
  JSON-RPC / SSE / push webhook）。「A2A 留给未来」的成本假设已从
  「需自研 client/server」降为「开配置即用」（`gateway.platforms.a2a.
  enabled: true` + `a2a_agents` 对端列表）。
- **选型依据不变**：决策基于接缝的**关系模型**（主从派活 vs 对等协作），
  非平台能力。执行者（dsh）无 A2A server（`packages/` 仅 ACP），主从
  派活仍走 ACP 子进程 stdio；A2A 仅留给未来「多编排者对等协作」。
- **协议同名警示**：ACP 有双义——Agent **Client** Protocol（Zed 发起，
  dsh/Hermes copilot-acp 所用，独立活跃）与 Agent **Communication**
  Protocol（IBM BeeAI，2025-08-29 已并入 A2A）。本文「ACP」一律指
  Agent Client Protocol。

## 端口规划（2026-08-15 定案）

A2A inbound 与 Hermes 全组件统一规划，原则：**Hermes 相关端口一律用
官方默认值**（官方默认即天然互不冲突的分配方案）。

| 端口 | 归属 | 说明 |
|:--|:--|:--|
| 9900 | A2A inbound | 官方默认（`adapter.py:62` `_DEFAULT_PORT`），本机已启用并持久化 |
| 9901 | Hermes serve | 现有运行实例（TUI/API），固定不动 |
| 9119 | Dashboard | 官方默认（`hermes dashboard --help`），将来直接用 |
| 8642/8644/8645 | API server / webhook | 官方默认（`config_defaults.py`），未启用，预留 |
| 9222 | browser CDP | 调试用（`browser_connect.py:20`），未启用 |

排除项：9900 与 dashboard（9119）无冲突——两者官方默认端口即相隔
200+ 端口；非 Hermes 服务（ZeroTier 9993 / mihomo 9090,1053 / llama
8091 / aigate 20128）均不在 99xx 段竞争。

**实测（2026-08-15）**：本机 A2A 双向对等全链路已验证（L0 发现
Agent Card → L1 本机自连 → L2 双 profile 对调），零代码纯配置。

