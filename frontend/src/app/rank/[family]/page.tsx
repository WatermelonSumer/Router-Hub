import type { Metadata } from "next";
import Link from "next/link";

import { ApiError, rankApi, type RankEntry, type RankFamily, type RankSort } from "@/lib/api";
import { SiteShell } from "@/components/site-shell";

// 三大分榜元信息（顺序即 Tab 顺序）
const FAMILIES: { key: RankFamily; label: string; blurb: string }[] = [
  { key: "claude", label: "Claude 榜", blurb: "Claude 系模型中转站实测排名，真实性权重最高" },
  { key: "gpt", label: "GPT 榜", blurb: "GPT 系模型中转站实测排名，看重在线率与价格" },
  { key: "gemini", label: "Gemini 榜", blurb: "Gemini 系模型中转站实测排名，看重在线率" },
];

const SORTS: { key: RankSort; label: string }[] = [
  { key: "composite", label: "综合分" },
  { key: "speed", label: "速度" },
  { key: "uptime", label: "在线率" },
];

function familyOf(slug: string): (typeof FAMILIES)[number] | undefined {
  return FAMILIES.find((f) => f.key === slug);
}

function sortOf(value: string | undefined): RankSort {
  return SORTS.some((s) => s.key === value) ? (value as RankSort) : "composite";
}

export function generateStaticParams() {
  return FAMILIES.map((f) => ({ family: f.key }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ family: string }>;
}): Promise<Metadata> {
  const { family } = await params;
  const meta = familyOf(family);
  if (!meta) return { title: "排行榜 · Router-Hub" };
  return {
    title: `${meta.label} · Router-Hub AI 中转站排行榜`,
    description: meta.blurb,
  };
}

// PLACEHOLDER_PAGE

export default async function RankFamilyPage({
  params,
  searchParams,
}: {
  params: Promise<{ family: string }>;
  searchParams: Promise<{ sort?: string }>;
}) {
  const { family } = await params;
  const { sort: sortParam } = await searchParams;
  const meta = familyOf(family);

  if (!meta) {
    return (
      <SiteShell>
        <div className="mx-auto max-w-md px-4 py-32 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">未知分榜</h1>
          <p className="mt-2 text-sm text-muted-foreground">该分榜不存在。</p>
          <Link href="/rank/claude" className="mt-6 inline-block text-sm text-primary hover:underline">
            前往 Claude 榜
          </Link>
        </div>
      </SiteShell>
    );
  }

  const sort = sortOf(sortParam);

  let main: RankEntry[] = [];
  let observing: RankEntry[] = [];
  let loadError = false;
  try {
    const data = await rankApi.list(meta.key, sort);
    main = data.main;
    observing = data.observing;
  } catch (err) {
    // 后端不可达/出错：兜底空态，不让整页崩
    loadError = !(err instanceof ApiError && err.status === 0);
  }

  // JSON-LD ItemList（SEO 富摘要，blueprint 第九节红线）
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: `${meta.label} · Router-Hub`,
    itemListElement: main.slice(0, 20).map((e, i) => ({
      "@type": "ListItem",
      position: e.rank ?? i + 1,
      name: e.name,
      url: e.site_url ?? undefined,
    })),
  };

  return (
    <SiteShell>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <div className="mx-auto max-w-5xl px-4 py-10">
        <header>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            AI 中转站排行榜
          </h1>
          <p className="mt-1.5 text-sm text-muted-foreground">{meta.blurb}</p>
        </header>

        <FamilyTabs current={meta.key} sort={sort} />
        <SortBar family={meta.key} current={sort} />

        {loadError && (
          <p className="mt-6 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            榜单加载失败，请稍后再试。
          </p>
        )}

        <MainBoard entries={main} sort={sort} />
        <ObservingBoard entries={observing} />
      </div>
    </SiteShell>
  );
}

// PLACEHOLDER_COMPONENTS

// 状态 → 中文标签 + 样式（与站长端一致的语义色，零硬编码）
const STATUS_META: Record<string, { label: string; className: string }> = {
  online: { label: "在线", className: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400" },
  abnormal: { label: "异常", className: "bg-orange-500/15 text-orange-600 dark:text-orange-400" },
  revived: { label: "复活", className: "bg-violet-500/15 text-violet-600 dark:text-violet-400" },
  observing: { label: "观察中", className: "bg-sky-500/15 text-sky-600 dark:text-sky-400" },
};

function StatusBadge({ status }: { status: string }) {
  const meta = STATUS_META[status] ?? { label: status, className: "bg-muted text-muted-foreground" };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${meta.className}`}>
      {meta.label}
    </span>
  );
}

// 分数展示：null 不显示为 0，标「暂无」（blueprint 六之二陷阱 C）
function fmtScore(v: number | null): string {
  return v === null || v === undefined ? "暂无" : String(Math.round(v));
}

function FamilyTabs({ current, sort }: { current: RankFamily; sort: RankSort }) {
  return (
    <nav className="mt-6 flex gap-1 overflow-x-auto rounded-lg border border-border bg-muted/40 p-1">
      {FAMILIES.map((f) => {
        const active = f.key === current;
        const href = sort === "composite" ? `/rank/${f.key}` : `/rank/${f.key}?sort=${sort}`;
        return (
          <Link
            key={f.key}
            href={href}
            className={`flex-1 whitespace-nowrap rounded-md px-3 py-2 text-center text-sm font-medium transition-colors ${
              active
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {f.label}
          </Link>
        );
      })}
    </nav>
  );
}

