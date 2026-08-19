# 14. Session Discovery & Injection — 跨 Agent 的已有会话发现与消息注入

> **目的**：解决「用户手动创建的会话（非 A2A）如何被其他 Agent 发现并注入消息」的问题。
> 本章补充 docs/13 的空白：docs/13 覆盖的是 A2A context_id 已知的场景；
> 本章覆盖的是 session 由用户手动打开、Agent 事后才知道的场景。

> 本章正文面向读者使用简体中文；RFC 2119 关键词（MUST/SHOULD/MAY）保留英文。

## 14.1 问题定义

### 14.1.1 场景描述

用户在浏览器中手动打开多个标签页，每个标签页是一个独立的 Hermes 会话：

```
┌─────────────────────────────────────────────┐
│  浏览器                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │Tab 1:    │ │Tab 2:    │ │Tab 3:    │    │
│  │Core 模块  │ │Auth 模块  │ │Deploy    │    │
│  │设计      │ │实现      │ │方案      │    │
│  └──────────┘ └──────────┘ └──────────┘    │
│         ↑                                    │
│   用户手动创建，未经过 A2A                    │
└─────────────────────────────────────────────┘
```

这些会话的特征：
- **无 A2A context_id**（不是通过 `a2a_call()` 创建的）
- **有 Hermes session_id**（`state.db.sessions.id`）
- **有 chat_id**（对非 A2A 会话，chat_id 是 gateway 生成的随机 UUID）
- **Agent 事后才知道它们存在**（用户告诉 Agent「去跟做 Auth 的那个会话协作」）

### 14.1.2 核心差距

docs/13 的 A2A 机制要求知道 `context_id` 才能调用目标会话。但手动创建的会话：
1. **不一定有 context_id**（可能完全没有 A2A 关联）
2. **即使有 context_id，也不等于 session_id**
3. **Agent 无法通过 A2A 协议发现它们**

**结论**：需要一套**不依赖 A2A context_id** 的发现与注入机制。

## 14.2 数据源：state.db.sessions

Hermes Gateway 将所有会话记录在 `~/.hermes/state.db` 的 `sessions` 表中：

```sql
SELECT id, title, source, chat_id, started_at, ended_at,
       message_count, parent_session_id, last_activity_at
FROM sessions
WHERE ended_at IS NULL          -- 只找活跃会话
ORDER BY last_activity_at DESC;
```

关键字段：
| 字段 | 说明 | 可搜索性 |
|:--|:--|:--|
| `id` | session_id（如 `20260819_abc123`） | 精确匹配 |
| `title` | 会话标题（自动或手动设置） | **模糊搜索**（`LIKE '%keyword%'`） |
| `source` | 来源（`matrix`/`telegram`/`cli`/`acp`/`desktop`/`a2a`） | 精确匹配 |
| `chat_id` | 平台聊天 ID（A2A 时 = context_id） | 可用于区分 A2A vs 非 A2A |
| `ended_at` | 结束时间（NULL = 活跃） | 过滤条件 |
| `last_activity_at` | 最后活动时间 | 排序 |
| `parent_session_id` | 父会话 ID（subagent 派生） | 层级关系 |

**关键事实**：所有 Hermes 会话（无论通过什么平台创建）都记录在此表中。这意味着**一个 SQL 查询就能找到目标会话**。

## 14.3 注入机制：`hermes chat --resume <session_id> -q "<message>"`

### 14.3.1 行为确认

经过源码分析（`cli.py` line 4685-4687, `cli_commands_mixin.py` line 950-1098），`hermes chat --resume <session_id> -q "<message>"` 的确切行为是：

1. **新建一个 CLI 进程**（独立于目标会话的进程）
2. **将当前进程的 `session_id` 直接设为目标 session_id**（line 4686）
3. **加载目标会话的完整对话历史**（`get_resume_conversations(target_id)` → `self.conversation_history`）
4. **发送 `-q` 中的消息**到该会话（通过 `agent._persist_user_message_override` → `hermes_state.append_message(session_id, role="user", content=message)`）
5. **获取回复**（基于完整历史 + 新消息生成）
6. **所有记录追加到原 session**（新消息和回复都持久化到目标 session 的 SQLite）
7. **退出**（CLI 进程结束，但消息已写入目标 session）

**这就是你要的行为——向已有会话注入一条新消息，后续所有记录追加到同一个 session。**

### 14.3.2 示例

```bash
# 向 session_id=20260819_auth_module 的会话注入任务
hermes chat --resume 20260819_auth_module \
  -q "请继续实现 OAuth2 token 刷新逻辑，参考 auth_contract.md"
```

目标会话收到这条消息后，会继续工作并产出结果。

## 14.4 完整流程：发现 → 注入

### 14.4.1 自然语言触发

```
用户: "让那个推进 auth 模块设计的分身来协作一下"
```

### 14.4.2 Agent 自动执行

**Step 1 — 搜索**

