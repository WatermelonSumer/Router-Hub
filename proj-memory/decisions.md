# 技术决策

## 2026-06-30 - 站点探测身份变更需重新审核

### Decision

站长编辑站点时，slug 不开放修改；展示/硬信息可直接更新。Base URL、API Key、声明模型被视为“探测身份”，任一变更都会让站点退回 `pending`，并软删除旧 `probe_results` 与 `site_scores`。

### Reason

旧探测履历只对旧目标有效。如果核心探测身份变了仍沿用旧分数，会让新目标借旧站信誉上榜，破坏客观征信。

### Impact

- 变更探测身份后需要 admin 重新审核，worker 再重新产出探测事实和分数。
- 旧探测/旧分数保留软删除痕迹，不再参与默认查询、公开详情或排行。
- slug 稳定不变，避免已收录 URL 和站点详情链接失效。
> 完整决策速查见 `docs/dev/features.md` 第 14 节，这里只记骨架阶段落地相关的关键点。

## 2026-06-28 - 后端栈与数据层约定落地

### Decision

- 后端：FastAPI + Tortoise ORM + Aerich + PostgreSQL + Redis。**不用 SQLAlchemy**（aerich 是 Tortoise 官方迁移工具）。
- 所有表强制：双键制（内部 bigint `id` + uuid7 业务键 `<实体>_id`）、虚拟外键（零 DB FK，存对方业务键值，完整性在 service 层）、软删除（is_deleted + deleted_at，默认查询过滤）、uuid7 用 `uuid-utils`。
- 唯一约束用 Postgres **partial unique index**（`WHERE is_deleted=false`），假删除行不占唯一值。

### Reason

解耦、便于迁移/分库、数据可追溯；用户明确要求。

### Impact

- 不使用 `ForeignKeyField`，改存 uuid7 值。
- 模型 `unique=True` 仅占位，首个迁移需手工改写成 partial unique index。
- 业务键 uuid7 不复用、不碰撞，保留普通 unique 即可。

## 2026-06-28 - 探测 worker 与 web 进程分离

### Decision

探测调度（APScheduler 三周期：存活/质量/触发）放独立进程 `app.worker.scheduler`，不在 FastAPI 进程内。

### Reason

探测是慢 IO + 可能被上游限速，绝不能阻塞用户请求（blueprint 架构原则 1）。

### Impact

部署需起两个进程：`uvicorn app.main:app` 与 `python -m app.worker.scheduler`。

## 2026-06-28 - 配置位置划分

### Decision

全局/低频/运维改 → `.env`（pydantic-settings 加载，代码只读 settings）；按业务维度区分/要热更新 → DB 表（leaderboard_weights）。key 加密密钥仅 .env。

### Reason

阈值要整体生效、低频；权重每榜不同要热调。

### Impact

`core/config.py` 集中全部 .env 项；分榜权重不进 Settings，进表。
