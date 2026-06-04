# 测试用例评审报告 — UI 重设计开发计划

> 目标：将现有深色主题仪表盘重构为浅色自适应主题，新增雷达图，修复渲染 bug，提升整体信息可读性。

---

## 背景与目标

当前系统存在以下问题：
1. 九方评分卡片中出现 `[object Object],[object Object]` 渲染 bug
2. 整体深色主题对比度不足，长时间阅读疲劳
3. 九方评审缺乏整体维度对比视图
4. 角色标签、缺陷类型标签无语义色彩区分
5. 优先级、优化记录等状态标签视觉权重不足

---

## 一、设计规范（Design Tokens）

所有颜色使用 CSS 变量，支持系统浅色/深色模式自动切换。

### 1.1 基础色板

使用以下颜色族，每色取 50（最浅背景）、400（中间调）、600（边框/强调）、800（深色文字）四个色阶：

| 用途 | 颜色族 | 背景 | 边框 | 文字 |
|------|--------|------|------|------|
| 信息/链接 | Blue | `#E6F1FB` | `#B5D4F4` | `#0C447C` |
| 成功/通过 | Teal | `#E1F5EE` | `#9FE1CB` | `#085041` |
| 警告/P1 | Amber | `#FAEEDA` | `#FAC775` | `#633806` |
| 危险/P0 | Red | `#FCEBEB` | `#F09595` | `#791F1F` |
| 架构角色 | Purple | `#EEEDFE` | `#AFA9EC` | `#3C3489` |
| 开发角色 | Green | `#EAF3DE` | `#C0DD97` | `#27500A` |
| 运维角色 | Teal | `#E1F5EE` | `#9FE1CB` | `#085041` |
| 性能角色 | Coral | `#FAECE7` | `#F0997B` | `#712B13` |
| 数据角色 | Gray | `#F1EFE8` | `#D3D1C7` | `#444441` |
| 产品角色 | Amber | `#FAEEDA` | `#FAC775` | `#633806` |
| 用户体验 | Pink | `#FBEAF0` | `#ED93B1` | `#72243E` |
| 安全角色 | Red | `#FCEBEB` | `#F09595` | `#791F1F` |

### 1.2 页面结构色

```css
--page-bg:        var(--color-background-tertiary)   /* 页面底色 */
--surface:        var(--color-background-primary)    /* 卡片/表格白色面 */
--surface-muted:  var(--color-background-secondary)  /* 表头/次级面 */
--border:         var(--color-border-tertiary)        /* 0.5px 默认边框 */
--border-strong:  var(--color-border-secondary)      /* hover/强调边框 */
--text-primary:   var(--color-text-primary)
--text-secondary: var(--color-text-secondary)
--text-hint:      var(--color-text-tertiary)
```

### 1.3 主强调色

```css
--accent:       #185FA5   /* 主按钮、激活 tab、边框左线 */
--accent-hover: #0C447C
```

---

## 二、全局布局与组件

### 2.1 Header 组件

```
┌─────────────────────────────────────────────────┐
│ 标题 + 副标题                      [徽章] [徽章] │
│ [下载Excel] [复制数据] [开始编辑] [新增行] [撤销] │
│ Tab1  Tab2  Tab3  Tab4  Tab5                     │
│                                   ^^^^^^^ 激活线 │
└─────────────────────────────────────────────────┘
```

- 背景：`--surface`，底部 `0.5px solid --border`
- 标题：`font-size: 16px; font-weight: 500`
- 副标题：`font-size: 12px; color: --text-hint`
- 徽章：`background: #E6F1FB; color: #0C447C; border: 0.5px solid #B5D4F4; border-radius: 20px; font-size: 11px; padding: 3px 8px`
- Tab 激活态：`color: #185FA5; border-bottom: 2px solid #185FA5`
- Tab 非激活：`color: --text-secondary; border-bottom: 2px solid transparent`

### 2.2 按钮规范

| 类型 | 样式 |
|------|------|
| 主要（下载） | `background: #185FA5; color: #fff; border: none` |
| 默认 | `background: --surface; border: 0.5px solid --border-strong; color: --text-primary` |
| 危险（撤销） | `color: #A32D2D; border-color: #F09595; background: transparent` |

