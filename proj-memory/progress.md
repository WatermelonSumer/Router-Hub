# 进度

## 2026-06-30（续12：站长站点编辑 + 下架）

### Completed

- **站长控制台补齐站点编辑/下架闭环**：
  - 后端：新增 `SiteUpdateRequest`、`PATCH /sites/{site_id}`、`DELETE /sites/{site_id}`；站长只能操作自己站点，越权统一 404。
  - slug 继续遵守“URL 用，永不改”；展示/硬信息（name/site_url/min_topup/pay_methods/rpm_limit/probe_budget_daily）可直接更新。
  - Base URL / API Key / 声明模型属于探测身份：变更后站点退回 `pending`，清空 review_note/status_changed_at/first_seen_at/last_probe_at，并软删除旧 `probe_results` 与 `site_scores`，避免旧探测履历继续给新目标背书。
  - 下架走 `RelaySite.soft_delete()`，保留审计痕迹；默认查询、公开详情、站长列表均不再显示。
  - 前端：`siteApi.update/remove` + `/owner` 站点卡片新增详情、编辑、下架；编辑表单支持更换 key、硬信息、模型、质量探测预算，并提示探测身份变更会退回待审。
- 测试：`tests/test_sites.py` 补 4 条（展示字段编辑不退审/探测身份变更退审并清旧数据/越权 404/下架隐藏公开详情）。后端共 **114 passed**；前端 lint + build 通过。

### Current State（存档点 2026-06-30 续12）

- 站长端现在可完成：上架 → 审核 → 查看 → 编辑硬信息/探测身份 → 必要时重新审核 → 下架。
- **新接口需 VM 后端重载才生效**；变更探测身份后需要 admin 重新审核，再由 worker 重新产出探测和分数。
- `pre-commit run --all-files` 因当前网络无法拉取 hook 仓库失败（GitHub ruff-pre-commit fetch 走 127.0.0.1:7897 失败）；已用本地 ruff/pytest/npm lint/build 覆盖本次改动。

### Next Steps（下次从这里挑）

- VM：后端重载 + `aerich upgrade`（应用 site_id 迁移）+ 重跑 seed_demo；worker 常驻。
- C 端评价（root key 前提具备后）；详情页展示评价列表。
## 2026-06-30（续11：集市阶段2——B 端站长互评 owner_deal）

### Completed

- **B 端互评打通**（features.md 第 9 节，B 端信誉链最后一环）。reviews 表首个使用者：
  - 模型+迁移：`marketplace_post` 加 `site_id`（null=True，虚拟外键→relay_sites）+ 手写迁移
    `1_20260630120000_add_post_site_id.py`（ALTER ADD + index）。
  - **发帖自动绑定站点**（用户确认：当前一人一站，无需下拉）：create_post 取发帖人名下站点填 site_id；
    无站点（纯买家）则留空、该帖不可被评。PostView 加 site_id/site_name/site_slug。
  - `schemas/review.py`（ReviewCreateRequest rating1-5+content / ReviewView）；
    `services/review_service.py`（create_owner_deal_review：校验对接 confirmed + author 是两方之一 +
    帖子绑定了站点 + 防重复，写 Review(owner_deal, **verified=True**——对接本身即凭证)，
    刷 recompute_site_scores 喂 review_score；list_site_reviews）；
    路由 `POST /market/responses/{id}/review`（get_current_owner）。
  - 评价对象 = 帖子绑定站点；对接两方各评一次（最多 2 条 owner_deal/对接）。复用 C 端 review_score 链路。
  - 前端：marketApi.review + 类型；帖子卡显示绑定站点名（链详情页）；对接卡 confirmed 后出现
    **星级互评小部件**（ReviewWidget：1-5 星 + 可选文字，提交即标记已评）。
  - seed_demo：给 demo-seller 造站点 SellerRelay + 演示帖绑定其 site_id（互评可演示），--wipe 同步清。
- 测试：`tests/test_review.py` 8 测试（发帖绑定站点/双方可评 owner_deal+verified/刷 review_score/
  pending 409/非对接方 403/重复 409/rating 越界 422/无站点 400）。后端共 **110 passed**，ruff 通过；
  前端 lint+build 通过。

### Current State（存档点 2026-06-30 续11）