function SortBar({ family, current }: { family: RankFamily; current: RankSort }) {
  return (
    <div className="mt-4 flex flex-wrap items-center gap-2">
      <span className="text-xs text-muted-foreground">排序</span>
      {SORTS.map((s) => {
        const active = s.key === current;
        const href = s.key === "composite" ? `/rank/${family}` : `/rank/${family}?sort=${s.key}`;
        return (
          <Link
            key={s.key}
            href={href}
            className={`rounded-full border px-3 py-1 text-xs transition-colors ${
              active
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            {s.label}
          </Link>
        );
      })}
    </div>
  );
}

// PLACEHOLDER_BOARDS

function MainBoard({ entries, sort }: { entries: RankEntry[]; sort: RankSort }) {
  if (entries.length === 0) {
    return (
      <div className="mt-8 flex flex-col items-center rounded-xl border border-dashed border-border py-16 text-center">
        <p className="text-sm text-muted-foreground">该榜暂无数据，平台正在探测中。</p>
      </div>
    );
  }
  return (
    <section className="mt-8">
      {/* 桌面：表格 */}
      <div className="hidden overflow-hidden rounded-xl border border-border sm:block">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-xs text-muted-foreground">
            <tr>
              <th className="px-4 py-3 text-left font-medium">#</th>
              <th className="px-4 py-3 text-left font-medium">站点</th>
              <th className="px-4 py-3 text-right font-medium">综合</th>
              <th className="px-4 py-3 text-right font-medium">在线率</th>
              <th className="px-4 py-3 text-right font-medium">速度</th>
              <th className="px-4 py-3 text-right font-medium">真实性</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e, i) => (
              <tr key={e.site_id} className="border-t border-border">
                <td className="px-4 py-3 font-mono text-muted-foreground">{e.rank ?? i + 1}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Link href={`/site/${e.slug}`} className="font-medium hover:text-primary hover:underline">
                      {e.name}
                    </Link>
                    <StatusBadge status={e.status} />
                  </div>
                </td>
                <ScoreCell value={e.composite_score} highlight={sort === "composite"} strong />
                <ScoreCell value={e.uptime_score} highlight={sort === "uptime"} />
                <ScoreCell value={e.speed_score} highlight={sort === "speed"} />
                <ScoreCell value={e.authenticity_score} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 移动：卡片堆叠 */}
      <div className="grid gap-3 sm:hidden">
        {entries.map((e, i) => (
          <div key={e.site_id} className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm text-muted-foreground">#{e.rank ?? i + 1}</span>
                <Link href={`/site/${e.slug}`} className="font-medium hover:text-primary hover:underline">
                  {e.name}
                </Link>
              </div>
              <StatusBadge status={e.status} />
            </div>
            <dl className="mt-3 grid grid-cols-4 gap-2 text-center">
              <ScoreStat label="综合" value={e.composite_score} strong />
              <ScoreStat label="在线率" value={e.uptime_score} />
              <ScoreStat label="速度" value={e.speed_score} />
              <ScoreStat label="真实性" value={e.authenticity_score} />
            </dl>
          </div>
        ))}
      </div>
    </section>
  );
}

function ScoreCell({
  value,
  highlight,
  strong,
}: {
  value: number | null;
  highlight?: boolean;
  strong?: boolean;
}) {
  return (
    <td
      className={`px-4 py-3 text-right tabular-nums ${
        highlight ? "text-primary font-semibold" : strong ? "font-semibold" : "text-muted-foreground"
      }`}
    >
      {fmtScore(value)}
    </td>
  );
}

function ScoreStat({ label, value, strong }: { label: string; value: number | null; strong?: boolean }) {
  return (
    <div>
      <dt className="text-[11px] text-muted-foreground">{label}</dt>
      <dd className={`tabular-nums ${strong ? "font-semibold" : ""}`}>{fmtScore(value)}</dd>
    </div>
  );
}

function ObservingBoard({ entries }: { entries: RankEntry[] }) {
  if (entries.length === 0) return null;
  return (
    <section className="mt-10">
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-semibold tracking-tight">新站观察区</h2>
        <span className="rounded-full bg-sky-500/15 px-2 py-0.5 text-xs text-sky-600 dark:text-sky-400">
          数据积累中
        </span>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        新上架站点先在此积累探测样本，满 7 天且样本达标后进入主榜。
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {entries.map((e) => (
          <div key={e.site_id} className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center justify-between gap-2">
              <Link href={`/site/${e.slug}`} className="font-medium hover:text-primary hover:underline">
                {e.name}
              </Link>
              <StatusBadge status={e.status} />
            </div>
            <dl className="mt-3 grid grid-cols-3 gap-2 text-center">
              <ScoreStat label="综合" value={e.composite_score} strong />
              <ScoreStat label="在线率" value={e.uptime_score} />
              <ScoreStat label="真实性" value={e.authenticity_score} />
            </dl>
          </div>
        ))}
      </div>
    </section>
  );
}



