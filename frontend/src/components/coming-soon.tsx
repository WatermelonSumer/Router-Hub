/**
 * 通用「建设中」占位页：用于尚未实现的路由，避免导航点击 404。
 */

import { Construction } from "lucide-react";

import { SiteShell } from "@/components/site-shell";

export function ComingSoon({
  title,
  desc,
}: {
  title: string;
  desc?: string;
}) {
  return (
    <SiteShell>
      <div className="mx-auto flex max-w-md flex-col items-center px-4 py-32 text-center">
        <div className="mb-5 flex size-14 items-center justify-center rounded-2xl border border-border bg-muted/50 text-muted-foreground">
          <Construction className="size-7" />
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {desc ?? "该页面正在建设中，敬请期待。"}
        </p>
      </div>
    </SiteShell>
  );
}
