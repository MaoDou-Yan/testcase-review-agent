# HTML Report Implementation Specification

This document defines the HTML report structure, styling, and interaction patterns for the Testcase Review Agent.

## Report Structure

The report is a standalone HTML file with 5 tabs:

1. **需求抽取清单** - Requirement extraction inventory
2. **原始用例集** - Original test case set
3. **AI评审详情** - AI review findings
4. **优化后用例集** - Optimized test case set
5. **评审与覆盖度报告** - Review and coverage report

## Data Format

The report consumes a `report-data.json` file with this structure:

```jsonc
{
  "meta": {
    "title": "测试用例评审报告 - {模块名}",
    "subtitle": "基于 ISO 25010 质量模型的 AI 九方评审",
    "generated_at": "ISO-8601 timestamp",
    "prd_name": "PRD document name"
  },
  "requirements": {
    "modules": [{ "level1", "level2", "feature", "description" }],
    "interfaces": [{ "source", "target", "trigger", "payload", "idempotent" }],
    "status_transitions": [{ "trigger", "from", "to", "note" }],
    "ambiguities": [{ "id", "description", "scope", "owner", "risk" }],
    "state_coverage": [{ "item", "valid", "invalid", "duplicate", "delayed", "disorder" }]
  },
  "raw_cases": [{ "id", "level1", "level2", "feature", "title", "precondition", "steps", "expected", "priority" }],
  "review_findings": [{ "case_id", "role", "opinion", "defect_type" }],
  "optimized_cases": [{ "id", "level1", "category", "level2", "feature", "title", "precondition", "steps", "expected", "priority", "optimization_note" }],
  "scoring": {
    "role_scores": { "RoleKey": { "name", "score", "breakdown" } },
    "defect_distribution": [{ "type", "count", "percentage" }],
    "quality_radar": [{ "dimension", "score" }],
    "coverage": { "func_orig", "func_opt", "func_total", "scenario_orig", "scenario_opt" },
    "rtm": [{ "req_id", "feature", "orig_cases", "opt_cases" }],
    "summary": "HTML summary text"
  }
}
```

## Tab 1: 需求抽取清单

Contains 5 sections with tables:

| Section | Columns |
|---------|---------|
| 模块与功能点 | 一级模块, 二级模块, 功能点, 功能描述 |
| 接口与集成系统 | 源系统, 目标系统, 接口/触发, 数据内容, 幂等/重试 |
| 状态转换 | 触发事件, 源状态, 目标状态, 备注 |
| 需求疑点/待确认项 | 编号, 疑点描述, 影响范围, 建议确认方, 风险等级 |
| 接口与状态机专项覆盖 | 覆盖项, 有效转换, 无效转换, 重复事件, 延迟回调, 乱序事件 |

Risk levels render as colored badges: 高=P0, 中=P1, 低=P2.

## Tab 2-4: Case Tables

Each case table has a filter bar with:
- 一级模块 dropdown (auto-populated)
- 优先级 dropdown (P0/P1/P2/P3) - for case tabs
- 评审角色 and 缺陷类型 dropdowns - for review tab
- 关键词 text search (matches any column)
- Live row count display

### Filter Behavior
- Filters combine with AND logic
- Deleted rows are hidden from filter results
- Row count updates in real-time

## Tab 5: 评审与覆盖度报告

Contains:
- Core metrics (4 cards): 总用例数, 评审通过数, 驳回/修改数, 优化后总用例
- Coverage metrics (2 cards with progress bars): 功能点覆盖率, 场景覆盖率
- Role scores (9 cards): ISO 25010 quality model roles
- Summary notice
- Two-column grid: 问题分布 + 质量特性覆盖雷达
- RTM table

### Scoring Rules

Start each role at 100. Apply deductions:

| Finding | Case Priority | Deduction |
|---------|---------------|-----------|
| 逻辑遗漏, 场景遗漏 | P0 | -8 |
| 安全漏洞, 数据一致性风险, 数据完整性风险, 性能风险, 边界遗漏 | P0/P1 | -6 |
| 可验证性不足, 运维盲区, 架构腐化风险 | Any | -4 |
| 表述不清, 优先级不准, 易用性缺陷 | Any | -2 |
| 交互不符 (UX role) | Any | -3 |

Minimum score: 0. Show calculation breakdown.

## Styling

### CSS Variables
```css
:root {
  --bg: #0b0f1a;
  --bg-card: #111827;
  --bg-elevated: #1a2035;
  --text: #e2e8f0;
  --text-muted: #8892a8;
  --text-bright: #f8fafc;
  --border: #1e293b;
  --accent: #3b82f6;
}
```

### Priority Badges
- P0: Red (`--p0-bg`, `--p0-text`)
- P1: Orange (`--p1-bg`, `--p1-text`)
- P2: Yellow (`--p2-bg`, `--p2-text`)
- P3: Gray (`--p3-bg`, `--p3-text`)

### Print Styles
- Switch to light theme
- Hide toolbar, edit controls, action columns
- Reduce font size for compact printing

## Interactions

### Edit Mode
- Toggle button: ✏ 开启编辑 / ✔ 完成编辑
- All data cells become `contenteditable`
- Focus shows yellow highlight border
- Action column appears with 🗑 delete button
- ＋ 新增行 appends editable row
- ↩ 撤销全部 restores snapshot
- Header badge shows edit state

### XSS Prevention
- User input uses `textContent` for storage
- Badge rendering uses regex validation (`/^P[0-3]$/`)
- `esc()` helper escapes HTML entities

### Download
- Generates .xlsx from current in-page data
- Includes edits (new rows, deletions, modifications)
- Filename: `测试用例集_{YYYY-MM-DD}.xlsx` (local timezone)
- 3 sheets: 原始用例集, AI评审详情, 优化后用例集

### Copy
- Copies visible (filtered, non-deleted) optimized cases
- Tab-separated format for spreadsheet paste

## XLSX Styles

Read from `assets/xlsx-styles.json`:
```json
{
  "header_fill": "FFD6E4F0",
  "priority_colors": { "P0": "FFFFC7CE", "P1": "FFFFEB9C", "P2": "FFFFFFCC" },
  "border_color": "FFD9DEE8"
}
```

## Build Process

1. Python reads `report-data.json`
2. Python reads `report-template.html`
3. Python injects data as `<script>window.__REPORT_DATA__ = {...}</script>`
4. Python injects xlsx styles as `<script>window.__XLSX_STYLES__ = {...}</script>`
5. JS renders all tables dynamically from data
6. Output: standalone `report.html`
