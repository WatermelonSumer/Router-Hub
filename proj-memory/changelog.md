# Changelog

## 2026-07-01

- 提交 `1254f6e`：完成 C 端 user_topup 评价、worker VM 常驻模板、前端提交入口与回归测试。

## 2026-07-01

- worker VM 常驻：新增 systemd service 模板与启动脚本，README 记录启用步骤。
- C 端 user_topup 评价：新增登录用户充值/用量 key 验证提交接口、验证适配层、详情页评价表单与回归测试。

## 2026-06-30

- 部署联调：确认迁移无待执行项，幂等重跑 seed_demo，验证 VM health/graveyard/rank/站点编辑路由，启动本机 worker scheduler 并手动跑一轮存活探测。
- 详情页评价展示：新增 `GET /sites/{slug}/reviews` verified 评价列表；详情页展示星级、来源、日期和文字评价，并补 AggregateRating JSON-LD。
## 2026-06-30

- 站长站点编辑/下架：新增 `PATCH /sites/{site_id}` 和 `DELETE /sites/{site_id}`；站长可编辑展示/硬信息，变更 Base URL/API Key/声明模型会退回 `pending` 并软删除旧探测事实与旧分数；下架走软删除。
- 前端 `/owner` 站点卡片新增详情、编辑、下架；编辑表单支持更换 key、模型、硬信息与质量探测预算。
- `tests/test_sites.py` 补站点编辑/下架回归测试，后端测试数更新为 114 passed。
## 2026-06-29

- 探测 worker（技术核心，真实探测+状态机+评分）：
  - worker/http_probe.py：probe_alive 打 /v1/models、probe_quality 用站长 key 打 /v1/chat（注入 client、随机 UA/prompt 防作弊、key 不进结果/日志）。
  - worker/state_machine.py：decide_transition 纯函数，照搬 blueprint 五之二全转移表，阈值走 settings。
  - worker/probe_stats.py：从 probe_results 算连续成败（维护窗失败剔除）+ observing 天数/样本数，不加列。
  - services/scoring.py：四指标归一化（uptime 时间衰减/speed P90 锚点/authenticity 比例/review 贝叶斯）+ 缺失数据动态权重不补 0；recompute_site_scores 按声明模型归榜 upsert + recompute_ranks。
  - worker/probes.py：替换桩，alive/quality 轮并发探测→写 probe_results→跑状态机落库→online→abnormal 插队触发质量探测→轮尾重算 scores/ranks。
  - RelaySite 加 status_changed_at（时间型转移用）+ 手写迁移；review_site 通过时打戳；seed_demo 同步打戳。
  - 18 测试（http_probe 6 + state_machine 12 + scoring 12 + worker_round 5，MockTransport/sqlite/纯函数）。后端共 65 passed。
- 排行榜展示：GET /rank?leaderboard=&sort=（游客可读、无鉴权，主榜 online/abnormal/revived + 观察区 observing 分列、坟场状态不上榜、sort=composite|speed|uptime、null 分垫底）；schemas/rank、services/rank_service(只读预计算分 join 站点)、routes/rank；前端 URL /leaderboard→/rank(blueprint SEO 永久结构)、/rank/[family] 服务端渲染(RSC + 动态 metadata + JSON-LD ItemList、三 Tab + 排序、桌面表格/窄屏卡片、观察区区块)；seed_demo.py 演示数据脚本(幂等 + --wipe，5 站含各状态 + 三榜权重)；9 测试(后端共 30 passed)。
- 管理员审核：GET /admin/sites/pending、POST /admin/sites/{id}/approve|reject；pending→observing(通过)/rejected(驳回，必填理由写 review_note 回传站长)；get_current_admin 依赖；RelaySite 加 review_note 字段 + 手写迁移(PG 当时不可达)；前端 /admin 后台页(待审卡片含站长联系方式+通过/驳回)、站长端显示驳回理由；8 测试(后端共 21 passed)。
- 站点上架（站长端）：POST /sites、GET /sites/mine；key Fernet 加密落库只回掩码；slug 去重；/owner 控制台；修复 SoftDeleteManager 共享串表 bug。
- 主框架顶栏布局：AuthProvider 全局登录态、Navbar 响应式、UserMenu、SiteShell；首页改简洁落地页；占位路由若干。
- 创建管理员脚本 app/scripts/create_admin.py（getpass 隐藏输入、EmailStr 校验、admin 仅脚本可建）。
- 前端登录页对接后端：后端 CORS；lib/api.ts、lib/auth.ts；注册/登录跑通。
- 首个数据库迁移 + email/slug partial unique index。
- 后端认证接口：JWT、register/login/me，7 测试。
- 搭建前端骨架 frontend/：Next.js 16 + React 19 + Tailwind v4 + shadcn/ui + motion + next-themes。
- 双主题基建(全套语义 token + ThemeProvider/ThemeToggle)、shadcn 基础组件、登录页 /login(玻璃拟态/赛博风,角色切换)。
- 因网络限制改用：手动搭 shadcn(CLI 连不上 ui.shadcn.com)、自托管 geist 字体包(next/font/google 拉不到)。
- 完善 .pre-commit-config.yaml(rev 对齐 ruff 0.8.6、排除 migrations、补 check-toml 等)。

## 2026-06-28

- 搭建后端骨架 backend/：core 配置层、8 张表 Tortoise 模型（双键制/虚拟外键/软删除/uuid7）、
  health 路由、APScheduler 探测调度骨架（探测函数为桩）、pytest（sqlite 内存库）。
- 新增工程配置：backend/pyproject.toml(Poetry+aerich+ruff)、.env.example、backend/README.md。
- 根级：.gitattributes(统一 LF)、更新 .gitignore(Python)、.pre-commit-config.yaml(ruff)。
- frontend/ 占位 README；建立 proj-memory/（README/progress/decisions/todo/changelog）。
