# DESIGN.md

> 本文件定义整个量化交易平台的 UI 设计语言。
> AI 编写任何页面时**必须**遵循本规范。视觉一致性 > 视觉创新。

---

## 1. 整体设计风格

参考产品：

- TradingView（图表 / 行情表格）
- 项目首页（品牌 / 登录 / 平台框架）
- Linear（布局 / 间距 / 排版）
- Vercel Dashboard（卡片 / 空状态 / 导航）
- shadcn/ui（组件基底）

关键词：

- 极简、专业、金融科技
- 留白充足、信息密度高
- 动效轻微、不花哨

禁止：

- ❌ 业务工作区使用装饰性渐变背景（首页与认证页的视频淡出遮罩除外）
- ❌ 七彩按钮
- ❌ 大面积阴影（shadow-xl 及以上）
- ❌ 花哨动画
- ❌ 纯装饰性插图

---

## 2. 色彩系统

### 2.1 基础色板

> **分隔原则**：业务工作区以白色面板、轻灰背景和 1px 中性分隔线建立层级；胶囊用于搜索、主命令和状态切换，不把页面分区做成悬浮卡片。

| 语义 | 变量名 | 亮色值 | 暗色值 | 用途 |
|------|--------|--------|--------|------|
| 页面背景 Background | `--background` | `#F7F7F8` | `#131722` | 主内容区底色（最浅/最深） |
| 卡片/侧边栏 Card | `--card` | `#FFFFFF` | `#141414` | 浮于背景之上的面板 |
| 分区色块 Muted/Accent | `--muted` | `#F4F4F6` | `#2A2E39` | Tab 栏 / 输入框底 / 行间隔 |
| 次背景 Secondary | `--secondary` | `#F4F4F6` | `#2A2E39` | 卡片背景 / 表格条纹 |
| 边框 Border | `--border` | `#E5E5E7` | `#2A2E39` | 面板分割与表单边界 |
| 主色 Primary | `--primary` | `#101010` | `#F5F5F5` | 主按钮 / 链接 / 选中态 |
| 危险 Danger | `--danger` | `#EF4444` | `#EF4444` | 删除 / 错误 / 跌 |
| 成功 Success | `--success` | `#22C55E` | `#22C55E` | 成功提示 / 涨 |
| 警告 Warning | `--warning` | `#F59E0B` | `#F59E0B` | 警告 / 待处理 |
| 主文字 Foreground | `--foreground` | `#101010` | `#D1D4DC` | 标题 / 正文 |
| 次文字 Muted | `--muted-foreground` | `#737373` | `#868993` | 辅助说明 / 占位符 |

### 2.2 涨跌色（A 股惯例）

> A 股市场**红涨绿跌**，与国际市场相反。全站必须统一遵循。

| 语义 | 色值 | 用途 |
|------|------|------|
| 涨 Up | `#EF4444`（红） | 上涨数字 / 阳线 |
| 跌 Down | `#22C55E`（绿） | 下跌数字 / 阴线 |
| 平 Flat | `#6B7280`（灰） | 持平 |

**禁止**在行情相关页面使用「绿涨红跌」的国际配色。

### 2.3 暗色模式

已启用全局暗色模式，通过 `useThemeStore`（Zustand + persist）管理：

- 主题状态持久化到 `localStorage`（key: `quant-theme`）
- 通过 `document.documentElement.classList.toggle("dark")` 全局切换
- 所有 CSS 变量在 `.dark` 选择器下重新定义（见 `globals.css`）
- 主题切换按钮位于右侧导航栏底部（非页面局部）
- hydration 安全：store 含 `_hasHydrated` 标志，hydration 完成后才渲染主题相关 UI

| 变量 | 亮色 | 暗色 |
|------|------|------|
| `--background` | `#F7F7F8` | `#131722` |
| `--card` | `#FFFFFF` | `#1E222D` |
| `--popover` | `#FFFFFF` | `#1E222D` |
| `--muted` / `--accent` | `#F4F4F6` | `#2A2E39` |
| `--border` | `#E5E5E7` | `#2A2E39` |
| `--foreground` | `#101010` | `#D1D4DC` |

