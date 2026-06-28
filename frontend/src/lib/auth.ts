/**
 * 登录态底层工具：token / 用户信息的 localStorage 读写（纯函数，无 React）。
 *
 * 状态管理见 components/auth-provider.tsx（Context + useAuth）。
 * 骨架阶段用 localStorage（最简单）；后续若要防 XSS 可换 httpOnly cookie。
 */

import type { TokenResponse, UserPublic } from "@/lib/api";

const TOKEN_KEY = "routerhub_token";
const USER_KEY = "routerhub_user";

/** 读取本地令牌（仅客户端）。 */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

/** 保存登录结果到 localStorage。 */
export function saveSession(data: TokenResponse) {
  window.localStorage.setItem(TOKEN_KEY, data.access_token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(data.user));
}

/** 清除本地登录态。 */
export function clearSession() {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

/** 读取缓存的用户信息（不校验令牌有效性）。 */
export function readCachedUser(): UserPublic | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UserPublic;
  } catch {
    return null;
  }
}
