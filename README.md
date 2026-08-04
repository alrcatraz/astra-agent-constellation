# Astra Agent Constellation

> 多智能体编排架构蓝图 —— 单一编排者、位置化执行者、看护者与工具门禁。

**An agent-orchestration architecture blueprint: one orchestrator, positional
executors, a guardian and a tool gate.**

本仓库是一份**架构蓝图**（Blueprint，非软件/插件/CLI）：定义「一个编排者 + 若干个位置化执行者 + 一个看护者 + 一个工具门禁」如何组织、如何同步、如何传导纪律、如何被审计。采纳方式：阅读规范 → 复制模板 → 按自家拓扑适配。

[![License: CC BY-SA 4.0](https://badgen.net/badge/license/CC%20BY-SA%204.0/blue)](LICENSE)
[![GitHub stars](https://badgen.net/github/stars/alrcatraz/astra-agent-constellation)](https://github.com/alrcatraz/astra-agent-constellation)
[![Last commit](https://badgen.net/github/last-commit/alrcatraz/astra-agent-constellation)](https://github.com/alrcatraz/astra-agent-constellation)

## 核心设计

| 角色 | 职责 | 部署 |
|:-----|:-----|:-----|
| **编排者** Orchestrator | 唯一用户交互入口；任务拆解；验收 | 主工作机 |
| **执行者** Executors（按需） | 在指定平台完成编码/构建/训练/测试；永不直接与用户对话 | 承担开发/编译/训练/测试功能的机器 |
| **看护者** Guardian（0–1） | 维护除自己外所有智能体的更新与恢复；经独立渠道可被用户直接访问 | **独立物理机**（防单点） |
| **工具门禁** Tool Gate | 所有智能体共用工具服务的统一鉴权与审计 | 基础设施层 |

配套约定：模型层共用现有网关（零新订阅）；工具层网络化 + 凭证服务端持有；同步分层「知识跟代码走、配置跟 git 走、记忆留本地、凭证集中保管」；纪律分层「门留在编排层、规则进 AGENTS.md、权限进工具配置」。

## 仓库结构

```
astra-agent-constellation/
├── DESIGN.md            ← 文档站界面设计规范（IBM Carbon 风格）
├── mkdocs.yml           ← 文档站配置（简体中文）
├── docs/                ← 卷一：规范正文（简体中文，RFC 2119）
│   ├── 00-overview.md … 09-game-day.md
│   └── references/      ← 卷三：决策记录（ADR 0001–0005）
├── templates/           ← 卷二：参考实现（英式英语，可复制适配）
│   ├── AGENTS.md / opencode.json / dotfiles/ / agent-registry/ / task-brief/
└── scripts/             ← 配套脚本（health-check.sh、registry-check.py）
```

## 快速开始

1. 阅读 [文档站](https://alrcatraz.github.io/astra-agent-constellation/) 的[采纳路径](docs/07-adoption.md)，从 **Phase 0（同步地基）** 开始——这是整个方案的命门。
2. 复制 `templates/` 下的模板到你的仓库/机器，按需适配。
3. 按 Phase 1→3 逐步落地，每阶段验收通过再进下一阶段。

## 本地构建文档站

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install mkdocs-material
mkdocs serve   # 或 mkdocs build
```

> 注意：界面按 IBM Carbon 规范设计（DESIGN.md），字体走系统字体栈，**不依赖 Google Fonts CDN**（国内可正常加载）。

## 版本

遵循三层 SemVer（与 astra 生态一致）：

| 层级 | 版本 | 用途 |
|:-----|:-----|:-----|
| official | `v0.1.0` | GitHub 公开副本 / registry.yaml / git tag（当前发布） |
| personal | `v0.1.0+alrcatraz.Y` | 私有副本个性化修订（真实拓扑覆盖后） |
| local | `v0.1.0+alrcatraz.Y.<variant>.Z` | 本机变体 |

> 正式版 `v1.0.0`：待 AIGate 开发完成后对应更新，并经过我们实际部署验证后再出。

## 许可

- 规范正文与决策记录（docs/、README、DESIGN.md）：**CC BY-SA 4.0**
- 模板与脚本（templates/、scripts/）：**MIT**（各目录含 LICENSE-MIT）

## 相关项目

- [astra-hub](https://github.com/alrcatraz/astra-hub) — astra 生态索引
- [astra-aigate](https://github.com/alrcatraz/astra-aigate) — AI Gate 工具门禁（Phase 4 域）
