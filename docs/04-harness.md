# 纪律传导

编排者（Hermes）有一整套行为纪律（阶段门、研究门、变更防护、收尾检查）。执行者（OpenCode）没有 Hermes 的插件 API——**纪律不能复制，要分层传导**。

## 1. 三层传导模型

| Hermes 的纪律机制 | 执行者的等价物 | 性质 |
|:------------------|:--------------|:-----|
| 研究门（先调研后动手） | 任务 brief 中写死「先读这些文件再改」；permissions 里 read 放行、edit 受限 | 编排层软约束 |
| 变更门（改动要经过编排者） | permissions 硬门：`git push *` → deny，`git commit *` → ask | 工具层硬锁 |
| 防死循环 | `doom_loop`：同一工具调用重复 N 次自动转询问 | 工具层硬锁 |
| 阶段纪律（plan→execute→verify） | AGENTS.md 行为规范 + 编排者验收对照契约 | 规则层软约束 |

**核心原则：门留在编排层，规则进 AGENTS.md，权限进工具配置。执行者保持轻量。**

## 2. 编排层（最强的一扇门）

- **MUST**：执行者永远只通过编排者的调用出现（headless、非交互）。
- **MUST**：编排者在任务 brief 中注入约束：「只实现 X，不碰 Y，跑验证命令 Z」。
- **MUST**：执行者返回后，编排者**重跑验证** + diff 审查——执行者自报「过了」不算数。
- **MUST**：编排者与用户一同分析确认项目规划与细节，再拆任务给执行者。
- **MUST**：技术路线行不通时，执行者**停下汇报**（卡点 + 已尝试 + 失败证据 + 建议方向），**不得自行换方案**继续推进——换路线是编排者的决定。
- **MUST**：验证命令失败时，执行者停下汇报原始输出与根因初判，**不得修改命令或预期结果来制造通过**。
- **MUST**：执行者发现范围外需求（bug、副作用、历史债）时，记入报告并停下，**不得顺手扩大改动范围**。

任务 brief 模板（见 [templates/task-brief/task-brief.md.example](https://github.com/alrcatraz/astra-agent-constellation/blob/main/templates/task-brief/task-brief.md.example)），复制到 `tasks/<TASK-ID>-<task-name>.md` 使用。简版结构：

```markdown
任务：<目标 + 为什么>
范围：<允许改动的文件/模块>
禁止：<不可触碰的部分 + 停止条件>
验证：<CI 等效命令 + 预期结果，如 tsc typecheck-core 零新增错误>
报告：<决策记录 + diff 摘要 + 验证输出>
```

**ACP 化（ADR 0006）**：协议化派发时，上述字段映射为 ACP content blocks
（Metadata → `_meta`、Objective/Scope/Stopping → text block、验收命令 →
逐条 text block、AGENTS.md → resource_link），完整映射见
[10 章 ACP 内容映射](10-acp-mapping.md)。task-brief.md 仍是执行者的工作文档
与人类可读完整版，与 ACP 传输并行存在。

## 3. 工具层（硬锁）

执行者配置文件（opencode.json）中声明 permissions：

```json
{
  "permissions": {
    "deny": ["git push *", "rm -rf *", "env"],
    "ask": ["git commit *", "git push origin main"],
    "allow": ["read", "edit", "bash"]
  }
}
```

- **MUST**：`git push` 默认 deny（推送到远端的唯一途径是编排者验收后执行）。
- **MUST**：`env` 默认 deny（防止执行者读取并回显凭证环境变量）。
- **SHOULD**：`doom_loop` 开启（同一工具调用重复 3 次转询问，防死循环烧 token）。
- **MUST NOT**：执行者被授予任何超出其工作目录的写权限。

**dsh 执行者的权限模型（等价实现，2026-08-14 实测）**：dsh 用沙箱策略替代
permissions 声明——`executor/cordis.yml`（模板 `templates/cordis-executor.yml.example`）
中 `sandbox-policy` 设 `mode: workspace-write`：

- **写墙**：workdir 外写入被沙箱直接拒绝并返回清晰错误（`file access denied ...
  outside my working directory`）——**无 OpenCode headless ask 挂起问题**，
  模型立即理解并报告，无需人工介入。
- **读自由**：workdir 外读取允许（执行者读参考材料/蓝图仓 brief 无需应答）。
- **/tmp 临时区可写**（平台临时区豁免，sandbox 设计行为）。
- **纪律 persona**：cordis.yml 的 acp-agent persona 声明「NEVER run git write
  operations (commit/push/rebase/reset/checkout)」——git 写操作归编排者。

两种实现满足同一硬锁规范：OpenCode 走 permissions 声明（deny 黑名单 +
external_directory ask），dsh 走沙箱写墙（workspace-write 强制边界）。

## 4. 规则层（AGENTS.md 行为规范）

项目 AGENTS.md 中声明行为要求，执行者加载项目即获得：

- 先读后改（动手前阅读相关文件并引用）
- 删除不留占位（见[可观察性](05-observability.md)的代码卫生条款）
- 注释只解释「为什么」，不记录「删了什么」
- 验证命令与预期结果写死，不临时发挥
- 路线不通停下汇报，不自行换方案（见[纪律传导](04-harness.md) §2 停止条件）

## 5. 看护者的纪律

看护者执行维护操作时，遵循同一套纪律的「维护版」：

- 变更前记录当前状态（agent 注册表 + git）
- 变更后验证（健康检查通过才算完成）
- 所有维护动作落 git 历史，可审计
- 涉及编排者的恢复操作，遵循预定义的恢复流程（见[双星模式](06-gemini-pattern.md)）

## 6. 纪律漂移的检测

- **SHOULD**：每月审查执行者的 permissions 配置是否被放宽（git 历史可查）。
- **SHOULD**：AGENTS.md 与 dotfiles 的变更走 git，漂移可通过 diff 发现。
- **MUST**：发现纪律放宽时，回滚到真源配置并记录原因。
