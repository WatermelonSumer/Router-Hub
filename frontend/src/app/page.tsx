import Link from "next/link";

import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";

export default function Home() {
  return (
    <div className="relative flex flex-1 flex-col items-center justify-center px-4 text-center">
      <div className="absolute right-5 top-5">
        <ThemeToggle />
      </div>

      <h1 className="max-w-2xl text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
        Router-Hub
      </h1>
      <p className="mt-4 max-w-md text-balance text-muted-foreground">
        带客观探测征信的 AI 中转站排行榜、避雷坟场与站长批发撮合市场。
      </p>

      <div className="mt-8 flex gap-3">
        <Button asChild size="lg">
          <Link href="/login">登录 / 注册</Link>
        </Button>
        <Button asChild size="lg" variant="outline">
          <Link href="/login">浏览排行榜</Link>
        </Button>
      </div>

      <p className="mt-12 text-xs text-muted-foreground">
        骨架阶段 · 仅登录页可预览
      </p>
    </div>
  );
}
