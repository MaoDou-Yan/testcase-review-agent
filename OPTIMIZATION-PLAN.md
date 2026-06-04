# Testcase Review Agent v3 - 优化执行方案

> 生成日期：2026-06-04
> 基于项目全量代码审查，覆盖 SKILL.md、generate_report.py、report-template.html、write_xlsx.py 及项目结构。

---

## 一、问题总览

| 编号 | 类别 | 问题 | 严重度 |
|------|------|------|--------|
| #1 | 架构 | generate_report.py 数据与渲染耦合，641 行硬编码，不可复用 | 高 |
| #2 | 架构 | 模板 JS 修改依赖 js.replace 字符串精确匹配，静默失败风险 | 高 |
| #3 | 架构 | 模板 FILTER_CONFIG 列索引与生成报告不一致（priorityCol:8 vs 实际 9） | 高 |
| #4 | SKILL.md | 文件编码：实际 UTF-8 正常，PowerShell 控制台显示乱码（已确认无需修复） | 低 |
| #5 | SKILL.md | 指令 17KB 过重，实现细节与策略混杂，消耗大量 token | 中 |
| #6 | SKILL.md | 评分规则机械确定，与 AI 评审的灵活性矛盾 | 中 |
| #7 | 前端 | 暗色主题打印/PDF 导出不可读，xlsx JS 端 header 色与 Python 端不一致 | 中 |
| #8 | 前端 | 多列表格无横向滚动，窄屏无法阅读 | 中 |
| #9 | 前端 | 编辑模式 innerHTML 写入用户输入，存在 XSS 风险 | 低 |
| #10 | 前端 | 下载文件名使用 UTC 时区，中国用户可能日期差一天 | 低 |
| #11 | 工程 | 无数据校验，字段缺失时 HTML 静默损坏 | 中 |
| #12 | 工程 | 临时文件（prd_content.txt、temp_prd_*.txt）未排除出版本控制 | 低 |
| #13 | 工程 | Python 端和 JS 端 xlsx 样式重复且不一致 | 低 |
| #14 | 体验 | 大 PRD 场景缺少渐进式反馈，一次生成全部阶段 | 中 |
| #15 | SKILL.md | 大文档处理策略不够具体，无 token 预算分配规则 | 中 |

---

## 二、优化架构

### 目标架构

```
输入 PRD
    ↓
[AI Agent] ← SKILL.md（策略层，~3KB）
    ↓ 产出
output/report-data.json    ← 结构化数据（用例、评审、需求、评分）
    ↓
[report_builder.py] ← report-template.html（含 CSS/JS 交互）
    ↓ 渲染
output/report.html          ← 最终交付物
```

### 核心原则

1. **数据与渲染分离**：AI 只产出结构化 JSON，报告组装由脚本完成。
2. **模板驱动**：HTML 结构、样式、交互逻辑全部由模板承载，SKILL.md 不重复描述。
3. **单一数据源**：评分、样式常量、列定义等只在一个地方维护。
4. **防御性编程**：数据校验、编码安全、打印适配作为基线要求。

---

## 三、执行计划

### Phase 1: 基础修复（预计 30 分钟）

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| 1a | 检查 SKILL.md 编码 | ✅ 已完成 | 确认 UTF-8 无 BOM，中文完整，无需修复 |
| 1b | 更新 .gitignore | 待执行 | 排除 prd_content.txt、temp_prd_*.txt 等中间产物 |

**1b 具体改动：**

在 `.gitignore` 中确认已有以下条目（当前已存在 `temp_*` 和 `prd_content.txt`）：
```
temp_*
prd_content.txt
```

若缺少其他中间产物条目，补充即可。

---

### Phase 2: 架构重构（预计 2-3 小时）

#### 2a. 定义 report-data.json schema

AI agent 产出的 JSON 结构定义，所有下游消费方（report_builder.py、未来可能的其他格式导出）共用此 schema。

