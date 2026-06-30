/**
 * 后端 API 封装：统一 baseURL、JSON 序列化、Bearer 令牌、错误处理。
 *
 * baseURL 来自 NEXT_PUBLIC_API_BASE（见 .env.local）。
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ?? "http://localhost:8000";

/** 后端返回的业务错误（带 HTTP 状态码与可读信息）。 */
export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  token?: string | null;
  // 服务端组件（RSC）用：Next.js ISR 重验证秒数。仅服务端 fetch 生效。
  revalidate?: number;
};

/** 通用请求：自动拼 baseURL、带 JSON 头、附 Bearer 令牌、解析错误。 */
async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, token, revalidate } = options;

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      ...(revalidate !== undefined ? { next: { revalidate } } : {}),
    });
  } catch {
    // 网络层失败（后端没起、断网、CORS 预检失败等）
    throw new ApiError(0, "无法连接服务器，请稍后再试");
  }

  if (resp.status === 204) return undefined as T;

  let data: unknown = null;
  try {
    data = await resp.json();
  } catch {
    data = null;
  }

  if (!resp.ok) {
    const detail = extractDetail(data) ?? `请求失败（${resp.status}）`;
    throw new ApiError(resp.status, detail);
  }

  return data as T;
}

/** 从 FastAPI 错误响应中提取可读信息（兼容 detail 为字符串或校验错误数组）。 */
function extractDetail(data: unknown): string | null {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    // 422 校验错误：detail 是数组，取第一条 msg
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      if (first && typeof first === "object" && "msg" in first) {
        return String((first as { msg: unknown }).msg);
      }
    }
  }
  return null;
}

// ===== 类型（与后端 schemas/auth.py 对应） =====

// 系统内全部角色；admin 只能由后端脚本创建
export type Role = "user" | "owner" | "admin";
// 注册时允许的角色（不含 admin）
export type RegisterRole = "user" | "owner";

export type UserPublic = {
  user_id: string;
  email: string;
  role: Role;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user: UserPublic;
};

export type RegisterPayload = {
  email: string;
  password: string;
  role: RegisterRole;
  wechat?: string;
  qq?: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};

// ===== auth 接口 =====

export const authApi = {
  register: (payload: RegisterPayload) =>
    request<TokenResponse>("/auth/register", { method: "POST", body: payload }),

  login: (payload: LoginPayload) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: payload }),

  me: (token: string) => request<UserPublic>("/auth/me", { token }),
};

// ===== 中转站（与后端 schemas/site.py 对应） =====

export type SiteCreatePayload = {
  name: string;
  base_url: string;
  api_key: string;
  slug?: string;
  site_url?: string;
  declared_models?: string[];
  min_topup?: string;
  pay_methods?: string;
  rpm_limit?: number;
};

export type SiteUpdatePayload = {
  name?: string;
  site_url?: string | null;
  base_url?: string;
  api_key?: string;
  declared_models?: string[] | null;
  min_topup?: string | null;
  pay_methods?: string | null;
  rpm_limit?: number | null;
  probe_budget_daily?: number;
};

export type SiteOwnerView = {
  site_id: string;
  name: string;
  slug: string;
  base_url: string;
  site_url: string | null;
  key_hint: string;
  status: string;
  review_note: string | null;
  declared_models: string[] | null;
  min_topup: string | null;
  pay_methods: string | null;
  rpm_limit: number | null;
  probe_budget_daily: number;
};

// 管理员审核视角：站长字段 + 站长联系方式 + 上架时间（仍不含 key）
export type SiteAdminView = SiteOwnerView & {
  owner_id: string;
  owner_email: string | null;
  owner_wechat: string | null;
  owner_qq: string | null;
  created_at: string;
};

// 站点详情（与后端 schemas/site_detail.py 对应）

// 在线率曲线一个点；uptime 为 null 表示当天无样本（前端断点，不画成 0）
export type UptimePoint = {
  date: string; // YYYY-MM-DD
  uptime: number | null;
};

// 该站在某分榜的综合分/名次摘要
export type SiteScoreBrief = {
  leaderboard: string;
  composite_score: number | null;
  rank: number | null;
};

// 游客可见详情（SSR）：绝不含 base_url / key / 硬信息
export type SitePublicView = {
  site_id: string;
  name: string;
  slug: string;
  site_url: string | null;
  status: string;
  declared_models: string[] | null;
  first_seen_at: string | null;
  listed_at: string;
  last_probe_at: string | null;
  status_changed_at: string | null;
  verified: boolean;
  uptime_30d: number | null;
  uptime_history: UptimePoint[];
  scores: SiteScoreBrief[];
};