```python
import sqlite3

def find_session(query: str) -> list[dict]:
    """根据用户描述搜索活跃 session。"""
    db = sqlite3.connect("~/.hermes/state.db")
    cursor = db.execute("""
        SELECT id, title, source, chat_id, model, last_activity_at
        FROM sessions 
        WHERE title LIKE ? AND ended_at IS NULL
        ORDER BY last_activity_at DESC
        LIMIT 5
    """, (f"%{query}%",))
    rows = cursor.fetchall()
    return [{"id": r[0], "title": r[1], "source": r[2]} for r in rows]

results = find_session("auth")
# → [
#     {"id": "20260819_auth_module", "title": "Auth module design", "source": "matrix"},
#     {"id": "20260818_oauth_impl", "title": "OAuth implementation", "source": "cli"}
# ]
```

**Step 2 — 选择**

Agent 根据搜索结果和用户意图选择最匹配的 session（取第一个，或展示列表让用户选）。

**Step 3 — 注入**

```bash
hermes chat --resume 20260819_auth_module \
  -q "请协作完成 OAuth2 token 刷新逻辑，参考 auth_contract.md"
```

### 14.4.3 自动化封装

建议封装为一个标准化接口（CLI 命令或脚本），让所有 Agent 都能用：

```bash
# 封装后的统一接口
hermes agent-collab inject \
  --query "auth module" \
  --task "请协作完成 OAuth2 token 刷新逻辑"
```

内部实现：
1. 执行 SQL 搜索 `find_session(query)`
2. 选择最匹配的 session_id
3. 执行 `hermes chat --resume <id> -q "<task>"`
4. 返回结果

## 14.5 跨 Agent 兼容性

### 14.5.1 现实约束

| Agent | 能否读 state.db？ | 能否调 hermes chat --resume？ | 注入方式 |
|:--|:--|:--|:--|
| **Hermes** | ✅ 直接读 SQLite | ✅ 原生 CLI | `hermes chat --resume <id> -q "<msg>"` |
| **DSH** | ⚠️ 取决于部署位置 | ⚠️ 如果跑在同一台机器上 | subprocess 调 `hermes chat --resume` |
| **OpenCode** | ⚠️ 同上 | ⚠️ 同上 | subprocess 调 `hermes chat --resume` |
| **Codex** | ❌ 独立存储 | ❌ 无此命令 | 需各自适配 |

**务实方案：以 Hermes 为调度中心**。

因为：
- `state.db` 是 Hermes 的，所有 Agent 共享同一台机器
- `hermes chat --resume` 是唯一统一的注入接口
- DSH/OpenCode/Codex 如果需要被唤起，可以通过 Hermes 作为中介

### 14.5.2 架构决策

```
用户 → 任意 Agent（Hermes/DSH/OpenCode/Codex）
        │
        ├── 如果当前 Agent 是 Hermes：
        │     直接查 state.db + hermes chat --resume
        │
        └── 如果当前 Agent 不是 Hermes：
              ├── 方案 A：该 Agent 通过 subprocess 调 hermes chat --resume
              │     （前提：同一台机器，有执行权限）
              ├── 方案 B：该 Agent 通过 HTTP/RPC 调用 Hermes 的注入端点
              │     （需要扩展 Hermes Gateway API）
              └── 方案 C：用户直接向 Hermes 说（最简单，推荐初期）
```

**推荐初期用方案 C**（用户直接向 Hermes 说），因为：
1. 零开发成本
2. Hermes 是你主要用的 Agent
3. 后续可以逐步演进到 A/B

## 14.6 与 docs/13 的关系

| 维度 | docs/13（A2A context） | 本章（session discovery） |
|:--|:--|:--|
| **前提** | 已知 A2A context_id | 只知道自然语言描述 |
| **发现方式** | 编排者持有 context_id | SQL 模糊搜索 title |
| **注入方式** | `a2a_call(URL, msg, context_id)` | `hermes chat --resume <id> -q "<msg>"` |
| **适用场景** | A2A 主动创建的会话 | 用户手动创建的会话 |
| **跨 Agent** | 需要 A2A 协议支持 | 只需能读 state.db + 调 CLI |

**二者互补**：
- A2A context 适合编排者主动发起的协作（已知 target）
- Session discovery 适合事后发现和召回（不知道 target）

## 14.7 Pitfalls

1. **title 为空时无法搜索**：ACP sessions（OpenCode/DSH 创建的）大多数 title 为 NULL。解决方案：确保每个模块会话都有有意义的标题（可通过 `/title` 命令或 AGENTS.md 约定自动设置）。
2. **多结果歧义**：SQL 搜索可能返回多个匹配。解决方案：取 `last_activity_at` 最高的（最近活跃的），或展示列表让用户选。
3. **状态.db 锁表**：SQLite 是单写者，高并发写入时可能阻塞。解决方案：读取用 WAL 模式（Hermes 默认开启），写入走 `hermes chat --resume`（它自己处理锁）。
4. **压缩链**：如果目标 session 被压缩了，`--resume` 会自动重定向到最新的 continuation（见 cli.py line 1015-1024）。无需额外处理。
5. **非 Hermes session 不可注入**：`hermes chat --resume` 只能注入 Hermes 管理的 session。对其他 Agent 的 session，需要各自的注入方式。