- B 端信誉闭环完整：发帖（绑站）→ 对接 → confirmed 换名片 → **互评 owner_deal → 喂该站 review_score**。
- C 端 user_topup 评价仍待 root key 前提（与 owner_deal 共用 reviews 表 + review_score 加权，已验证可共存）。
- **需 VM：后端重载 + `aerich upgrade`（应用 site_id 迁移）+ 重跑 seed_demo。**
- **Git：本次（续11）改动待提交（feat/hero）。**

### Next Steps（下次从这里挑）

- C 端评价（root key 前提具备后）；站点编辑/下架；worker 在 VM 常驻；详情页展示评价列表。

## 2026-06-30（续10：超级管理员集市监管视角——浏览 + 下架）

### Completed

- **admin 可进中转集市（监管视角：浏览 + 下架，不发帖/不对接）**：
  - 后端：deps 加 `get_owner_or_admin`（站长或管理员，用于只读浏览/下架）；
    `GET /market/posts` 改用该依赖（站长交易方 + admin 监管方均可读，admin 的 is_mine 恒 False）；
    `close_post` 加 `is_admin` 参数——admin 可关**任意**帖（内容下架），站长仍只能关自己的；
    发帖/对接/确认/我的对接仍 `get_current_owner`（仅站长）。
  - 前端：/market 登录墙放行 admin；admin 视角隐藏发帖表单与「我的对接」tab、不拉对接数据，
    每帖显示「管理下架」按钮（destructive）替代「对接/报名」；描述文案切监管措辞。
- 测试：test_marketplace +5（admin 可浏览/可关任意帖/不能发帖 403/不能对接 403/普通用户仍 403）。
  后端共 **102 passed**，ruff 通过；前端 lint+build 通过。

### Current State（存档点 2026-06-30 续10）

- 集市三类角色边界清晰：游客/普通用户拦截；站长交易（发帖/对接/换名片）；admin 监管（浏览/下架）。
- **新接口需 VM 后端重载才生效。**
- **Git：本次（续10）改动待提交（feat/hero）。**

### Next Steps（下次从这里挑）

- 集市阶段 2/3：B 端互评（confirmed 解锁 owner_deal → 写 reviews，喂 review_score）。
- C 端评价（待 root key 前提）；站点编辑/下架；worker 在 VM 常驻。

## 2026-06-30（续9：中转集市阶段1——发帖+浏览筛选+对接撮合）

### Completed

- **中转集市 /market**（B 端，features.md 第 8/9 节，登录墙后刻意不 SEO）。模型骨架
  （marketplace_posts/post_responses）早已就绪，本次补 API + UI 层，形成发帖→对接→换名片闭环：
  - 后端：`schemas/marketplace.py`（PostCreate/PostView/ResponseView/ContactCard/OwnerReputation）；
    `services/marketplace_service.py`（create_post 枚举校验、list_posts 多维筛选 + N+1 去重批量算履历、
    close_post、respond_to_post 幂等/不能对接自己/关闭帖不可对接、confirm_response、
    list_my_responses/list_responses_to_my_posts，**confirmed 才换名片**红线；reputation_for 沿用 C 端征信）；
    `routes/market.py`（全程 **get_current_owner 登录墙**：POST /market/posts、GET /market/posts 筛选、
    close、respond、confirm、responses/mine、responses/incoming）注册进 router。
  - 前端：`marketApi` + 全套类型；`/market` 替换 ComingSoon → 登录墙（仅 owner，普通用户/游客拦截）+
    浏览/发帖 tab（发帖折叠表单 + 多维筛选条 + 帖子卡片挂**探测履历名片**：最高分/最长存活/在册数/坟场污点）
    + 我的对接 tab（收到的对接可确认、确认后双方互见名片）。拆 page.tsx + parts.tsx。
  - seed_demo 补集市：两个真实演示站长（demo-seller/demo-buyer@routerhub.local，密码 demo1234，
    带 wechat/qq）+ 3 演示帖（claude/gpt 供给、gemini 需求），按 email/note 幂等锚，--wipe 同步清。
