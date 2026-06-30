# Router-Hub 架构蓝图

> AI 中转站 Rank 系统 —— 技术架构真相源
> 状态:设计定稿(尚未开始实现)
> 最后更新:2026-06-28

本文件是技术实现的「真相源」。所有产品决策的来龙去脉见同目录 `features.md`。
本蓝图只描述**怎么建**,不解释**为什么**(那在功能文档里)。

---

## 一、技术栈(已定稿)

| 层 | 选型 |
|---|---|
| 后端 API | FastAPI(纯 API)+ Pydantic + Tortoise ORM |
| 数据库迁移 | Aerich(Tortoise 官方迁移工具) |
| 探测 Worker | 独立进程,APScheduler 三周期调度,httpx.AsyncClient 并发 |
| 数据库 | PostgreSQL |
| 缓存/排行榜 | Redis(ZSET 存榜单,限流,会话) |
| 前端 | Next.js(App Router)+ TypeScript + Tailwind + shadcn/ui + Framer Motion + next-themes(light/dark) |
| key 加密 | Fernet / AES-GCM,密钥走环境变量(绝不进代码库/日志) |

---

## 二、服务拓扑

```
Next.js (SSR/SSG)  ──REST──>  FastAPI ──> PostgreSQL
   榜单/坟场可被收录              │  ↑          ↑
   广场在登录墙后                 │  │          │
                          Redis(榜单ZSET/限流)  │
                                              │
              探测 Worker(独立进程)───────────┘
              ├ 存活探测   每 3–5 分钟   /v1/models  (便宜·高频)
              ├ 质量探测   每 30–60 分钟 /v1/chat    (烧钱·低频·用站长key)
              └ 触发探测   异常时插队     快速确认宕机/跑路
```

**关键架构原则:**

1. **Web 进程与探测 Worker 必须分离**。探测是慢 IO + 可能被上游限速,绝不能阻塞用户请求。
2. **排名分数预计算,不实时算**。用户查榜 = 一次 Redis ZSET 有序读取。
3. **评分公式透明可配**,权重写在配置表,不写死在代码里 —— 透明度是 rank 平台的信誉基础。
4. **key 永不下发前端**,连站长本人也只见掩码 `sk-***1234`。所有用 key 的动作只在后端 worker 内。

---

## 三、数据模型(核心表)

### 全表通用约定(强制,所有表无例外)

1. **双键制:每张表都有**
   - `id` —— 内部主键,bigint 自增(仅 ORM 内部用,**不对外暴露**)。
   - `<实体>_id` —— 业务键,**uuid7(有序 uuid)**,建唯一索引。如 `user_id`、`goods_id`、`site_id`。
   - 有序 uuid7 写入时近似递增,B-tree 索引友好,避免 uuid4 随机分布导致的索引碎片。

2. **虚拟外键:数据库层零外键约束**
   - 关联只存对方的**业务键值**,不建 DB FK,无级联。
   - 例:Goods 关联 User → Goods 表存 `user_id` 字段(值 = `User.user_id`),自身另有 `goods_id`。
   - 所有关联完整性、级联行为**全部在业务层(service)处理**。
   - 关联字段一律建索引。

3. **假删除:全表软删除,绝不物理删除**
   - 每表带 `is_deleted`(bool,默认 false)+ `deleted_at`(nullable)。
   - 所有查询默认过滤 `is_deleted = false`(用 Tortoise 的默认 manager/基类统一处理)。
   - 业务层「删除」= 置 `is_deleted=true` + 写 `deleted_at`。
   - **唯一约束 + 假删除冲突** → 用 Postgres **partial unique index**(`WHERE is_deleted = false`),
     使已假删除的行不占用唯一值(如 email 假删除后可重新注册)。

4. **时间戳:全表带** `created_at`、`updated_at`。

5. **uuid7 生成:用 `uuid-utils`**(Rust 实现,性能优于纯 Python uuid6 库)。

> 下方各表字段省略了这套通用列(`id` / `is_deleted` / `deleted_at` / `created_at` / `updated_at`),只列业务字段。所有 `xxx_id` 字段均为 uuid7 虚拟外键。

