"use client";

import * as React from "react";
import Link from "next/link";
import { motion } from "motion/react";
import { KeyRound, Mail, ShieldCheck, Store, User } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ThemeToggle } from "@/components/theme-toggle";

type Role = "user" | "owner";

export default function LoginPage() {
  const [role, setRole] = React.useState<Role>("user");

  return (
    <main className="relative flex min-h-screen w-full items-center justify-center overflow-hidden bg-background px-4 py-10">
      {/* 赛博光晕背景：网格 + 双色辉光，纯装饰 */}
      <CyberBackground />

      {/* 右上角主题切换 */}
      <div className="absolute right-5 top-5 z-20">
        <ThemeToggle />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 24, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="relative z-10 w-full max-w-md"
      >
        {/* 玻璃拟态卡片 */}
        <div className="relative rounded-2xl border border-white/10 bg-card/60 p-8 shadow-2xl backdrop-blur-xl">
          {/* 顶部渐变描边光 */}
          <div className="pointer-events-none absolute inset-x-0 -top-px mx-auto h-px w-3/4 bg-gradient-to-r from-transparent via-primary/60 to-transparent" />

          {/* 品牌 */}
          <div className="mb-8 flex flex-col items-center text-center">
            <div className="mb-4 flex size-12 items-center justify-center rounded-xl border border-white/10 bg-primary/10 backdrop-blur">
              <ShieldCheck className="size-6 text-primary" />
            </div>
            <h1 className="text-2xl font-semibold tracking-tight">
              登录 Router-Hub
            </h1>
            <p className="mt-1.5 text-sm text-muted-foreground">
              客观探测征信的 AI 中转站排行榜
            </p>
          </div>

          {/* 角色选择：我是用户 / 我是站长 */}
          <div className="mb-6">
            <div className="relative grid grid-cols-2 gap-1 rounded-lg border border-border bg-muted/50 p-1">
              {/* 选中态滑块 */}
              <motion.div
                layout
                transition={{ type: "spring", stiffness: 400, damping: 32 }}
                className={cn(
                  "absolute inset-y-1 w-[calc(50%-0.25rem)] rounded-md bg-background shadow-sm",
                  role === "user" ? "left-1" : "left-[calc(50%+0rem)]",
                )}
              />
              <RoleTab
                active={role === "user"}
                onClick={() => setRole("user")}
                icon={<User className="size-4" />}
                label="我是用户"
              />
              <RoleTab
                active={role === "owner"}
                onClick={() => setRole("owner")}
                icon={<Store className="size-4" />}
                label="我是站长"
              />
            </div>
            <p className="mt-2 px-1 text-xs text-muted-foreground">
              {role === "user"
                ? "查看排行榜、坟场与站点详情，充值验证后可评价。"
                : "上架中转站、查看探测看板，验证后进入中转集市。"}
            </p>
          </div>

          {/* 表单 */}
          <form
            className="flex flex-col gap-4"
            onSubmit={(e) => e.preventDefault()}
          >
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">邮箱</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  autoComplete="email"
                  className="pl-9"
                />
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">密码</Label>
                <Link
                  href="#"
                  className="text-xs text-muted-foreground transition-colors hover:text-foreground"
                >
                  忘记密码？
                </Link>
              </div>
              <div className="relative">
                <KeyRound className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  autoComplete="current-password"
                  className="pl-9"
                />
              </div>
            </div>

            <Button type="submit" size="lg" className="mt-2 w-full">
              {role === "user" ? "以用户身份登录" : "以站长身份登录"}
            </Button>
          </form>

          {/* 分隔 */}
          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted-foreground">还没有账号</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          <Button asChild variant="outline" className="w-full">
            <Link href="#">注册新账号</Link>
          </Button>
        </div>

        {/* 游客入口 */}
        <p className="mt-6 text-center text-sm text-muted-foreground">
          只想看榜单？
          <Link
            href="/"
            className="ml-1 font-medium text-foreground underline-offset-4 hover:underline"
          >
            以游客身份浏览排行榜
          </Link>
        </p>
      </motion.div>
    </main>
  );
}

/** 角色切换 Tab（透明按钮，选中态由父级滑块体现）。 */
function RoleTab({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "relative z-10 flex items-center justify-center gap-2 rounded-md py-2 text-sm font-medium transition-colors",
        active ? "text-foreground" : "text-muted-foreground hover:text-foreground",
      )}
    >
      {icon}
      {label}
    </button>
  );
}

/** 赛博风装饰背景：网格 + 双色辉光球。纯展示，aria-hidden。 */
function CyberBackground() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 z-0">
      {/* 网格 */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,var(--border)_1px,transparent_1px),linear-gradient(to_bottom,var(--border)_1px,transparent_1px)] bg-[size:44px_44px] opacity-40 [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_75%)]" />
      {/* 辉光球 */}
      <motion.div
        initial={{ opacity: 0.5 }}
        animate={{ opacity: [0.5, 0.8, 0.5] }}
        transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
        className="absolute -left-24 top-0 size-[28rem] rounded-full bg-primary/20 blur-[120px]"
      />
      <motion.div
        initial={{ opacity: 0.4 }}
        animate={{ opacity: [0.4, 0.7, 0.4] }}
        transition={{ duration: 9, repeat: Infinity, ease: "easeInOut", delay: 1 }}
        className="absolute -right-24 bottom-0 size-[26rem] rounded-full bg-sky-500/20 blur-[120px]"
      />
    </div>
  );
}
