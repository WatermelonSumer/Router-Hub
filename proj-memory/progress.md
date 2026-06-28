# 进度

## 2026-06-29

### Completed

- 搭建前端骨架（frontend/）：Next.js 16(App Router)+ React 19 + TS + Tailwind v4 + shadcn/ui(new-york) + motion + next-themes。
  - 双主题基建：globals.css 全套语义 token(slate，light/dark 两套 oklch)；ThemeProvider(class 策略,跟随系统) + ThemeToggle。
  - shadcn 基础组件源码进 src/components/ui/(button/input/label/card) + lib/utils.cn()。
  - 登录页 /login（玻璃拟态/赛博风，角色切换 用户/站长，spring 动画，纯 UI 未接后端）。
  - 首页占位 /，全程零硬编码颜色。
  - 验证：npm run build / lint 均过，dev server /、/login 200。

### Current State

- 前端骨架可构建可预览，登录页 UI 完成；榜单/详情/坟场/集市页面未开始；未接后端鉴权。

### Next Steps

- 实现后端 /auth(注册/登录 JWT) 并前端对接。
- 生成首个 aerich 迁移并手工补 partial unique index（需可达 Postgres）。

## 2026-06-28

### Completed

- 设计阶段定稿：`docs/dev/blueprint.md`（技术真相源）+ `docs/dev/features.md`（功能与决策）。
- 搭建后端骨架（backend/）：
  - 配置层 `app/core/`：`config.py`(pydantic-settings Settings，镜像全部 .env 阈值)、`db.py`(TORTOISE_ORM)、`security.py`(Fernet key 加解密 + bcrypt 密码哈希)。
  - 数据模型 `app/models/`：base 基类（双键制/虚拟外键/软删除/uuid7）+ 8 张表
    （users / relay_sites / probe_results / site_scores / leaderboard_weights / reviews / marketplace_posts / post_responses）。
  - API：`app/main.py`(工厂+lifespan)、`app/api/router.py`、`routes/health.py`(GET /health)。
  - Worker：`app/worker/scheduler.py`(APScheduler 三周期，独立进程)+ `probes.py`(探测桩)。
  - 测试：`tests/`（sqlite 内存库，不依赖 Postgres）health 测试。
  - 工程：pyproject.toml(Poetry+aerich+ruff)、.env.example、README、根 .gitattributes/.gitignore/.pre-commit-config.yaml。

### Current State

- 后端骨架可启动、可测试；业务逻辑为桩。
- 首个 aerich 迁移是否已生成取决于本机 PostgreSQL 是否可达（见 todo）。

### Next Steps

- 生成首个迁移并手工补 partial unique index（users.email / relay_sites.slug）。
- 搭前端 Next.js 骨架（下一轮）。
- 逐项打磨 blueprint 第十三节 6 个 TODO，再实现业务逻辑。