- 测试：`tests/test_marketplace.py` 12 测试（发帖/枚举 422/owner 墙/多维筛选/max_rate/关帖/越权关帖 403/
  不能对接自己 400/对接 pending 无名片/confirmed 双方换名片/越权确认 403/关闭帖对接 409）。
  后端共 **97 passed**，ruff 通过；前端 lint+build 通过。

### Current State（存档点 2026-06-30 续9）

- 集市阶段 1 闭环：发帖 → 浏览筛选（带履历名片）→ 对接 pending → 发帖人确认 confirmed → 换微信/QQ 名片。
- **新接口需 VM 后端重载才生效**；集市演示数据需在 VM 重跑 seed_demo（会建两个 demo 站长账号）。
- **Git：本次（续9）改动待提交（feat/hero）。**

### Next Steps（下次从这里挑）

- **集市阶段 2/3**：对接的 connected 中间态通知；**B 端互评**（confirmed 解锁 owner_deal 评价 →
  写 reviews，与 C 端评价共用 review_score，scoring 已留口子）。
- C 端评价（待中转站提供 root key 查充值接口的前提具备后再做）。
- 站点编辑/下架；worker 在 VM 常驻。

## 2026-06-30（续8：坟场页打通——传播引爆点 + SEO 富矿）

### Completed

- **坟场页 /graveyard**（features.md 第 5 节，最大化复用详情页）：
  - 关键复用：坟场站详情页早已可用（site_detail._PUBLIC_STATUSES 含 suspected_dead/dead，
    详情页 STATUS_META 已写两态客观措辞），故本次只做**列表页 + 只读接口**，行链到已有详情页。
  - 后端：公开 schema 补 status_changed_at（坟场计时/「曾阵亡」起点）；
    `schemas/graveyard.py`（GraveyardEntry/Response，suspected/dead 两区，**无 key/base_url**）；
    `services/graveyard_service.py`（只读筛坟场态、按 status_changed_at 倒序、分流，仿 rank_service）；
    `routes/graveyard.py`（GET /graveyard 无鉴权吃 SEO）注册进 router。
  - 前端：`graveyardApi` + 类型；SitePublicView 加 status_changed_at；
    /graveyard 替换 ComingSoon → RSC SSR+ISR 两区块（疑似跑路/已确认阵亡），
    每行「连续探测失败 N 天」(now-status_changed_at) + 曾存活天数 + 链到 /site/{slug}；
    **客观措辞红线**（只陈述探测事实，不主观定性）；动态 metadata + JSON-LD ItemList；兜底空态。
  - seed_demo 补两坟场站（MeteorAPI suspected_dead 3 天前 / VoidRelay dead 9 天前，全失败探测，
    无分数），spec 加 dead_days_ago 控制 status_changed_at。
- 测试：`tests/test_graveyard.py` 5 测试（分流/排序倒序/非坟场态排除/无 key 泄露/空坟场）+
  test_site_detail 补 status_changed_at 断言。后端 **85 passed**，ruff 通过；前端 lint+build 通过。

### Current State（存档点 2026-06-30 续8）

- C 端浏览链路再扩：榜单 + 详情页 + **坟场**（疑似/阵亡两区，行链详情）。
- **新接口 /graveyard 需 VM 后端重载才生效**（当前 VM 跑旧码返回 404，逻辑单测全绿）；
  坟场演示站需在 VM 重跑 seed_demo 才有内容。
- **Git：本次（续8）改动待提交（feat/hero）；之前 5 提交已 push（用户自行 push）。**

### Next Steps（下次从这里挑）

- C 端评价（充值 key 自证 verified → 喂 review_score，scoring 已留口子）。
- 中转集市（B 端发帖/对接/确认 + 互评解锁）。
- 站点编辑/下架（站长改 base_url/key/硬信息）。
- worker 在 VM 常驻 + 重启后端使新接口生效 + 重跑 seed_demo。

## 2026-06-29（续7：管理员各状态总览 + 导航栏角色控制台入口）

### Completed

- **管理员查看观察区/各状态的站**（扩展管理后台，非新建独立页）：
  - 后端 `GET /admin/sites?status=<状态>`（admin 鉴权，默认 observing，非法状态 422）；
    service 加 `list_sites_by_status`（按 status_changed_at 倒序，附站长，仍不含 key）。
    复用现有 SiteAdminView。
  - 前端 /admin 加状态标签页（待审/观察区/在线/异常/疑似阵亡/已阵亡/已驳回）：
    待审走专属 /pending（先到先审 + 通过/驳回操作），其余 tab 走 byStatus 只读总览；
    PendingCard 加 `reviewable` 开关——非待审隐藏审核按钮、显示驳回理由；slug 链到 /site/{slug}。
