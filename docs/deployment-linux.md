# Linux 服务器部署

> 适用于单台 Ubuntu 22.04/24.04 服务器。开发环境仍可在 Windows 运行；生产环境建议使用 Linux，因为回测进程的 CPU、内存与超时限制在 Linux 上更完整。

## 1. 推荐架构

```text
Internet
  -> Nginx :80/:443
     -> Next.js 127.0.0.1:3000
     -> FastAPI 127.0.0.1:8000
        -> PostgreSQL/TimescaleDB 127.0.0.1:5432
        -> Redis 127.0.0.1:6379
        -> market_worker / strategy_worker / trade_executor
```

最低建议 4 核 CPU、8 GB 内存、50 GB SSD。仅开放 SSH、HTTP、HTTPS；不要向公网开放 3000、8000、5432、6379。项目的 `docker-compose.yml` 默认只把 PostgreSQL 和 Redis 绑定到 `127.0.0.1`。

## 2. 安装运行环境

完整容器部署只需 Git、Docker Engine + Compose plugin 和可选的 GNU Make。只有宿主机/systemd 部署才需 Node.js 20.9+、pnpm 和 uv。安装方式以官方文档为准：

- Docker: <https://docs.docker.com/engine/install/ubuntu/>
- uv: <https://docs.astral.sh/uv/getting-started/installation/>
- Next.js/Node 要求: <https://nextjs.org/docs/app/getting-started/installation>

```bash
sudo apt update
sudo apt install -y git make nginx curl ca-certificates
```

创建独立用户和目录，避免用 root 运行应用：

```bash
sudo useradd --system --create-home --shell /bin/bash quant
sudo mkdir -p /opt/quant-platform
sudo chown -R quant:quant /opt/quant-platform
sudo -u quant git clone <repository-url> /opt/quant-platform
```

## 3. 配置生产环境

```bash
cd /opt/quant-platform
cp .env.docker.sample .env.docker
cp backend/.env.example backend/.env
```

必须修改：

- `.env.docker` 的 `DB_PASSWORD`，并与 `backend/.env` 的 `DB__PASSWORD` 完全一致。
- `backend/.env`: `ENV=prod`、`DEBUG=false`、数据库密码、JWT 密钥、凭据加密密钥和实际域名 CORS。
- `.env.docker`: `NEXT_PUBLIC_API_BASE_URL` 使用 `https://`，`NEXT_PUBLIC_WS_URL` 使用 `wss://`。它们在前端镜像构建时写入产物，修改后必须重新构建。
- `.env.docker`: `MOOTDX_SERVER` 为容器内通达信 TCP 节点；若节点失效，替换为可访问的 `host:port`。

生成密钥：

```bash
cd /opt/quant-platform/backend
uv run python -c "import secrets; print(secrets.token_hex(32))"
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

生产配置示例：

```env
ENV=prod
DEBUG=false
CORS_ORIGINS=["https://quant.example.com"]
```

AI Key 可以留空，此时非 AI 功能正常启动，AI 接口会返回配置错误。

## 4. Docker 一键部署（推荐）

使用根目录 Makefile：

```bash
cd /opt/quant-platform
make docker-deploy
make docker-status
```

Windows 或没有 Make 时：

```bash
docker compose --env-file .env.docker \
  -f docker-compose.yml -f docker-compose.deploy.yml \
  up -d --build
```

该命令会构建两个应用镜像，启动 PostgreSQL、Redis，等待健康检查，执行 Alembic 迁移，然后启动 API、三个 Worker 和前端。更新时重复执行同一命令即可。

```bash
make docker-logs
make docker-stop
make docker-down  # 不删除 data 目录
```

若 `3000` 已被占用，在 `.env.docker` 中设置 `FRONTEND_PORT=3002` 后重新执行。

## 5. 宿主机 + systemd（备选）

仅在不希望应用进程容器化时使用本方案。先安装 Node.js、pnpm 和 uv，然后执行 `make install build migrate`。

生产环境建议改由 systemd 托管五个应用进程，以获得开机启动和异常重启。每个 unit 使用以下公共设置：

```ini
[Unit]
After=network-online.target docker.service
Wants=network-online.target

