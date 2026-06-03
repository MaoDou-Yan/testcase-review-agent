---
name: testcase-review-agent
description: Generate complete software testing case sets from product prototypes, PRDs, UX flows, screenshots, or requirements documents. Use when the user asks for a QA/test-case agent, test case generation, AI tri-party review, optimized test cases, requirement coverage reports, or an HTML report with Excel export and copy actions.
---

# Testcase Review Agent

## Objective

Produce a complete, reviewable, and directly executable test case deliverable from product prototype and requirements input. Always follow these stages:

0. Extract and normalize requirements.
1. Generate the original test case set.
2. Simulate AI tri-party review from Dev, QA, and PM perspectives.
3. Optimize the test cases according to the review findings.
4. Generate review and requirement coverage reports.
5. Generate a real `.xlsx` workbook and wire the HTML download button to it.

The final deliverable should include an HTML report and a real `.xlsx` workbook unless the user explicitly requests another format.

## Input Handling

When the user provides prototype files, screenshots, PRDs, Markdown, Word/PDF documents, tables, or pasted requirements:

- Extract modules, pages, user flows, form fields, business rules, permissions, statuses, error states, notifications, and data constraints.
- Infer missing normal and abnormal scenarios conservatively from common product behavior, and mark them as inferred when needed.
- If critical inputs are missing, continue with available information and add assumptions in the report instead of blocking.
- For ambiguous business rules, include test cases that verify the most likely rule and call out the ambiguity in the review/report.

**Input prompt guidance** (shown to user when no file is attached):

> 请上传产品原型截图、PRD 需求文档、Markdown 或 Word/PDF 说明，我将为你生成：需求抽取清单 → 原始用例集 → AI 三方评审 → 优化后用例集 → 评审与覆盖度报告，并输出带下载 .xlsx 和筛选功能的 HTML 页面。

## Large Document Handling

When the input PRD or prototype is large (estimated >8,000 words or >5 modules):

- Split the work by primary module. Process modules sequentially.
- After each module's cases are generated, append them to the master list rather than rewriting from scratch.
- In the final report, note how many modules were processed and whether any were partially skipped.
- Do not truncate or summarize requirements silently; if context limits are reached, state which module processing stopped at and ask the user to continue.

## Idempotency of Case IDs

Within a single project or conversation session:

- Case IDs for the same function point must remain stable across re-runs.
- If the user re-runs the agent on the same PRD, reuse existing IDs for unchanged function points.
- New function points discovered in a re-run append IDs continuing from the highest existing number in that module.
- Explicitly note in the optimization record whether a case was retained, modified, or newly added.

## Stage 0: Requirement Extraction

Before creating cases, extract a structured requirement inventory:

- Modules and pages.
- Function points and business rules.
- Interfaces and integrated systems.
- Status transitions and illegal transitions.
- Permissions, roles, and data scopes.
- Field constraints and master data dependencies.
- Abnormal flows, retries, idempotency keys, duplicate messages, delayed callbacks, and out-of-order messages.
- Requirement ambiguities and product-confirmation items.

Output this inventory in the report as:

- `需求抽取清单`
- `需求疑点/待确认项`
- `接口与状态机专项覆盖`
- `需求追踪矩阵 RTM`

When the user requires fixed test case columns, keep requirement IDs and RTM outside the case table. When the user allows expanded columns, add `需求编号` to case tables.

## Stage 1: Original Test Case Set

Create a table with these fixed columns:

- 用例编号
- 一级模块
- 二级模块
- 功能点
- 用例标题
- 前置条件
- 用例步骤
- 预期结果
- 用例优先级

Rules:

- Number cases as `PrimaryModuleEnglish-SecondaryModuleEnglish-001`, for example `Login-Password-001`.
- Use stable English module names in PascalCase or concise English words.
- For each function point, include at least one normal scenario and at least one abnormal or boundary scenario where applicable.
- Use this priority standard:
  - P0: main chain blockers, settlement/stock/voucher impact, irreversible data impact.
  - P1: core abnormal flow, interface failure, idempotency, concurrency, data consistency, permission risk.
  - P2: boundary, audit log, retry detail, UI interaction, compatibility, low-frequency exception.
  - P3: low-risk display, auxiliary prompt, cosmetic or non-blocking check.