### users — 用户与站长共表,role 区分
```
user_id(uuid7,业务键), email, password_hash, role(user|owner),
wechat, qq            -- 站长必填;联系方式默认隐藏,对接时才交换
```

### relay_sites — 站长上架的中转站
```
site_id(uuid7,业务键), owner_id(虚拟FK → users.user_id),
name, slug(唯一·URL用·永不改),
site_url, base_url,
encrypted_key, key_hint('sk-***1234'),   -- key加密落库,永不下发前端
probe_budget_daily,                       -- 站长设每日探测预算上限,超额自动降频
declared_models(jsonb),                   -- 站长声称支持的模型
min_topup, pay_methods, rpm_limit,        -- 决策硬信息(详情页对游客锁,登录可见)
status(pending|observing|online|abnormal|suspected_dead|dead|revived),
maintenance_windows(jsonb),               -- 站长声明的维护窗;窗内失败不计入在线率
first_seen_at, last_probe_at
```
> **status 是统管三件事的状态机:**
> - 审核:`pending`
> - 冷启动观察区:`observing`(新站满 7 天攒够样本后转 `online`)
> - 坟场分级:`online → abnormal → suspected_dead → dead → revived`

### probe_results — 探测时序数据(会膨胀,后期分区/降采样)
```
probe_id(uuid7,业务键), site_id(虚拟FK → relay_sites.site_id),
probe_type(alive|quality|triggered), probed_at,
target_model, ttfb_ms, total_ms, http_status,
is_alive, is_authentic(0/1),   -- MVP真实性只做「通了/没通」,降智检测留长期
error_sample
```

### site_scores — 预计算的综合分(用户查榜读这里)
```
score_id(uuid7,业务键), site_id(虚拟FK → relay_sites.site_id),
leaderboard(claude|gpt|gemini),
uptime_score, speed_score, authenticity_score, review_score,
composite_score, rank, updated_at
```
> 每个站 × 每个分榜一行。Worker 每轮探测后重算,并刷新 Redis ZSET。

### leaderboard_weights — 每个分榜一套权重(可配)
```
weight_id(uuid7,业务键), leaderboard, w_uptime, w_speed, w_authenticity, w_review
```
> 三榜权重不同:Claude 榜抬高真实性;GPT 榜抬高价格/在线率;Gemini 榜抬高在线率。

### reviews — 评价(C 端 + B 端共表,review_type 区分)
```
review_id(uuid7,业务键),
site_id(虚拟FK → relay_sites.site_id), author_id(虚拟FK → users.user_id),
review_type(user_topup|owner_deal),
rating, content,
verified(bool)                -- user_topup: 用key查到该站消费记录
                              -- owner_deal: 在广场对接 confirmed 过
```
> 展示时两类分开标注:「来自用户(已充值✓)」vs「来自交易对手(已对接✓)」。

### marketplace_posts — 站长广场帖子(登录墙后,刻意不可 SEO)
```
post_id(uuid7,业务键), author_id(虚拟FK → users.user_id),
post_type(supply|demand), direction(upstream|downstream),
model_family, rate, rpm, volume, settlement(daily|weekly|prepaid),
note(自由文本), status(open|closed)
```

### post_responses — 广场对接记录(解锁 B 端互评的凭证)
```
response_id(uuid7,业务键),
post_id(虚拟FK → marketplace_posts.post_id),
responder_id(虚拟FK → users.user_id),
status(pending|connected|confirmed)
```
> 双方 `confirmed` 后,才解锁彼此的 `owner_deal` 评价权 + 交换微信/QQ 名片。

---

## 四、API 分组(FastAPI 路由)

```
/auth      register, login(JWT), 注册时选择 role(user|owner)
/rank      GET 榜单(游客可读, ?leaderboard=claude&sort=composite|speed|uptime)
/sites     GET 详情(游客见基础+在线率 / 登录见硬信息)
           POST 上架(owner)
           GET 自己站探测看板(owner,只读不可申诉)
/reviews   POST(需验证), GET
/graveyard GET 坟场列表/详情(可 SEO)
/market    GET 帖子列表(仅已验证 owner)
           POST 发帖, POST 对接, POST 确认成交
/admin     审核站点
```

