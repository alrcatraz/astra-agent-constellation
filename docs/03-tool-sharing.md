# 基础设施共用

所有智能体（编排者、执行者、看护者）应当共用同一套 AI 基础设施，但「共用」不是想当然——模型层天然可共用，工具层则需要先解决部署形态问题。

## 1. 分层视图

<figure class="cn-figure">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 380" font-family="IBM Plex Sans, Noto Sans SC, sans-serif" role="img" aria-labelledby="cn-toolsharing-title cn-toolsharing-desc">
  <title id="cn-toolsharing-title">基础设施共用分层</title>
  <desc id="cn-toolsharing-desc">Model gateway at the top, agents in the middle, tool gate and credential store below, network services at the bottom.</desc>
  <rect width="800" height="380" fill="var(--cn-svg-bg)"/>
  <!-- Model gateway -->
  <rect x="200" y="20" width="400" height="52" fill="var(--cn-svg-block)"/>
  <text x="400" y="42" text-anchor="middle" font-size="15" font-weight="600" fill="var(--cn-svg-on-block)">模型网关 Model Gateway</text>
  <text x="400" y="60" text-anchor="middle" font-size="11" fill="var(--cn-svg-on-block)">OpenAI-compatible · 示例：如 OmniRoute</text>
  <!-- Agents row -->
  <rect x="60" y="120" width="180" height="48" fill="var(--cn-svg-surface)" stroke="var(--cn-svg-accent)" stroke-width="2"/>
  <text x="150" y="148" text-anchor="middle" font-size="13" font-weight="600" fill="var(--cn-svg-fg)">编排者</text>
  <rect x="310" y="120" width="180" height="48" fill="var(--cn-svg-surface)" stroke="var(--cn-svg-accent)" stroke-width="2"/>
  <text x="400" y="148" text-anchor="middle" font-size="13" font-weight="600" fill="var(--cn-svg-fg)">执行者</text>
  <rect x="560" y="120" width="180" height="48" fill="var(--cn-svg-surface)" stroke="var(--cn-svg-accent)" stroke-width="2"/>
  <text x="650" y="148" text-anchor="middle" font-size="13" font-weight="600" fill="var(--cn-svg-fg)">看护者</text>
  <!-- Tool gate + credentials -->
  <rect x="120" y="220" width="260" height="52" fill="var(--cn-svg-surface)" stroke="var(--cn-svg-border)"/>
  <text x="250" y="242" text-anchor="middle" font-size="13" font-weight="600" fill="var(--cn-svg-fg)">工具门禁 Tool Gate</text>
  <text x="250" y="260" text-anchor="middle" font-size="10" fill="var(--cn-svg-fg-sub)">示例：如 Astra AI Gate</text>
  <rect x="420" y="220" width="260" height="52" fill="var(--cn-svg-surface)" stroke="var(--cn-svg-border)"/>
  <text x="550" y="242" text-anchor="middle" font-size="13" font-weight="600" fill="var(--cn-svg-fg)">凭证库 Credential Store</text>
  <text x="550" y="260" text-anchor="middle" font-size="10" fill="var(--cn-svg-fg-sub)">集中保管 · 永不进 git</text>
  <!-- Services -->
  <rect x="180" y="320" width="440" height="40" fill="var(--cn-svg-surface)" stroke="var(--cn-svg-border)"/>
  <text x="400" y="345" text-anchor="middle" font-size="12" fill="var(--cn-svg-fg-sub)">网络化工具服务（MarkItDown / pageindex / SearXNG …）</text>
  <!-- Arrows -->
  <line x1="400" y1="72" x2="400" y2="120" stroke="var(--cn-svg-fg)" stroke-width="1.5"/>
  <line x1="150" y1="168" x2="150" y2="220" stroke="var(--cn-svg-border)" stroke-width="1.5" stroke-dasharray="4 3"/>
  <line x1="400" y1="168" x2="250" y2="220" stroke="var(--cn-svg-border)" stroke-width="1.5" stroke-dasharray="4 3"/>
  <line x1="650" y1="168" x2="250" y2="220" stroke="var(--cn-svg-border)" stroke-width="1.5" stroke-dasharray="4 3"/>
  <line x1="250" y1="272" x2="400" y2="320" stroke="var(--cn-svg-border)" stroke-width="1.5"/>