- **导航栏角色控制台入口**：navbar 用 useAuth 读角色，在导航栏最后（榜单/坟场/集市之后）
  显示角色专属入口——owner→站长控制台、admin→管理后台（桌面 + 移动汉堡菜单都加），主色高亮。
  原头像下拉菜单的入口保留（user-menu.tsx 未动）。
- 测试：test_admin 新增 5 测试（observing 总览含联系方式不含 key/缺省 observing/非法 422/站长 403）。
  后端 **80 passed**，ruff 通过；前端 lint + build 均过。

### Current State（存档点 2026-06-29 续7）

- 管理员能在 /admin 切换 tab 看任意状态的站；HeroAPI 在「观察区」tab 可见。
- **新接口需 VM 后端重载才生效**（当前 VM 跑旧码，/admin/sites 返回 404 属正常，逻辑单测全绿）。
- **Git：续6（3 提交：详情页/探测带 key/迁移合并）+ 续7（本次）均在 feat/hero，尚未 push。**

### Next Steps（下次从这里挑）

- 让 worker 在 VM 常驻持续探测 + 重启后端使新接口生效。
- 坟场页 /graveyard、C 端评价、中转集市、站点编辑/下架。

## 2026-06-29（续6：真实数据打通——存活探测带 key + 上架审核链路验证）

### Completed

- **真实站点 HeroAPI 端到端跑通**（首个真实探测产出真实分）：
  - 上架→审核链路验证无误：站长 hero@gmail.com 上架 HeroAPI（上游 makabaka.chat，
    声明 gpt-5.5），admin@example.com（密码已被站长改为 test1234）审核通过→observing。
    **「管理员没有审核按钮」实为误会**：审核按钮一直在（admin/page.tsx 待审卡片内），
    当时是登录了站长号被 /admin「管理员专属页」拦截所致。
  - **修真 bug：存活探测不带 key 误判离线**（提交 810b64f）。makabaka.chat 的 /v1/models
    需鉴权（不带 key 返回 401），导致真实可用站被判离线、observing 无法毕业。
    `probe_alive` 加可选 api_key 带 Authorization 头；`_record_alive` 即时解密传入用完即弃。
    诊断确认：带 key GET /v1/models→200、POST /v1/chat→200 真实回复（gpt-5.5）。
  - **补 leaderboard_weights**：真实库该表为空导致 composite=None（scoring._weights_for
    缺权重返回全 0）。调 seed_demo._seed_weights() 补三榜权重（幂等，不动站点）。
  - 探测结果：HeroAPI 在 gpt 观察区 composite=93.3（uptime=100/speed=75.8/auth=100），
    详情页 verified=True、uptime_30d=100%、30 点曲线。**rank=None 是正确行为**——
    observing 不上主榜名次，毕业到 online 才有（blueprint 第七节）。无 key/base_url 泄露
    （site_url=makabaka.chat 是站长主动填的公开主页，非泄露）。
  - 迁移重整（提交 9f86695）：3 个手写迁移合并为单一 0_20260629215040_init.py（含全字段）。

### Current State（存档点 2026-06-29 续6）

- 全链路真实跑通：上架→审核→**带 key 真实探测→真实分→榜单观察区/详情页**。
- **数据靠手动跑一轮产出**：worker 尚未在 VM 常驻，不会自动更新；observing 也无法靠
  时间+样本自然毕业到 online（需 worker 周期跑 + 满 OBSERVING_MIN_DAYS/样本数）。
- **Git：本会话 3 提交（feat/hero，尚未 push）**：44779ec 详情页 / 810b64f 探测带 key /
  9f86695 迁移合并。
- 尚无：坟场页、评价、集市；质量探测预算扣减；Redis ZSET。

### Next Steps（下次从这里挑）

