# Router-Hub Backend

AI 中转站 Rank 系统后端：FastAPI + Tortoise ORM + Aerich + PostgreSQL + Redis。

> 设计真相源见 `../docs/dev/blueprint.md`，功能与决策见 `../docs/dev/features.md`。

## 目录结构

```
backend/
├── app/
│   ├── main.py            # FastAPI 工厂 + lifespan
│   ├── core/              # config(Settings) / db(TORTOISE_ORM) / security(加密·哈希)
│   ├── models/            # 8 张表，统一双键制/虚拟外键/软删除/uuid7
│   ├── api/               # 聚合路由 + routes/(目前仅 health)
│   └── worker/            # 探测调度器（独立进程）+ 探测桩
├── migrations/            # aerich 迁移
└── tests/                 # pytest（sqlite 内存库，不依赖 Postgres）
```

## 环境准备

```bash
cd backend
poetry install
cp .env.example .env        # 然后按需修改

# 生成 key 加密密钥并填入 .env 的 KEY_ENCRYPTION_SECRET
poetry run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## 数据库迁移（Aerich）

首次（需本机/远端有可达的 PostgreSQL，库名见 DATABASE_URL）：

```bash
poetry run aerich init -t app.core.db.TORTOISE_ORM
poetry run aerich init-db          # 生成首个迁移并建表
```

之后每次改模型：

```bash
poetry run aerich migrate --name <变更说明>
poetry run aerich upgrade
```

> **partial unique index（重要）**：`users.email`、`relay_sites.slug` 等业务唯一字段，
> 需在生成的首个迁移里把普通唯一约束改写为 Postgres partial unique index
> （`CREATE UNIQUE INDEX ... WHERE is_deleted = false`），
> 使假删除的行不占用唯一值。详见 blueprint 第三节通用约定第 3 条。

## 运行

```bash
# Web API（开发）。注意：本机 8000 端口被占用时改用 8010
poetry run uvicorn app.main:app --reload --port 8010
# 健康检查
curl http://127.0.0.1:8010/health

# 探测 worker（独立进程）
poetry run python -m app.worker.scheduler
```

## VM 常驻部署

worker 不在 Web 进程内跑。VM 上建议用 systemd 托管 `poetry run python -m app.worker.scheduler`。

仓库已提供最小模板：

```bash
# 假设仓库路径为 /opt/router-hub
chmod +x /opt/router-hub/backend/start-worker.sh
sudo cp /opt/router-hub/backend/router-hub-worker.service /etc/systemd/system/router-hub-worker.service
sudo systemctl daemon-reload
sudo systemctl enable --now router-hub-worker
sudo systemctl status router-hub-worker
sudo journalctl -u router-hub-worker -f
```

如果 VM 路径不是 `/opt/router-hub/backend`，先调整 `router-hub-worker.service` 里的 `WorkingDirectory` 和 `ExecStart`。

## 创建管理员

admin 角色只能由脚本创建，注册接口无法产生（防止外部注册出管理员）。

```bash
# 新建管理员（按提示隐藏输入密码，两次确认）
poetry run python -m app.scripts.create_admin --email admin@example.com

# 邮箱已存在时，把该用户升级为管理员
poetry run python -m app.scripts.create_admin --email someone@example.com --promote
```


## 测试与代码质量

```bash
poetry run pytest
poetry run ruff check .
poetry run pre-commit run --all-files
```

## 当前进度

骨架阶段：配置层、8 张表模型、health 路由、worker 调度骨架（探测函数为桩）已就位。
业务逻辑（鉴权、上架、真实探测、评分计算、集市撮合）尚未实现。
