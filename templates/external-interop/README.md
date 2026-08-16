# external-interop — 对外互操作端点模板

对外互操作门面的**可运行参考实现**：为团体成员暴露 A2A 与 ANP 两类对外
端点，供外部智能体/团体对等协作。设计决策见 [ADR 0006 对外互操作门面](../../docs/references/0006-inter-agent-protocol-selection.md)，成员接入步骤见 [12 章对外互操作](../../docs/12-external-interop.md)。

## 文件

| 文件 | 作用 |
|:--|:--|
| `a2a_server_main.py` | **对外 A2A 端点**（A2A v1.0 JSON-RPC + AgentCard）。顶部 `EXTERNAL_*` 常量读环境变量，默认占位。 |
| `anp_server_main.py` | **对外 ANP 端点**（OpenANP，`/agent/ad.json`、`/rpc`、`/agent/did.json`）。机器值全由 env 注入。 |
| `anp_auth.py` | ANP 端点用 HTTP Message Signature（RFC 9421）鉴权中间件，验证方来自预共享 DID 文档目录（Phase-1，免 HTTPS/DNS）。 |

## 运行

模板本身**不含任何机器特定值**——把成员实例值注入环境变量后运行：

```bash
# 公共环境变量
export EXTERNAL_HOST=<对外绑定的地址，如 0.0.0.0 / 指定网卡>

# A2A
export EXTERNAL_A2A_PORT=9910
export EXTERNAL_A2A_KEY=<对外 A2A 任务的 API key>
export EXTERNAL_CARD_URL=https://<public-host>:<port>   # 对外可达的 AgentCard URL

# ANP
export EXTERNAL_ANP_PORT=9911
export EXTERNAL_ANP_NAME=<对外展示名>
export EXTERNAL_ANP_DID=did:all:<...>
export ANP_ENABLE_AUTH=1
export ANP_TRUSTED_DIDS_DIR=<可信对端 DID 文档目录>
export ANP_ALLOWED_DOMAINS=<允许的 Host 域白名单，逗号分隔>

<venv>/bin/python a2a_server_main.py   # 启动 A2A 端点
<venv>/bin/python anp_server_main.py   # 启动 ANP 端点
```

> 依赖：`a2a-*`（Google A2A Python SDK）、`anp`（OpenANP）、`fastapi`、
> `uvicorn`、`starlette`。实例化时在目标机建 venv 安装。

## 实例化到私有副本

每个成员把本模板拷入自己的**私有副本**（`~/.astra/...` 机器实例），
填入该成员真实值（绑定地址、端口、key、DID、信任目录）。模板保持通用，
机器特定值永远在私有副本，不写回公共模板——公共版推 GitHub 公开时不含
任何成员基础设施细节。

## 鉴权现状

- **A2A**：`A2A_*_KEY` 有值时启用 X-API-Key 鉴权（错误/缺失 → 401）。
- **ANP**：`ANP_ENABLE_AUTH=1` 时启用 RFC 9421 签名验证（对签 200 /
  无签/错签 401）。完整 DID-WBA（`did:wba:<domain>`，需 HTTPS）为 Phase-2。
