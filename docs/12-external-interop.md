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

## 12.9 DID-WBA 身份层（落地要点，2026-08-16 核实）

当身份/信任层启用 **did:wba**（DID Web 绑定网络解析）时，ANP 签名验证
从「本地预共享 DID 文档」演进为「对端 did:wba 域名身份 + HTTPS 网络解析」。
本节记通用落地要点（不对应任何具体 agent）。

### 12.9.1 形态与职责

- **身份形态**：`did:wba:<hostname>`，其中 `<hostname>` 是 DID 文档可被
  HTTPS 解析的域名（常与对外子域一致，`https://<hostname>/.well-known/did.json`）。
- **职责分离**：A2A 承担对话，ANP 承担信任；信任层升级为 did:wba 后，对端
  不再依赖本地预共享身份，而是**现场网络解析对方 DID 文档**完成认证。
- **原生 verifier**：服务端启用 `enable_auth_middleware` 后，OpenANP 原生
  `DidWbaVerifier` 会对对端 did:wba 身份做真实 HTTPS 解析（不是本地查表）。

### 12.9.2 身份密钥选型（防踩坑）

| 组件 | 推荐 | 忌讳 | 原因 |
|:--|:--|:--|:--|
| DID 文档签名 key | **k1 profile**（secp256k1 / JWK） | e1（Ed25519 / Multikey） | 原生 verifier 对 Multikey 有算法推断 bug |
| JWT / HTTP 签名密钥 | **ES256（EC P-256）** | RSA | verifier 内部按 EC 算法强校验，RSA 密钥报 `RSAPrivateKey` |

### 12.9.3 公开解析约束

- **DID 文档必须公开可达**，且不落鉴权：`/.well-known/did.json` 与
  `/{agent}/did.json` 由反向代理暴露；RPC 面仍鉴权，仅身份解析公开。
  注：部分框架（OpenANP）的鉴权豁免路径列表不含 did.json，需在应用层
  加「公开路径中间件」放行身份文档（不影响 RPC 鉴权）。
- **反向代理必须透传 Host 与 X-Forwarded-Proto**（server 级
  `proxy_set_header Host $host;` + `proxy_set_header X-Forwarded-Proto https;`），
  否则对端用 upstream 名/内部名当 authority、或把对外 https 建回 http 重建
  签名 URL，验签失败。**注意 `proxy_set_header` 非继承**：location 内写了任一
  proxy_set_header 会让 server 级全部失效（见 12.11.4），`/rpc` location 内
  不要写。
- **签名 URL 必须匹配服务端重建形态**：服务端经 uvicorn `proxy_headers=True`
  读 X-Forwarded-Proto 以对外 HTTPS wire 形态重建请求 URL
  （`https://<HOST>/rpc`），客户端签名覆盖的 URL 必须与之逐字一致（见
  12.10.4 示例，直接签对外 https 形态最稳健）。

### 12.9.4 对端要求

- 原生 did:wba verifier **只接受 `did:wba:` 身份**；`did:all` 等旧身份会被
  拒绝（"must start with 'did:wba:'"）。启用 did:wba 前，在线对端须先迁移
  为 did:wba（各自域名可解析其 DID 文档），否则协作中断。
- 对端 verifier 会对你的域名做真实 HTTPS 解析——因此对外子域 + 证书
  （12.6）是 did:wba 的前提，不只是反代路径问题。

### 12.9.5 测试客户端提示

- 走 HTTPS 门面验证签名闭环时，注意客户端实现差异：部分 stdlib 客户端
  （如 urllib）经反向代理转发时**请求体可能丢失**（Content-Digest 验签
  失败），真实对端（HTTPX / curl 样式）无此问题。诊断时先确认后端实际
  收到的 body 长度与摘要，再归因服务器或客户端。

## 12.10 对端互连操作手册（可执行）

本节面向**作为对端**接入本蓝图的 agent / 会话 / 脚本：即你的系统要
连接到一个已按 12.2–12.9 部署的外部成员，读取其身份与能力、发起一次
受信任调用。本节是操作手册（怎么用），不是架构说明；所有示例脱敏，
用 `<HOST>`（对外域名）、`<PORT>`（A2A 或 ANP 端口）等占位符表示。

### 12.10.1 两条路径，先分清

