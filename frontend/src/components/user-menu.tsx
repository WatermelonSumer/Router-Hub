"use client";

/**
 * 顶栏右侧用户区：
 * - 未登录：显示「登录 / 注册」按钮
 * - 已登录：头像首字母 + 下拉菜单（邮箱、角色、角色专属入口、登出）
 *
 * 下拉用自写轻量 popover（点外部/Esc 关闭），不引入额外依赖。
 */

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LayoutDashboard, LogOut, ShieldCheck, Store } from "lucide-react";

import { cn } from "@/lib/utils";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";

const ROLE_LABEL: Record<string, string> = {
  user: "用户",
  owner: "站长",
  admin: "管理员",
};

export function UserMenu() {
  const { user, loading } = useAuth();

  // 首次核对登录态时占位，避免「未登录→已登录」闪烁
  if (loading) {
    return <div className="size-9 animate-pulse rounded-full bg-muted" />;
  }

  if (!user) {
    return (
      <Button asChild size="sm">
        <Link href="/login">登录 / 注册</Link>
      </Button>
    );
  }

  return <LoggedInMenu />;
}

function LoggedInMenu() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);

  // 点外部 / Esc 关闭
  React.useEffect(() => {
    if (!open) return;
    function onPointerDown(e: PointerEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!user) return null;

  const initial = user.email.charAt(0).toUpperCase();
  const roleLabel = ROLE_LABEL[user.role] ?? user.role;

  function handleLogout() {
    logout();
    setOpen(false);
    router.push("/");
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex size-9 items-center justify-center rounded-full border border-border bg-primary/10 text-sm font-semibold text-primary transition-colors hover:bg-primary/20"
      >
        {initial}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-11 z-50 w-60 overflow-hidden rounded-lg border border-border bg-popover p-1 text-popover-foreground shadow-lg"
        >
          {/* 账号信息 */}
          <div className="border-b border-border px-3 py-2.5">
            <p className="truncate text-sm font-medium">{user.email}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{roleLabel}</p>
          </div>

          {/* 角色专属入口 */}
          <div className="py-1">
            {user.role === "owner" && (
              <MenuLink
                href="/owner"
                icon={<Store className="size-4" />}
                label="站长控制台"
                onNavigate={() => setOpen(false)}
              />
            )}
            {user.role === "admin" && (
              <MenuLink
                href="/admin"
                icon={<ShieldCheck className="size-4" />}
                label="管理后台"
                onNavigate={() => setOpen(false)}
              />
            )}
            {user.role === "user" && (
              <MenuLink
                href="/me"
                icon={<LayoutDashboard className="size-4" />}
                label="我的"
                onNavigate={() => setOpen(false)}
              />
            )}
          </div>

          {/* 登出 */}
          <div className="border-t border-border pt-1">
            <button
              type="button"
              role="menuitem"
              onClick={handleLogout}
              className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-destructive transition-colors hover:bg-destructive/10"
            >
              <LogOut className="size-4" />
              退出登录
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function MenuLink({
  href,
  icon,
  label,
  onNavigate,
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
  onNavigate: () => void;
}) {
  return (
    <Link
      href={href}
      role="menuitem"
      onClick={onNavigate}
      className={cn(
        "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors hover:bg-accent hover:text-accent-foreground",
      )}
    >
      {icon}
      {label}
    </Link>
  );
}