---

## 3. 圆角 Radius

统一 `8px`（Tailwind `rounded-lg`）。

| 元素 | 圆角 |
|------|------|
| 按钮 / 输入框 / 卡片 | `8px` |
| 小标签 / Badge | `6px` |
| 头像 | `50%`（圆形） |

禁止出现 `20px` / `30px` 大圆角。

---

## 4. 阴影 Shadow

尽量不用阴影。仅在以下场景使用：

| 场景 | 阴影 |
|------|------|
| Card Hover | `shadow-sm` |
| Dropdown / Popover / Dialog | `shadow-md` |

禁止 `shadow-lg` / `shadow-xl` / `shadow-2xl`。

---

## 5. 间距 Spacing

统一 **8px Grid** 系统。使用 Tailwind 间距 token：

```
1 = 4px    2 = 8px     3 = 12px    4 = 16px
5 = 20px   6 = 24px    8 = 32px    10 = 40px
12 = 48px  16 = 64px
```

禁止出现 `13px` / `19px` / `27px` 等非 8 的倍数的值（4px 半步允许）。

---

## 6. 字体 Typography

### 6.1 字族

- UI 字体：`Inter`（通过 `next/font` 加载）
- 数字 / 金额 / 价格：`Inter` + `font-variant-numeric: tabular-nums`（等宽数字对齐）

所有金额、价格、百分比、数量**必须**使用 `tabular-nums`，保证列对齐。

### 6.2 字号层级

| 层级 | 字号 | 字重 | 用途 |
|------|------|------|------|
| 页面标题 | `24px` | `700` | 页面主标题 |
| 一级标题 | `20px` | `600` | 区块标题 |
| 二级标题 | `18px` | `600` | 卡片标题 |
| 正文 | `14px` | `400` | 默认正文 |
| 辅助 | `12px` | `400` | 标签 / 时间 / 说明 |

行高统一 `1.5`，紧凑场景（表格）用 `1.25`。

---

## 7. 图标 Icon

统一使用 `lucide-react`。

- 大小：默认 `16px` / `20px`，按场景选
- 描边宽度：`1.5px`（`strokeWidth={1.5}`）
- 颜色继承 `currentColor`

禁止使用 HeroIcon / FontAwesome / Antd Icon / 自制 SVG（logo 除外）。

---

## 8. 按钮 Button

| 类型 | 样式 | 尺寸 |
|------|------|------|
| Primary | 蓝底（`#2563EB`）白字 | 高度 `36px`，`px-4` |
| Secondary | 白底描边（`border` `#E5E7EB`） | 同上 |
| Danger | 红底（`#EF4444`）白字 | 同上 |
| Ghost | 透明，hover 浅灰背景 | 同上 |
| Icon | 仅图标，`32×32px` | — |

- 所有按钮高度统一 `36px`（`h-9`）
- 圆角 `8px`
- 字号 `14px`
- 禁用态：`opacity-50 cursor-not-allowed`
- 加载态：显示 spinner，禁用点击

---

## 9. 表格 Table

风格参考 TradingView。

必须支持：

- ✅ Sticky Header（表头吸顶）
- ✅ Hover 行高亮（`bg-secondary`）
- ✅ 底部分页
- ✅ Loading Skeleton（首屏加载）
- ✅ Empty State（无数据时展示空状态组件）
- ✅ 数字列右对齐（`text-right tabular-nums`）
- ✅ 涨跌色着色

列间距紧凑，行高 `40px`~`48px`。斑马纹可选（用 `bg-secondary/50`）。

---

## 10. 卡片 Card

```
rounded-lg bg-card p-6
```

- **无硬边框**（不使用 `border border-border`），靠 `bg-card` 与 `bg-background` 的明度差浮起
- 无重阴影
- 内边距 `24px`（`p-6`）
- 标题区与内容区间距 `16px`

### 区域分隔规范

