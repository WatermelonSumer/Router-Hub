/**
 * 登录态管理：token 存 localStorage，提供 useAuth hook。
 *
 * 骨架阶段用 localStorage（最简单）；后续若要防 XSS 可换 httpOnly cookie。
 */

"use client";

import * as React from "react";

import { authApi, type TokenResponse, type UserPublic } from "@/lib/api";

const TOKEN_KEY = "routerhub_token";
const USER_KEY = "routerhub_user";

/** 读取本地令牌（仅客户端）。 */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

/** 保存登录结果到 localStorage。 */
function saveSession(data: TokenResponse) {
  window.localStorage.setItem(TOKEN_KEY, data.access_token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(data.user));
}

/** 清除本地登录态。 */
function clearSession() {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

/** 读取缓存的用户信息（不校验令牌有效性）。 */
function readCachedUser(): UserPublic | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UserPublic;
  } catch {
    return null;
  }
}

type AuthState = {
  user: UserPublic | null;
  loading: boolean;
  /** 保存登录结果（登录/注册成功后调用）。 */
  setSession: (data: TokenResponse) => void;
  /** 退出登录。 */
  logout: () => void;
};

/** 登录态 hook：挂载后用本地令牌向后端核对当前用户。 */
export function useAuth(): AuthState {
  const [user, setUser] = React.useState<UserPublic | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;

    async function init() {
      const token = getToken();
      if (!token) {
        if (!cancelled) setLoading(false);
        return;
      }
      // 先用缓存的用户占位
      if (!cancelled) setUser(readCachedUser());
      // 再用令牌向后端核对（令牌过期/无效则清除）
      try {
        const u = await authApi.me(token);
        if (!cancelled) setUser(u);
      } catch {
        clearSession();
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void init();
    return () => {
      cancelled = true;
    };
  }, []);

  const setSession = React.useCallback((data: TokenResponse) => {
    saveSession(data);
    setUser(data.user);
  }, []);

  const logout = React.useCallback(() => {
    clearSession();
    setUser(null);
  }, []);

  return { user, loading, setSession, logout };
}