// 登录可见硬信息：决策区 + 实测延迟（仍不含 key / base_url）
export type SiteGatedView = {
  site_id: string;
  slug: string;
  min_topup: string | null;
  pay_methods: string | null;
  rpm_limit: number | null;
  ttfb_p50_ms: number | null;
  ttfb_p90_ms: number | null;
  latency_samples: number;
};

export type SiteReviewView = {
  review_id: string;
  site_id: string;
  author_id: string;
  review_type: "user_topup" | "owner_deal" | string;
  rating: number;
  content: string | null;
  verified: boolean;
  created_at: string;
};

export type SiteReviewsResponse = {
  site_id: string;
  reviews: SiteReviewView[];
};

export const siteApi = {
  create: (payload: SiteCreatePayload, token: string) =>
    request<SiteOwnerView>("/sites", { method: "POST", body: payload, token }),

  mine: (token: string) => request<SiteOwnerView[]>("/sites/mine", { token }),

  update: (siteId: string, payload: SiteUpdatePayload, token: string) =>
    request<SiteOwnerView>(`/sites/${siteId}`, { method: "PATCH", body: payload, token }),

  remove: (siteId: string, token: string) =>
    request<void>(`/sites/${siteId}`, { method: "DELETE", token }),

  /**
   * 站点详情（游客可见部分）。吃 SEO，故走 SSR + ISR（默认 60s 重验证）。
   * 404（不存在/未公开）抛 ApiError(404)，由页面转 notFound。
   */
  publicDetail: (slug: string) =>
    request<SitePublicView>(`/sites/${encodeURIComponent(slug)}`, {
      revalidate: 60,
    }),

  /**
   * 站点硬信息（登录可见）：决策区 + 实测延迟。
   * 未登录后端抛 401，前端据此渲染注册转化钩子。
   */
  privateDetail: (slug: string, token: string) =>
    request<SiteGatedView>(`/sites/${encodeURIComponent(slug)}/private`, { token }),

  /** 站点公开评价列表：仅展示已验证评价。 */
  reviews: (slug: string) =>
    request<SiteReviewsResponse>(`/sites/${encodeURIComponent(slug)}/reviews`, {
      revalidate: 60,
    }),
};

// ===== 管理员审核（与后端 routes/admin.py 对应） =====

export const adminApi = {
  pending: (token: string) =>
    request<SiteAdminView[]>("/admin/sites/pending", { token }),

  /** 按状态列站点（管理员总览观察区/在线/坟场等）。 */
  byStatus: (status: string, token: string) =>
    request<SiteAdminView[]>(`/admin/sites?status=${encodeURIComponent(status)}`, { token }),

  approve: (siteId: string, token: string) =>
    request<SiteOwnerView>(`/admin/sites/${siteId}/approve`, {
      method: "POST",
      token,
    }),

  reject: (siteId: string, note: string, token: string) =>
    request<SiteOwnerView>(`/admin/sites/${siteId}/reject`, {
      method: "POST",
      body: { note },
      token,
    }),
};

// ===== 排行榜（与后端 schemas/rank.py 对应） =====

export type RankEntry = {
  site_id: string;
  name: string;
  slug: string;
  site_url: string | null;
  status: string;
  rank: number | null;
  composite_score: number | null;
  uptime_score: number | null;
  speed_score: number | null;
  authenticity_score: number | null;
  review_score: number | null;
  declared_models: string[] | null;
};

export type RankResponse = {
  leaderboard: string;
  sort: string;
  main: RankEntry[];
  observing: RankEntry[];
};

export type RankFamily = "claude" | "gpt" | "gemini";
export type RankSort = "composite" | "speed" | "uptime";

export const rankApi = {
  /**
   * 服务端组件用：拉某分榜。榜单吃 SEO，故走 SSR + ISR（默认 60s 重验证）。
   * 失败时抛 ApiError，由页面兜底成空态。
   */
  list: (family: RankFamily, sort: RankSort = "composite") =>
    request<RankResponse>(`/rank?leaderboard=${family}&sort=${sort}`, {
      revalidate: 60,
    }),
};

// ===== 坟场（与后端 schemas/graveyard.py 对应） =====