所有按钮：`padding: 5px 11px; border-radius: 8px; font-size: 12px; cursor: pointer`

### 2.3 筛选栏（Filter Row）

- `display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 14px`
- label：`font-size: 12px; color: --text-secondary`
- select/input：`background: --surface; border: 0.5px solid --border-strong; padding: 5px 8px; border-radius: 8px; font-size: 12px`
- 条数统计：`margin-left: auto; font-size: 12px; color: --text-hint`

### 2.4 通用表格

```css
.table-wrap {
  border-radius: 12px;
  border: 0.5px solid var(--color-border-tertiary);
  overflow: hidden;
  overflow-x: auto;
  background: var(--color-background-primary);
}
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th {
  background: var(--color-background-secondary);
  color: var(--color-text-secondary);
  font-weight: 500;
  padding: 9px 12px;
  border-bottom: 0.5px solid var(--color-border-tertiary);
  white-space: nowrap;
}
td {
  padding: 8px 12px;
  border-bottom: 0.5px solid var(--color-border-tertiary);
  vertical-align: top;
  line-height: 1.5;
}
tr:last-child td { border-bottom: none; }
tr:hover td { background: var(--color-background-secondary); }
```

---

## 三、各页面实现要求

### Tab 1 — 需求抽取清单

**子区块 1：模块与功能点**

- 区块标题：左侧 `3px solid #378ADD` 竖线，`border-radius: 0`，`font-size: 13px; font-weight: 500`
- 表格列：一级模块 / 二级模块 / 功能点 / 功能描述
- 二级模块首次出现时，该单元格文字用 `color: #185FA5; font-weight: 500` 高亮（相同二级模块连续行不重复高亮）
- 功能点列：`font-weight: 500`
- 功能描述列：`color: --text-secondary; line-height: 1.6`

**子区块 2：接口与集成系统**

- 表格列：源系统 / 目标系统 / 接口/触发 / 数据内容 / 冪等/重试
- 源系统、目标系统：`font-family: monospace; font-size: 11px; color: #185FA5`
- 冪等/重试状态"待确认"：`background: #FAEEDA; color: #633806; padding: 2px 6px; border-radius: 8px; font-size: 11px`

---

### Tab 2 — 原始用例集

筛选项：优先级（全部/P0/P1）、关键词搜索，右侧显示"共 N 条"。

搜索联动：输入关键词时实时过滤表格行，更新条数。

表格列：用例编号 / 二级模块 / 功能点 / 用例标题 / 前置条件 / 用例步骤 / 预期结果 / 优先级

- 用例编号：`font-family: monospace; font-size: 11px; color: #185FA5`
- 用例标题：`font-weight: 500`
- 二级模块、功能点：`font-size: 11px; color: --text-secondary`
- 前置条件/用例步骤/预期结果：`font-size: 11px; color: --text-secondary; line-height: 1.5`
- 优先级标签见下方标签规范

---

### Tab 3 — AI 评审详情

筛选项：评审角色（全部 + 9 个角色）、缺陷类型（全部 + 9 种）、关键词搜索，三者联合过滤。

表格列：用例编号 / 评审角色 / 评审意见/建议 / 缺陷类型

**评审角色标签**（`font-size: 11px; font-weight: 500; padding: 2px 7px; border-radius: 4px`）：

| 角色 | 背景 | 文字 |
|------|------|------|
| QA | `#E6F1FB` | `#0C447C` |
| Dev | `#EAF3DE` | `#27500A` |
| Arch | `#EEEDFE` | `#3C3489` |
| PM | `#FAEEDA` | `#633806` |
| UX | `#FBEAF0` | `#72243E` |
| Sec | `#FCEBEB` | `#791F1F` |
| Ops | `#E1F5EE` | `#085041` |
| Perf | `#FAECE7` | `#712B13` |
| DBA | `#F1EFE8` | `#444441` |

**缺陷类型标签**（`font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 10px`）：

