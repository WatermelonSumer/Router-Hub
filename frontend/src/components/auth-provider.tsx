"use client";

/**
 * 全局登录态：用 Context 共享一份，登录/登出后全站（含顶栏）自动更新。
 */

import * as React from "react";

import { authApi, type TokenResponse, type UserPublic } from "@/lib/api";
import {
  clearSession,
  getToken,
  readCachedUser,
  saveSession,
} from "@/lib/auth";

type AuthState = {
  user: UserPublic | null;
  /** 首次用本地令牌向后端核对当前用户期间为 true。 */
  loading: boolean;
  /** 保存登录结果（登录/注册成功后调用）。 */
  setSession: (data: TokenResponse) => void;
  /** 退出登录。 */
  logout: () => void;
};

const AuthContext = React.createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
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
      // 先用缓存的用户占位，再用令牌向后端核对（令牌过期/无效则清除）
      if (!cancelled) setUser(readCachedUser());
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

  const value = React.useMemo<AuthState>(
    () => ({ user, loading, setSession, logout }),
    [user, loading, setSession, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** 读取全局登录态；必须在 AuthProvider 内使用。 */
export function useAuth(): AuthState {
  const ctx = React.useContext(AuthContext);
  if (ctx === null) {
    throw new Error("useAuth 必须在 <AuthProvider> 内使用");
  }
  return ctx;
}