- Make steps executable and observable. Avoid vague wording such as "verify normal".
- Make expected results verifiable, including UI text, state changes, persisted data, permissions, audit logs, or downstream effects when relevant.

## Stage 2: AI Nine-Party Review (ISO 25010 Quality Model)

Review the original cases with nine professional roles aligned to ISO 25010 quality characteristics:

| 角色标识 | 角色名称 | 对应质量特性 | 评审维度 |
|----------|----------|--------------|----------|
| **Arch** | 开发架构师 | 可维护性、可移植性 | 模块性、可重用性、可分析性、可修改性、可测试性、适应性 |
| **Dev** | 开发工程师 | 功能适合性（实现层面） | 功能正确性、边界处理、异常分支、并发逻辑 |
| **QA** | 测试工程师 | 可靠性、可测试性 | 成熟性、可用性、容错性、易恢复性、场景覆盖、回归风险 |
| **PM** | 产品经理 | 功能适合性（业务层面） | 功能完整性、功能恰当性、业务规则、用户旅程 |
| **UX** | 用户体验设计师 | 易用性 | 可识别性、易学性、易操作性、用户差错防御、界面美感、可访问性 |
| **Sec** | 安全工程师 | 安全性 | 保密性、完整性、抗抵赖性、可审计性、真实性 |
| **Ops** | 运维工程师 | 可维护性、可靠性 | 可分析性、易恢复性、部署兼容性、监控告警、灰度回滚 |
| **Perf** | 性能工程师 | 性能效率 | 时间行为、资源利用、容量、并发承载、响应时间 |
| **DBA** | 数据工程师 | 数据完整性 | 数据一致性、迁移兼容性、备份恢复、数据生命周期 |

### Quality Characteristics Mapping

**功能适合性 (Functional Suitability)**
- 功能完整性 → PM：需求功能点是否全覆盖
- 功能正确性 → Dev：实现逻辑是否正确、边界是否处理
- 功能恰当性 → PM：功能是否解决业务问题、ROI 合理

**性能效率 (Performance Efficiency)**
- 时间行为 → Perf：响应时间、超时处理
- 资源利用 → Perf：CPU/内存/IO 占用、资源释放
- 容量 → Perf：大数据量处理、并发承载

**兼容性 (Compatibility)**
- 共存性 → Ops：多版本并存、灰度发布
- 互操作性 → Dev：接口协议、数据格式兼容

**易用性 (Usability)**
- 可识别性 → UX：功能可发现性、引导提示
- 易学性 → UX：新手引导、操作提示
- 易操作性 → UX：操作步骤数、快捷方式
- 用户差错防御 → UX：输入校验、误操作保护、撤销机制
- 界面美感 → UX：视觉一致性、布局合理性
- 可访问性 → UX：无障碍支持、键盘导航、屏幕阅读器

**可靠性 (Reliability)**
- 成熟性 → QA：正常场景稳定性、长期运行
- 可用性 → QA：系统可用率、故障频率
- 容错性 → QA：异常输入处理、降级策略
- 易恢复性 → Ops：故障恢复时间、数据恢复

**安全性 (Security)**
- 保密性 → Sec：数据脱敏、权限控制、传输加密
- 完整性 → Sec：防篡改、注入防护、CSRF/XSS
- 抗抵赖性 → Sec：操作审计、签名验证
- 可审计性 → Sec：日志完整性、追溯能力
- 真实性 → Sec：身份认证、会话管理

**可维护性 (Maintainability)**
- 模块性 → Arch：模块解耦、接口清晰
- 可重用性 → Arch：组件复用、公共逻辑抽取
- 可分析性 → Ops：日志可观测性、问题定位
- 可修改性 → Arch：配置化、扩展点设计
- 可测试性 → QA：可测试接口、Mock 能力

**可移植性 (Portability)**
- 适应性 → Ops：多环境适配、配置外部化
- 易安装性 → Ops：部署自动化、依赖管理
- 易替换性 → Arch：组件可替换、迁移方案

Output a review table with these columns:

- 用例编号
- 评审角色
- 评审意见/建议
- 缺陷类型

Use defect types aligned to ISO 25010 quality characteristics:

