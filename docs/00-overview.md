# 总览

本蓝图回答一个问题：**当你需要不止一个 AI 智能体协同工作时，它们应该如何组织？**

## 1. 问题背景

单个通用智能体（如 Hermes Agent）能处理大多数任务，但在三类场景下力不从心：

1. **长编码任务**——一次编码会话可能持续 30–100 轮工具调用。通用智能体的会话会被打断或上下文压缩，导致任务中途丢失状态。
2. **跨机构建-修复循环**——在一台机器上写代码、在另一台机器上编译验证。每次传输代码、等待构建、回报错误、再修改，往返成本极高。
3. **恢复与更新**——智能体自身需要升级、打补丁、故障恢复。如果主智能体所在的机器宕机，谁来恢复它？

**解决方案不是「更多智能体」，而是「有组织的智能体」。** 本蓝图给出一种位置化部署（只在承担开发、编译、训练、测试等功能的机器上部署执行者，不会遍布所有设备）、每类角色职责单一、信息同步边界清晰的架构。

## 2. 架构总览

<figure class="cn-figure">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 460" font-family="IBM Plex Sans, Noto Sans SC, sans-serif" role="img" aria-labelledby="cn-constellation-title cn-constellation-desc">
  <title id="cn-constellation-title">Astra Agent Constellation — 架构总览</title>
  <desc id="cn-constellation-desc">One orchestrator at the centre, positional executors on the sides, a guardian on a separate machine, and a tool gate shared by all agents.</desc>
  <rect width="800" height="460" fill="var(--cn-svg-bg)"/>
  <!-- Tool gate (bottom, shared) -->
  <rect x="250" y="380" width="300" height="56" fill="var(--cn-svg-surface)" stroke="var(--cn-svg-border)"/>
  <text x="400" y="402" text-anchor="middle" font-size="16" font-weight="600" fill="var(--cn-svg-fg)">工具门禁 Tool Gate</text>
  <text x="400" y="422" text-anchor="middle" font-size="12" fill="var(--cn-svg-fg-sub)">统一鉴权 · 审计 · 工具服务入口</text>
  <!-- Orchestrator (centre) -->
  <circle cx="400" cy="120" r="52" fill="var(--cn-svg-block)"/>
  <text x="400" y="112" text-anchor="middle" font-size="15" font-weight="600" fill="var(--cn-svg-on-block)">编排者</text>
  <text x="400" y="132" text-anchor="middle" font-size="12" fill="var(--cn-svg-on-block)">Orchestrator</text>
  <text x="400" y="150" text-anchor="middle" font-size="10" fill="var(--cn-svg-on-block)">唯一用户交互入口</text>
  <!-- Executors (left and right) -->
  <circle cx="120" cy="120" r="46" fill="var(--cn-svg-surface)" stroke="var(--cn-svg-accent)" stroke-width="2"/>
  <text x="120" y="112" text-anchor="middle" font-size="14" font-weight="600" fill="var(--cn-svg-fg)">执行者 #1</text>
  <text x="120" y="130" text-anchor="middle" font-size="11" fill="var(--cn-svg-fg-sub)">开发机</text>
  <text x="120" y="145" text-anchor="middle" font-size="10" fill="var(--cn-svg-fg-sub)">编码 · 测试</text>
  <circle cx="680" cy="120" r="46" fill="var(--cn-svg-surface)" stroke="var(--cn-svg-accent)" stroke-width="2"/>
  <text x="680" y="108" text-anchor="middle" font-size="14" font-weight="600" fill="var(--cn-svg-fg)">执行者 #N</text>
  <text x="680" y="126" text-anchor="middle" font-size="11" fill="var(--cn-svg-fg-sub)">按需部署</text>
  <text x="680" y="141" text-anchor="middle" font-size="10" fill="var(--cn-svg-fg-sub)">开发/编译/训练/测试</text>
  <!-- Guardian (top right, separate machine) -->
  <circle cx="680" cy="300" r="46" fill="var(--cn-svg-surface)" stroke="var(--cn-svg-accent)" stroke-width="2" stroke-dasharray="4 3"/>
  <text x="680" y="292" text-anchor="middle" font-size="14" font-weight="600" fill="var(--cn-svg-fg)">看护者</text>
  <text x="680" y="310" text-anchor="middle" font-size="11" fill="var(--cn-svg-fg-sub)">Guardian</text>
  <text x="680" y="325" text-anchor="middle" font-size="10" fill="var(--cn-svg-fg-sub)">独立物理机 · 恢复</text>
  <!-- User (top centre) -->
  <rect x="340" y="20" width="120" height="34" fill="var(--cn-svg-accent)"/>
  <text x="400" y="42" text-anchor="middle" font-size="14" font-weight="600" fill="var(--cn-svg-on-accent)">用户 User</text>
  <!-- Arrows -->
  <line x1="400" y1="54" x2="400" y2="68" stroke="var(--cn-svg-fg)" stroke-width="1.5"/>
  <line x1="347" y1="120" x2="174" y2="120" stroke="var(--cn-svg-fg)" stroke-width="1.5"/>
  <line x1="452" y1="120" x2="634" y2="120" stroke="var(--cn-svg-fg)" stroke-width="1.5"/>
  <line x1="634" y1="290" x2="452" y2="140" stroke="var(--cn-svg-fg)" stroke-width="1.5" stroke-dasharray="4 3"/>
  <line x1="400" y1="172" x2="400" y2="380" stroke="var(--cn-svg-border)" stroke-width="1.5" stroke-dasharray="4 3"/>
  <line x1="120" y1="166" x2="360" y2="380" stroke="var(--cn-svg-border)" stroke-width="1.5" stroke-dasharray="4 3"/>
  <line x1="680" y1="166" x2="440" y2="380" stroke="var(--cn-svg-border)" stroke-width="1.5" stroke-dasharray="4 3"/>
  <!-- Legend -->
  <text x="400" y="452" text-anchor="middle" font-size="11" fill="var(--cn-svg-fg-sub)">实线 = 调用链 · 虚线 = 健康检查 / 同步 / 门禁访问</text>
