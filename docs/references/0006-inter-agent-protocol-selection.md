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

## 对外互操作门面（2026-08-16 定案，更新本节）

> 本节扩展 ADR 0006 的接缝模型：除**内部接缝**外，还存在**对外接缝**——
> 与团体外智能体/智能体团体的互操作。内部接缝受「禁 agent 直连、走共享
> 事实层」约束；对外接缝则必须暴露可发现、可对话、可信任的通道。二者
> 分属不同边界，协议选择互不冲突。

### 决策：对外接缝按「分层」选型，不二选一

| 对外接缝 | 协议 | 职责 | 关系模型 |
|:--|:--|:--|:--|
| 任务/对话 | **A2A**（Agent2Agent） | AgentCard 能力发现 + JSON-RPC 派活/取结果/推送 | 平级对等协商 |
| 身份/信任 | **ANP**（DID + HTTP Signature） | DID 身份 + 请求签名强认证 | 认证层，叠加于任务层之上 |

判断标准：**对外互操作不是「宿主驱动 worker」，也不是纯异步状态交换，
而是与外部独立实体的对等协作**。对等协作 → 需要任务层（A2A）承载对话；
同时需要身份层（ANP）建立信任。两者**分层叠加**，非互斥。

### URL 模式（通用约定）

- 对外域采用**子域式** `{agent}.{public-domain}`（非路径式），每个外部可
  达的 agent 一个子域。
- 证书采用**团体认可的公开 CA 泛域证书** `*.{public-domain}`，一张覆盖
  全部对外 agent；加成员 = 新增子域，零重建。
- 内部转发统一经**团体自有 overlay 的 DNS 域名**回程，按 SD-WAN 层级
  （P0/P1/P2）多级回落——每级用不同 DNS zone 前缀，`upstream` 按
  primary + backup 先后 failover。
- 对外只暴露 `{public-domain}`；内部 overlay 组织、具体 zone 前缀、机器
  网络拓扑一律不对外泄露。

### 鉴权分级

| 层 | 路径 | 鉴权 |
|:--|:--|:--|
| 发现 | Agent Card / 能力文档（`/.well-known/*`、`ad.json` 之类） | 公开，或需任务 key |
| 对话 | A2A JSON-RPC 入口 | 任务 API key |
| 身份 | ANP 签名端点 | HTTP Signature（RFC 9421）签名认证 |

### 理由

- **A2A 承担对外对话**：外部智能体（A2A 生态）通过标准 AgentCard 发现 +
  JSON-RPC 对话，才能与团体成员互操作；缺 A2A 则外部方「身份可认却无法
  派活」。
- **ANP 承担身份信任**：解决「谁在跟我说话、我信不信它」；与 A2A 的任务
  语义正交，可分可合。是否部署 ANP 取决于外部方是否走 DID 生态。
- **子域式 + 泛域证书**：符合 A2A/ANP 标准发现路径（`https://{agent}.
  {domain}/.well-known/agent-card.json`），可扩展，证书好签。
- **单协议会拒外部方**：只 A2A 拒掉 DID 生态方，只 ANP 拒掉 A2A 生态方；
  两者并存才能「足够可靠泛用」。

### 与内部接缝结论的关系

不矛盾，分属不同边界：

- **内部接缝**（编排者→执行者、看护者）仍按关系模型：主从派活走 ACP，
  异步状态走共享事实层，**维持「禁直连」**。
- **对外接缝**是组织边界的**暴露面**：与外部实体对等互操作，走
  A2A + ANP。外部实体通过统一对外域发现与对话，回程经团体 overlay 落到
  具体成员。

判定一句话：**内部禁直连，对外按需暴露**。A2A 在此前的「留给未来」判断
（2026-08-14）针对**内部**多编排者对等协作；本期「现在引入」针对**对外**
互操作——场景不同，不构成决策矛盾（见下「事实注记」）。

### 后果

- 团体需一个**公网可达的外部入口**（跳板节点 + 泛域 DNS + 泛域证书 +
  反向代理），把对外域映射到各成员。
- 内部回程可靠性 = overlay 多级回落（P0 主 → P1 → P2 备），
  `upstream` primary/backup 实现 failover；单级失联自动切下级，不中断。
- 鉴权分级保证最小暴露：发现公开、对话需 key、身份签名。
- 新增对外成员 = 新增子域 + 新增 upstream server + 目录/路由登记，模式
  固定、可扩展。
- 对外互操作的具体部署（跳板节点身份、机器网络、DNS 记录值）属私有边界，
  记录在私有副本（见 AGENTS.md §Sanitisation），不进公开版。

### 事实注记（2026-08-16 核实）

- Hermes A2A 平台的 `resolve_bind_host()` 安全模型：无配置 token 时强制只
  绑定回环；配置 `A2A_HOST` 宽地址 + per-peer token / bearer token +
  `A2A_TRUSTED_PEERS` 白名单后，才向对等方开放——为「内/外访问区分」提供
  原生机制（本机天然放行、外部 peer 命名身份认证、审计 + 限流）。
- nginx 1.22 的 `upstream server ... resolve` 参数**不受支持**（加载报
  `invalid parameter "resolve"`）；多级回落改用 `primary + backup` 热备，
  域名在 reload 时解析一次。主地址不可达自动切 backup。
- 对外门面全链路已在外部网络实测通过：DNS 解析 → 跳板节点 → 泛域证书
  HTTPS → 反向代理 → overlay 多级回程 → 成员端点；Agent Card（鉴权拦/
  公开）与能力文档（公开）响应符合预期。