---

## 五、探测 Worker 流程

```
存活轮(3-5min):
  拉所有 online/observing 站 → 并发打 /v1/models
  → 写 probe_results → 更新 uptime → 异常计数++
  → 连续 N 次失败 → 触发探测插队 + 状态降级

质量轮(30-60min):
  拉所有 online 且预算未超的站 → 用站长 key 打 /v1/chat 最短 prompt(max_tokens=1)
  → 测 TTFB / 真实性(0/1)→ 写 probe_results → 扣站长每日预算

触发轮(异常时):
  存活探测发现连续失败 → 立即插队做一次质量探测 → 快速判定真宕机 or 误报

每轮收尾:
  重算 site_scores(滑动窗口 + 时间加权,抗抖动)→ 刷新 Redis ZSET
```

**防作弊小成本措施:** 探测不用固定 UA / 固定 IP / 固定 prompt,留随机性,抬高站长「给探测开小灶」的门槛。

---

## 五之二、探测判定状态机(坟场 + 冷启动共用)

**核心原则:状态转移由「连续探测结果次数」驱动,不由时间驱动。**
时间只做辅助展示。这样判定只依赖实际探测到的事实,worker 自身宕机不会污染判定。
所有阈值见 `.env`(配置项名见「配置管理」节);下表括号内时间按存活探测 5 分钟/次换算,仅供直观。

### 状态转移表

| 当前状态 | 触发条件 | 转到 | 说明 |
|---|---|---|---|
| `pending` | admin 审核通过 | `observing` | 上架后先进观察区 |
| `pending` | admin 拒绝 | 拒绝/删除 | —— |
| `observing` | 成功探测数达标 **且** 满 7 天 | `online` | 冷启动毕业,入主榜(与条件) |
| `observing` | 连续失败达「疑似」阈值 | `suspected_dead` | 新站直接暴毙,跳过 abnormal |
| `online` | 连续失败 `FAIL_TO_ABNORMAL`(3,≈15min) | `abnormal` | 短暂抖动,榜上标黄,**不进坟场** |
| `abnormal` | 恢复成功 `RECOVER_FROM_ABNORMAL`(2) | `online` | 抖动恢复,摘黄标 |
| `abnormal` | 连续失败累计 `FAIL_TO_SUSPECTED`(36,≈3h) | `suspected_dead` | 进坟场「疑似」区 |
| `suspected_dead` | 恢复成功 `RECOVER_FROM_SUSPECTED`(3) | `revived` | 诈尸恢复 |
| `suspected_dead` | 连续失败累计 `FAIL_TO_DEAD`(576,≈48h) | `dead` | 确认阵亡 |
| `dead` | 恢复成功 `RECOVER_FROM_DEAD`(5) | `revived` | 死而复生(要求更严) |
| `revived` | 稳定在线满 `REVIVED_STABLE_HOURS`(24h) | `online` | 观察期过,回归;**永久保留「曾阵亡 X 天」污点** |
| `revived` | 再次连续失败达「疑似」阈值 | `suspected_dead` | 反复横跳,不给缓冲直接打回 |

### 关键设计点
- **`abnormal` 是缓冲带,绝不进坟场**:唯一目的是吸收网络抖动/上游瞬断/重启。只有熬过 ≈3h 仍不恢复才进坟场,防误伤 + 防法律纠纷。
- **恢复阈值随死亡程度递增(2→3→5)**:深度死亡的站偶尔回包可能是回光返照,要求更多次连续成功才认「复活」。
- **`revived` 保留污点 + 反复横跳直接打回**:给过一次机会的站不再给 abnormal 缓冲。
- **观察区毕业是「与」条件**:次数 **且** 时间都要满足,防止刷量速成。
- **触发探测的角色**:`online→abnormal` 发生瞬间立即插入一次质量探测(用 key 真打 chat),分辨「整站挂了」还是「只是 /v1/models 接口抽风」,避免误降级还能用的站。