```jsonc
{
  "meta": {
    "title": "测试用例评审报告 - 知识库问答模块",
    "subtitle": "基于 ISO 25010 质量模型的 AI 九方评审",
    "generated_at": "2026-06-04T10:00:00+08:00",
    "prd_name": "知识库问答模块需求文档（PRD）"
  },

  // Stage 0: 需求抽取
  "requirements": {
    "modules": [
      { "level1": "用户端问答", "level2": "输入与发送", "feature": "问答输入框", "description": "支持自然语言输入..." }
    ],
    "interfaces": [
      { "source": "用户端", "target": "语义匹配引擎", "trigger": "语义匹配请求", "payload": "用户问题文本...", "idempotent": "幂等：重复问题返回历史答案" }
    ],
    "status_transitions": [
      { "trigger": "新增词条", "from": "—", "to": "下架", "note": "新增词条默认下架状态" }
    ],
    "ambiguities": [
      { "id": "AMB-001", "description": "语义相似度阈值未定义", "scope": "智能匹配准确性", "owner": "产品/算法", "risk": "高" }
    ],
    "state_coverage": [
      { "item": "语义匹配", "valid": "精准/高相似/关键词", "invalid": "无匹配/超时", "duplicate": "重复问题直接返回", "delayed": "引擎超时3s兜底", "disorder": "暂无" }
    ]
  },

  // Stage 1: 原始用例集
  "raw_cases": [
    {
      "id": "QA-Send-001",
      "level1": "用户端问答",
      "level2": "输入与发送",
      "feature": "问答输入框",
      "title": "正常输入并发送问题",
      "precondition": "用户已登录且有问答权限",
      "steps": "1. 在问答输入框输入问题\n2. 点击发送按钮",
      "expected": "1. 问题成功发送\n2. 输入框清空\n3. 用户问题以对话气泡展示",
      "priority": "P0"
    }
  ],

  // Stage 2: AI 评审发现
  "review_findings": [
    {
      "case_id": "QA-Send-003",
      "role": "Dev",
      "opinion": "500 字边界用例缺少超长输入截断机制的验证",
      "defect_type": "边界遗漏"
    }
  ],

  // Stage 3: 优化后用例集
  "optimized_cases": [
    {
      "id": "QA-Send-001",
      "level1": "用户端问答",
      "level2": "输入与发送",
      "feature": "问答输入框",
      "title": "正常输入并发送问题",
      "precondition": "用户已登录且有问答权限",
      "steps": "1. 在问答输入框输入问题\n2. 点击发送按钮",
      "expected": "1. 问题成功发送\n2. 输入框清空\n3. 用户问题以对话气泡展示",
      "priority": "P0",
      "category": "功能",
      "optimization_note": "无"
    }
  ],

  // Stage 4: 评分与覆盖度
  "scoring": {
    "role_scores": {
      "Arch": { "name": "开发架构师", "score": 96, "breakdown": "100 - 4x1(架构腐化风险) = 96" },
      "Dev":  { "name": "开发工程师", "score": 78, "breakdown": "100 - 8x1 - 8x1 - 6x1 - 6x1 - 4x1 = 78" }
    },
    "defect_distribution": [
      { "type": "逻辑遗漏", "count": 3, "percentage": 10.0 }
    ],
    "quality_radar": [
      { "dimension": "功能适合性", "score": 95 }
    ],
    "coverage": {
      "func_orig": 35, "func_opt": 40, "func_total": 40,
      "scenario_orig": 78, "scenario_opt": 97
    },
    "rtm": [
      { "req_id": "F-QA-001", "feature": "问答输入框", "orig_cases": "QA-Send-001~005", "opt_cases": "QA-Send-001~006" }
    ],
    "summary": "原始55条用例经九方评审后..."
  }
}
```

#### 2b. 重构 generate_report.py

**改动范围：** 将现有 641 行脚本拆分为两个模块。