- **让 worker 在 VM 常驻**（`python -m app.worker.scheduler`）持续探测，观察 HeroAPI 毕业。
- 坟场页 /graveyard（复用详情页布局 + 客观措辞）。
- C 端评价（充值 key 自证 verified）→ 喂 review_score。
- 中转集市（B 端发帖/对接/确认 + 互评解锁）。
- 站点编辑/下架（站长改 base_url/key/硬信息——目前只能脚本改库）。

### 环境 / 联调要点（更新）

- 后端在 VM 8010 跑着（db up）；本机可直连 VM PG（192.168.142.129:15432）跑脚本。
- **admin 账号密码已改为 test1234**（admin@example.com）；站长 hero@gmail.com。
- 前端：`cd frontend && npm run dev`（.env.local 指向 http://192.168.142.129:8010）。
- 手动跑一轮探测：本机连 VM 库后 `await run_alive_probe()` / `run_quality_probe()`（无需传 client）。
- 详情页访问 /site/heroapi；榜单 /rank/gpt 观察区可见 HeroAPI。

## 2026-06-29（续5：站点详情页打通——闭合榜单死链）

### Completed

- 站点详情页 `/site/{slug}`（features.md 第 4 节三屏分区 + 可见性表），无新 DB 列/迁移：
  - 后端 `schemas/site_detail.py`：`SitePublicView`（游客字段 + uptime_history/uptime_30d +
    verified + 各榜 scores）、`UptimePoint`、`SiteScoreBrief`、`SiteGatedView`（min_topup/
    pay_methods/rpm_limit + ttfb_p50/p90）。**红线：两者都绝不含 base_url/key/key_hint。**
  - `services/site_detail_service.py`：`get_public_detail`（pending/rejected 不公开→404）、
    `compute_uptime_history`（近 30 天逐日分桶 alive+triggered，**复用 probe_stats._in_maintenance_window
    剔除维护窗失败**红线，无样本当天记 None 不补 0）、`get_gated_detail`（质量探测 TTFB 分位）。
  - `routes/sites.py`：`GET /sites/{slug}`（无鉴权，吃 SEO，SSR）+ `GET /sites/{slug}/private`
    （get_current_user，401→前端转化钩子）。**声明在 /mine 之后，确保字面量优先匹配**（已验证路由序）。
  - 前端 `app/site/[slug]/page.tsx`（RSC SSR + ISR 60s）：信任卡（风险灯+存活时长+最近探测+30 天
    在线率曲线，**纯内联柱状图不引图表库**+已验证可用）/ 性能区（模型清单游客可见）/ 决策区（GatedPanel）；
    动态 generateMetadata + JSON-LD WebPage（评价上线再补 AggregateRating）；404 走 notFound、
    后端不可达兜底（区分真 404）。`gated-panel.tsx` 客户端组件：读 getToken()，无 token 渲染登录转化钩子，
    有则拉 /private 渲染硬信息。坟场措辞红线：风险灯说明只陈述探测事实。
  - **闭合榜单死链**：rank 页主榜/移动卡/观察区站名全部 `<Link href={/site/slug}>`。
  - `lib/api.ts`：siteApi.publicDetail/privateDetail + 全套类型。
  - seed_demo 补探测时序：每站 ~30 天 alive 探测（按 downtime_ratio 确定式掺失败，幂等可复现）+
    在线/异常/复活站每天 1 条成功 quality 探测（TTFB+is_authentic）；站补 first_seen_at/last_probe_at/
    硬信息；--wipe 同步清 probe_results。已在 sqlite 验证（stellar 98.9%/quasar 66.7%/comet observing
    无质量探测 verified=False，幂等二次跑全跳过）。
- 测试：`tests/test_site_detail.py` 10 测试（公开字段+无 key/base_url 泄露/在线率分桶/维护窗剔除/
  verified/pending 404/未知 404/gated 401/登录见硬信息+不泄露/gated 404）。后端共 **75 passed**，ruff 通过。
  前端 lint + build 均过（/site/[slug] 为 ƒ 动态 SSR）。

### Current State（存档点 2026-06-29 续5）

- 全 C 端浏览链路闭合：榜单 → 点站名 → 详情页（信任卡/性能/决策三屏，游客 SEO + 登录硬信息）。
- **Git 状态：本功能待提交（feat/hero 分支，尚未 push）。** 之前三提交见续4。
- 尚无：坟场页、评价、集市；质量探测预算扣减；Redis ZSET（直读 PG 够用）。