### 维护窗特殊处理
站长声明的维护窗内:探测照常进行,但失败**不计入连续失败计数器、不计入在线率分母**(豁免);窗口结束后计数器清零重算。
维护窗有上限(`MAINTENANCE_MAX_HOURS_PER_WINDOW`=4h / `MAINTENANCE_MAX_WINDOWS_PER_WEEK`=2),防止用「假维护窗」长期掩盖真跑路。

---

## 六、评分公式

```
composite_score = uptime×w_uptime + speed×w_speed
                + authenticity×w_authenticity + review×w_review
```

| 指标 | 来源 | 要点 |
|---|---|---|
| uptime 在线率 | 存活探测 | 时间加权:近 7 天权重 > 30 天前;维护窗内失败不计 |
| speed 速度分 | 质量探测 TTFB | 用**中位数/P90**(非均值,防抖动);归一化到 0–100 |
| authenticity 真实性 | 质量探测 | MVP 只做 0/1;返回假模型必须狠扣分 |
| review 评价分 | C 端充值验证评价 | 权重低(≤10%);仅 verified 评价计入 |

**抗抖动:** 状态变更需连续 N 次确认;分数用滑动窗口,不被单次探测带跳。
**防躺赢:** 近期表现权重 > 历史累积,老站变差会掉、新站变好能升。

### 六之二、归一化(四指标各算法,均 0-100)

**总原则:** 四个原始数据性质不同(比例/毫秒/0-1/星级),归一化方式各异,绝不套同一公式;
最终都归一到 0-100 再加权。所有参数见 `.env`。

**① uptime_score —— 时间衰减加权(非简单比例)**
```
uptime_raw = Σ(wᵢ × resultᵢ) / Σ(wᵢ)        # resultᵢ∈{0,1}
wᵢ = 0.5^(age_days / UPTIME_HALFLIFE_DAYS)   # 指数半衰减,默认半衰期7天
uptime_score = uptime_raw × 100
```
- 越近的探测权重越高:"现在稳不稳" > "历史稳不稳"。
- 维护窗内探测从分子分母**双双剔除**,不参与加权(与状态机维护窗豁免一致)。

**② speed_score —— P90 + 锚点分段映射(非均值、非线性)**
- 陷阱A:用最近窗口质量探测 TTFB 的 **P90**(非均值,防极值带歪)。
- 陷阱B:延迟体感非线性 → 锚点分段映射,快区间分得细、慢区间一锅烩。
```
SPEED_ANCHORS_MS=1500,3000,6000,10000   SPEED_ANCHORS_SCORE=100,75,50,20
规则:≤首拐点(1500ms)=100;拐点间线性插值;超末拐点在[0,末分数(20)]线性到0;完全不可用=0
```
  (中转站多跳,普遍比直连慢,故 1500ms 为满分基准而非 300ms)
- 陷阱C:无质量探测数据(观察区/预算耗尽)**绝不给0分** → 标"暂无数据",权重动态重分配(见⑤)。

**③ authenticity_score —— 最近N次成功比例(非单次)**
```
authenticity_score = (最近 AUTHENTICITY_WINDOW(20) 次质量探测中 is_authentic=1 比例) × 100
```
- 偶尔一次失败只扣一点;持续造假/打不通才归零。权重高(尤其Claude榜),狠拉造假站。

**④ review_score —— 贝叶斯平均(评价少时不可信)**
```
review_raw = (C × m + Σ ratings) / (C + n)
  n=该站verified评价数; m=全站verified评价均星(先验); C=REVIEW_BAYESIAN_C(5)
review_score = review_raw / 5 × 100
```
- 评价少时被先验稀释,不暴涨暴跌(IMDb 同款)。仅 `verified=true` 评价计入;权重≤10%。

**⑤ 综合分合成 + 缺失数据动态权重(关键)**
```
有数据指标集 S;  composite = Σ(scoreᵢ×wᵢ for i∈S) / Σ(wᵢ for i∈S)
```
- 某指标无数据时**不补0**,把其权重按比例摊给有数据的指标 → 冷启动公平性的数学保证。
- 例:观察区新站无 speed 数据,则用 uptime+authenticity(+review)的有效权重归一化排序。