[Service]
User=quant
Group=quant
WorkingDirectory=/opt/quant-platform/backend
Environment=TZ=Asia/Shanghai
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

分别创建 `quant-api.service`、`quant-market-worker.service`、`quant-strategy-worker.service`、`quant-trade-executor.service`，对应 `ExecStart`：

```text
/home/quant/.local/bin/uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
/home/quant/.local/bin/uv run python workers/market_worker/main.py
/home/quant/.local/bin/uv run python workers/strategy_worker/scheduler.py
/home/quant/.local/bin/uv run python workers/trade_executor/adapters/main.py
```

前端 unit 使用 `WorkingDirectory=/opt/quant-platform/frontend`，`ExecStart=/usr/bin/pnpm exec next start --hostname 127.0.0.1 --port 3000`。先用 `command -v uv` 和 `command -v pnpm` 确认服务器实际路径。

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now quant-api quant-market-worker quant-strategy-worker quant-trade-executor quant-frontend
```

不要同时运行 Makefile 后台进程和 systemd 服务，否则会产生重复 Worker。

## 6. Nginx 与 HTTPS

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

server {
    listen 80;
    server_name quant.example.com;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

配置证书后将 80 重定向至 443，并确认前端 WebSocket 地址为 `wss://`。可使用 Certbot 或云厂商证书服务。

## 7. 上线检查

```bash
curl -fsS http://127.0.0.1:8000/health
curl -I http://127.0.0.1:3000
make docker-status
docker compose --env-file .env.docker exec -T redis redis-cli LLEN backtest_queue
docker compose --env-file .env.docker exec -T redis redis-cli LLEN trade:order_queue
docker compose --env-file .env.docker exec -T redis redis-cli LLEN trade:order_dlq
```

交易时段内，分钟线应每分钟推进；日线在上海时间 15:10 同步，收盘分钟线在 15:02 补拉。公司行为数据在标的首次进入实时跟踪时按需同步并缓存 7 天，每周日 16:00 再做全市场校准。调度代码使用上海时区和交易所日历，不依赖服务器本地时区。

首次冷启动的全市场日线回填会明显慢于日常增量同步。Worker 会先处理自选股、活跃预警和当前在线查看标的，再继续补齐其余市场；不要在回填期间重复启动 `quant-market-worker`。

## 8. 更新、回滚与备份

更新前先备份数据库：

```bash
mkdir -p /opt/quant-backups
docker compose --env-file .env.docker exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > /opt/quant-backups/quant_$(date +%F_%H%M).dump
```

容器部署更新：

```bash
git pull --ff-only
make docker-deploy
```

宿主机/systemd 部署更新：

```bash
sudo systemctl stop quant-api quant-market-worker quant-strategy-worker quant-trade-executor quant-frontend
git pull --ff-only
make install
make build
make migrate
sudo systemctl start quant-api quant-market-worker quant-strategy-worker quant-trade-executor quant-frontend
```

代码回滚应切回已验证 tag 后重新安装、构建和重启。数据库迁移不要盲目 downgrade；优先恢复升级前备份。恢复会覆盖现有数据，必须在停服并确认备份后执行。

## 9. 常见问题

- K 线停更：检查 `quant-market-worker`、Redis、数据库连接和腾讯/mootdx 网络；仅打开的股票也会通过活跃 WebSocket 订阅进入分钟调度。
- 回测一直排队：检查 `quant-strategy-worker` 和 `backtest_queue`。
- 订单一直 pending：检查 `quant-trade-executor`、`trade:order_queue` 与死信队列。
- 页面正常但 API 失败：检查构建时的 `NEXT_PUBLIC_API_BASE_URL`、后端 CORS 和 Nginx `/api/` 转发。
- WebSocket 断开：检查 `wss://` 地址以及 Nginx Upgrade/Connection 请求头。
- 前复权不变化：先确认标的在所选区间内是否发生除权；企业行动表为空时运行一次企业行动同步，AKShare 只作为 CNINFO 失败后的兜底。