| 文件 | 职责 | 预估行数 |
|------|------|----------|
| `scripts/data_loader.py` | 读取 report-data.json，校验必填字段，返回结构化数据对象 | ~80 行 |
| `scripts/report_builder.py` | 读取模板 HTML，注入数据（JSON 嵌入 + CSS/JS 补丁），输出 report.html | ~150 行 |
| `generate_report.py` | 保留为入口脚本，串联 data_loader → report_builder，保持向后兼容 | ~20 行 |

**关键设计决策：**

- 数据注入方式：在 HTML `<head>` 中插入 `<script>window.__REPORT_DATA__ = {JSON};</script>`，JS 端从该全局变量读取数据并动态渲染表格。
- 模板中的表格 HTML 由 JS 端根据数据动态生成，而非 Python 端拼接 HTML 字符串。这样 Python 端只需负责注入 JSON，不再需要 `gen_case_rows()`、`gen_review_rows()` 等 HTML 拼接函数。
- 移除所有 `js.replace()` 字符串修补逻辑。

#### 2c. 模板引入 JSON 驱动渲染

**report-template.html 改动：**

1. 移除模板中的静态 `<table>` HTML，改为 JS 从 `window.__REPORT_DATA__` 动态生成。
2. `FILTER_CONFIG` 由 JS 根据实际渲染的表格列数自动推导，不再硬编码列索引。
3. 保留 CSS、编辑模式、xlsx 下载、复制等交互逻辑不变。

**JS 端数据渲染伪代码：**

```javascript
const DATA = window.__REPORT_DATA__;

// 动态渲染各 tab 表格
function renderRawCases() {
  const columns = ["用例编号","一级模块","二级模块","功能点","用例标题","前置条件","用例步骤","预期结果","用例优先级"];
  const rows = DATA.raw_cases;
  renderTable("raw-table", columns, rows, ["id","level1","level2","feature","title","precondition","steps","expected","priority"]);
}

// FILTER_CONFIG 自动推导
function buildFilterConfig(tableId) {
  const table = document.getElementById(tableId);
  const headers = Array.from(table.rows[0].cells).map(c => c.textContent.trim());
  // 根据列名自动定位模块列、优先级列等
}
```

#### 2d. 统一 xlsx 样式常量

**当前不一致：**

| 元素 | Python (write_xlsx.py) | JS (report-template.html) |
|------|----------------------|--------------------------|
| Header 填充色 | `FFD6E4F0`（浅蓝） | `FF1A2035`（深蓝黑） |
| P0 填充色 | `FFFFC7CE`（浅红） | `FFEF4444`（红） |
| P1 填充色 | `FFFFEB9C`（浅橙） | `FFF59E0B`（橙） |
| P2 填充色 | `FFFFFFCC`（浅黄） | `FFEAB308`（黄） |
| 边框色 | `FFD9DEE8` | `FF1E293B` |

**统一方案：** 以 `assets/xlsx-styles.json` 为单一数据源，Python 和 JS 各自读取。

```json
{
  "header_fill": "FFD6E4F0",
  "header_font_bold": true,
  "priority_colors": {
    "P0": "FFFFC7CE",
    "P1": "FFFFEB9C",
    "P2": "FFFFFFCC",
    "P3": null
  },
  "border_color": "FFD9DEE8"
}
```

- Python 端：`json.loads(Path("assets/xlsx-styles.json").read_text())`
- JS 端：模板中内联该 JSON 或由 Python 注入

---

### Phase 3: 体验增强（预计 1-1.5 小时）

#### 3a. 打印适配

在 `report-template.html` 的 `<style>` 末尾追加：