### Next Steps（下次从这里挑）

- 坟场页 `/graveyard`（suspected_dead/dead 站，复用详情页客观措辞；详情页布局已成型可复用）。
- C 端评价（充值 key 自证 verified）→ 喂 review_score（scoring 已留口子）。
- 中转集市（B 端发帖/对接/确认 + 互评解锁）。
- 质量探测预算扣减（probe_budget_daily>0 时按当日已用降频）。
- PG/上游恢复后：`aerich upgrade`（review_note + status_changed_at 两迁移）+ seed_demo + 真实联调。

### 环境 / 联调要点（沿用）

- 后端 8010：`cd backend && poetry run uvicorn app.main:app --port 8010`；worker：`python -m app.worker.scheduler`
- 前端：`cd frontend && npm run dev`（.env.local 指向 http://192.168.142.129:8010）
- 演示数据：`poetry run python -m app.scripts.seed_demo`（需可达 PG；--wipe 清理）。详情页访问 `/site/stellar-relay`。
- 测试管理员：admin@example.com / RouterHub@2026；admin 只能脚本造。

## 2026-06-29（续4：探测 worker 打通——技术核心）

### Completed

- 探测 worker 全链路（真实探测 + 状态机 + 评分），分层「纯函数 + 依赖注入」便于单测：
  - `worker/http_probe.py`：probe_alive(GET /v1/models)、probe_quality(POST /v1/chat，用站长 key，
    max_tokens=1)；client 注入(测试用 httpx.MockTransport)；随机 UA + 轻随机 prompt 防作弊；
    超时/错误归一化；**key 绝不进 error_sample/日志/返回值**。
  - `worker/state_machine.py`：`decide_transition(status, ProbeStats)` 纯函数，照搬 blueprint 五之二
    全转移表（online↔abnormal→suspected→dead、各级恢复、observing 毕业「与」条件/暴毙跳过 abnormal、
    revived 横跳直接打回）；阈值全走 settings。pending 不在此（admin 审核管）。
  - `worker/probe_stats.py`：从 probe_results 倒序数连续成败（**维护窗内失败剔除**红线）+ observing
    天数/alive·quality 样本数。**不加计数列**，符合「只依赖探测事实」原则。
  - `services/scoring.py`：四指标归一化(① uptime 时间衰减半衰期 ② speed P90+锚点分段 ③ authenticity
    最近 N 次成功率 ④ review 贝叶斯)，**缺数据记 None 不补 0**，composite 动态权重重分配（陷阱 C）；
    recompute_site_scores 按声明模型子串归榜(claude/gpt/gemini) upsert + recompute_ranks。
  - `worker/probes.py`：替换桩。alive 轮拉 online/abnormal/observing/revived/坟场态 并发探测→写
    ProbeResult→跑状态机落库→online→abnormal 瞬间插队 triggered 质量探测→轮尾重算 scores/三榜 ranks；
    quality 轮拉主榜+观察态用 key 打 chat。key 即时 decrypt 用完即弃。run_*_probe(client=None) 默认建真实
    AsyncClient，scheduler 无需改。预算扣减记 TODO（budget_daily=0 视为不限）。
  - 模型：RelaySite 加 `status_changed_at`（时间型转移条件需要，updated_at 每次保存都变不可用）
    + 手写迁移 `2_20260629194500_add_status_changed_at.py`；review_site 审核通过时打戳；seed_demo 同步打戳。
- 测试：test_http_probe(6, MockTransport)、test_state_machine(12, 纯函数穷举转移边)、
  test_scoring(12, 归一化边界+动态权重)、test_worker_round(5, sqlite+注入 client 端到端)。
  后端共 **65 passed**，ruff 通过。

### Current State（存档点 2026-06-29 续4）

- 探测 worker 逻辑完整：能真实打上游、判状态机、算分刷 site_scores，喂给已就绪的 /rank。
- 全链路：注册→上架→审核→**探测产出真实分**→榜单展示，闭环（探测在 sqlite+MockTransport 验证，
  实跑待 PG/上游可达）。