| 缺陷类型 | 对应质量特性 | 适用角色 |
|----------|--------------|----------|
| 逻辑遗漏 | 功能适合性 | Dev |
| 场景遗漏 | 可靠性 | QA |
| 表述不清 | 易用性 | QA/UX |
| 边界遗漏 | 功能适合性 | Dev |
| 数据一致性风险 | 功能适合性 | DBA |
| 交互不符 | 易用性 | UX |
| 优先级不准 | 功能适合性 | PM |
| 可验证性不足 | 可测试性 | QA |
| 安全漏洞 | 安全性 | Sec |
| 性能风险 | 性能效率 | Perf |
| 运维盲区 | 可维护性 | Ops |
| 数据完整性风险 | 功能适合性 | DBA |
| 易用性缺陷 | 易用性 | UX |
| 架构腐化风险 | 可维护性/可移植性 | Arch |

Only create review rows for meaningful findings. If a case passes all roles, do not force a fake issue; count it as review-passed in the report.

## Stage 3: Optimized Test Case Set

Generate the complete optimized case set with all original columns plus:

- 优化记录

Rules:

- Preserve original case IDs for modified cases.
- Add a concise optimization summary in `优化记录`, such as `已优化：补充边界值和可验证预期结果`.
- For unchanged cases, use `无`.
- For newly added cases, continue numbering within the same module, and use `新增：来自AI评审补充`.
- Remove only duplicate or invalid cases. If a case is removed, mention it in the report.
- Ensure every review finding is either reflected in optimized cases or explicitly explained as not adopted.

## Stage 4: Reports

Generate two reports.

### AI Review Summary Report

Include:

- 总用例数
- 评审通过数
- 驳回/修改数
- 问题分布 by defect type with count and percentage
- 9 role scores out of 100 (Arch/Dev/QA/PM/UX/Sec/Ops/Perf/DBA) with calculation breakdown
- Quality characteristic coverage radar data (8 dimensions)

**Scoring rules (deterministic):**

Start each role at 100. Apply the following deductions based on findings assigned to that role:

| Finding severity | Deduction per finding |
|---|---|
| P0 case with 逻辑遗漏 or 场景遗漏 | -8 |
| P0/P1 case with 安全漏洞 or 数据一致性风险 | -6 |
| P0/P1 case with 性能风险 or 数据完整性风险 | -6 |
| P0/P1 case with 边界遗漏 | -6 |
| Any case with 可验证性不足 | -4 |
| Any case with 运维盲区 or 架构腐化风险 | -4 |
| Any case with 表述不清 or 优先级不准 | -2 |
| Any case with 易用性缺陷 | -2 |
| Any case with 交互不符 (UX role) | -3 |
| Minor wording suggestion without functional impact | -1 |

Cap the minimum score at 0. Show the calculation breakdown in the report for each of the 9 roles (e.g., "Dev: 100 - 8(逻辑遗漏×1) - 4(可验证性不足×1) = 88", "Sec: 100 - 6(安全漏洞×1) = 94").

### Requirement Coverage Report

Compare before and after optimization:

- 功能点覆盖率 = 已覆盖功能点 / 总功能点 * 100%
- 场景覆盖率 = 覆盖场景数 / 总预估场景数 * 100%
- 提升幅度 = 优化后 - 优化前

Define scenario categories as positive, negative, boundary, permission, state transition, data consistency, network/error recovery, and UI interaction scenarios where applicable.

### Additional Report Sections

Include these sections when the product is workflow-heavy, interface-heavy, or cross-system:

- Requirement extraction inventory.
- Product-confirmation items table with ambiguity, impacted cases, owner, and risk level.
- Interface coverage table with source system, target system, trigger, payload key fields, idempotency/retry expectations, and failure handling.
- Status machine coverage table with valid transitions, invalid transitions, duplicate events, delayed callbacks, and out-of-order events.
- RTM table mapping requirement/function point to original and optimized case IDs.

## Final HTML Deliverable

Create a complete standalone HTML page. Use `assets/report-template.html` as the visual and interaction pattern.

The page must contain five tabs:

1. 需求抽取清单
2. 原始用例集
3. AI评审详情
4. 优化后用例集
5. 评审与覆盖度报告

