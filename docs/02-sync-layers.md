# 同步分层

多个智能体分布在多台机器上，最大的问题不是「怎么通信」，而是**「它们各自知道什么」如何保持一致**。本蓝图采用**分层真源（single source of truth per layer）**方案：每一类信息有且只有一个 git 化（或集中化）的真源，其余全是它的消费方。

## 1. 黄金法则

> **知识跟着代码走（AGENTS.md），配置跟着 git 走（dotfiles），记忆留在本地（绝不跨机），凭证集中保管（绝不复用）。**

## 2. 分层总表

| 层 | 内容 | 真源 | 同步机制 | 谁消费 |
|:---|:-----|:-----|:---------|:-------|
| **L1 项目规则** | 构建禁令、验证命令、代码卫生条款、语言约定 | 仓库内 `AGENTS.md` | git（随仓库零成本同步） | 所有操作该仓库的智能体 |
| **L2 全局配置** | opencode.json、settings.json、工具链配置 | dotfiles 仓库 | git（`~/.config` 符号链接或拉取脚本） | 各机器上的智能体运行时 |
| **L3 技能/程序记忆** | 可复用流程、排查路径、修复步骤 | skills 仓库（git 双副本：公开 + 私有） | git + 生命周期同步工具 | 各智能体按需加载 |
| **L4 跨机知识** | 服务配置、事故记录、参考数据 | 知识库（KB）+ llm-wiki | git 化/服务化 | 所有智能体按需查询 |
| **L5 凭证** | API key、令牌、连接串 | KeePassXC + GPG 加密 YAML（三层库） | 集中保管，**永不进 git** | 各智能体经环境变量注入引用 |
| **记忆（例外层）** | 会话局部状态、用户偏好快照 | **各智能体本机** | **不跨机同步** | 仅本智能体 |

## 3. 各层细则

### L1 项目规则（AGENTS.md）

- **MUST**：每个活跃仓库根目录有 `AGENTS.md`，写清：构建在哪台机器做、验证用什么命令、禁止什么操作、代码卫生要求。
- **MUST**：AGENTS.md 内容可被执行者直接读取——它是执行者「知道项目规矩」的唯一途径。
- **MUST NOT**：把个人偏好、记忆、会话内容写进 AGENTS.md（那是 L3/L6 的职责）。

示例（构建机分离）：

```markdown
## Build

- Next.js compilation MUST run on <BUILD_HOST>, never on the dev machine.
- Verification: npx tsc -p tsconfig.typecheck-core.json
```

### L2 全局配置（dotfiles）

- **MUST**：所有智能体的全局配置（OpenCode 的 `opencode.json`、shell 配置等）以 dotfiles 仓库为真源。
- **MUST NOT**：凭证进 dotfiles。API key 用环境变量从凭证库注入。
- **SHOULD**：用符号链接或一次性拉取脚本将 dotfiles 部署到各机器，而不是手工复制。

### L3 技能（skills）

- **MUST**：技能以 git 仓库管理，公开内容与私有覆盖层分离（双副本架构）。
- **MUST NOT**：把「会话特定」的知识存成技能——那是临时信息，只应存在于会话历史。
- **SHOULD**：技能是 class-level 的（可复用的流程/方法），session 细节放技能的 references/ 私有目录。

### L4 跨机知识（KB / wiki）

- **MUST**：跨机共享的参考数据（服务端口、配置约定、事故根因）进知识库或 wiki。
- **MUST NOT**：把会变的临时状态（PR 号、commit SHA、任务进度）写进知识库——用会话搜索回溯。

### L5 凭证

- **MUST**：凭证只存在凭证库（KeePassXC / GPG 加密 YAML / .env），配置与代码中只留**引用**。
- **MUST NOT**：凭证以明文进入任何 git 仓库、dotfiles、AGENTS.md、技能或知识库。
- **MUST**：编码执行者如需访问外部服务，经环境变量注入凭证（与编排者同机的本地执行者可走内网 loopback 免凭证）。

### 记忆（例外层，不跨机）

- **MUST**：每个智能体的记忆/事实库是本机私有状态，**绝不跨机双向同步**。
- 理由：SQLite 双向同步是冲突制造机；记忆的「我知道什么」如果被合并，会污染各智能体的上下文判断。
- **MAY**：新机器上的智能体通过 `git log` + AGENTS.md + README 自举，而不是复制旧记忆。

## 4. 跨机一致性验证

- **SHOULD**：定期检查各机器配置与 dotfiles 真源的差异（`dotfiles diff` 或拉取脚本的 dry-run）。
- **SHOULD**：新机器加入时，按 L1→L2→L3→L4→L5 顺序部署，最后自举记忆。
- **MUST**：任何「同步」失败都必须显式报错，不得静默降级为「本地已有配置凑合用」。
