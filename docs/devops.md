# 开发运维手册

> 后端开发过程中常见的环境维护操作：改了表结构怎么迁移、换了 Docker 配置怎么重启、加了配置项怎么同步。
> 每次操作都给出具体命令，按场景查找即可。

---

## 场景速查

| 场景 | 去哪看 |
|------|--------|
| 改了 SQLAlchemy Model（加字段 / 改类型 / 加表） | [场景 1](#场景-1修改了-model-字段加列改类型加表) |
| Docker 配置改了（镜像 / 端口 / 环境变量） | [场景 2](#场景-2修改了-docker-composeyml-或-envdocker) |
| `.env` 加了新配置项 | [场景 3](#场景-3新增了配置项-env-example-同步) |
| 要彻底重置数据库（清空重建） | [场景 4](#场景-4彻底重置数据库) |
| 后端启动报 ImportError / 找不到模块 | [场景 5](#场景-5后端启动报-importerror) |
| 前端 `pnpm dev` 报 ignored builds | [场景 6](#场景-6前端-pnpm-dev-报-ignored-builds) |
| 同事拉代码后首次跑起来 | [场景 7](#场景-7同事拉代码后首次启动) |

---

## 场景 1：修改了 Model（字段 / 加列 / 改类型 / 加表）

这是最常见的操作。改了 `app/models/` 下的 SQLAlchemy 模型后，需要生成迁移并应用。

### 前置检查

确认新模型已在 `migrations/env.py` 中 import，否则 autogenerate 检测不到：

```python
# migrations/env.py 末尾的 import 区
from app.models.user import User  # noqa: F401
from app.models.market import Watchlists, WatchlistItems, Klines, CorporateActions  # noqa: F401
from app.models.alert import AlertRules, AlertLogs  # noqa: F401
from app.models.strategy import Strategies, BacktestRuns, BacktestResults  # noqa: F401
from app.models.trading import BrokerAccount, Order, Position, PositionReconciliation, AuditLog, TradeOutbox  # noqa: F401
from app.models.ai import AIConversation, AIMessage  # noqa: F401
# 新建的 model 文件必须在这里补一行 import
```

### 操作步骤

```bash
cd backend

# 1. 生成迁移（autogenerate 对比 Model 与 DB 的差异）
uv run alembic revision --autogenerate -m "描述你改了什么"

# 2. 打开生成的文件检查！重点看：
#    - 新增的列类型是否正确
#    - server_default 是否合理
#    - 有没有误删列（autogenerate 偶尔会多检测）
# 文件在 migrations/versions/ 下，文件名是 <revision>_<描述>.py

# 3. 应用迁移
uv run alembic upgrade head
```

### 常见坑

| 问题 | 原因 | 解决 |
|------|------|------|
| autogenerate 说 "No changes" | model 没在 `env.py` 里 import | 补 import |
| 迁移报 `relation "xxx" does not exist` | 迁移链断了——ALTER 了一张从未 CREATE 的表 | 删掉该迁移文件，重新 autogenerate |
| 迁移报 `syntax error at or near "AT"` | `server_default` 用了 `now() AT TIME ZONE 'UTC'`，DDL 中需要括号 | 用 `func.now()` 代替 |
| autogenerate 多检测了删列 | model 删了字段但 DB 还有 | 手动从迁移文件中删掉多余的 `op.drop_column` |

### 回滚迁移

```bash
# 回退一个版本
uv run alembic downgrade -1

# 回退到指定版本
uv run alembic downgrade <revision_id>

# 查看当前版本
uv run alembic current

# 查看迁移历史
uv run alembic history
```

---

## 场景 2：修改了 docker-compose.yml 或 .env.docker

改了 Docker 配置（换镜像、改端口、改环境变量等），需要重启容器。

### 如果只改了配置（不涉及数据兼容性）

```bash
cd /Users/zhangkaipeng/Downloads/quant-platform

# 重启（保留数据）
docker compose --env-file .env.docker down
docker compose --env-file .env.docker up -d
```

### 如果换了 PostgreSQL 镜像（如从普通 PG 换到 TimescaleDB）

旧数据目录是用旧镜像初始化的，直接换镜像启动会有兼容问题。需要清空重建：

```bash
cd /Users/zhangkaipeng/Downloads/quant-platform

# 1. 停容器
docker compose --env-file .env.docker down

# 2. 删旧数据（会丢失所有数据库数据！开发环境可接受）
rm -rf data/postgres

# 3. 重新启动（新镜像会重新初始化）
docker compose --env-file .env.docker up -d

# 4. 等 3 秒让 PG 初始化完成
sleep 3

# 5. 重新跑全部迁移
cd backend
uv run alembic upgrade head
```

### 验证 Docker 状态

```bash
# 容器是否运行
docker compose --env-file .env.docker ps

# PostgreSQL 能否连接
docker exec quant-platform-postgres-1 psql -U quant_user -d quant_platform -c "SELECT 1;"

# TimescaleDB 扩展是否可用
docker exec quant-platform-postgres-1 psql -U quant_user -d quant_platform -c "SELECT extname FROM pg_extension;"

# Redis 是否运行
docker exec quant-platform-redis-1 redis-cli ping
```

---

## 场景 3：新增了配置项（.env.example 同步）

后端 `app/core/config.py` 的 `Settings` 类加了新字段后，需要在 `.env` 和 `.env.example` 中同步。

### 操作步骤

1. 在 `backend/.env.example` 中添加新字段（用 `change_me` 或合理默认值）
2. 在 `backend/.env` 中添加新字段（填实际值）
3. 如果新增的是 Docker 也需要的变量（如 DB 密码），同步更新 `.env.docker`

### 规则

| 文件 | 用途 | 谁读它 | 是否提交 Git |
|------|------|--------|-------------|
| `backend/.env` | Python 应用配置（pydantic-settings） | 后端进程 | ❌ 不提交（含密钥） |
| `backend/.env.example` | 配置模板 | 新开发者参考 | ✅ 提交 |
| `.env.docker` | Docker Compose 变量替换 | docker-compose | ❌ 不提交（含密钥） |

### 配置项命名规则

- Python 应用配置用 `__` 嵌套：`DB__HOST`、`JWT__SECRET_KEY`、`LLM__MODEL`
- Docker 变量用 `_` 扁平：`DB_HOST`、`DB_PASSWORD`、`DB_NAME`
- 两边密码等共享值必须手动保持一致

---

## 场景 4：彻底重置数据库

开发过程中表结构改乱了，想从零开始。

```bash
cd /Users/zhangkaipeng/Downloads/quant-platform

# 1. 停容器
docker compose --env-file .env.docker down

# 2. 删数据
rm -rf data/postgres

# 3. 重启
docker compose --env-file .env.docker up -d
sleep 3

# 4. 跑全部迁移
cd backend
uv run alembic upgrade head

# 5. 验证
docker exec quant-platform-postgres-1 psql -U quant_user -d quant_platform -c "\dt"
```

---

## 场景 5：后端启动报 ImportError

通常是代码引用了不存在的模块或函数。

### 排查步骤

```bash
# 单独测试 import，看具体报什么
cd backend
uv run python -c "from app.main import app; print('OK')"
```

### 常见原因

| 报错 | 原因 | 修复 |
|------|------|------|
| `cannot import name 'get_async_db'` | `deps.py` 缺函数定义 | 在 `shared/db/session.py` 定义，在 `deps.py` 导入 |
| `cannot import name 'XXX' from 'app.core.exceptions'` | 枚举里没这个值 | 在 `BizErrorCode` 中补上 |
| `XXX is not defined` | API 文件用了但没 import | 补 import |
| `Could not locate SQLAlchemy Core type` | `mapped_column(type_=None)` | 改成正确的 SQL 类型（如 `JSONB`） |

---

## 场景 6：前端 `pnpm dev` 报 ignored builds

pnpm 11+ 默认阻止依赖的构建脚本，需要手动批准。

### 一次性修复

编辑 `frontend/pnpm-workspace.yaml`：

```yaml
allowBuilds:
  sharp: true
  unrs-resolver: true
onlyBuiltDependencies:
  - sharp
  - unrs-resolver
```

然后：

```bash
cd frontend
pnpm install
pnpm dev
```

### 如果还报错

```bash
# 检查 pnpm install 退出码
pnpm install > /dev/null 2>&1; echo $?

# 如果非 0，说明 pnpm-workspace.yaml 没生效
# 确保 allowBuilds 的值是 true/false（不是占位符字符串）
```

---

## 场景 7：同事拉代码后首次启动

### 推荐：一键部署启动

根目录 `Makefile` 会启动 PostgreSQL/Redis、执行迁移和构建，并拉起 API、market_worker、strategy_worker、trade_executor、前端五个进程。部署主机需提供 POSIX shell、GNU Make、Docker、uv、Node.js 和 pnpm。

```bash
cp .env.docker.example .env.docker
cp backend/.env.example backend/.env
make deploy
make status
```

默认前端端口为 `3000`、API 为 `8000`。端口被占用时可覆盖：

```bash
make start FRONTEND_PORT=3002 API_PORT=8000
```

### 手动开发启动

### 后端与 Worker

```bash
# 前提：已安装 Python 3.13+、uv、Docker

# 1. 启动 PostgreSQL + Redis
cd quant-platform
cp .env.docker.example .env.docker  # 填入 DB 密码等
docker compose --env-file .env.docker up -d

# 2. 配置后端环境
cd backend
cp .env.example .env  # 填入实际的密钥、API Key 等

# 3. 安装依赖
uv sync

# 4. 跑迁移
uv run alembic upgrade head

# 5. 分别启动 API 与三个 Worker
uv run python main.py
uv run python workers/market_worker/main.py
uv run python workers/strategy_worker/scheduler.py
uv run python workers/trade_executor/adapters/main.py
```

### 前端

```bash
# 前提：已安装 Node.js 18+、pnpm

cd frontend
pnpm install
pnpm dev
# 打开 http://localhost:3000
```

前端 `.env.local` 不需要创建——代码里默认指向 `localhost:8000`。
如果后端不在 localhost，创建 `.env.local`：

```env
NEXT_PUBLIC_API_BASE_URL=http://<后端IP>:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://<后端IP>:8000/ws/market
```

---

## 日常开发命令速查

```bash
# ── 后端 ──
cd backend
uv run python main.py                    # 启动后端 (:8000)
uv run python workers/market_worker/main.py
uv run python workers/strategy_worker/scheduler.py
uv run python workers/trade_executor/adapters/main.py
uv run alembic current                   # 查看当前迁移版本
uv run alembic upgrade head              # 应用全部迁移
uv run alembic revision --autogenerate -m "描述"  # 生成新迁移
uv run alembic downgrade -1              # 回退一个迁移

# ── 前端 ──
cd frontend
pnpm dev                                 # 启动前端 (:3000)
pnpm build                               # 生产构建
pnpm lint                                # ESLint 检查
npx tsc --noEmit                         # TypeScript 类型检查

# ── Docker ──
docker compose --env-file .env.docker up -d      # 启动
docker compose --env-file .env.docker down        # 停止
docker compose --env-file .env.docker ps          # 查看状态
docker compose --env-file .env.docker logs -f     # 查看日志

# ── 数据库直连 ──
docker exec -it quant-platform-postgres-1 psql -U quant_user -d quant_platform
```