---

## 七、冷启动(方案 C:隔离观察区)

新站上架 → `observing` 状态,进独立「新站观察区/试用榜」,标注「数据积累中,7 天后入主榜」。
攒够探测样本后转 `online`,进主榜正常排名。
好处:不污染主榜公信力、给新站曝光位、刷榜只能刷观察区影响不到主榜。

**观察区排序:** 用与主榜同一套归一化公式(缺失指标走⑤动态权重),排在独立榜;
分数旁显示置信度(基于已有探测次数)。毕业进主榜时历史探测数据**沿用不清零**,平滑过渡。

---

## 八、权限矩阵(最终版)

| 能力 | 游客 | user | owner未验证 | owner已验证真站 |
|---|---|---|---|---|
| rank 榜单 / 坟场 | ✅ | ✅ | ✅ | ✅ |
| 详情页基础+在线率 | ✅ | ✅ | ✅ | ✅ |
| 详情页硬信息(延迟/价格/地址) | ❌ | ✅ | ✅ | ✅ |
| C 端评价(充值验证) | ❌ | ✅ | ✅ | ✅ |
| 自己站探测看板 | — | — | ✅ | ✅ |
| 查看/使用广场 | ❌ | ❌ | ❌ | ✅ |
| 广场互评(需对接 confirmed) | — | — | — | ✅ |

> **owner 验证条件:** 必须成功上架并通过探测**至少一个真实站点**,才解锁广场。

---

## 九、SEO 基建(建站期一次性埋好,不可后补)

| 现在必须埋(架构性) | 以后再做(内容性) |
|---|---|
| Next.js SSR/SSG 渲染 | 关键词布局 |
| URL 永久结构 `/rank/{family}`、`/site/{slug}`、`/graveyard/{slug}` | 外链建设 |
| 每页动态 metadata(title/description) | 导购长文运营 |
| JSON-LD:榜单=ItemList、评价=AggregateRating、坟场=客观事实措辞 | |
| sitemap.xml 自动生成 | |

> **广场刻意排除在 SEO 之外**,保护批发底价不外泄。
> 详情页对游客**部分可见**(基础+在线率),既保 SEO 入口又留注册转化钩子。

---

## 十、底座项目背景

中转站本身由开源项目搭建,决定了可探测面:
- **new-api**(QuantumNous):one-api 增强分支,OpenAI 兼容网关,暴露 `/v1/models`、`/v1/chat/completions` 及后台 `/api/...`。主流搭建框架。
- **sub2api**(Wei-Shaw):订阅账号转 API,账号池中转。

C 端充值验证(评价资格)正是复用 new-api/sub2api 的 key:用用户提供的 key 调该站额度/用量查询接口,查到消费记录即证明真实付费用户,无需上传截图。

---

## 十一、配置管理

**划分原则:全局/低频/运维改 → `.env`;按业务维度区分/要热更新 → 数据库表。**

| 配置 | 放哪 | 为什么 |
|---|---|---|
| 探测阈值(状态机各次数、观察期、维护窗上限) | `.env` | 全局生效、低频、运维改 |
| 探测频率(存活/质量间隔) | `.env` | 同上,重启 worker 生效 |
| 分榜权重(w_uptime 等) | 表 `leaderboard_weights` | 每榜不同、要热调、未来后台界面 |
| key 加密密钥 | `.env`(绝不进库) | 安全 |

`.env` 由 Pydantic `Settings` 类(`pydantic-settings`)统一加载,代码只读 settings 对象,
不直接读 `os.environ` —— 有类型校验、默认值、好测试。

