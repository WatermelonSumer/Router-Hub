"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import {
  Activity,
  KeyRound,
  Loader2,
  Mail,
  MessageCircle,
  Server,
  ShieldCheck,
  Skull,
  Store,
  User,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { ApiError, authApi, type Role } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ThemeToggle } from "@/components/theme-toggle";

type Mode = "login" | "register";

export default function LoginPage() {
  const router = useRouter();
  const { setSession } = useAuth();

  const [mode, setMode] = React.useState<Mode>("login");
  const [role, setRole] = React.useState<Role>("user");

  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [wechat, setWechat] = React.useState("");
  const [qq, setQq] = React.useState("");

  const [error, setError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  const isRegister = mode === "register";
  const ownerRegister = isRegister && role === "owner";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    // 前端基础校验，减少无谓请求
    if (!email.trim() || !password) {
      setError("请填写邮箱和密码");
      return;
    }
    if (isRegister && password.length < 8) {
      setError("密码至少 8 位");
      return;
    }
    if (ownerRegister && (!wechat.trim() || !qq.trim())) {
      setError("站长注册必须填写微信和 QQ");
      return;
    }

    setSubmitting(true);
    try {
      const data = isRegister
        ? await authApi.register({
            email: email.trim(),
            password,
            role,
            wechat: ownerRegister ? wechat.trim() : undefined,
            qq: ownerRegister ? qq.trim() : undefined,
          })
        : await authApi.login({ email: email.trim(), password });

      setSession(data);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "操作失败，请重试");
    } finally {
      setSubmitting(false);
    }
  }

  function switchMode(next: Mode) {
    setMode(next);
    setError(null);
  }

  return (
    <main className="relative flex min-h-screen w-full items-center justify-center overflow-hidden bg-background px-4 py-10">
      {/* 赛博数据感背景：网格 + 辉光 + 浮动粒子 + 扫描线 + 站点名滚动 */}
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
          <div className="mb-6 flex flex-col items-center text-center">
            <div className="mb-4 flex size-12 items-center justify-center rounded-xl border border-white/10 bg-primary/10 backdrop-blur">
              <ShieldCheck className="size-6 text-primary" />
            </div>
            <h1 className="text-2xl font-semibold tracking-tight">
              {isRegister ? "注册 Router-Hub" : "登录 Router-Hub"}
            </h1>
            <p className="mt-1.5 text-sm text-muted-foreground">
              客观探测征信的 AI 中转站排行榜
            </p>
          </div>

          {/* 实时统计条（mock 数据，后端接入后替换） */}
          <StatBar />

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
          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
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
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={submitting}
                />
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">密码</Label>
                {!isRegister && (
                  <Link
                    href="#"
                    className="text-xs text-muted-foreground transition-colors hover:text-foreground"
                  >
                    忘记密码？
                  </Link>
                )}
              </div>
              <div className="relative">
                <KeyRound className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  placeholder={isRegister ? "至少 8 位" : "••••••••"}
                  autoComplete={isRegister ? "new-password" : "current-password"}
                  className="pl-9"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={submitting}
                />
              </div>
            </div>

            {/* 站长注册：必填微信 + QQ */}
            {ownerRegister && (
              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-2">
                  <Label htmlFor="wechat">微信</Label>
                  <div className="relative">
                    <MessageCircle className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="wechat"
                      placeholder="微信号"
                      className="pl-9"
                      value={wechat}
                      onChange={(e) => setWechat(e.target.value)}
                      disabled={submitting}
                    />
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="qq">QQ</Label>
                  <Input
                    id="qq"
                    placeholder="QQ 号"
                    value={qq}
                    onChange={(e) => setQq(e.target.value)}
                    disabled={submitting}
                  />
                </div>
              </div>
            )}

            {/* 错误提示 */}
            {error && (
              <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                {error}
              </p>
            )}

            <Button
              type="submit"
              size="lg"
              className="mt-2 w-full"
              disabled={submitting}
            >
              {submitting && <Loader2 className="size-4 animate-spin" />}
              {isRegister
                ? role === "user"
                  ? "注册用户账号"
                  : "注册站长账号"
                : role === "user"
                  ? "以用户身份登录"
                  : "以站长身份登录"}
            </Button>
          </form>

          {/* 分隔 */}
          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted-foreground">
              {isRegister ? "已有账号" : "还没有账号"}
            </span>
            <div className="h-px flex-1 bg-border" />
          </div>

          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={() => switchMode(isRegister ? "login" : "register")}
            disabled={submitting}
          >
            {isRegister ? "返回登录" : "注册新账号"}
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

/** 实时统计条：探测中 / 已收录 / 坟场阵亡，数字滚动入场。 */
function StatBar() {
  return (
    <div className="mb-6 grid grid-cols-3 gap-2 rounded-lg border border-border bg-muted/30 px-2 py-3">
      <Stat
        icon={<Activity className="size-3.5" />}
        to={142}
        label="实时探测"
        accent
      />
      <Stat
        icon={<Server className="size-3.5" />}
        to={8600}
        label="已收录"
      />
      <Stat icon={<Skull className="size-3.5" />} to={37} label="坟场阵亡" />
    </div>
  );
}

function Stat({
  icon,
  to,
  label,
  accent,
}: {
  icon: React.ReactNode;
  to: number;
  label: string;
  accent?: boolean;
}) {
  return (
    <div className="flex flex-col items-center gap-0.5 text-center">
      <div
        className={cn(
          "flex items-center gap-1 tabular-nums",
          accent ? "text-primary" : "text-foreground",
        )}
      >
        {accent && (
          <motion.span
            aria-hidden
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
            className="inline-flex"
          >
            {icon}
          </motion.span>
        )}
        {!accent && <span className="text-muted-foreground">{icon}</span>}
        <span className="text-base font-semibold leading-none">
          <CountUp to={to} />
        </span>
      </div>
      <span className="text-[10px] leading-none text-muted-foreground">
        {label}
      </span>
    </div>
  );
}

/** 数字滚动：SSR 渲染目标值（无 hydration mismatch），挂载后从 0 缓动到目标。 */
function CountUp({ to }: { to: number }) {
  const [n, setN] = React.useState(to);

  React.useEffect(() => {
    let raf = 0;
    let startTs = 0;
    const duration = 1100;
    const easeOut = (p: number) => 1 - Math.pow(1 - p, 3);

    const tick = (ts: number) => {
      if (!startTs) startTs = ts;
      const p = Math.min((ts - startTs) / duration, 1);
      setN(Math.round(easeOut(p) * to));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [to]);

  return <>{formatCompact(n)}</>;
}

/** ≥1000 显示为 x.xk。 */
function formatCompact(n: number): string {
  if (n >= 1000) {
    const k = n / 1000;
    return `${k % 1 === 0 ? k.toFixed(0) : k.toFixed(1)}k`;
  }
  return String(n);
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
        active
          ? "text-foreground"
          : "text-muted-foreground hover:text-foreground",
      )}
    >
      {icon}
      {label}
    </button>
  );
}