- **Git 状态：本会话三功能已分 3 提交、工作区干净，均在 feat/hero 分支「尚未 push」**：
  - `57c18fb` 探测 worker（真实探测+状态机+评分）
  - `1e4d6fe` 排行榜展示页（三分榜 SSR + 只读接口）
  - `e085b33` 管理员站点审核（pending→observing/rejected）
  - 回来后若要推远程：`git push -u origin feat/hero`。
- 尚无：详情页、坟场页、评价、集市；Redis ZSET（/rank 直读 PG 够用，ZSET 作缓存优化记 TODO）。

### Next Steps（下次从这里挑）

- 站点详情页 /site/{slug}（游客基础+在线率 / 登录见硬信息 + 在线率曲线，读 probe_results）。
- 坟场页 /graveyard（suspected_dead/dead 站，客观探测事实措辞）。
- C 端评价（充值 key 自证 verified）→ 喂 review_score。
- 中转集市（发帖/对接/确认 + B 端互评解锁）。
- 质量探测预算扣减（probe_budget_daily>0 时按当日已用降频）。
- PG/上游恢复后：`aerich upgrade`（review_note + status_changed_at 两迁移）+ seed_demo + 真实站点联调 worker。

### 环境 / 联调要点（沿用）

- 后端 8010：`cd backend && poetry run uvicorn app.main:app --port 8010`；worker：`python -m app.worker.scheduler`
- 前端：`cd frontend && npm run dev`（.env.local 指向 http://192.168.142.129:8010）
- 演示数据：`poetry run python -m app.scripts.seed_demo`（需可达 PG；--wipe 清理）。
- 测试管理员：admin@example.com / RouterHub@2026；admin 只能脚本造。

## 2026-06-29（续3：排行榜展示打通）

### Completed

- 排行榜只读接口 + 服务端渲染展示页：
  - 后端：`schemas/rank.py`（RankEntry 公开安全字段、RankResponse 主榜+观察区分列）；
    `services/rank_service.py`（**只读** site_scores 预计算分，service 层 join relay_sites；
    按站点 status 分流：主榜 online/abnormal/revived、观察区 observing、坟场状态不上榜；
    sort=composite|speed|uptime，null 分垫底；**不在此算分，算分是 worker 的活**）；
    `routes/rank.py`（GET /rank?leaderboard=&sort=，游客无鉴权，非法 leaderboard/sort→422）注册进 router。
  - 前端 URL 迁移：删 app/leaderboard，navbar + 首页全量改 /rank（blueprint「一次定终身」永久结构，
    收录前改最佳时机）；`app/rank/page.tsx` redirect→/rank/claude。
  - 榜单页 `app/rank/[family]/page.tsx`（**RSC 服务端渲染**，为 SEO 红线）：
    服务端 fetch 后端 /rank（lib/api `rankApi.list`，next.revalidate=60 ISR）；
    三 Tab（claude/gpt/gemini，<Link> 保 SSR）+ 排序切换（?sort= query 服务端读）；
    主榜桌面表格 / 窄屏卡片（mobile-first）；观察区独立区块标「数据积累中」；
    动态 generateMetadata + JSON-LD ItemList；null 分显示「暂无」不显示 0；后端不可达兜底空态。
  - 演示数据 `scripts/seed_demo.py`（幂等以 slug 锚、--wipe 清理）：1 假 owner、5 站
    （online/abnormal/observing 各状态）、三榜 site_scores（分数手编排名）、leaderboard_weights
    三行（Claude 抬真实性/GPT/Gemini 抬在线率，blueprint 3.3）。已在 sqlite 验证幂等 + 排序正确。
- 测试：`tests/test_rank.py` 9 测试（默认 composite 降序/sort=speed 改序/observing 分流/坟场不上榜/
  null 垫底/公开安全无 key/非法 leaderboard 422/非法 sort 422/空榜）。后端共 **30 passed**，ruff 通过。
  前端 lint + build 均过（/rank/[family] 为 ƒ 动态 SSR）。

### Current State（存档点 2026-06-29 续3）

- 注册/登录 → 上架(pending) → 审核(approve→observing/reject→rejected) → **榜单展示**（主榜+观察区，三榜+排序）全链路 UI 可走。
- 榜单读真后端预计算分；但分数目前只能靠 seed_demo 造（探测 worker 仍是桩，还没有真实探测产出分）。
- 尚无：真实探测、真实算分刷分、站点详情页、坟场页、评价、集市、站点编辑/下架。

