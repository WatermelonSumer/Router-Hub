"use client";

/**
 * 全局顶栏：Logo + 导航（榜单/坟场/集市）+ 主题切换 + 用户区。
 * 移动端导航收成汉堡菜单（落实 mobile-first 约定）。
 */

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, ShieldCheck, Store, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { UserMenu } from "@/components/user-menu";
import { useAuth } from "@/components/auth-provider";

const NAV_ITEMS = [
  { href: "/rank", label: "排行榜" },
  { href: "/graveyard", label: "中转站坟场" },
  { href: "/market", label: "中转集市" },
];

// 角色专属控制台入口：放在导航栏最后，按登录角色显示
const ROLE_NAV: Record<string, { href: string; label: string; icon: React.ReactNode }> = {
  owner: { href: "/owner", label: "站长控制台", icon: <Store className="size-4" /> },
  admin: { href: "/admin", label: "管理后台", icon: <ShieldCheck className="size-4" /> },
};

export function Navbar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const [mobileOpen, setMobileOpen] = React.useState(false);

  function isActive(href: string) {
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  function closeMobile() {
    setMobileOpen(false);
  }

  const roleNav = user ? ROLE_NAV[user.role] : undefined;

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-lg">
      <div className="relative mx-auto flex h-14 max-w-6xl items-center gap-4 px-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <ShieldCheck className="size-5 text-primary" />
          <span className="tracking-tight">Router-Hub</span>
        </Link>

        {/* 桌面导航：绝对居中，不受 Logo / 右侧宽度影响 */}
        <nav className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-1 md:flex">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                isActive(item.href)
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {item.label}
            </Link>
          ))}
          {/* 角色控制台入口：导航栏最后 */}
          {roleNav && (
            <Link
              href={roleNav.href}
              className={cn(
                "ml-1 flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                isActive(roleNav.href)
                  ? "bg-primary/10 text-primary"
                  : "text-primary/80 hover:bg-primary/10 hover:text-primary",
              )}
            >
              {roleNav.icon}
              {roleNav.label}
            </Link>
          )}
        </nav>

        {/* 右侧：主题 + 用户 + 移动菜单按钮 */}
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          <div className="hidden md:block">
            <UserMenu />
          </div>
          <Button
            variant="outline"
            size="icon"
            className="md:hidden"
            aria-label="菜单"
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen((v) => !v)}
          >
            {mobileOpen ? <X className="size-4" /> : <Menu className="size-4" />}
          </Button>
        </div>
      </div>

      {/* 移动端展开菜单 */}
      {mobileOpen && (
        <div className="border-t border-border bg-background md:hidden">
          <nav className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-3">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={closeMobile}
                className={cn(
                  "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive(item.href)
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {item.label}
              </Link>
            ))}
            {/* 角色控制台入口：移动端同样置于导航最后 */}
            {roleNav && (
              <Link
                href={roleNav.href}
                onClick={closeMobile}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive(roleNav.href)
                    ? "bg-primary/10 text-primary"
                    : "text-primary/80 hover:bg-primary/10 hover:text-primary",
                )}
              >
                {roleNav.icon}
                {roleNav.label}
              </Link>
            )}
            <div className="mt-2 border-t border-border pt-3">
              <UserMenu />
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
