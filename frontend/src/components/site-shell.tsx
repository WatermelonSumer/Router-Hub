/**
 * 站点外壳：顶栏 + 内容区 + 页脚。
 * 公共页面（首页、榜单、坟场、集市等）用它包裹；登录页等沉浸式页面不用。
 */

import { Navbar } from "@/components/navbar";

export function SiteShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1">{children}</main>
      <footer className="border-t border-border py-6">
        <div className="mx-auto max-w-6xl px-4 text-center text-xs text-muted-foreground">
          Router-Hub · 客观探测征信的 AI 中转站排行榜 · 骨架阶段
        </div>
      </footer>
    </div>
  );
}