### 需求抽取清单 Tab

The first tab displays the structured requirement extraction from Stage 0. It must contain these sections:

**模块与功能点** table with columns:
- 一级模块
- 二级模块
- 功能点
- 功能描述

**接口与集成系统** table with columns:
- 源系统
- 目标系统
- 接口/触发
- 数据内容
- 幂等/重试

**状态转换** table with columns:
- 触发事件
- 源状态
- 目标状态
- 备注

**需求疑点/待确认项** table with columns:
- 编号
- 疑点描述
- 影响范围
- 建议确认方
- 风险等级 (render as colored badge: 高=P0, 中=P1, 低=P2)

**接口与状态机专项覆盖** table with columns:
- 覆盖项
- 有效转换
- 无效转换
- 重复事件
- 延迟回调
- 乱序事件

This tab does not need a filter bar since it is reference documentation, not case data.

Each case table tab must include a **filter bar** with:

- 一级模块 dropdown (auto-populated from table data)
- 优先级 dropdown (P0/P1/P2/P3) — for case tabs
- 评审角色 and 缺陷类型 dropdowns — for review tab
- 关键词 text search (matches any column)
- Live row count display (e.g. "显示 12 / 48 条")

Interaction and export requirements:

- Include `下载Excel（含编辑）` button. **The button must always generate the xlsx from the current in-page table data at download time**, so that any in-page edits are included. Do not wire the button to a static pre-generated file path. Use the in-page JS xlsx builder from `assets/report-template.html`.
- The generated workbook must include these sheets: 原始用例集, AI评审详情, 优化后用例集.
- Use `scripts/write_xlsx.py` when running server-side batch generation outside the browser. For the interactive HTML report, the in-page JS builder takes precedence.
- Include `复制数据` button that copies visible (filtered, non-deleted) optimized cases to clipboard, reflecting any in-page edits.
- Render priority values (P0/P1/P2/P3) as colored badges in HTML tables.
- Keep styling clean, professional, and readable.
- Avoid depending on remote CDN assets so the file can be opened locally.

Inline editing requirements:

- All case tables (原始用例集, AI评审详情, 优化后用例集) must support in-page editing.
- Include a `✏ 开启编辑` / `✔ 完成编辑` toggle button in the toolbar. When edit mode is on:
  - All data cells become `contenteditable`. Focused cells show a yellow highlight border.
  - An action column appears with a 🗑 delete button per row. Deleted rows are visually struck through and excluded from download and copy.
  - A `＋ 新增行` button appends a blank editable row (highlighted green) to the active tab's table.
  - A `↩ 撤销全部` button restores all tables to their initial state via a pre-captured snapshot.
- A header badge shows "编辑中" or "已修改 N 行" while changes are pending.
- After edit mode is closed, priority badges are re-rendered for any updated priority cells.
- All edits (modified cells, new rows, deleted rows) must be reflected in the downloaded xlsx and copied clipboard data.

## Quality Checklist

Before finalizing:

- Confirm the "需求抽取清单" tab contains all five sections: 模块与功能点, 接口与集成系统, 状态转换, 需求疑点/待确认项, 接口与状态机专项覆盖.
- Confirm the requirement extraction tables accurately reflect the PRD content without遗漏.
- Confirm risk levels in 需求疑点 are rendered as colored badges (高=P0, 中=P1, 低=P2).
- Confirm all modules and function points from the requirements are represented.
- Confirm each major function has positive and negative coverage.
- Confirm all IDs match the required format and are stable relative to prior runs.
- Confirm review findings map to optimizations.
- Confirm coverage math is internally consistent.
- Confirm the HTML has working tabs (5 tabs total), filter bars, copy action, and the in-page xlsx download button.
- Confirm the edit mode toggle works: contenteditable cells, action column (delete/restore), add-row, reset-all, and the header edit badge.
- Confirm the downloaded xlsx is generated from current in-page data (including edits), opens as a styled workbook with header row formatting, column widths, and priority color fills.
- Confirm deleted rows are excluded from download and copy; new rows are included.
- Confirm scoring breakdown is shown and consistent with the deduction table.
- Confirm large-document processing notes (if applicable) are included in the report.