| 层 | 端点形态 | 用途 | 鉴权 |
|:--|:--|:--|:--|
| **A2A** | `<HOST>/` 上 JSON-RPC，卡片在 `/.well-known/agent.json` | 投递任务、会话式协作（agent 对 agent） | API key 头 / 白名单 |
| **ANP** | `<HOST>/rpc`，身份在 `/<agent>/ad.json` + DID 文档 | 受信任的**接口调用**（函数式 RPC） | did:wba 身份 + HTTP 签名 |

- 需要「把一个任务交给对方 agent 去执行、拿回结果」→ **A2A**。
- 需要「调用对方暴露的一个具体 RPC 接口，且带身份凭据」→ **ANP**。
- 两边可并存、可独立；一次互连常先 A2A 发现能力，再按能力用 ANP 调
  具体接口。

### 12.10.2 一次性接入流程

以下流程对 A2A / ANP 通用，只是每步读的文档不同：

1. **发现**：拿到对方对外域名 `<HOST>`（成员登记/目录/部署方提供）。
2. **拉取身份与能力**：
   - A2A：`GET https://<HOST>/.well-known/agent.json` → Agent Card
     （`name`、`skills[]`、`supportedInterfaces[0].url`。
     注意 **client 连的是卡片里声明的 URL**，不是你自己拼的地址）。
   - ANP：`GET https://<HOST>/agent/ad.json` → AgentDescription（接口列表）
     与 `GET https://<HOST>/agent/did.json` → did:wba DID 文档（验签公钥）。
3. **判断是否 did:wba**：对端 DID 必须是 `did:wba:<hostname>` 前缀。
   `did:all` 等旧身份在启用 did:wba 的 verifier 侧会被拒绝
   （见 12.9.4）。若对端仍是旧身份，需先在服务端迁移为 did:wba，否则
   连接握手必败。
4. **按目标层鉴权并发起调用**：
   - A2A：带 API key 头，POST JSON-RPC `message.send`（见 12.10.3）。
   - ANP：用 DID 文档里的密钥构造 RFC 9421 HTTP 签名，POST `/rpc`
     （见 12.10.4）。
5. **验证响应**：成功回包带 `result`；鉴权失败为 401/403；签名错误为
   400/401 且带验签失败原因。

### 12.10.3 A2A：拉卡片 + 投递消息（最小可执行）

```python
import httpx
from a2a.client import ClientConfig, create_client, A2ACardResolver
from a2a.helpers import new_text_message
from a2a.types import Role, SendMessageRequest

BASE = "https://<HOST>"          # 对方对外域名
API_KEY = "<KEY>"                # 对方发你的 API key（无则留空，受白名单保护）
headers = {"X-API-Key": API_KEY} if API_KEY else {}

async def main():
    async with httpx.AsyncClient(headers=headers) as hc:
        card = await A2ACardResolver(httpx_client=hc, base_url=BASE).get_agent_card()
        client = await create_client(agent=card,
            client_config=ClientConfig(streaming=False))
        async for chunk in client.send_message(SendMessageRequest(
                message=new_text_message("你好，请执行验证任务", role=Role.ROLE_USER))):
            # chunk 是 Task；最终文本 =
            #   [a.parts[0].text for a in chunk.artifacts if a.parts]
            final = [p.text for a in chunk.artifacts if a.parts
                     for p in a.parts if p.text]
            if final:
                print("result:", final[-1])
```

对应带鉴权的 curl 仅为健康检查（真正的 A2A 消息通常走 SDK/流式）：

```bash
curl -s -H "X-API-Key: $KEY" "https://<HOST>/.well-known/agent.json" \
  | python3 -m json.tool | head
```

> 客户端连的是 Agent Card 声明的 `url`，**不是**你自己传的 `base_url`
> 拼出的路径——配置服务端 `CARD_URL` 必须与会话实际端口一致，
> 否则出现 "All connection attempts failed"（见 external-interop
> reference 的坑）。

### 12.10.4 ANP：取 DID 文档 + 构造签名调用（最小可执行）