### Next Steps（下次从这里挑）

- **探测 worker 接真实站点**（替换 probes.py 桩，用加密 key 打 base_url 写 probe_results，
  驱动 observing→online 毕业与坟场状态机）——这是让榜单有真实数据的关键，也是技术核心。
- 评分计算服务（blueprint 六之二归一化 + 动态权重）+ 刷 site_scores/Redis ZSET，喂给已就绪的 /rank。
- 站点详情页 /site/{slug}（游客基础+在线率 / 登录见硬信息）。
- 坟场页 /graveyard。
- 站点编辑/下架。
- PG 恢复后：跑 `aerich upgrade`（review_note 迁移）+ `python -m app.scripts.seed_demo` 让榜单有内容。

### 环境 / 联调要点（沿用）

- 后端端口 8010（本机 8000 被占）：`cd backend && poetry run uvicorn app.main:app --port 8010`
- 前端：`cd frontend && npm run dev`（.env.local 指向 http://192.168.142.129:8010）
- 演示数据：`poetry run python -m app.scripts.seed_demo`（需可达 PG；--wipe 清理重来）。
- 测试管理员账号：admin@example.com / RouterHub@2026；admin 只能脚本造。

## 2026-06-29（续2：管理员审核打通）

### Completed

- 管理员审核闭环：
  - 后端：`get_current_admin` 依赖（与 get_current_owner 对称，role!=admin→403）；
    `SiteAdminView`（站长字段 + owner_email/wechat/qq + created_at，审核触达用，仍不含 key）、
    `SiteRejectRequest`（note 必填）；service `list_pending_sites`（虚拟外键 service 层 join 站长）
    + `review_site`（仅 pending 可审，否则 SiteNotPending→409；通过→observing，驳回→rejected 写 review_note）；
    `routes/admin.py`（GET /admin/sites/pending、POST .../approve、.../reject）注册进 router。
  - 模型：`RelaySite` 加 `review_note TextField(null=True)`，站长可见驳回理由；`SiteOwnerView` 同步加该字段。
  - 迁移：PG 当时不可达（VM 192.168.142.129:15432 down），手写
    `migrations/models/1_20260629181200_add_site_review_note.py`（ALTER ADD review_note），
    待 PG 恢复后 `aerich upgrade` 应用。
  - 前端：`adminApi.pending/approve/reject` + `SiteAdminView` 类型；`/admin` 替换 ComingSoon
    为审核后台（非 admin 拦截、待审卡片含站长联系方式、通过/驳回按钮、驳回弹理由输入、审核后即时移除）；
    `/owner` STATUS_META 加 rejected、站点卡片 rejected 时显示驳回理由。
- 测试：`tests/test_admin.py` 8 测试（列待审/通过→observing/驳回→rejected+理由/驳回必填/重复审核 409/
  404/站长 403/未登录 401）。后端共 **21 passed**，ruff 通过。前端 lint + build 均过。

### Current State（存档点 2026-06-29 续2）

- 已打通注册/登录 → 站长上架(pending) → 管理员审核(approve→observing / reject→rejected+理由)。
- 状态机前两步落地（pending→observing/rejected）；observing 之后的 online 毕业、坟场分级仍待真实探测驱动。
- 尚无：真实探测、评分、榜单只读接口、站点编辑/下架、集市。

### Next Steps（下次从这里挑）

- 探测 worker 接真实站点（替换 probes.py 桩，用加密 key 打 base_url 写 probe_results，
  驱动 observing→online 毕业与坟场状态机）。
- 排行榜页（可先用假数据做展示）。
- 站点编辑/下架（站长对自己站点的管理）。
- PG 恢复后跑 `aerich upgrade` 应用 review_note 迁移。

### 环境 / 联调要点（沿用）

- 后端端口 8010（本机 8000 被占）：`cd backend && poetry run uvicorn app.main:app --port 8010`
- 前端：`cd frontend && npm run dev`（.env.local 指向 http://localhost:8010）
- 测试管理员账号（真实 PG）：admin@example.com / RouterHub@2026；admin 只能脚本造
  （`python -m app.scripts.create_admin --email ...`）。

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