| 层级 | 背景 | 用途 |
|------|------|------|
| L0 页面底 | `bg-background` | 主内容区（最浅灰） |
| L1 面板 | `bg-card` | 侧边栏 / 信息栏 / K 线卡（白底浮起） |
| L2 分区 | `bg-muted/30` | Tab 栏 / 输入框底 / 列表偶数行 |
| L3 交互高亮 | `bg-accent` | hover / 选中态 |

**禁止用 `border-b` / `border-t` / `border-l` 做区域分隔**。仅在表单输入框、表格边框等必要场景使用 `border`。

---

## 11. 表单 Form

- Label 在上，字号 `14px`，`mb-1.5`
- Input 高度 `40px`（`h-10`），圆角 `8px`
- 必填项 Label 后加红色 `*`
- 错误提示：`text-danger text-xs mt-1`
- 聚焦态：`ring-2 ring-primary/20 border-primary`
- Select / DatePicker 统一 `40px` 高度

---

## 12. 加载状态 Loading

统一使用 **Skeleton**（骨架屏）。

- 颜色：`bg-secondary`
- 动画：`animate-pulse`
- 形状匹配实际内容（表格骨架用矩形行，卡片骨架用卡片轮廓）

禁止使用纯文字 `Loading...`。

局部按钮加载可使用 spinner。

---

## 13. 空状态 Empty

所有列表 / 表格的空状态必须包含：

| 元素 | 说明 |
|------|------|
| Icon | `lucide-react` 图标，`48px`，`text-muted` |
| Title | 简短标题，`18px` `font-semibold` |
| Description | 一句话说明，`14px` `text-muted` |
| CTA Button | 引导操作的按钮（如「创建策略」「添加自选股」） |

---

## 14. 动效 Motion

使用 `framer-motion`。

| 场景 | 时长 | 缓动 |
|------|------|------|
| 页面切换 | `200ms` | `ease-out` |
| 弹窗 / 抽屉 | `250ms` | `ease-out` |
| Hover / 过渡 | `150ms` | `ease` |

不要超过 `400ms`。禁止弹跳（`spring bounce`）、旋转等花哨动效。

---

## 15. 图表 Chart

统一使用 **TradingView Lightweight Charts**。

- K 线图：阳线红色 `#EF4444`，阴线绿色 `#22C55E`
- 折线图：主色 `#2563EB`
- 体积柱：半透明涨跌色
- 图表背景：`#FFFFFF`
- 网格线：`#F8F9FB`
- 十字线：`#E5E7EB` 虚线

禁止使用 ECharts（除非 Lightweight Charts 无法满足的特殊场景，需说明理由）。

回测净值曲线同样使用 Lightweight Charts 的折线图。

---

## 16. 响应式 Responsive

优先 Desktop。

| 断点 | 宽度 | 说明 |
|------|------|------|
| xl | `1440px` | 最佳体验 |
| lg | `1280px` | 主流桌面 |
| md | `1024px` | 小屏桌面 |
| sm | `768px` | 最低支持 |

低于 `768px` 时采用单工作区模式：默认只显示 K 线；告警、回测、交易通过右侧导航切换为全宽面板；回测完成后结果全宽显示。顶部搜索与右侧图标导航保持可用。

---

## 17. 导航布局

### 17.1 整体结构

```
┌──────────────────────────────────────────────────────────┐
│  [Logo]  [股票搜索框]          [持仓N] [成本¥]  [头像]    │  顶部栏 h-14
├────────────────────────────────────────────────┬─────────┤
│                                                │  📊     │
│           主内容区（浅灰底 bg-background）       │  🔔     │
│                                                │  </>    │  右侧导航 w-14
│  ┌─────────────────────────────────────┐      │  ⇄      │
│  │  右侧面板（白底 bg-card）            │      │  💹     │
│  │  自选股 / 告警 / AI（可切换）         │      │         │
│  └─────────────────────────────────────┘      │  ☀️/🌙  │  主题切换（底部）
└────────────────────────────────────────────────┴─────────┘
```

### 17.2 顶部栏（Navbar）