```css
@media print {
  :root {
    --bg: #ffffff;
    --bg-card: #ffffff;
    --bg-elevated: #f8f9fa;
    --text: #1a1a1a;
    --text-muted: #555;
    --text-bright: #000;
    --border: #ccc;
  }
  header { background: #fff; border-bottom: 2px solid #333; }
  header::after { display: none; }
  .toolbar, .edit-badge, .col-action { display: none !important; }
  .tab { border: 1px solid #ccc; }
  .tab.active { background: #e8e8e8; }
  table { font-size: 10px; }
  .badge-p0 { background: #fee; color: #c00; }
  .badge-p1 { background: #fff3e0; color: #e65100; }
  .badge-p2 { background: #fffde7; color: #f57f17; }
  .badge-p3 { background: #f5f5f5; color: #666; }
  body { background-image: none; }
}
```

#### 3b. 表格横向滚动

```css
section > table, section > div > table {
  display: block;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

@media (max-width: 768px) {
  table { font-size: 12px; }
  th, td { padding: 6px 8px; white-space: nowrap; }
}
```

#### 3c. 编辑模式防 XSS

在 `toggleEdit()` 和 `resetEdits()` 中，将所有 `td.innerHTML = ...` 改为 `td.textContent = ...`（仅保留 badge 渲染时使用 `innerHTML`，但 badge 内容由代码控制，非用户输入）。

#### 3d. 下载文件名时区修正

```javascript
// 替换前
a.download = "测试用例集_" + new Date().toISOString().slice(0,10) + ".xlsx";
// 替换后
a.download = "测试用例集_" + new Date().toLocaleDateString("sv-SE") + ".xlsx";
```

#### 3e. SKILL.md 拆分

**当前 SKILL.md 结构（372 行，17KB）：**

- YAML frontmatter + 目标描述
- Stage 0-4 的详细实现指令（HTML 结构、CSS class、JS 交互细节）
- 质量检查清单

**拆分后：**

| 文件 | 内容 | 预估大小 |
|------|------|----------|
| `SKILL.md` | 策略层：目标、阶段定义、输入输出规范、质量标准、大文档处理策略、幂等性规则 | ~3KB |
| `assets/report-spec.md` | 实现层：HTML 结构、CSS 变量、JS 交互规范、编辑模式、xlsx 下载、复制功能 | ~8KB（被 SKILL.md 引用） |

SKILL.md 末尾引用：`> 详细实现规范见 assets/report-spec.md`

#### 3f. 评分逻辑脚本化

**当前流程：** AI 读取评分规则 → 手动计算每个角色的扣分 → 硬编码到报告数据中。

**优化后：** AI 只产出 `review_findings`（每条包含 case_id、role、defect_type），评分由脚本自动完成。

在 `scripts/report_builder.py` 中新增：

```python
DEDUCTION_RULES = {
    ("逻辑遗漏", "P0"): 8,
    ("场景遗漏", "P0"): 8,
    ("安全漏洞", "P0"): 6,
    ("安全漏洞", "P1"): 6,
    ("数据一致性风险", "P0"): 6,
    ("数据一致性风险", "P1"): 6,
    # ... 其余规则
}

def compute_role_scores(findings, raw_cases):
    """根据评审发现和用例优先级自动计算九方评分。"""
    scores = {role: 100 for role in ROLES}
    case_priority_map = {c["id"]: c["priority"] for c in raw_cases}
    for f in findings:
        priority = case_priority_map.get(f["case_id"], "P2")
        deduction = DEDUCTION_RULES.get((f["defect_type"], priority), 0)
        if deduction == 0:
            # 通用扣分规则
            deduction = GENERIC_DEDUCTION.get(f["defect_type"], 0)
        scores[f["role"]] = max(0, scores[f["role"]] - deduction)
    return scores
```

SKILL.md 中删除评分扣分表，替换为：`> 评分由 report_builder.py 自动计算，AI 只需产出评审发现。`

---

### Phase 4: 工程加固（预计 1 小时）

#### 4a. 数据校验

在 `scripts/data_loader.py` 中加入校验逻辑：