</svg>
</figure>

## 2. 模型层（天然共用，零改造）

- **MUST**：所有智能体通过同一模型网关（如 OmniRoute，OpenAI-compatible）获取模型能力。
- **MUST**：执行者经 `baseURL` 直连模型网关，模型 = 网关配置的编码模型，**不引入新 API key、不引入新订阅**。
- **MAY**：按角色分配不同模型档位（编排者用推理强模型，执行者用编码模型），但都走同一个网关的 provider 路由。

示例（执行者配置，`baseURL` 为示例网关地址）：

```json
{
  "provider": {
    "default": {
      "baseURL": "http://127.0.0.1:20128",
      "models": { "coding": { "name": "deepseek-coding" } }
    }
  }
}
```

## 3. 工具层（「几乎不能共用」的根因与解法）

### 3.1 为什么某些工具几乎不能共用

工具能否共用，取决于**部署形态**：

| 部署形态 | 谁能连 | 例子 |
|:---------|:-------|:-----|
| 独立 HTTP/SSE 服务（网络端点） | **任何客户端** | SearXNG（:8080）、pageindex（:3002）、camofox（容器 API） |
| 挂在某个进程里的 stdio 子进程 | **只有宿主进程** | MarkItDown MCP（凭证从宿主的 .env 注入、生命周期由宿主管理） |

结论：**「不能共用」不是工具本身私有，而是它没有被网络化**。挂在编排者进程里的 stdio 工具，执行者伸手拿不到——没有端点可连，也不知道去哪要凭证。

### 3.2 解法：工具服务网络化 + 凭证服务端持有

- **MUST**：需要多智能体共用的工具，包装为独立 HTTP/SSE 服务，作为系统服务常驻（已有先例：pageindex 的 stdio→SSE 迁移）。
- **MUST**：凭证住在服务进程里（服务端持有），客户端只连端点、不碰凭证。
- **MUST**：网络化后的工具服务**注册进工具门禁**（如 Astra AI Gate 的 mcp_servers 表，kind=http），由门禁统一鉴权与审计。

### 3.3 工具门禁的角色

工具门禁不是「另一个服务」，而是**共享工具服务的统一入口**：

- 所有智能体只配一把门禁钥匙（API Key + scopes），不再各自配置每个工具服务。
- 门禁做统一鉴权、审计日志、可观测性聚合。
- 门禁把工具能力暴露为 MCP 端点，智能体经 MCP 协议消费（Hermes 原生、OpenCode 支持 MCP）。

### 3.4 工具门禁注册域契约

门禁维护**工具服务注册表**（配置源，单一事实源），新服务按 03 §6「新增工具服务的流程」注册进该表。注册条目契约：

```yaml
# 工具服务注册条目（注册域契约）
service: <service-name>          # 唯一名，命名空间：<domain>-<tool>（如 markitdown-ocr）
kind: builtin | stdio | http | sse   # 端点形态（对齐 MCP 服务器 kind）
endpoint: <url-or-command-ref>   # http/sse: URL；stdio: 命令引用；builtin: 进程内
scopes:                          # 门禁授权粒度——每个 scope 一个最小权限
  - <resource>:<action>          # 如 search:read、ocr:convert、registry:write
exposed:                         # 对哪些智能体可见
  - <agent-ref>
audit: true                      # 必开：所有调用进审计日志（见 05 §5.2）
```

- **MUST**：智能体消费工具只经门禁（03 §5 降级路径除外），配置中只留门禁钥匙引用。
- **MUST**：scopes 遵循最小权限，`*` 通配仅限门禁内部服务，不得授予智能体。
- **MUST**：新增服务先注册后暴露——未注册的端点门禁拒绝转发。
- **MUST**：注册表条目变更（增/改 scope/停用）落 git 历史，可审计。
- **MUST NOT**：注册条目中出现凭证值或端点内嵌凭据（凭证走凭证层，03 §4）。

### 3.4.1 实现指向与审计落点

本契约是**规范**，当前已挂到具体门禁实现：

