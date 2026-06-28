import Link from "next/link";
import {
  ArrowRight,
  Bot,
  Brain,
  ShieldCheck,
  Skull,
  Sparkles,
  Store,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { SiteShell } from "@/components/site-shell";

// 三个分榜入口（数据接入前用静态占位）
const BOARDS = [
  {
    href: "/leaderboard/claude",
    name: "Claude 榜",
    desc: "Claude 系模型中转站实测排名",
    icon: Sparkles,
  },
  {
    href: "/leaderboard/gpt",
    name: "GPT 榜",
    desc: "GPT 系模型中转站实测排名",
    icon: Bot,
  },
  {
    href: "/leaderboard/gemini",
    name: "Gemini 榜",
    desc: "Gemini 系模型中转站实测排名",
    icon: Brain,
  },
];

// 卖点（落地页用静态文案）
const FEATURES = [
  {
    icon: ShieldCheck,
    title: "客观探测征信",
    desc: "平台真实付费探测，在线率、延迟、真实性全部实测，不靠站长自报。",
  },
  {
    icon: Skull,
    title: "中转站坟场",
    desc: "跑路预警与阵亡名单，连续探测失败的站点公开留痕，帮你避雷。",
  },
  {
    icon: Store,
    title: "中转集市",
    desc: "已验证站长之间批发撮合上下游产能，平台只撮合不碰钱。",
  },
];

export default function Home() {
  return (
    <SiteShell>
      {/* Hero */}
      <section className="relative overflow-hidden">
        {/* 背景辉光 */}
        <div
          aria-hidden
          className="pointer-events-none absolute left-1/2 top-0 -z-10 size-[40rem] -translate-x-1/2 rounded-full bg-primary/10 blur-[120px]"
        />
        <div className="mx-auto max-w-6xl px-4 py-20 text-center sm:py-28">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-muted/50 px-3 py-1 text-xs text-muted-foreground">
            <span className="relative flex size-2">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary/60" />
              <span className="relative inline-flex size-2 rounded-full bg-primary" />
            </span>
            平台实时探测中
          </div>

          <h1 className="mx-auto max-w-3xl text-balance text-4xl font-semibold tracking-tight sm:text-6xl">
            找到靠谱的 AI 中转站
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-balance text-base text-muted-foreground sm:text-lg">
            带客观探测征信的 AI 中转站排行榜、避雷坟场与站长批发撮合市场。
            不听一面之词，只看实测数据。
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Button asChild size="lg">
              <Link href="/leaderboard">
                浏览排行榜
                <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/login">登录 / 注册</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* 三个分榜入口 */}
      <section className="mx-auto max-w-6xl px-4 pb-16">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {BOARDS.map((b) => {
            const Icon = b.icon;
            return (
              <Link
                key={b.href}
                href={b.href}
                className="group rounded-xl border border-border bg-card p-6 transition-colors hover:border-primary/50 hover:bg-accent/40"
              >
                <div className="mb-4 flex size-11 items-center justify-center rounded-lg border border-border bg-primary/10 text-primary">
                  <Icon className="size-5" />
                </div>
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold">{b.name}</h3>
                  <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-1 group-hover:text-foreground" />
                </div>
                <p className="mt-1.5 text-sm text-muted-foreground">{b.desc}</p>
              </Link>
            );
          })}
        </div>
      </section>

      {/* 卖点 */}
      <section className="border-t border-border bg-muted/20">
        <div className="mx-auto max-w-6xl px-4 py-16">
          <div className="grid gap-8 sm:grid-cols-3">
            {FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <div key={f.title} className="flex flex-col">
                  <Icon className="mb-3 size-6 text-primary" />
                  <h3 className="font-semibold">{f.title}</h3>
                  <p className="mt-1.5 text-sm text-muted-foreground">
                    {f.desc}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>
    </SiteShell>
  );
}
