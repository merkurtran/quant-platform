# DESIGN.md

> 本文件定义整个量化交易平台的 UI 设计语言。
> AI 编写任何页面时**必须**遵循本规范。视觉一致性 > 视觉创新。

---

## 1. 整体设计风格

参考产品：

- TradingView（图表 / 行情表格）
- Linear（布局 / 间距 / 排版）
- Vercel Dashboard（卡片 / 空状态 / 导航）
- shadcn/ui（组件基底）

关键词：

- 极简、专业、金融科技
- 留白充足、信息密度高
- 动效轻微、不花哨

禁止：

- ❌ 渐变背景
- ❌ 七彩按钮
- ❌ 大面积阴影（shadow-xl 及以上）
- ❌ 花哨动画
- ❌ 纯装饰性插图

---

## 2. 色彩系统

### 2.1 基础色板

| 语义 | 变量名 | 色值 | 用途 |
|------|--------|------|------|
| 背景 Background | `--background` | `#FFFFFF` | 页面主背景 |
| 次背景 Secondary | `--secondary` | `#F8F9FB` | 卡片背景 / 表格条纹 / 侧边栏 |
| 边框 Border | `--border` | `#E5E7EB` | 所有边框 / 分割线 |
| 主色 Primary | `--primary` | `#2563EB` | 主按钮 / 链接 / 选中态 |
| 危险 Danger | `--danger` | `#EF4444` | 删除 / 错误 / 跌 |
| 成功 Success | `--success` | `#22C55E` | 成功提示 / 涨 |
| 警告 Warning | `--warning` | `#F59E0B` | 警告 / 待处理 |
| 主文字 Text | `--text` | `#111827` | 标题 / 正文 |
| 次文字 Muted | `--muted` | `#6B7280` | 辅助说明 / 占位符 |

### 2.2 涨跌色（A 股惯例）

> A 股市场**红涨绿跌**，与国际市场相反。全站必须统一遵循。

| 语义 | 色值 | 用途 |
|------|------|------|
| 涨 Up | `#EF4444`（红） | 上涨数字 / 阳线 |
| 跌 Down | `#22C55E`（绿） | 下跌数字 / 阴线 |
| 平 Flat | `#6B7280`（灰） | 持平 |

**禁止**在行情相关页面使用「绿涨红跌」的国际配色。

### 2.3 暗色模式

当前版本仅做亮色模式。暗色模式预留 CSS 变量，后续迭代。

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
rounded-lg border border-border bg-background p-6
```

- 无重阴影
- 内边距 `24px`（`p-6`）
- 标题区与内容区间距 `16px`

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

低于 `768px` 的移动端暂不支持（后续迭代）。

侧边栏在 `lg` 以下可折叠为图标栏。

---

## 17. 导航布局

- 左侧固定侧边栏（`width: 240px`），含 Logo + 主导航
- 顶部栏（`height: 56px`），含页面标题 / 用户头像 / 通知
- 内容区 `max-width: 1440px`，`padding: 24px`

主导航分组：

1. 行情（自选股 / K 线）
2. 策略（策略列表 / 回测）
3. 交易（订单 / 持仓 / 券商账户）
4. 告警（规则 / 日志）
5. AI 助手（对话）

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
