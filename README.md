# Quant Platform

A 股个人量化交易平台 — 行情、策略、回测、模拟交易、告警、AI 助手一站式。

---

## 项目结构

```
.
├── backend/          # FastAPI 后端（Python 3.13 + SQLAlchemy 2.0 + TimescaleDB + Redis）
├── frontend/         # Next.js 前端（首页、行情、策略、回测、交易）
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

### 开发启动

```bash
cd backend
cp .env.example .env  # 填写数据库 / JWT / LLM 配置
uv sync
uv run alembic upgrade head
uv run python main.py  # 启动在 :8000
uv run python workers/market_worker/main.py
uv run python workers/strategy_worker/scheduler.py
uv run python workers/trade_executor/adapters/main.py
```

### 基础设施

```bash
docker compose --env-file .env.docker up -d  # PostgreSQL + Redis
```

---

## 前端

- **框架**：Next.js 16（App Router）
- **语言**：TypeScript
- **UI**：shadcn/ui + TailwindCSS
- **包管理**：pnpm

详见 `AGENTS.md` 技术栈与目录结构。

```bash
cd frontend
pnpm install
pnpm dev
```

## 一键部署

Linux/WSL 部署环境可在项目根目录执行：

```bash
cp .env.docker.sample .env.docker
cp backend/.env.example backend/.env
make docker-deploy
make docker-status
```

`docker-deploy` 会构建前后端镜像，启动 PostgreSQL、Redis、迁移任务、API、三个 Worker 和生产前端。默认只监听 `127.0.0.1`；端口或域名在 `.env.docker` 中设置。Windows 没有 GNU Make 时可直接运行：

```bash
docker compose --env-file .env.docker -f docker-compose.yml -f docker-compose.deploy.yml up -d --build
```

完整的 Ubuntu/Linux、systemd、Nginx、HTTPS、备份、升级与故障排查说明见 [`docs/deployment-linux.md`](docs/deployment-linux.md)。

---

## 当前阶段

- ✅ 后端 Phase 1-3 完成（行情、策略、回测、交易、告警去重、AI 助手）
- ✅ 前端首页、认证、行情、AI 分析、策略、回测与模拟交易主流程已接通
