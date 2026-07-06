
## 待改进

### [P2] models/ 应迁移到 shared/
这里最初设计的时候没有考虑到，当时是希望将 workers和 app 分开，但是现在 worker 和 app 都需要用到 models，所以这里需要将 models 移到 shared 下，然后 app 和 workers 都引用 shared 下的 models

**现状**: `app/models/` 同时被 `app/` 和 `workers/` 引用，存在耦合。
- `app/api/*.py` 查询数据时 import models
- `workers/market_worker/fetcher.py` 写入数据时也 import models

**目标**: 将 `models/` 移入 `shared/models/`，实现：
```
shared/
├── db/ # SessionLocal, Base, TimestampMixin
└── models/ # 所有 ORM 模型（Klines, User, Watchlists...）

app/ # 只引用 shared.models
workers/ # 只引用 shared.models
```

**影响范围**: 
- 移动文件后修改所有 `from app.models.xxx` → `from shared.models.xxx`
- 更新 `migrations/env.py` 的 import 路径

