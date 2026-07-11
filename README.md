# Quant Platform

A 股个人量化交易平台 — 行情、策略、回测、模拟交易、告警、AI 助手一站式。

---

## 项目结构

```
.
├── backend/          # FastAPI 后端（Python 3.13 + SQLAlchemy 2.0 + TimescaleDB + Redis）
├── frontend/         # Next.js 前端（待创建）
├── data/             # Docker 持久化数据（PostgreSQL / Redis）
├── docker-compose.yml
├── AGENTS.md         # AI 开发规范（怎么写代码）
├── CONVENTIONS.md    # 项目约定（接口格式 / 错误码 / WebSocket 协议）
├── DESIGN.md         # UI 设计规范（视觉风格）
├── docs/
│   ├── api.md        # API 接口文档
│   ├── database.md   # 数据库设计文档
│   └── product.md    # 产品文档
├── INTEGRATION_GUIDE.md
└── PHASE2_TECHDEBT.md
```

---

## AI 协作文档

AI 编写前端代码前，按以下顺序阅读：

| 顺序 | 文档 | 职责 |
|------|------|------|
| 1 | `AGENTS.md` | 开发纪律 — 技术栈、目录结构、代码规范、完成标准 |
| 2 | `CONVENTIONS.md` | 项目约定 — 响应格式、错误码、认证、分页、WebSocket、AI 对话 |
| 3 | `DESIGN.md` | 视觉规范 — 色彩、字体、组件、图表、涨跌色 |
| 4 | `docs/api.md` | 接口清单 — 所有端点的方法、参数、响应结构 |
| 5 | `docs/database.md` | 数据结构 — 表设计（参考用） |
| 6 | `docs/product.md` | 产品全貌 — 功能模块、页面规划 |
| 7 | `docs/devops.md` | 开发运维 — 改表结构、Docker、迁移、配置同步等常见操作 |

---

## 后端

- **框架**：FastAPI
- **语言**：Python 3.13
- **数据库**：PostgreSQL 15 + TimescaleDB（K 线 hypertable）
- **缓存 / 消息**：Redis 7（行情缓存 + pubsub）
- **ORM**：SQLAlchemy 2.0
- **迁移**：Alembic
- **包管理**：uv
- **数据源**：腾讯财经 → mootdx → AKShare（三级降级）

### 启动

```bash
cd backend
cp .env.example .env  # 填写数据库 / JWT / LLM 配置
uv sync
uv run alembic upgrade head
uv run python main.py  # 启动在 :8000
```

### 基础设施

```bash
docker compose --env-file .env.docker up -d  # PostgreSQL + Redis
```

---

## 前端（待创建）

- **框架**：Next.js 15（App Router）
- **语言**：TypeScript
- **UI**：shadcn/ui + TailwindCSS
- **包管理**：pnpm

详见 `AGENTS.md` 技术栈与目录结构。

---

## 当前阶段

- ✅ 后端 Phase 1-3 完成（行情、策略、回测、交易、告警去重、AI 助手）
- ⬜ 前端开发（进行中）
