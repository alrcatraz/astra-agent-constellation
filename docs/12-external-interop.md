# 12. 对外互操作 — 团体边界与外部智能体协作

> **目的**：定义团体与**外部**智能体/智能体团体对等互操作的边界、协议
> 分层与操作步骤。内部接缝（编排者→执行者、看护者）仍遵守「禁直连、走
> 共享事实层」纪律（见 [01 拓扑](01-topology.md)）；本章只描述**对外
> 暴露面**。选型的理由与证据见 [ADR 0006 对外互操作门面](references/0006-inter-agent-protocol-selection.md)。

## 12.1 边界与判定

| 接缝类型 | 对象 | 纪律 |
|:--|:--|:--|
| 内部接缝 | 编排者→执行者、看护者 | 主从派活走 ACP；异步状态走共享事实层；**禁 agent 直连** |
| 对外接缝 | 团体外智能体 / 智能体团体 | 对等协作，暴露可发现可对话可信任的通道 |

**判定一句**：内部禁直连，对外按需暴露。对外互操作是与**外部独立实体**
的对等协作，不是宿主驱动 worker，也不是纯异步状态交换。

## 12.2 协议分层（不二选一）

| 层 | 协议 | 职责 | 触发 |
|:--|:--|:--|:--|
| 任务/对话 | **A2A**（Agent2Agent） | AgentCard 能力发现 + JSON-RPC 派活/取结果/推送 | 外部智能体要与你协作对话 |
| 身份/信任 | **ANP**（DID + HTTP Signature） | DID 身份 + 请求签名强认证 | 需要「谁在跟我说话、我信不信它」 |

A2A 承担对话，ANP 承担信任，二者正交分合。是否部署 ANP 取决于外部方是否
走 DID 生态；A2A 是主流开放 Agent 生态的标准对话协议，缺它则外部方「身份
可认却无法派活」。

## 12.3 URL 与暴露（通用约定）

- 对外域：**子域式** `https://{agent}.{public-domain}`，每个对外可达的
  agent 一个子域。不使用路径式（`/agent`）——nginx 无法按路径段动态路由
  到变量 hostname，且证书难覆盖。
- 证书：`*.{public-domain}` 泛域证书，一张覆盖全部对外 agent。
- 内部转发：统一经**团体自有 overlay 的 DNS 域名**回程，按 SD-WAN 层级
  （P0 → P1 → P2）多级回落，`upstream` 用 primary + backup 热备 failover。
- 对外只暴露 `{public-domain}`；内部 overlay 组织、zone 前缀、机器网络
  拓扑一律不对外泄露。

### 标准发现路径

```
https://{agent}.{public-domain}/.well-known/agent-card.json   # A2A AgentCard
https://{agent}.{public-domain}/ad.json                        # ANP 能力描述（如启用）
https://{agent}.{public-domain}/rpc                            # ANP JSON-RPC（如启用）
https://{agent}.{public-domain}/                               # A2A JSON-RPC 入口
```

## 12.4 鉴权分级

| 层 | 路径 | 鉴权 |
|:--|:--|:--|
| 发现 | Agent Card / 能力文档 | 公开，或需任务 key |
| 对话 | A2A JSON-RPC 入口 | 任务 API key |
| 身份 | ANP 签名端点 | HTTP Signature（RFC 9421） |

最小暴露原则：发现公开、对话需 key、身份签名强认证。

## 12.5 操作步骤（新增对外成员）

1. 在对外域新增子域（`{agent}.{public-domain}`），DNS CNAME/A 指向对外入口。
2. 证书：成员数 ≥2 且有泛域证书（`*.{public-domain}`）时无需单签；若当前
   尚未签发泛域证书，可先为成员签发单域证书（HTTP-01 / DNS-01 均可），
   待成员增多再升级泛域（见 12.6）。
3. 反向代理新增 `server_name {agent}.{public-domain}`，`upstream` 加入该
   成员 overlay 域名（primary + backup 热备，继承多级回落）。
4. 按 A2A / ANP 路径分流到成员对应服务端口。
5. 目录/注册表登记该成员的能力与对外地址。

> 具体部署（入口节点身份、DNS 记录值、成员机器网络）属私有边界，只写
> 进私有副本（见 AGENTS.md §Sanitisation、§External interop）。

## 12.6 证书选型

| 场景 | 方案 | 说明 |
|:--|:--|:--|
| 单成员 | 单域证书（HTTP-01） | 零新增凭据，certbot 自动续期即可 |
| 多成员 / 成员频繁增减 | 泛域证书（`*.{public-domain}`，DNS-01） | 一张覆盖全部；需 DNS 服务商 API 凭据 |
| 新增成员不想动 DNS 服务商 | 每成员单域证书 | 可脚本化，但 n 个成员 n 张证书 |

泛域证书（DNS-01）依赖 DNS 服务商 API 凭据（如托管商 token）；若不便持有，
退化为逐成员单域证书，功能等价（子域式 URL 不变），仅证书管理略有开销。

## 12.7 安全与降级语义

- **多级回落是「降级可用」，不是默认**：P0 不可达自动切 P1/P2，代价是
  走次优链路（延迟/带宽/稳定性）。对实时同步敏感的协作应感知当前回程层级，
  回落不代表链路质量等同。
- **只暴露「对外安全」的服务**：成员端点上与对外互操作无关的内部接口
  （管理端口、内部鉴权接口）一律不映射到 `{agent}.{public-domain}`。
- **对外鉴权是底线**：即便成员在同一私有网络，对外门面也必须启用 A2A
  key / ANP 签名，不能假设「外部不可达 = 安全」。
- **回落域名解析是单个事实点**：`upstream` 在 reload 时解析一次成员域名，
  overlay 重连导致地址变化需 reload 反向代理（SD-WAN 地址通常固定，实际
  影响有限）。

## 12.8 已知实现要点（2026-08-16 核实）

- Hermes A2A 平台的 `resolve_bind_host()` 安全模型：无 token 时强制只绑定
  回环；配置 `A2A_HOST` 宽地址 + per-peer token / bearer token +
  `A2A_TRUSTED_PEERS` 白名单后才向对等方开放——为「内/外访问区分」提供
  原生机制（本机天然放行、外部 peer 命名身份认证、审计 + 限流）。
- nginx 1.22 的 `upstream server ... resolve` 参数**不受支持**（加载报
  `invalid parameter "resolve"`）；多级回落改用 `primary + backup` 热备，
  域名在 reload 时解析一次，主地址不可达自动切 backup。
- 对外门面全链路已在外部网络实测通过：DNS → 对外入口 → HTTPS → 反向
  代理 → overlay 多级回程 → 成员端点；AgentCard 与能力文档响应符合预期。
