# 进度

## 2026-06-29（续：认证→上架打通）

### Completed（本日后续，按提交顺序）

- 后端认证接口（eb3468f）：JWT 签发/解码，POST /auth/register、/auth/login、GET /auth/me；
  schema 拆 Role(含 admin)/RegisterRole(仅 user/owner)；7 测试。
- 首个数据库迁移（e7db7e6）：aerich init-db 生成 8 表；手工补 users.email / relay_sites.slug
  的 partial unique index（WHERE is_deleted=false）。
- 前端登录页对接后端（1fce7bd）：后端加 CORS；lib/api.ts（API client，NEXT_PUBLIC_API_BASE）；
  lib/auth.ts（token 存取）；登录页接通注册/登录，成功跳首页。
- 创建管理员脚本（378a4fd）：`python -m app.scripts.create_admin --email ... [--promote]`，
  getpass 隐藏输入，EmailStr 校验；admin 只能脚本造，注册接口造不出。
- 主框架顶栏布局（7e8301a）：AuthProvider(Context 全局登录态) + Navbar(响应式汉堡菜单)
  + UserMenu(角色专属入口+登出) + SiteShell；首页改简洁落地页；
  占位路由 leaderboard/graveyard/market/owner/admin/me。
- 站点上架（8beb038）：get_current_owner；POST /sites、GET /sites/mine；key Fernet 加密落库
  只回 key_hint 掩码；slug 自动生成+去重；新站 status=pending；前端 /owner 站长控制台
  (列表+上架表单)；6 测试。
  - 修复全局隐患：SoftDeleteManager 被所有模型共享导致 _model 串表，改为每个模型
    Meta 独立 manager=SoftDeleteManager()（见 .claude 记忆 backend-tortoise-gotchas）。

### Current State（存档点 2026-06-29）

- 已打通「3→1→2」三步 + 管理员脚本 + 站点上架。注册/登录/登出、站长上架可用，数据落真实 PG。
- 计划顺序中「3 后端认证→1 前端对接→2 主框架」已全部完成。
- 测试：后端 13 passed（7 auth + 6 sites）。前端 tsc/lint/build 均过。
- 站点上架后均为 status=pending，尚无审核流转、尚无真实探测。

### 环境 / 联调要点（重要，下次直接用）

- **后端端口用 8010**（本机 8000 被另一应用 "Media Studio" 占用）。
  启动：`cd backend && poetry run uvicorn app.main:app --port 8010`
- 前端：`cd frontend && npm run dev`（.env.local 已指向 http://localhost:8010）
- PG/Redis 连接信息在 backend/.env（已配，不进 git）。库名 router_hub，已建表。
- 测试管理员账号（联调时建的，在真实 PG）：admin@example.com / RouterHub@2026
  （改密接口尚未做；可用脚本重建自己的）。

### Next Steps（下次从这里挑）

- 推荐：管理员审核 —— pending 站点流转到 observing（管理员看待审列表+通过/驳回）。
- 探测 worker 接真实站点（替换 probes.py 桩，用加密 key 打 base_url 写 probe_results）。
- 排行榜页（可先用假数据做展示）。
- 站点编辑/下架（站长对自己站点的管理）。

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
