# AGENTS.md

> 本文件定义 AI Agent 的开发规范。任何修改代码之前，**必须**遵守。
> 项目约定（接口格式 / 错误码 / WebSocket 协议等）见 `CONVENTIONS.md`。
> UI 视觉规范见 `DESIGN.md`。

---

## 0. 阅读顺序

每次开始工作前，按以下顺序阅读：

1. `AGENTS.md`（本文件）— 怎么写代码
2. `CONVENTIONS.md` — 接口契约 / 数据格式 / 通信协议
3. `DESIGN.md` — 页面长什么样
4. `docs/api.md` — 调哪个接口
5. `docs/database.md` — 数据结构（参考用，前端不直接操作 DB）

---

## 1. 第一原则

- **不要为了完成需求而重构整个项目。**
- 只修改当前需求涉及的代码。
- 保持 diff 最小。
- 优先修改已有文件，不要轻易新增文件。
- 新增文件必须符合目录结构（见下方「目录结构」）。

---

## 2. 技术栈

| 分类 | 选型 | 说明 |
|------|------|------|
| Framework | Next.js 15（App Router） | — |
| Language | TypeScript（strict） | 禁止 `any`（除极少数第三方兼容场景，需注释说明） |
| UI 组件 | shadcn/ui | 基于 Radix UI，按需 add |
| 样式 | TailwindCSS | 唯一样式方案 |
| 状态管理 | Zustand | 全局状态 |
| 表单 | React Hook Form | — |
| 校验 | Zod | 前端校验 + 类型推导 |
| 图表 | TradingView Lightweight Charts | K 线 / 折线 |
| 请求 | Axios | 封装在 `services/` |
| 表格 | TanStack Table v8 | 分页 / 排序 |
| 动效 | Framer Motion | — |
| 图标 | lucide-react | — |
| 日期 | dayjs | 已选定，禁止引入 moment |
| 通知 | sonner | Toast 提示 |
| WebSocket | 原生 WebSocket | 封装 hook |

---

## 3. 包管理器

统一使用 **pnpm**。

```
pnpm install
pnpm dev
pnpm build
```

禁止使用 `npm` / `yarn`。

---

## 4. 新增依赖

安装前必须确认：

1. 项目已存在同类库 → 不要重复安装
2. 已有 `dayjs` → 禁止装 `moment`
3. 已有 `axios` → 禁止装 `fetch` 封装库
4. 已有 `lucide-react` → 禁止装其他图标库
5. 已有 `zustand` → 不要引入 `redux` / `jotai` / `recoil`

安装命令：

```bash
pnpm add <package>
```

安装后在 PR / 任务报告中说明新增了什么依赖、为什么。

---

## 5. 目录结构

前端代码放在 `frontend/` 目录（与 `backend/` 平级）：

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router 路由
│   │   ├── (auth)/             # 登录 / 注册（无需鉴权布局）
│   │   ├── (dashboard)/        # 主应用（需鉴权布局）
│   │   │   ├── market/         # 行情
│   │   │   ├── strategies/     # 策略
│   │   │   ├── trading/        # 交易
│   │   │   ├── alerts/         # 告警
│   │   │   └── ai/             # AI 助手
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── components/             # 通用组件
│   │   ├── ui/                 # shadcn/ui 组件
│   │   ├── table/              # 表格相关
│   │   ├── chart/              # 图表相关
│   │   └── layout/             # 布局组件（Sidebar / Header）
│   ├── services/               # API 请求层（封装 axios）
│   ├── types/                  # TypeScript 类型定义
│   ├── hooks/                  # 自定义 Hooks
│   ├── stores/                 # Zustand stores
│   ├── lib/                    # 工具函数（axios 实例 / utils）
│   └── constants/              # 常量（错误码 / 枚举）
├── public/
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

新增文件必须落入上述结构，不要在根目录随意建文件。

---

## 6. 禁止修改的文件

以下文件**不要修改**，除非明确要求：

- `next.config.ts`
- `tsconfig.json`
- `tailwind.config.ts`
- `eslint.config.mjs`
- `.prettierrc`
- `backend/` 下的任何文件（前端任务不碰后端）
- `docker-compose.yml`
- 根目录 `AGENTS.md` / `DESIGN.md` / `CONVENTIONS.md`

---

## 7. API 请求规范

- 所有接口请求**统一放** `services/` 目录，按模块拆分（`auth.ts` / `market.ts` / `alerts.ts` / `strategies.ts` / `trading.ts` / `ai.ts`）。
- **禁止**在组件中直接 `axios.get()`。
- 统一通过 `lib/api.ts` 中封装的 axios 实例发请求。
- axios 实例必须处理：
  - 请求拦截：自动附加 `Authorization: Bearer <token>`
  - 响应拦截：解包 `{ code, message, data }`，`code !== 0` 时抛错
  - 401 自动刷新 token（用 refresh_token），刷新失败跳登录页
  - 统一错误 Toast（`sonner`）