### `.env` 阈值清单(带默认值)
```
# 探测频率
PROBE_ALIVE_INTERVAL_SEC=300          # 存活探测 5 分钟
PROBE_QUALITY_INTERVAL_SEC=1800       # 质量探测 30 分钟

# 状态机阈值(单位:连续探测次数)
PROBE_FAIL_TO_ABNORMAL=3              # online→abnormal
PROBE_RECOVER_FROM_ABNORMAL=2        # abnormal→online
PROBE_FAIL_TO_SUSPECTED=36           # abnormal→suspected_dead (≈3h)
PROBE_RECOVER_FROM_SUSPECTED=3       # suspected→revived
PROBE_FAIL_TO_DEAD=576               # suspected→dead (≈48h)
PROBE_RECOVER_FROM_DEAD=5            # dead→revived
REVIVED_STABLE_HOURS=24              # revived→online 观察期

# 冷启动观察区毕业(与条件)
OBSERVING_MIN_DAYS=7
OBSERVING_MIN_ALIVE_PROBES=1500
OBSERVING_MIN_QUALITY_PROBES=48

# 维护窗上限
MAINTENANCE_MAX_HOURS_PER_WINDOW=4
MAINTENANCE_MAX_WINDOWS_PER_WEEK=2

# 评分归一化
UPTIME_HALFLIFE_DAYS=7                 # 在线率时间衰减半衰期
SPEED_ANCHORS_MS=1500,3000,6000,10000 # 速度映射拐点(毫秒)
SPEED_ANCHORS_SCORE=100,75,50,20      # 拐点对应分数
AUTHENTICITY_WINDOW=20                 # 真实性取最近N次质量探测
REVIEW_BAYESIAN_C=5                    # 评价贝叶斯置信常数(虚拟评价数)

# 安全(绝不进库/日志)
KEY_ENCRYPTION_SECRET=<env-only>
```

---

## 十二、前端强制约定

1. **双主题(light / dark)是贯穿性约束,从第一个组件起生效。**
   - 所有颜色走 **shadcn 语义化 CSS 变量**(`bg-background`/`text-foreground`/`primary`/`muted`/`border`…)。
   - **禁止硬编码颜色**(不写 `bg-white`/`text-black`/`#fff`/具体 hex)。双主题是「按规矩写」的自然结果,不是额外工作;违反则后期返工是地狱。
2. **主题切换 + 持久化用 `next-themes`**:处理 ① localStorage 记忆选择 ② 跟随系统 `prefers-color-scheme` ③ 防 SSR 刷新白屏闪烁(FOUC)。
3. **默认主题 = 跟随系统**,用户手动切换后记住。切换按钮放全局 navbar。
4. 主题切换纯客户端,不影响 SSR HTML 内容 → **不影响 SEO**。
5. **移动端适配(mobile-first)是贯穿性约束,与双主题并列,从第一个组件起生效。**
   - 默认样式写移动端,用 Tailwind 断点(`sm:`/`md:`/`lg:`)向上加桌面增强;**禁止「先桌面后补移动」**(返工成本高)。
   - 验收基线:核心流程在 **375px 宽**下不破版可用;触控目标 ≥ 44px;不以 hover 作为唯一交互。
   - 响应式重点:榜单表格窄屏转卡片/横滚、详情页三屏分区、导航折叠汉堡菜单;适配 `env(safe-area-inset-*)`,杜绝横向溢出。

---

## 十三、待打磨清单(设计 TODO,尚未细化)

以下点已识别但未深入设计,实现前需逐个打磨:

1. **详情页字段细化** —— 历史在线率曲线的存储粒度(原始 probe vs 降采样聚合)、模型清单展示方式、各字段的 response 形态。
2. **API 接口出入参** —— 将第四节路由细化为具体 request/response schema(Pydantic models)。
3. **中转集市对接流程状态机** —— `pending→connected→confirmed` 各步谁能操作、超时/拒绝/取消怎么处理、双方确认的时序。
4. **充值验证具体实现** —— 如何用用户 key 调 new-api/sub2api 额度/用量接口判断"有消费";不同版本接口路径不一,需做适配层(**实际适配难点**)。
5. **探测 worker 的并发与限流细节** —— httpx 并发度、单站超时、对上游的礼貌限速、质量探测预算扣减的原子性。
6. **probe_results 膨胀治理** —— 分区策略、降采样/归档周期(时序数据长期增长)。
