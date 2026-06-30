import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Activity, CheckCircle2, Clock, ExternalLink, Star } from "lucide-react";

import { ApiError, siteApi, type SitePublicView, type SiteReviewView } from "@/lib/api";
import { SiteShell } from "@/components/site-shell";
import { GatedPanel } from "./gated-panel";

// 状态 → 风险灯（标签 + 语义色 + 一句客观说明，坟场措辞红线：只陈述探测事实）
const STATUS_META: Record<
  string,
  { label: string; className: string; dot: string; note: string }
> = {
  online: {
    label: "在线",
    className: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
    dot: "bg-emerald-500",
    note: "近期探测持续可用",
  },
  abnormal: {
    label: "异常",
    className: "bg-orange-500/15 text-orange-600 dark:text-orange-400",
    dot: "bg-orange-500",
    note: "近期探测出现连续失败，正在确认",
  },
  observing: {
    label: "观察中",
    className: "bg-sky-500/15 text-sky-600 dark:text-sky-400",
    dot: "bg-sky-500",
    note: "新上架站点，正在积累探测样本",
  },
  revived: {
    label: "复活",
    className: "bg-violet-500/15 text-violet-600 dark:text-violet-400",
    dot: "bg-violet-500",
    note: "曾连续探测失败，现已恢复",
  },
  suspected_dead: {
    label: "疑似阵亡",
    className: "bg-red-500/15 text-red-600 dark:text-red-400",
    dot: "bg-red-500",
    note: "连续多日探测失败，疑似停止服务",
  },
  dead: {
    label: "已阵亡",
    className: "bg-red-500/20 text-red-700 dark:text-red-400",
    dot: "bg-red-600",
    note: "长期探测失败，判定为停止服务",
  },
};

function statusMeta(status: string) {
  return (
    STATUS_META[status] ?? {
      label: status,
      className: "bg-muted text-muted-foreground",
      dot: "bg-muted-foreground",
      note: "",
    }
  );
}

// 存活时长：从最早探测/上架时间到现在，转「X 天」
function aliveDays(detail: SitePublicView): number {
  const anchor = detail.first_seen_at ?? detail.listed_at;
  const ms = Date.now() - new Date(anchor).getTime();
  return Math.max(0, Math.floor(ms / 86_400_000));
}