ANP 用 **did:wba 身份 + RFC 9421 HTTP 签名**。签名覆盖请求方法、
`@target-uri`、`content-digest` 等；服务端从 Host 头重建实际 URL 验签。
**客户端必须对 `@target-uri` 与「服务端会重建的形态」逐字一致**
（见 12.9.3）。**推荐直接用对外 HTTPS wire 形态签名**：客户端签
`https://<HOST>/rpc`，服务端经 nginx 透传 `X-Forwarded-Proto: https`
（`proxy_headers=True`）重建相同的 `https://<HOST>/rpc`——wire 与签名一致，
最稳健。不要用"内部 http scheme"，它会让签名 URL 与对外形态分裂，一旦
反代未透传 X-Forwarded-Proto，服务端重建回 `http://` 即验签失败（见
12.11.4 的 nginx 非继承陷阱）。

```python
import base64, json, time
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from anp.authentication.http_signatures import generate_http_signature_headers

# 1) 材料：对端 DID 文档 + 我方签名私钥（二者来自 did:wba 身份注册）
did_doc   = json.load(open("<PATH>/did_wba_document.json"))   # 已注册的 DID 文档
priv      = serialization.load_pem_private_key(
    open("<PATH>/key-1_priv.pem", "rb").read(), password=None)
did       = did_doc["id"]

# 2) 目标：签名 URL 用对外 HTTPS wire 形态（须与服务端经 X-Forwarded-Proto
#    重建的形态一致；nginx 必须透传 X-Forwarded-Proto: https，见 12.11.4）
url  = f"https://<HOST>/rpc"

# 3) 请求体：JSON-RPC 格式，method 取 ad.json 里登记的接口
body = b'{"jsonrpc":"2.0","id":1,"method":"<METHOD>","params":{"<K>":"<V>"}}'

# 4) 生成 RFC 9421 签名头（keyid = did#key-1，ES256 用 P-256/sha256）
sig = generate_http_signature_headers(
    did_document=did_doc, request_url=url, request_method="POST",
    sign_callback=lambda d, a: priv.sign(d, ec.ECDSA(hashes.SHA256())),
    body=body, keyid=f"{did}#key-1", nonce=str(int(time.time() * 1000)))

# 5) 经 HTTPS 门面发送
import subprocess
cmd = ["curl", "-sk", "--http1.1", "-X", "POST", f"https://<HOST>/rpc",
       "-H", "Content-Type: application/json"]
for k, v in sig.items():
    cmd += ["-H", f"{k}: {v}"]
cmd += ["--data-binary", body.decode()]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
print(r.stdout[:400])
```

等价 httpx 直接 POST（与真实现一致，签名头原样透传）：
`POST https://<HOST>/rpc`，headers = `sig`，data = `body`。

### 12.10.5 失败速查表

| 现象 | 根因 | 处置 |
|:--|:--|:--|
| 401/403（A2A 卡片都拿不到） | API key 不对 / 白名单未含本端 | 核对 key 与白名单来源 |
| `"must start with 'did:wba:'"` | 对端/本方身份是 `did:all` 等旧身份 | 迁移为 did:wba，双方域名可解析（见 12.9.4） |
| `RSAPrivateKey` / 验签算法不符 | 签名密钥用了 RSA，或 e1/Multikey 推断 bug | 用 k1(secp256k1) 身份 + ES256 签名（12.9.2） |
| Content-Digest 失败但 body 正常 | 客户端只摘要了 body，没覆盖签名字段；或 urllib body 经反代丢失 | 用 `generate_http_signature_headers` 带 `body=`；换 httpx/curl 客户端（12.9.5） |
| "All connection attempts failed"（A2A） | client 连卡片声明的 URL，与服务端实际端口不符 | 服务端 `CARD_URL` 与端口一致 |
| 签名 URL 不匹配 | 客户端签的 `@target-uri` 与服务端重建的形态不一致 | 双方统一用对外 `https://<HOST>/rpc`；nginx 透传 Host + X-Forwarded-Proto（勿在 location 内覆盖 proxy_set_header，12.9.3/12.11.4） |
| 404（ad.json/did.json） | 公开身份文档未挂载/被鉴权拦截 | 应用层加「公开路径中间件」放行身份文档，仅 RPC 面鉴权（12.9.3） |

> 本手册与 docs/12 其余部分同属**通用蓝图**：不含任何特定 agent 的
> 真实域名、DID 或密钥。具体某个成员的登记值属私有边界，见部署方。

## 12.11 从 phase1 升级到真 did:wba（操作清单，2026-08-16 验证）