- 所有接口类型放 `types/`，与服务端 schema 对应。

---

## 8. 类型规范

- 所有接口请求 / 响应类型放 `types/` 目录。
- 禁止大量 `any`。
- 优先用 `interface` 定义对象类型，`type` 定义联合 / 工具类型。
- 从 API 响应推导类型，避免手写重复。

---

## 9. 组件规范

- 组件超过 **150 行** → 拆分。
- 页面超过 **300 行** → 拆分。
- 组件文件使用 PascalCase（`StockTable.tsx`）。
- 通用组件放 `components/`，页面专属组件放在页面目录下。
- props 必须定义 `interface`，不要内联。

---

## 10. Hooks 规范

- 公共逻辑必须抽 hooks，放 `hooks/` 目录。
- 命名 `useXXX`（`useWatchlists` / `useKlines` / `useMarketSocket`）。
- 禁止复制代码——相同的请求逻辑抽成 hook。
- 数据请求优先使用自定义 hook 封装（含 loading / error / data 状态）。

---

## 11. CSS 规范

- 全部使用 Tailwind class。
- 禁止 `style={{}}` 内联样式（动态计算值除外，如图表宽度）。
- 禁止 `.css` 文件（`globals.css` 除外）。
- 颜色 / 间距 / 圆角必须使用 `DESIGN.md` 定义的值，通过 Tailwind token 引用。

---

## 12. 命名规范

| 对象 | 规范 | 示例 |
|------|------|------|
| 变量 / 函数 | camelCase | `fetchKlines` |
| 组件 | PascalCase | `KlineChart` |
| Hook | useXXX | `useAlerts` |
| 文件（组件） | PascalCase | `AlertList.tsx` |
| 文件（其他） | kebab-case | `market-service.ts` → 实际用 `market.ts` |
| 常量 | UPPER_SNAKE | `API_PREFIX` |
| 类型 / 接口 | PascalCase | `AlertRule` |

---

## 13. Import 规范

统一使用绝对路径（`@/`）：

```ts
import { Button } from "@/components/ui/button";
import { useKlines } from "@/hooks/use-klines";
import type { KlineItem } from "@/types/market";
```

禁止相对路径 `../../../`。

---

## 14. 注释规范

- 不要写无意义注释（如 `// 设置变量` `// 返回数据`）。
- 复杂逻辑必须解释**为什么**，不是**做什么**。
- 函数自解释优先，注释补充意图。
- 删除代码不要注释保留，直接删除。

---

## 15. 错误处理

所有请求必须：

1. `try / catch`
2. Toast 提示错误（`sonner`）
3. Loading 状态
4. Error State（错误时展示可重试的错误态）

禁止请求失败后页面无反馈。

---

## 16. Loading 状态

任何异步操作必须展示 Loading：

- 页面首次加载 → Skeleton 骨架屏
- 表格加载 → Skeleton 行
- 按钮提交 → spinner + 禁用
- 禁止「点击没反应」

---

## 17. Empty 空状态

任何列表 / 表格必须有 Empty State（Icon + Title + Description + CTA）。

---

## 18. Dialog 确认

危险操作必须二次确认：

- 删除
- 撤单
- 重置
- 启用 / 停用

使用 shadcn `AlertDialog`。

---

## 19. 表格交互

统一使用 TanStack Table：

- 分页（底部）
- 排序（点击表头）
- Loading（Skeleton）
- Empty（空状态）
- 数字列右对齐 + `tabular-nums`
- 涨跌色着色

---

## 20. 日志

- 开发阶段可用 `console.debug()`
- **提交前删除所有 `console.log` / `console.debug`**
- 生产代码不得保留 console 输出

---

## 21. 完成开发后必须执行

```bash
pnpm lint          # 必须修复全部错误
pnpm tsc --noEmit  # 不得存在类型错误
pnpm build         # 保证构建通过
```

三个命令全部通过后才算完成。

---

## 22. Commit 规范

- 不要修改无关文件。
- 保持 commit 干净。
- commit message 格式：`<type>(<scope>): <description>`
  - type: `feat` / `fix` / `refactor` / `style` / `chore`
  - 示例：`feat(market): 添加 K 线图组件`

---

## 23. 输出要求

完成任务时必须说明：

1. **修改了哪些文件**（列清单）
2. **为什么这样修改**（设计理由）
3. **是否新增依赖**（包名 + 用途）
4. **是否影响其他模块**（影响范围）
5. **还有哪些可以优化**（后续建议）

不要只回复 `Done`。