```python
def validate(data: dict) -> list[str]:
    errors = []
    # 用例 ID 格式校验：Module-Sub-NNN
    id_pattern = re.compile(r"^[A-Z][a-zA-Z]+-[A-Z][a-zA-z]+-\d{3}$")
    for case in data.get("raw_cases", []):
        if not id_pattern.match(case["id"]):
            errors.append(f"用例 ID 格式错误: {case['id']}")
        for field in ("level1", "feature", "title", "steps", "expected", "priority"):
            if not case.get(field):
                errors.append(f"用例 {case['id']} 缺少必填字段: {field}")
        if case.get("priority") not in ("P0", "P1", "P2", "P3"):
            errors.append(f"用例 {case['id']} 优先级非法: {case.get('priority')}")

    # 评审引用完整性
    case_ids = {c["id"] for c in data.get("raw_cases", [])}
    for f in data.get("review_findings", []):
        if f["case_id"] not in case_ids:
            errors.append(f"评审发现引用不存在的用例: {f['case_id']}")
        if f["role"] not in ROLES:
            errors.append(f"评审角色非法: {f['role']}")

    return errors
```

校验失败时打印警告但不阻断（allow `--strict` 模式阻断）。

#### 4b. 端到端冒烟测试

创建 `tests/test_smoke.py`：

```python
def test_report_generation():
    """用示例数据生成报告，校验基本结构完整性。"""
    data = json.loads(Path("output/report-data.json").read_text("utf-8"))
    html = generate_report(data)

    # 5 个 tab 存在
    assert 'data-tab="requirements"' in html
    assert 'data-tab="raw"' in html
    assert 'data-tab="review"' in html
    assert 'data-tab="optimized"' in html
    assert 'data-tab="report"' in html

    # 表格有数据行
    assert html.count("<tr>") > 50

    # 下载按钮存在
    assert "downloadXlsx()" in html
    assert "copyOptimized()" in html

    # 编辑功能存在
    assert "toggleEdit()" in html
    assert "contenteditable" in html
```

#### 4c. 全链路验证

手动验证清单：

1. `python generate_report.py` 运行无报错
2. 浏览器打开 `output/report.html`
3. 5 个 tab 切换正常，数据展示完整
4. 筛选栏下拉、关键词搜索功能正常
5. 开启编辑 → 修改单元格 → 新增行 → 删除行 → 撤销全部 → 完成编辑
6. 下载 xlsx → 打开文件确认 3 个 sheet、样式、数据正确
7. 复制数据 → 粘贴到文本编辑器确认格式正确
8. `Ctrl+P` 打印预览确认浅色主题可读

---

## 四、依赖关系

```
Phase 1 (基础修复)
    │
    ▼
Phase 2 (架构重构)
    2a ──▶ 2b ──▶ 2c ──▶ 2d
    │
    ▼
Phase 3 (体验增强)
    ├── 3a, 3b, 3c, 3d（可并行）
    └── 3e, 3f（可并行）
    │
    ▼
Phase 4 (工程加固)
    4a ──▶ 4b ──▶ 4c
```

## 五、预计工时

| 阶段 | 时间 | 产出物 |
|------|------|--------|
| Phase 1 | ~30 min | 更新后的 .gitignore |
| Phase 2 | ~2-3 h | report-data.json schema、重构后的 report_builder.py、模板数据驱动改造、xlsx-styles.json |
| Phase 3 | ~1.5 h | 打印样式、移动端适配、XSS 修复、时区修正、精简版 SKILL.md、自动评分 |
| Phase 4 | ~1 h | 数据校验、冒烟测试、验证通过 |
| **合计** | **~5.5-6.5 h** | |

## 六、风险与回退

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 模板 JS 改造引入回归 | 编辑/下载/复制功能异常 | Phase 4 冒烟测试覆盖关键路径 |
| JSON schema 变更影响现有 agent 产出 | 需重新生成数据 | schema 设计时保持向后兼容，必填字段最小化 |
| SKILL.md 拆分后 agent 理解偏差 | 报告质量下降 | 拆分后用同一 PRD 对比前后产出 |
| 打印样式与暗色主题冲突 | 视觉不一致 | @media print 隔离，不影响屏幕显示 |