当某成员 ANP 服务当前跑 **phase1（预共享信任 DID 目录）**，要升级为
**真 DID-WBA（原生 DidWbaVerifier 现场网络解析对端 did:wba 身份）**时，
按此清单执行。核心是**信任模型反转**：phase1 靠本地 `trusted-dids/` 查表，
did:wba 靠现场 HTTPS 解析调用方的 DID 文档。

### 12.11.1 前置核查（缺一个切了必败）
- 公网 HTTPS 门面已挂该成员子域，且 `agent/did.json`、`/.well-known/did.json`、
  `agent/ad.json` 从公网**实测全部 200**（对外子域 + 证书是 did:wba 的前提，
  不只是反代路径问题，12.9.4）。
- 服务代码支持 didwba 分支（`ANP_AUTH_MODE` 开关 + `enable_auth_middleware`，
  FastANP 原生 `DidWbaVerifier`）。
- nginx 已透传 Host 与 X-Forwarded-Proto 到本成员（server 级
  `proxy_set_header Host $host;` + `X-Forwarded-Proto https;`，且 `/rpc`
  location 内**不写**任何 proxy_set_header——非继承规则会丢弃 server 级的
  X-Forwarded-Proto，导致服务端重建出 http、与客户端 https 签名不匹配，
  见 12.11.4 实测坑）。
- `ANP_ALLOWED_DOMAINS` 含该成员自己的对外域名。

### 12.11.2 迁移步骤（对齐已验证形态）
1. 备份：`keys/` 目录 + systemd unit 全备（change-safeguard 三档备份）。
2. **k1 身份重生成**：用 `create_did_wba_document(did_profile="k1")` 重生成
   did:wba 身份（参考已验证成员的 `gen_did_wba_k1.py`），把 DID 文档的
   `key-1` 从 Multikey 换成 `EcdsaSecp256k1VerificationKey2019`
   （secp256k1/JWK）——见 12.9.2 密钥选型红线。
3. **生成 ES256 JWT 密钥对**（`jwt_private.pem` + `jwt_public.pem`，
   NIST P-256）放进 `ANP_KEYS_DIR` 或 `~/.anp`——didwba 启动**硬性要求**，
   缺则 `RuntimeError` 拒启。
4. 改 unit `ANP_AUTH_MODE=phase1` → `didwba`，`daemon-reload` + 重启。
5. 确认服务 active + 端口监听。

### 12.11.3 验收（必须跨机真握手，非自闭环）
- 公网 did.json 的 `key-1` 现为 `EcdsaSecp256k1VerificationKey2019`（非 Multikey）。
- 未签名调用 `/rpc` → **401**（鉴权已激活）。
- **跨机签名闭环**：用另一台已 did:wba 成员的身份密钥（它自己的
  `did_wba_key-1_priv.pem` + did 文档）经公网门面签名调该成员 `/rpc` echo，
  期望 `HTTP 200` + `result.message` 含 `external-anp-ok`。verifier 现场网络
  解析调用方 did:wba 身份并验签通过，即证明**真 DID-WBA** 生效（12.10.4
  的 `generate_http_signature_headers` 客户端可用，keyid 取 did 文档第一个
  verificationMethod 的 `#key-1`）。

### 12.11.4 陷阱 / 红线（承接 12.9.2）
- 身份密钥必须 **k1 (secp256k1/JWK)**；Multikey/Ed25519（e1）触发 verifier
  算法推断 bug。JWT/签名密钥必须 **ES256 (EC P-256)**；RSA 报 `RSAPrivateKey` 拒验。
- **签名 URL 用对外 HTTPS wire 形态，nginx 必须透传 `X-Forwarded-Proto: https`**：
  客户端签 `https://<HOST>/rpc`，服务端 uvicorn `proxy_headers=True` +
  `forwarded_allow_ips="*"` 读到 X-Forwarded-Proto 后用 `https` 重建
  `@target-uri`——两边逐字一致。**严禁用"内部 http scheme"签名**，那会让
  `@target-uri` 与服务端口径分裂。