export type GraveyardEntry = {
  site_id: string;
  name: string;
  slug: string;
  site_url: string | null;
  status: string; // suspected_dead | dead
  declared_models: string[] | null;
  first_seen_at: string | null;
  last_probe_at: string | null;
  status_changed_at: string | null;
};

export type GraveyardResponse = {
  suspected: GraveyardEntry[];
  dead: GraveyardEntry[];
};

export const graveyardApi = {
  /**
   * 服务端组件用：拉坟场。吃 SEO，故走 SSR + ISR（默认 60s 重验证）。
   * 失败时抛 ApiError，由页面兜底成空态。
   */
  list: () => request<GraveyardResponse>("/graveyard", { revalidate: 60 }),
};

// ===== 中转集市（与后端 schemas/marketplace.py 对应） =====
// 红线：B 端登录墙后，刻意不 SEO；联系方式仅对接 confirmed 后交换。

export type PostType = "supply" | "demand";
export type Direction = "upstream" | "downstream";
export type Settlement = "daily" | "weekly" | "prepaid";

// 发帖站长探测履历名片（沿用 C 端征信，不含联系方式）
export type OwnerReputation = {
  best_composite: number | null;
  max_alive_days: number | null;
  site_count: number;
  graveyard_count: number;
};

export type PostView = {
  post_id: string;
  author_id: string;
  site_id: string | null;
  site_name: string | null;
  site_slug: string | null;
  post_type: string;
  direction: string;
  model_family: string;
  rate: string | null;
  rpm: number | null;
  volume: string | null;
  settlement: string | null;
  note: string | null;
  status: string; // open | closed
  created_at: string;
  is_mine: boolean;
  author_reputation: OwnerReputation;
};

// 对接 confirmed 后交换的名片（仅此处含联系方式）
export type ContactCard = {
  user_id: string;
  email: string;
  wechat: string | null;
  qq: string | null;
};

export type ResponseView = {
  response_id: string;
  post_id: string;
  responder_id: string;
  status: string; // pending | connected | confirmed
  created_at: string;
  contact: ContactCard | null; // confirmed 才给
};

export type PostCreatePayload = {
  post_type: PostType;
  direction: Direction;
  model_family: RankFamily;
  rate?: string;
  rpm?: number;
  volume?: string;
  settlement?: Settlement;
  note?: string;
};

export type PostFilter = {
  post_type?: string;
  direction?: string;
  model_family?: string;
  max_rate?: string;
};

export const marketApi = {
  create: (payload: PostCreatePayload, token: string) =>
    request<PostView>("/market/posts", { method: "POST", body: payload, token }),

  list: (filter: PostFilter, token: string) => {
    const qs = new URLSearchParams();
    if (filter.post_type) qs.set("post_type", filter.post_type);
    if (filter.direction) qs.set("direction", filter.direction);
    if (filter.model_family) qs.set("model_family", filter.model_family);
    if (filter.max_rate) qs.set("max_rate", filter.max_rate);
    const q = qs.toString();
    return request<PostView[]>(`/market/posts${q ? `?${q}` : ""}`, { token });
  },

  close: (postId: string, token: string) =>
    request<PostView>(`/market/posts/${postId}/close`, { method: "POST", token }),

  respond: (postId: string, token: string) =>
    request<ResponseView>(`/market/posts/${postId}/respond`, { method: "POST", token }),

  confirm: (responseId: string, token: string) =>
    request<ResponseView>(`/market/responses/${responseId}/confirm`, {
      method: "POST",
      token,
    }),

  myResponses: (token: string) =>
    request<ResponseView[]>("/market/responses/mine", { token }),

  incomingResponses: (token: string) =>
    request<ResponseView[]>("/market/responses/incoming", { token }),

  /** B 端互评：对 confirmed 对接的帖子绑定站点评价（每人每站一次）。 */
  review: (responseId: string, payload: ReviewCreatePayload, token: string) =>
    request<ReviewView>(`/market/responses/${responseId}/review`, {
      method: "POST",
      body: payload,
      token,
    }),
};

// ===== 评价（与后端 schemas/review.py 对应） =====

export type ReviewCreatePayload = {
  rating: number; // 1-5
  content?: string;
};

export type ReviewView = {
  review_id: string;
  site_id: string;
  author_id: string;
  review_type: string; // user_topup | owner_deal
  rating: number;
  content: string | null;
  verified: boolean;
  created_at: string;
};
