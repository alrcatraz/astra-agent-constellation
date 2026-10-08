# external-interop — 对外互操作端点模板

对外互操作门面的**可运行参考实现**：为团体成员暴露 A2A 与 ANP 两类对外
端点，供外部智能体/团体对等协作。设计决策见 ADR 0006 对外互操作门面，成员接入步骤见 [12 章跨 Agent 协作与互操作（Part A）](../../docs/12-cross-agent-collab.md)。

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
export HERMES_DISPATCH_WORKDIR=<执行者工作目录，可选；AGENTS.md 按此加载>
export HERMES_DISPATCH_TIMEOUT=300   # 收活窗口秒数（层①，ADR 0007 §9）；跨窗口的长活改走持久原语，不是调大它
export DISPATCH_IDENTITY_LABEL=<身份字段名，如 "external caller DID">

# A2A
export EXTERNAL_A2A_PORT=<A2A-PORT>
export EXTERNAL_A2A_KEY=<对外 A2A 任务的 API key>
# 可选：按外部方区分身份（每个外部 peer 一个 key -> 标识）
export EXTERNAL_A2A_PEERS="alpha=<keyA>,beta=<keyB>"
export EXTERNAL_CARD_URL=https://<public-host>:<port>   # 对外可达的 AgentCard URL

# ANP
export EXTERNAL_ANP_PORT=<ANP-PORT>
export EXTERNAL_ANP_NAME=<对外展示名>
export EXTERNAL_ANP_DID=did:wba:<domain>
export ANP_ALLOWED_DOMAINS=<允许的 Host 域白名单，逗号分隔>
export ANP_KEYS_DIR=<目录：jwt_private.pem + jwt_public.pem（JWT 密钥对）>

<venv>/bin/python a2a_server_main.py   # 启动 A2A 端点
<venv>/bin/python anp_server_main.py   # 启动 ANP 端点
```

> 依赖（实名）：`a2a-sdk`（A2A 官方 Python SDK，`from a2a.…` 导入）、`anp`
> （OpenANP，`from anp.fastanp import …`）、`fastapi`、`starlette`、
> `uvicorn`；**A2A 服务端路由另需 `sse-starlette`**（SSE 事件流，其依赖
> 声明里未列出，缺了 `import a2a_server_main` 直接 `ModuleNotFoundError`）。
> 实例化时在目标机建 venv 安装。
>
> **密钥前置（ANP 必需）**：`ANP_KEYS_DIR`（或 `~/.anp`）内须有
> `jwt_private.pem` + `jwt_public.pem`，否则 `build_app()` 抛
> `RuntimeError: DID-WBA requires jwt_*.pem`。生成示例：
> `openssl genrsa -out jwt_private.pem 2048 && openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem`
> （密钥属 L5 凭证层，不进任何仓库。）
>
> 构建自检（不需网络/凭据）：`python -c "import a2a_server_main as m; m.build_app()"`、
> 同理 `anp_server_main`；派发桥自检见 `dispatch.dispatch_ok()`。

## A2A 原生 JSON-RPC 直呼（绕开 SDK 客户端时）

用裸 HTTP 直呼 A2A 端点必须凑齐**三要素**（2026-10-08 在 `a2a-sdk 1.2.2`
实测，三者缺一各有专属错误码）：

| 要素 | 正确值 | 缺/错时的报错 |
|:--|:--|:--|
| 方法名 | **`SendMessage`**（v1.0 的 PascalCase；`message/send` 是 0.3 旧名） | `-32601 Method not found` |
| 版本头 | **`A2A-Version: 1.0`**（缺省按 `0.3` 处理） | `-32009 version '0.3' is not supported… Expected '1.0'` |
| 枚举写法 | proto JSON：`"role":"ROLE_USER"`（非 `"user"`） | `-32602 message.role: Field is required` |

```bash
curl -X POST http://127.0.0.1:<A2A-PORT>/ \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $EXTERNAL_A2A_KEY" \
  -H 'A2A-Version: 1.0' \
  -d '{"jsonrpc":"2.0","id":1,"method":"SendMessage",
       "params":{"message":{"role":"ROLE_USER","messageId":"m-1",
                 "parts":[{"kind":"text","text":"Reply with exactly: ok"}]}}}'
# 预期：result.task.status.state = TASK_STATE_COMPLETED，artifacts[].parts[].text = 回复正文
```

> 推荐仍用 SDK 客户端（`a2a.client`）：方法名/版本头/枚举由客户端拼装，
> 上表只服务于调试、网关验证与不带客户端的探针。

## 实例化到私有副本

每个成员把本模板拷入自己的**私有副本**（`~/.astra/...` 机器实例），
填入该成员真实值（绑定地址、端口、key、DID、信任目录、Hermes 路径）。模板保持通用，
机器特定值永远在私有副本，不写回公共模板——公共版推 GitHub 公开时不含
任何成员基础设施细节。

## 鉴权现状

- **A2A**：`EXTERNAL_A2A_KEY`（或 `EXTERNAL_A2A_PEERS` 每 peer 一 key）有值时
  启用 X-API-Key 鉴权（错误/缺失 → 401）。命中 PEERS 的调用方以该 peer 名
  作为身份透传给本机 Hermes。**发现层免 key**：`/.well-known/*`（AgentCard）
  恒公开——对端是先拿到卡片才会有 key 的，与 ANP `ad.json` 公开一致，
  也对应 0006 §鉴权分级「发现 = 公开」；任务入口 `/` 始终在门内。
- **ANP**：**did:wba only**（不再有 phase1 预共享形态）。原生 `DidWbaVerifier`
  现场网络解析对端 did:wba 身份并验签。需要公网子域 + 证书（身份文档须公开
  可达）。**门禁次序（2026-10-08 在 `anp 1.0.5` 实测）**：① Host 不在
  `ANP_ALLOWED_DOMAINS` → **403** `Domain <host> is not in the allowed domains list`；
  ② 无认证头 → **401** `Missing authentication headers`；③ 认证头格式不对 →
  **401** `Invalid authorization header format`。完整接入见
  docs/12-cross-agent-collab.md §12.10-12.12（Part A）。
- **只要可发现、不认证**（队内/内部场景）：`ad.json` 与 `interface.json`
  **不需要公网 DID、不需要认证**——描述与认证在 SDK 中是独立模块，回环监听
  即产出；开启认证则受「443 + 证书进信任链」约束。三条落地路径见
  docs/12-cross-agent-collab.md §12.13。