- 高度 `56px`（`h-14`），白色/暗色实底并使用 1px 底部分隔线
- 左侧：Logo + 统一股票搜索框（`StockSearch` 组件）
- 右侧：持仓数量 / 总成本 / 用户头像菜单
- 品牌图形、搜索胶囊和用户胶囊与首页保持一致；持仓摘要在移动端隐藏

### 17.3 右侧导航栏（RightNav）

- 宽度 `56px`（`w-14`），`bg-card` 实底并使用左分隔线
- 4 个导航图标（行情 / 告警 / 策略回测 / 交易），垂直居中（`flex-1`）
- 主题切换按钮（☀️/🌙）位于**底部**（`mt-auto`）
- hover 时左侧弹出中文 tooltip（`opacity-0 → group-hover:opacity-100`）
- 激活态：圆形 `bg-foreground text-background`
- hover tooltip 必须位于选中态左侧上层，不得被图标或面板遮挡

### 17.4 行情页面板切换

行情页（`/market`）是平台 hub。桌面端左侧保留 K 线，右侧面板通过 URL `?panel=` 参数切换；移动端使用上文单工作区模式：

| panel 参数 | 右侧面板 | 组件 |
|------------|---------|------|
| 无（默认） | 上半部自选股、下半部 AI 个股事件分析 | 内联 Watchlist + `<StockAnalysisPanel />` |
| `alerts` | 告警规则列表 | `<AlertPanel />` |
| `backtest` | 策略选择、参数、历史回测 | `<StrategyBacktestPanel />` |
| `trading` | 下单、订单、持仓 | `<TradingPanel />` |

策略编辑、完整订单/账户管理仍保留独立页面；主要工作流在行情 hub 内完成。

### 17.5 主导航分组

1. 行情（自选股 / K 线 / AI 个股分析 / 告警面板）
2. 策略（策略列表 / 回测）
3. 交易（订单 / 持仓 / 券商账户）

---

## 18. AI 要求

生成任何页面时：

- ✅ 优先保证**布局一致性**，而非视觉创新
- ✅ 不要自行发挥设计
- ✅ 不要修改整体设计语言
- ✅ 整个网站保持统一风格
- ✅ 颜色 / 间距 / 字号必须使用本文件定义的值，不要自创
- ✅ 所有数字（价格 / 金额 / 百分比 / 数量）使用 `tabular-nums`
- ✅ 涨跌色遵循 A 股红涨绿跌

---

## 19. 股票搜索组件

全站统一使用两个搜索组件：

### 19.1 StockSearch（内联搜索框）

- 用于顶部导航栏的搜索入口
- 圆角输入框，`bg-muted/50` 底色，focus 时 `bg-muted`
- 300ms 防抖，结果下拉为 `bg-popover shadow-lg`（无边框）
- 键盘导航：↑↓ 选中、Enter 确认、Esc 关闭
- 选中后清空输入（`clearOnSelect`）

### 19.2 StockSearchDialog（弹窗搜索）

- 用于「添加股票」「空状态选股」场景
- TradingView 风格：居中弹出，600px 宽，`rounded-xl shadow-2xl`
- 搜索框 + 筛选 Tab（全部 / 沪市 / 深市 / 北交所）
- 结果列表：左侧 `text-primary` 代码 + 右侧 `text-foreground` 名称
- 键盘导航同上

**禁止在不同入口使用不同的搜索 UI**，统一走这两个组件。

### 19.3 暗色模式图表适配

K 线图（Lightweight Charts）需根据当前主题切换配色：

| 元素 | 亮色 | 暗色 |
|------|------|------|
| 图表背景 | `#FFFFFF`（`--card`） | `#141414`（`--card`） |
| 网格线 | `#EEF0F4`（`--muted`） | `#1C1C1C`（`--muted`） |
| 文字 | `#111827`（`--foreground`） | `#E5E7EB`（`--foreground`） |
| 十字线 | `#E5E7EB` 虚线 | `#2A2A2A` 虚线 |

图表组件应从 `useThemeStore` 读取当前主题，主题切换时重新应用配色。
