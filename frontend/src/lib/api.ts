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
};

/** 通用请求：自动拼 baseURL、带 JSON 头、附 Bearer 令牌、解析错误。 */
async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, token } = options;

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
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

export type Role = "user" | "owner";

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
  role: Role;
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