| 缺陷类型 | 背景 | 文字 |
|----------|------|------|
| 场景遗漏 | `#E6F1FB` | `#0C447C` |
| 逻辑遗漏 | `#EEEDFE` | `#3C3489` |
| 架构腐化风险 | `#FAEEDA` | `#633806` |
| 安全漏洞 | `#FCEBEB` | `#791F1F` |
| 数据一致性风险 | `#EAF3DE` | `#27500A` |
| 易用性缺陷 | `#FBEAF0` | `#72243E` |
| 性能风险 | `#FAECE7` | `#712B13` |
| 运维盲区 | `#E1F5EE` | `#085041` |
| 表述不清 | `#F1EFE8` | `#444441` |

---

### Tab 4 — 优化后用例集

筛选项：分类（全部/功能/安全/可维护）、优先级、关键词搜索。

表格列：用例编号 / 分类 / 二级模块 / 功能点 / 用例标题 / 前置条件 / 用例步骤 / 预期结果 / 优先级 / 优化记录

**优化记录标签**：
- 新增场景：`background: #EAF3DE; color: #27500A; border: 0.5px solid #C0DD97` + 前缀"新增"
- 更新内容：`background: #E6F1FB; color: #0C447C; border: 0.5px solid #B5D4F4` + 前缀"更新"
- 无变化：`color: --text-hint; font-size: 11px` 显示"无"

标签统一：`font-size: 11px; padding: 2px 7px; border-radius: 10px; display: inline-block`

---

### Tab 5 — 评审与覆盖度报告

#### 5.1 统计卡片区（4列网格）

`display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 16px`

每张卡片：
```css
background: var(--color-background-primary);
border: 0.5px solid var(--color-border-tertiary);
border-radius: 12px;
padding: 14px 16px;
```

| 卡片 | 数值 | 颜色 |
|------|------|------|
| 总用例数（原始）49 | `font-size: 26px` | `#185FA5` |
| 评审通过数 28，通过率 57% | `font-size: 26px` | `#0F6E56` |
| 驳回/修改数 21，驳回率 43% | `font-size: 26px` | `#854F0B` |
| 优化后总用例 58，净增 +9 | `font-size: 26px` | `#534AB7` |

标签：`font-size: 11px; color: --text-hint; letter-spacing: 0.3px; margin-bottom: 6px`
辅助信息（通过率等）：`font-size: 11px; color: --text-hint; margin-top: 3px`

#### 5.2 覆盖率卡片区（2列网格）

`display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px`

每张卡片同统计卡片样式。内容：
- 标签（大写+字间距）
- `起始值 → 最终值`（起始值灰色 20px，箭头灰色，最终值彩色 26px）
- 进度条：`height: 5px; background: --surface-muted; border-radius: 3px`，填充色：
  - 功能点覆盖率（100%）：`background: #1D9E75`
  - 场景覆盖率（64%）：`background: #BA7517`
- 说明文字：`font-size: 11px; color: --text-hint; margin-top: 6px`

#### 5.3 九方评分 + 雷达图（左右布局）

```
display: grid;
grid-template-columns: 1fr 260px;
gap: 16px;
align-items: start;
margin-bottom: 20px;
```

**左侧：九方评分网格**（`grid-template-columns: repeat(3, 1fr); gap: 8px`）

每张评分卡：
```css
background: var(--color-background-primary);
border: 0.5px solid var(--color-border-tertiary);
border-radius: 12px;
padding: 12px 14px;
```

内容：
- 角色名称：`font-size: 11px; color: --text-secondary; margin-bottom: 4px`
- 分数：`font-size: 24px; font-weight: 500`，颜色按分段：
  - ≥95 分：`#0F6E56`（绿）
  - ≥90 分：`#185FA5`（蓝）
  - ≥85 分：`#534AB7`（紫）
  - <85 分：`#854F0B`（琥珀）
- 进度条：`height: 3px`，颜色与分数色一致，宽度 = 分数%
- 缺陷标签（小胶囊）：`font-size: 10px; background: --surface-muted; color: --text-hint; padding: 1px 5px; border-radius: 6px`

**右侧：雷达图卡片**

卡片同评分卡样式，内边距 `16px`。