- **已部署实现（2026-08-06 状态）**：astra-aigate（MCP 网关 + 辅助服务反代，多端点 non-merged-pool 架构）——其 `mcp_servers` 配置（kind=builtin|stdio|http、endpoint、scopes、预置 aigate-* 条目可禁不可删、旧端点 301）与本节契约对齐；鉴权 = API Key + scopes（方案 A），第三方 key 加密存 `auth_secret`。部署形态分两层：
  - **MCP 端点层**：工具经 `/api/mcp/servers/[id]/{sse,stream}` 暴露为 MCP 端点，智能体以 MCP 协议消费。已接入工具（消费端验证通过）：markitdown、pageindex、astra-kb。
  - **辅助服务监控层**：非 MCP 工具（如 camofox、SearXNG）经 `/api/svc/*` 反向代理暴露，门禁做健康监控与转发。该层健康检测完善中（服务容器已就位）。
- **消费端接入验证方法**：stream 端点 initialize 握手 → 会话建立（`Mcp-Session-Id`）→ `tools/list` 实测专属工具暴露，确认鉴权、scope、会话三通（该方法是部署会话的实操验证路径，由编排者执行，不涉及蓝图 ADR）。
- **执行者侧接入（2026-08-10）**：两个位置化执行者（OpenCode）实例均接入同一门禁消费共享 MCP 服务——markitdown / pageindex / astra-kb（经 `/api/mcp/servers/<id>/stream` + 各自 API key，OpenCode `type: remote` MCP 配置），并各装本地开发实用工具 codegraph（`codegraph serve --mcp` 本地 MCP）+ graphlint（CLI + prompt 注入 `~/.config/opencode/AGENTS.md`）。无头 CLI 下 skill/MCP 工具需在 permission 放行（`skill: allow`、工具前缀 allow），否则自动拒绝。跨机执行者经网桥域名访问门禁实测可用；**跨机文件路径边界**：门禁侧 MCP 工具解析本地路径，远程执行者的本地文件需以 data URI 或门禁侧路径传入（非故障，架构特性）。
- **执行者技能导入**：执行者技能经同一门禁的 Skill Hub 从外部源导入（编排者用自己的 key：`sources` → `discover` → `install` → `artifacts` → `?format=agent-plugin` + sha256 校验 → 规范化落位 `~/.config/opencode/skills/<name>/`）；技能加载并执行可用。详细流程见运行手册 skill「Importing skills from outside」小节。
- **审计落点**：门禁审计事件按 05 §5.2 格式（`ts/agent/service/scope/action/result/ref`）写入门禁日志存储；智能体侧会话按 05 §5.1 记 JSONL。两个落点分离：门禁日志 = 操作事实（谁调了什么），会话记录 = 思考过程（为什么调）——不得混写。
- **部署时机**：门禁本身也是工具服务，按 03 §6「新增工具服务的流程」注册进注册表后启用；未部署门禁期间，智能体直连工具服务是 03 §5 降级路径，需在注册表 `deploy_def` 中声明。当前已过降级期——共享工具经门禁消费，本地配置只留门禁钥匙引用。

## 4. 凭证层

- **MUST**：凭证集中保管于凭证库，任何智能体运行时不持有明文凭证文件。
- **MUST**：智能体经环境变量注入凭证引用（运行时解密），配置文件中只留 `$VAR` 引用。
- **MUST NOT**：执行者配置文件（如 opencode.json）中出现任何凭证值。

## 5. 降级路径

| 故障 | 降级 |
|:-----|:-----|
| 工具门禁不可达 | 编排者直接连接本地工具服务（绕开门禁，保留审计缺失告警） |
| 模型网关不可达 | 编排者走网关兜底链；执行者任务挂起等待恢复，不静默改模型 |
| 凭证库不可达 | 不启动任何需要凭证的智能体操作，显式报错 |

## 6. 新增工具服务的流程

1. 确认确有跨智能体共用需求（否则保持进程内工具即可）
2. 包装为独立 HTTP/SSE 服务（凭证服务端持有）
3. 注册进工具门禁（鉴权 + scopes + 审计）
4. 各智能体经门禁消费，本地配置只留门禁钥匙引用