// 相对时间（最近探测时间戳，体现「数据是活的」）
function timeAgo(iso: string | null): string {
  if (!iso) return "尚未探测";
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60_000);
  if (min < 1) return "刚刚";
  if (min < 60) return `${min} 分钟前`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} 小时前`;
  return `${Math.floor(hr / 24)} 天前`;
}

// PLACEHOLDER_META

async function fetchDetail(slug: string): Promise<SitePublicView | null> {
  try {
    return await siteApi.publicDetail(slug);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    // 后端不可达等：交给页面兜底（区分于真正的 404）
    throw err;
  }
}

async function fetchReviews(slug: string): Promise<SiteReviewView[]> {
  try {
    const data = await siteApi.reviews(slug);
    return data.reviews;
  } catch {
    // 评价不是详情页主链路；接口暂不可用时降级为空列表。
    return [];
  }
}

function reviewTypeLabel(type: string): string {
  if (type === "owner_deal") return "站长对接已验证";
  if (type === "user_topup") return "充值用户已验证";
  return "已验证评价";
}

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(iso));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  let detail: SitePublicView | null = null;
  try {
    detail = await fetchDetail(slug);
  } catch {
    detail = null;
  }
  if (!detail) return { title: "站点详情 · Router-Hub" };
  const uptime = detail.uptime_30d !== null ? `近30天在线率 ${detail.uptime_30d}%` : "";
  return {
    title: `${detail.name} 怎么样？实测在线率与评测 · Router-Hub`,
    description: `${detail.name} 中转站客观探测履历：${statusMeta(detail.status).label}，${uptime}，已存活 ${aliveDays(detail)} 天。基于真实探测的 AI 中转站征信。`,
  };
}

// 在线率曲线：服务端渲染的内联柱状图（不引图表库）。null 当天为断点（浅灰短柱）。
function UptimeCurve({ history }: { history: SitePublicView["uptime_history"] }) {
  return (
    <div className="flex h-16 items-end gap-[2px]" aria-label="近 30 天每日在线率">
      {history.map((p) => {
        const h = p.uptime === null ? 6 : Math.max(4, Math.round(p.uptime * 0.6));
        const color =
          p.uptime === null
            ? "bg-muted"
            : p.uptime >= 99
              ? "bg-emerald-500/70"
              : p.uptime >= 90
                ? "bg-emerald-500/50"
                : p.uptime >= 50
                  ? "bg-orange-500/60"
                  : "bg-red-500/60";
        const title = p.uptime === null ? `${p.date}：无样本` : `${p.date}：${p.uptime}%`;
        return (
          <div
            key={p.date}
            title={title}
            className={`flex-1 rounded-sm ${color}`}
            style={{ height: `${h}px` }}
          />
        );
      })}
    </div>
  );
}

// PLACEHOLDER_PAGE

const BOARD_LABEL: Record<string, string> = {
  claude: "Claude 榜",
  gpt: "GPT 榜",
  gemini: "Gemini 榜",
};

export default async function SiteDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  let detail: SitePublicView | null = null;
  let reviews: SiteReviewView[] = [];
  let loadError = false;
  try {
    detail = await fetchDetail(slug);
    if (detail) reviews = await fetchReviews(slug);
  } catch {
    loadError = true;
  }

  // 真正不存在/未公开 → 404；后端不可达 → 兜底提示（不误报 404）
  if (!detail && !loadError) notFound();
  if (!detail) {
    return (
      <SiteShell>
        <div className="mx-auto max-w-md px-4 py-32 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">暂时无法加载</h1>
          <p className="mt-2 text-sm text-muted-foreground">服务暂不可用，请稍后再试。</p>
          <Link href="/rank/claude" className="mt-6 inline-block text-sm text-primary hover:underline">
            返回排行榜
          </Link>
        </div>
      </SiteShell>
    );
  }

  const sm = statusMeta(detail.status);

  const ratingAverage =
    reviews.length > 0
      ? reviews.reduce((sum, review) => sum + review.rating, 0) / reviews.length
      : null;

  // JSON-LD：客观措辞的 WebPage；有 verified 评价时补 AggregateRating。
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: `${detail.name} · Router-Hub`,
    description: `${detail.name} 中转站客观探测履历`,
    ...(ratingAverage !== null
      ? {
          aggregateRating: {
            "@type": "AggregateRating",
            ratingValue: ratingAverage.toFixed(1),
            reviewCount: reviews.length,
            bestRating: 5,
            worstRating: 1,
          },
        }
      : {}),
  };

  return (
    <SiteShell>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <div className="mx-auto max-w-3xl px-4 py-10">
        <Link href="/rank/claude" className="text-sm text-muted-foreground hover:text-foreground">
          ← 返回排行榜
        </Link>

        {/* 信任卡（游客可见） */}
        <header className="mt-4">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{detail.name}</h1>
            <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${sm.className}`}>
              <span className={`size-1.5 rounded-full ${sm.dot}`} />
              {sm.label}
            </span>
            {detail.verified && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="size-3.5" />
                已验证可用
              </span>
            )}
          </div>
          {sm.note && <p className="mt-1.5 text-sm text-muted-foreground">{sm.note}</p>}
        </header>

        <section className="mt-5 grid gap-3 sm:grid-cols-3">
          <Stat icon={<Activity className="size-4" />} label="近 30 天在线率"
            value={detail.uptime_30d !== null ? `${detail.uptime_30d}%` : "暂无"} />
          <Stat icon={<Clock className="size-4" />} label="已存活" value={`${aliveDays(detail)} 天`} />
          <Stat icon={<Activity className="size-4" />} label="最近探测" value={timeAgo(detail.last_probe_at)} />
        </section>

        <section className="mt-5 rounded-xl border border-border bg-card p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-muted-foreground">近 30 天在线率</h2>
            <span className="text-xs text-muted-foreground">越高越稳，缺口为无样本</span>
          </div>
          <div className="mt-3">
            {detail.uptime_history.length > 0 ? (
              <UptimeCurve history={detail.uptime_history} />
            ) : (
              <p className="py-6 text-center text-sm text-muted-foreground">暂无探测数据</p>
            )}
          </div>
        </section>

        {/* 榜单分数 */}
        {detail.scores.length > 0 && (
          <section className="mt-5 flex flex-wrap gap-2">
            {detail.scores.map((s) => (
              <Link
                key={s.leaderboard}
                href={`/rank/${s.leaderboard}`}
                className="rounded-lg border border-border bg-card px-3 py-2 text-sm transition-colors hover:border-primary"
              >
                <span className="text-muted-foreground">{BOARD_LABEL[s.leaderboard] ?? s.leaderboard}</span>{" "}
                <span className="font-semibold tabular-nums">
                  {s.composite_score !== null ? Math.round(s.composite_score) : "暂无"}
                </span>
                {s.rank !== null && <span className="ml-1 text-xs text-muted-foreground">#{s.rank}</span>}
              </Link>
            ))}
          </section>
        )}

        {/* 性能区：模型清单（游客可见） */}
        <section className="mt-8">
          <h2 className="text-lg font-semibold tracking-tight">支持的模型</h2>
          {detail.declared_models && detail.declared_models.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {detail.declared_models.map((m) => (
                <span key={m} className="rounded-md bg-muted px-2.5 py-1 font-mono text-xs">{m}</span>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-sm text-muted-foreground">站长未声明模型清单。</p>
          )}
        </section>

        {/* 决策区：硬信息锁登录 */}
        <section className="mt-8">
          <h2 className="text-lg font-semibold tracking-tight">决策信息</h2>
          <div className="mt-3">
            <GatedPanel slug={detail.slug} />
          </div>
          {detail.site_url && (
            <a
              href={detail.site_url}
              target="_blank"
              rel="noopener noreferrer nofollow"
              className="mt-3 inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
            >
              访问站点主页 <ExternalLink className="size-3.5" />
            </a>
          )}
        </section>

        <section className="mt-8">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 className="text-lg font-semibold tracking-tight">已验证评价</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                只展示由真实交互解锁的评价，站长对接和充值用户会分开标注。
              </p>
            </div>
            {ratingAverage !== null && (
              <div className="flex items-center gap-1 rounded-lg border border-border bg-card px-3 py-2 text-sm">
                <Star className="size-4 fill-primary text-primary" />
                <span className="font-semibold tabular-nums">{ratingAverage.toFixed(1)}</span>
                <span className="text-muted-foreground">/ 5</span>
              </div>
            )}
          </div>

          {reviews.length > 0 ? (
            <div className="mt-4 grid gap-3">
              {reviews.map((review) => (
                <article key={review.review_id} className="rounded-xl border border-border bg-card p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-1" aria-label={String(review.rating) + " 星评价"}>
                      {Array.from({ length: 5 }, (_, index) => (
                        <Star
                          key={index}
                          className={
                            index < review.rating
                              ? "size-4 fill-primary text-primary"
                              : "size-4 text-muted-foreground/35"
                          }
                        />
                      ))}
                    </div>
                    <span className="text-xs text-muted-foreground">{formatDate(review.created_at)}</span>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                    <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 font-medium text-emerald-600 dark:text-emerald-400">
                      {reviewTypeLabel(review.review_type)}
                    </span>
                    <span className="font-mono text-muted-foreground">
                      {review.author_id.slice(0, 8)}
                    </span>
                  </div>
                  {review.content ? (
                    <p className="mt-3 text-sm leading-6 text-foreground">{review.content}</p>
                  ) : (
                    <p className="mt-3 text-sm text-muted-foreground">未填写文字评价。</p>
                  )}
                </article>
              ))}
            </div>
          ) : (
            <div className="mt-4 rounded-xl border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
              暂无已验证评价。
            </div>
          )}
        </section>
      </div>
    </SiteShell>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        {icon}
        {label}
      </div>
      <p className="mt-1 text-xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}