使用 **Chart.js 4.x**（`chart.umd.js`），类型 `radar`。

配置要点：
```javascript
{
  type: 'radar',
  data: {
    labels: ['Arch','Dev','QA','PM','UX','Sec','Ops','Perf','DBA'],
    datasets: [
      {
        label: '实际得分',
        data: [92, 86, 86, 92, 97, 88, 84, 84, 88],
        backgroundColor: 'rgba(55,138,221,0.12)',
        borderColor: '#378ADD',
        borderWidth: 2,
        pointBackgroundColor: '#378ADD',
        pointBorderColor: '#fff',
        pointRadius: 4,
      },
      {
        label: '基准线 80',
        data: [80, 80, 80, 80, 80, 80, 80, 80, 80],
        backgroundColor: 'rgba(192,221,151,0.08)',
        borderColor: '#97C459',
        borderWidth: 1,
        pointRadius: 0,
        borderDash: [4, 3],
      }
    ]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      r: {
        min: 70, max: 100,
        ticks: { stepSize: 10, font: { size: 10 }, backdropColor: 'transparent' },
        grid: { color: 'rgba(136,135,128,0.2)' },
        pointLabels: { font: { size: 11 } },
        angleLines: { color: 'rgba(136,135,128,0.2)' },
      }
    }
  }
}
```

图例（自定义 HTML，置于 canvas 下方居中）：
```html
<div style="display:flex;gap:12px;justify-content:center;margin-top:10px;font-size:11px">
  <span><span style="width:10px;height:10px;background:#378ADD;border-radius:2px;display:inline-block;margin-right:4px"></span>实际得分</span>
  <span><span style="width:10px;height:10px;background:#C0DD97;border-radius:2px;display:inline-block;margin-right:4px"></span>基准线 80</span>
</div>
```

#### 5.4 评审总结卡片

```css
background: var(--color-background-primary);
border: 0.5px solid var(--color-border-tertiary);
border-left: 3px solid #378ADD;
border-radius: 0 12px 12px 0;   /* 左侧无圆角，右侧有 */
padding: 18px 20px;
```

文字：`font-size: 13px; color: --text-secondary; line-height: 1.8`
关键词加粗：`font-weight: 500; color: --text-primary`
内部分隔线：`border-top: 0.5px solid --border; padding-top: 10px`

---

## 四、Bug 修复

### 4.1 九方评分 `[object Object]` 修复

**原因**：评分卡片下方渲染了对象数组，未进行字符串序列化。

**修复方式**：
- 检查评分卡数据结构，找到渲染缺陷标签的字段
- 若字段为对象数组（如 `[{text:'场景遗漏'}, ...]`），改为 `.map(item => item.text || item.label || String(item)).join('、')`
- 或改为渲染独立标签胶囊（见 5.3 评分卡规范）

---

## 五、实现优先级

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | 修复 `[object Object]` bug | 功能性问题，优先解决 |
| P0 | 整体浅色主题切换 | CSS 变量替换，影响全局 |
| P1 | 角色/缺陷标签语义配色 | Tab2/Tab3 可读性核心 |
| P1 | 雷达图新增 | 与九方评分卡并排，Tab5 |
| P2 | 统计卡片辅助信息 | 通过率、净增数等 |
| P2 | 覆盖率进度条颜色分段 | 按完成度用不同颜色 |
| P3 | 筛选联动优化 | 三筛联合过滤 + 条数实时更新 |

---

## 六、技术依赖

| 依赖 | 版本 | 用途 | CDN |
|------|------|------|-----|
| Chart.js | 4.4.1 | 雷达图 | `https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js` |
| Tabler Icons | 已加载 | 按钮图标 | 系统内置 |

Chart.js 注意事项：
- Canvas 不能直接读取 CSS 变量，颜色需使用硬编码 hex
- canvas wrapper 需设 `position: relative; height: 230px`，canvas 本身不设高度
- 使用 `responsive: true, maintainAspectRatio: false`

---

*本计划基于原型 Widget 代码提炼，可直接交付给 Claude 执行。建议按优先级分批提交，P0 问题单独一次 commit。*