- **nginx `proxy_set_header` 是非继承的（本次部署实测根因）**：一旦某个
  `location` 内**写了任一** `proxy_set_header`，server 级定义的所有
  `proxy_set_header` 对该 location **全部失效**。例如 HC01 曾把
  `proxy_set_header Host $host;` 写进 `/rpc` location，导致 server 级的
  `X-Forwarded-Proto https` 丢失 → 服务端重建出 `http://` → 与客户端签名的
  `https://<HOST>/rpc` 不匹配 → `Verification error: `（空描述，源自
  ECDSA InvalidSignature）。**修复**：`/rpc`（及任何需伪造信任头的 location）
  里不写 proxy_set_header，让 server 级的 Host/X-Forwarded-Proto/-For 完整继承；
  确需覆盖某个头时，把 server 级全部 proxy_set_header 一并复制进该 location。
- 升级切 did:wba 会**替换该成员 did:wba 公钥**——若有真实公网 peer 已缓存
  旧 key 会短暂失效；phase1 阶段通常无公网 peer，无影响，升级前确认。

## 12.12 把外部任务派发到本机 Hermes（dispatch 桥，v0.2.6）

外部 A2A/ANP 端点只做**入站鉴权与身份解析**，真正的任务执行由**本机自己的
Hermes 智能体**完成（而不是让端点 echo 或空转）。`templates/external-interop/`
的 `dispatch.py` 就是这座单跳桥：

```text
外部方 --A2A(9910)/ANP(9911)--> 端点(验身份) --dispatch.py--> hermes -z
         （DID / peer 身份注入 prompt） <--------- 本机智能体执行 ---------
                                         最终回复返给外部方
```

### 12.12.1 设计要点

- **执行引擎是本机 Hermes**：`dispatch.run_hermes_oneshot(task, identity)`
  调用 `hermes -z`（官方一次性脚本通道），把任务文本 + 已验证的外部方身份
  拼成 prompt，取最终回复返回。**无网络中继、无跨端口代理**——本机 hermes
  是唯一执行器。
- **身份透传是核心**：外部鉴权层解析出的真实身份（ANP 的 `Context.did`
  / A2A 的 `peer_name`）作为一行上下文注入 prompt，让本机智能体**能区分
  "这是哪个外部方"**，而不是笼统的"外部"——支撑按 peer 的授权/审计。
- **机器无关模板**：`dispatch.py` 不含任何机器特定值，全部经环境变量注入
  （`HERMES_DISPATCH_BIN` / `HERMES_DISPATCH_PROFILE` / `HERMES_DISPATCH_WORKDIR`
  / `DISPATCH_IDENTITY_LABEL`）。同一模板原样装在每台成员机器。

### 12.12.2 接通矩阵（端点 → dispatch）

| 端点 | 鉴权 | 取身份 | 注入的 identity | 返回 |
|:--|:--|:--|:--|:--|
| A2A `POST /` (9910) | `X-API-Key`（单 key 或 `EXTERNAL_A2A_PEERS` 每 peer 一 key） | `EXTERNAL_A2A_PEERS` 命中 → `request.state.peer_name`；单 key → `"external"` | `peer_name` | 本机 Hermes 最终回复（agent artifact） |
| ANP `POST /rpc` `/task` (9911) | RFC 9421 签名 + did:wba | 验签通过的 `Context.did` | `context.did` | `{"message": <回复>, "origin_did": <DID>}` |

### 12.12.3 部署要点（生产 unit）

- 生产 systemd unit 的 `ExecStart` **指向私有副本**（`~/astra/external-interop/`
  ，含机器真实值），**不直接指向 git 模板目录**；模板只作 git 单一来源
  （AGENTS「deployment specifics go to the private copy」）。
- **必须显式设 `HERMES_DISPATCH_BIN` 为绝对路径**（systemd user 环境默认
  PATH 不含 `~/.local/bin`，不设会 `FileNotFoundError`）。
- 端点监听：对外 9910/9911 绑 0.0.0.0；**内部 hermes A2A（9900）应只绑
  127.0.0.1**，与对外端口物理分隔，且 9900 永不经公网反代暴露。
- 部署后跨机验收：用另一台已 did:wba 成员的身份（它自己的 key + did 文档）
  经**公网**门面签调用 `/rpc` `/task`，期望 200 + `result.message` = 本机
  hostname 类真实执行输出 + `origin_did` = 调用方 DID（12.11.3 的闭环，但
  任务改为真执行而非 echo）。
