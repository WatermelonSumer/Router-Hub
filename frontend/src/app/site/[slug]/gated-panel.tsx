"use client";

/**
 * 详情页「决策区 + 实测延迟」：硬信息锁登录。
 *
 * 游客（无 token）→ 渲染注册转化钩子（不请求后端）。
 * 登录用户 → 拉 /sites/{slug}/private 渲染硬信息（价格/起充/限速/TTFB）。
 *
 * 红线：硬信息由后端 gated 接口返回，绝不含 key/base_url。
 */

import * as React from "react";
import Link from "next/link";
import { Gauge, Loader2, Lock } from "lucide-react";

import { ApiError, siteApi, type SiteGatedView } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { useAuth } from "@/components/auth-provider";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-border/60 py-2.5 last:border-0">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium tabular-nums">{value}</dd>
    </div>
  );
}

// 缺值统一显示「未提供」，不显示空白或 0
function orDash(v: string | number | null | undefined, suffix = ""): string {
  if (v === null || v === undefined || v === "") return "未提供";
  return `${v}${suffix}`;
}

export function GatedPanel({ slug }: { slug: string }) {
  const { user, loading: authLoading } = useAuth();
  const [data, setData] = React.useState<SiteGatedView | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (authLoading || !user) return;
    const token = getToken();
    if (!token) return;

    let cancelled = false;

    async function run() {
      setLoading(true);
      setError(null);
      try {
        const d = await siteApi.privateDetail(slug, token!);
        if (!cancelled) setData(d);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "加载失败");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [slug, user, authLoading]);

  // 等待登录态确定，避免闪烁
  if (authLoading) {
    return (
      <div className="flex items-center justify-center rounded-xl border border-border bg-card py-10 text-muted-foreground">
        <Loader2 className="size-5 animate-spin" />
      </div>
    );
  }

  // 游客：注册转化钩子（不请求后端）
  if (!user) {
    return (
      <div className="flex flex-col items-center rounded-xl border border-dashed border-border bg-card px-6 py-10 text-center">
        <div className="flex size-11 items-center justify-center rounded-full bg-primary/10">
          <Lock className="size-5 text-primary" />
        </div>
        <h3 className="mt-3 text-base font-semibold">登录后查看决策信息</h3>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          实测延迟、起充门槛、支付方式与限速属于硬信息，登录即可查看。
        </p>
        <Link
          href="/login"
          className="mt-4 inline-flex items-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          登录 / 注册
        </Link>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center rounded-xl border border-border bg-card py-10 text-muted-foreground">
        <Loader2 className="size-5 animate-spin" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
        {error ?? "暂无硬信息"}
      </div>
    );
  }

  const ttfb =
    data.latency_samples > 0 && data.ttfb_p50_ms !== null
      ? `${data.ttfb_p50_ms} ms（P90 ${orDash(data.ttfb_p90_ms, " ms")}）`
      : "暂无实测";

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-2 flex items-center gap-2 text-sm font-medium text-muted-foreground">
        <Gauge className="size-4" />
        实测延迟与决策信息
      </div>
      <dl>
        <Row label="实测延迟 TTFB" value={ttfb} />
        <Row label="起充门槛" value={data.min_topup ? `¥${data.min_topup}` : "未提供"} />
        <Row label="支付方式" value={orDash(data.pay_methods)} />
        <Row label="限速 RPM" value={orDash(data.rpm_limit)} />
      </dl>
    </div>
  );
}
