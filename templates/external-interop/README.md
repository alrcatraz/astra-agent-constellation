# external-interop — 对外互操作端点模板

对外互操作门面的**可运行参考实现**：为团体成员暴露 A2A 与 ANP 两类对外
端点，供外部智能体/团体对等协作。设计决策见 [ADR 0006 对外互操作门面](../../docs/references/0006-inter-agent-protocol-selection.md)，成员接入步骤见 [12 章对外互操作](../../docs/12-external-interop.md)。

## 文件

| 文件 | 作用 |
|:--|:--|
| `a2a_server_main.py` | **对外 A2A 端点**（A2A v1.0 JSON-RPC + AgentCard），收到任务转给本机 Hermes 智能体执行。 |
| `anp_server_main.py` | **对外 ANP 端点**（OpenANP，`/agent/ad.json`、`/rpc`、`/agent/did.json`），`/task` 方法转给本机 Hermes 智能体执行。信任层统一为 did:wba。 |
| `dispatch.py` | **本机 Hermes 派发桥**：把外部任务（带已验证的外部方身份）经 `hermes -z` 单跳交给本机智能体执行并返回结果。 |

## 运行

模板本身**不含任何机器特定值**——把成员实例值注入环境变量后运行：

```bash
# 公共环境变量
export EXTERNAL_HOST=<对外绑定的地址，如 0.0.0.0 / 指定网卡>

# 本机 Hermes 派发桥（两端点共用）
export HERMES_DISPATCH_BIN=hermes                              # Hermes 可执行路径
export HERMES_DISPATCH_PROFILE=<profile，可选>
export DISPATCH_IDENTITY_LABEL=<身份字段名，如 "external caller DID">

# A2A
export EXTERNAL_A2A_PORT=9910
export EXTERNAL_A2A_KEY=<对外 A2A 任务的 API key>
# 可选：按外部方区分身份（每个外部 peer 一个 key -> 标识）
export EXTERNAL_A2A_PEERS="alpha=<keyA>,beta=<keyB>"
export EXTERNAL_CARD_URL=https://<public-host>:<port>   # 对外可达的 AgentCard URL

# ANP
export EXTERNAL_ANP_PORT=9911
export EXTERNAL_ANP_NAME=<对外展示名>
export EXTERNAL_ANP_DID=did:wba:<domain>
export ANP_ALLOWED_DOMAINS=<允许的 Host 域白名单，逗号分隔>

<venv>/bin/python a2a_server_main.py   # 启动 A2A 端点
<venv>/bin/python anp_server_main.py   # 启动 ANP 端点
```

> 依赖：`a2a-*`（Google A2A Python SDK）、`anp`（OpenANP）、`fastapi`、
> `uvicorn`、`starlette`。实例化时在目标机建 venv 安装。

## 实例化到私有副本

每个成员把本模板拷入自己的**私有副本**（`~/.astra/...` 机器实例），
填入该成员真实值（绑定地址、端口、key、DID、信任目录、Hermes 路径）。模板保持通用，
机器特定值永远在私有副本，不写回公共模板——公共版推 GitHub 公开时不含
任何成员基础设施细节。

## 鉴权现状

- **A2A**：`EXTERNAL_A2A_KEY`（或 `EXTERNAL_A2A_PEERS` 每 peer 一 key）有值时
  启用 X-API-Key 鉴权（错误/缺失 → 401）。命中 PEERS 的调用方以该 peer 名
  作为身份透传给本机 Hermes。
- **ANP**：**did:wba only**（不再有 phase1 预共享形态）。原生 `DidWbaVerifier`
  现场网络解析对端 did:wba 身份并验签；未签名/错签名 401（`"must start with
  'did:wba:'"`）。需要公网子域 + 证书（身份文档须公开可达）。完整接入见
  docs/12 §12.10-12.12。
