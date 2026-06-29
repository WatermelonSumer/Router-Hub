# TODO

## High Priority

- 生成首个 aerich 迁移（`aerich init` + `aerich init-db`，需可达 PostgreSQL），并手工把
  `users.email`、`relay_sites.slug` 的唯一约束改写为 partial unique index（`WHERE is_deleted=false`）。
- 实现鉴权（注册/登录 JWT，注册选 role=user|owner）。
- 实现站点上架（owner，key 加密落库）+ admin 审核。【已完成：上架 + 审核(approve→observing/reject→rejected+理由)】
- PG 恢复后跑 `aerich upgrade` 应用 review_note 迁移（1_20260629181200_add_site_review_note，当时 VM 不可达手写）。

## Medium Priority

- 实现真实分层探测（替换 worker/probes.py 桩）：httpx 并发、TTFB 测量、状态机判定、预算扣减原子性。【已完成：探测+状态机+评分全做，65 测试。预算扣减仍 TODO(budget_daily=0 视为不限)】
- 实现评分归一化与综合分计算（blueprint 六之二）+ 刷 Redis ZSET。【已完成评分(services/scoring)；Redis ZSET 未做——/rank 直读 PG site_scores 够用，ZSET 作缓存优化待加】
- 实现榜单/详情/坟场只读接口 + 评价（充值 key 自证）。【榜单 /rank 已完成；详情页/坟场/评价待做（下一步推荐）】
- 实现中转集市发帖/对接/确认 + B 端互评解锁。
- 搭前端 Next.js 骨架。【已完成（骨架 + 登录 + 主框架 + 站长台 + 审核台 + 榜单页）】

## Low Priority（blueprint 第十三节待打磨）

- 详情页字段细化（在线率曲线存储粒度：原始 probe vs 降采样聚合）。
- API 出入参 Pydantic schema 细化。
- 中转集市对接流程状态机（超时/拒绝/取消）。
- 充值验证对 new-api/sub2api 不同版本额度接口的适配层。
- probe_results 膨胀治理（分区/降采样/归档）。

## 已知问题/注意

- `.env` 的 `KEY_ENCRYPTION_SECRET` 为空时，security 模块加解密会主动报错（设计如此，需先填密钥）。
- 测试用 sqlite 内存库，与 Postgres partial index 行为有差异，partial index 仅在真实 PG 验证。