/* 浮动粒子的确定性坐标（写死，避免 Math.random 导致 SSR/CSR hydration 不一致）。 */
const PARTICLES = [
  { left: "8%", top: "18%", size: 3, delay: 0, dur: 7 },
  { left: "22%", top: "62%", size: 2, delay: 1.2, dur: 9 },
  { left: "35%", top: "30%", size: 4, delay: 0.5, dur: 8 },
  { left: "48%", top: "78%", size: 2, delay: 2, dur: 10 },
  { left: "61%", top: "22%", size: 3, delay: 0.8, dur: 7.5 },
  { left: "73%", top: "55%", size: 2, delay: 1.6, dur: 9.5 },
  { left: "85%", top: "35%", size: 4, delay: 0.3, dur: 8.5 },
  { left: "92%", top: "70%", size: 2, delay: 2.4, dur: 11 },
  { left: "15%", top: "85%", size: 3, delay: 1, dur: 8 },
  { left: "55%", top: "12%", size: 2, delay: 1.9, dur: 9 },
  { left: "68%", top: "88%", size: 3, delay: 0.6, dur: 10.5 },
  { left: "40%", top: "50%", size: 2, delay: 2.2, dur: 7 },
];

/* 站点名极淡滚动（mock，纯氛围）。 */
const SITE_NAMES = [
  "claudehub",
  "gptpro",
  "geminix",
  "openrelay",
  "fastapi-gw",
  "neon-api",
  "sub2api",
  "modelhub",
  "tokenflow",
  "relaystation",
];

/** 赛博数据感背景：网格 + 双色辉光 + 浮动粒子 + 扫描线 + 站点名滚动。纯展示，aria-hidden。 */
function CyberBackground() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 z-0">
      {/* 网格 */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,var(--border)_1px,transparent_1px),linear-gradient(to_bottom,var(--border)_1px,transparent_1px)] bg-[size:44px_44px] opacity-40 [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_75%)]" />

      {/* 双色辉光球 */}
      <motion.div
        initial={{ opacity: 0.5 }}
        animate={{ opacity: [0.5, 0.8, 0.5] }}
        transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
        className="absolute -left-24 top-0 size-[28rem] rounded-full bg-primary/20 blur-[120px]"
      />
      <motion.div
        initial={{ opacity: 0.4 }}
        animate={{ opacity: [0.4, 0.7, 0.4] }}
        transition={{
          duration: 9,
          repeat: Infinity,
          ease: "easeInOut",
          delay: 1,
        }}
        className="absolute -right-24 bottom-0 size-[26rem] rounded-full bg-sky-500/20 blur-[120px]"
      />

      {/* 浮动粒子 */}
      {PARTICLES.map((p, i) => (
        <motion.span
          key={i}
          className="absolute rounded-full bg-primary/50"
          style={{
            left: p.left,
            top: p.top,
            width: p.size,
            height: p.size,
          }}
          animate={{ y: [0, -14, 0], opacity: [0.2, 0.7, 0.2] }}
          transition={{
            duration: p.dur,
            repeat: Infinity,
            ease: "easeInOut",
            delay: p.delay,
          }}
        />
      ))}

      {/* 扫描线：自上而下循环 */}
      <motion.div
        className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent"
        animate={{ top: ["-5%", "105%"] }}
        transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
      />

      {/* 底部站点名极淡横向滚动 */}
      <div className="absolute inset-x-0 bottom-6 overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_15%,black_85%,transparent)]">
        <motion.div
          className="flex w-max gap-8 whitespace-nowrap font-mono text-xs text-muted-foreground/25"
          animate={{ x: ["0%", "-50%"] }}
          transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
        >
          {[...SITE_NAMES, ...SITE_NAMES].map((name, i) => (
            <span key={i} className="flex items-center gap-2">
              <span className="size-1 rounded-full bg-primary/40" />
              {name}
            </span>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