</svg>
</figure>

所有智能体共享同一套基础设施（模型网关、工具服务、凭证库），通过**同步分层**保持一致，通过**纪律传导**遵守同样的行为规范，通过**可观察性机制**接受同样的审计。

## 3. 设计决策（摘要）

| 决策 | 内容 | 理由 |
|:-----|:-----|:-----|
| 单一编排者 | Hermes 是唯一编排者，负责调用所有执行者并**与用户一同分析确认项目规划与细节** | 保持用户交互入口唯一；执行者永不直接与用户对话 |
| 位置化部署 | 只在承担开发/编译/训练/测试功能的机器上部署编码智能体，**不遍布所有设备**；执行者数量随工作负载按需增长 | 每个智能体是「会积累私有记忆的状态机」——多一个就多一份配置维护与凭证暴露面 |
| 同步分层 | 知识跟代码走、配置跟 git 走、记忆留本地、凭证集中保管 | 避免双向同步冲突；新机器靠 git log + AGENTS.md 自举 |
| 看护者独立 | 看护者必须部署在独立物理机 | 防单点故障：编排者所在机器宕机时，看护者仍能恢复它 |
| 不依赖厂商框架 | 不用官方 multi-agent 框架（DAG/共享内存/角色体系）；执行者实现可选，如 OpenCode | 保持工具栈与模型栈复用现有设施；不引入新订阅 |

## 4. 适合谁

本蓝图适合：

- 已有 1 个主用 AI 智能体（Hermes 或同类），需要引入编码专用智能体但不想失控的团队/个人
- 维护多台机器（开发机、构建机、服务器），希望明确「哪个智能体住在哪、凭什么同步」的运维者
- 关注可审计性——希望即使智能体解耦，错误思路与错误改动仍能被发现的人

不适合：

- 追求全设备铺开、每个 agent 都独立自主的「多智能体自由主义」
- 需要智能体之间实时互相对话的协作模式（本蓝图明确不做）
- 尚未建立 git 纪律、连 AGENTS.md 都没有的项目（请先做 Phase 0）

## 5. 规范性声明

本规范正文使用 RFC 2119 关键词：

- **MUST** —— 必须遵守，违反即不符合本规范
- **SHOULD** —— 推荐遵守，特殊情况可豁免但需记录理由
- **MAY** —— 可选，由采纳者自行决定

这些关键词嵌入中文正文中，保持原文形式。
