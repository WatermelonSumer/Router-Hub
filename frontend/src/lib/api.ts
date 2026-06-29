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
};

// 管理员审核视角：站长字段 + 站长联系方式 + 上架时间（仍不含 key）
export type SiteAdminView = SiteOwnerView & {
  owner_id: string;
  owner_email: string | null;
  owner_wechat: string | null;
  owner_qq: string | null;
  created_at: string;
};

export const siteApi = {
  create: (payload: SiteCreatePayload, token: string) =>
    request<SiteOwnerView>("/sites", { method: "POST", body: payload, token }),

  mine: (token: string) => request<SiteOwnerView[]>("/sites/mine", { token }),
};

// ===== 管理员审核（与后端 routes/admin.py 对应） =====

export const adminApi = {
  pending: (token: string) =>
    request<SiteAdminView[]>("/admin/sites/pending", { token }),

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
