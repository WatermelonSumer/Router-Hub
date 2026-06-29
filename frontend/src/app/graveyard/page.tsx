import type { Metadata } from "next";
import Link from "next/link";
import { Skull, TriangleAlert } from "lucide-react";

import { ApiError, graveyardApi, type GraveyardEntry } from "@/lib/api";
import { SiteShell } from "@/components/site-shell";

export const metadata: Metadata = {
  title: "中转站坟场 · 跑路预警与阵亡名单 · Router-Hub",
  description:
    "基于客观探测的 AI 中转站坟场：连续多日探测失败的疑似跑路站与已确认阵亡站。用探测事实避雷，不主观定性。",
};

// 坟场两态的客观措辞（与详情页 STATUS_META 一致的语义）
const STATUS_META: Record<
  string,
  { label: string; className: string; dot: string }
> = {
  suspected_dead: {
    label: "疑似跑路",
    className: "bg-red-500/15 text-red-600 dark:text-red-400",
    dot: "bg-red-500",
  },
  dead: {
    label: "已确认阵亡",
    className: "bg-red-500/20 text-red-700 dark:text-red-400",
    dot: "bg-red-600",
  },
};

// 连续探测失败天数（now - status_changed_at），客观事实措辞
function failDays(entry: GraveyardEntry): number | null {
  if (!entry.status_changed_at) return null;
  const ms = Date.now() - new Date(entry.status_changed_at).getTime();
  return Math.max(0, Math.floor(ms / 86_400_000));
}

// 存活过多久（first_seen_at → status_changed_at）
function livedDays(entry: GraveyardEntry): number | null {
  if (!entry.first_seen_at) return null;
  const end = entry.status_changed_at
    ? new Date(entry.status_changed_at).getTime()
    : Date.now();
  const ms = end - new Date(entry.first_seen_at).getTime();
  return Math.max(0, Math.floor(ms / 86_400_000));
}

export default async function GraveyardPage() {
  let suspected: GraveyardEntry[] = [];
  let dead: GraveyardEntry[] = [];
  let loadError = false;
  try {
    const data = await graveyardApi.list();
    suspected = data.suspected;
    dead = data.dead;
  } catch (err) {
    loadError = !(err instanceof ApiError && err.status === 0);
  }

  const total = suspected.length + dead.length;

  // JSON-LD ItemList（SEO 富摘要）
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: "中转站坟场 · Router-Hub",
    itemListElement: [...dead, ...suspected].slice(0, 20).map((e, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: e.name,
    })),
  };

  return (
    <SiteShell>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <div className="mx-auto max-w-4xl px-4 py-10">
        <header>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight sm:text-3xl">
            <Skull className="size-7 text-muted-foreground" />
            中转站坟场
          </h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            以下站点连续多日探测失败。本页仅陈述客观探测事实，供避雷参考；站点恢复后会移出坟场。
          </p>
        </header>

        {loadError && (
          <p className="mt-6 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            坟场加载失败，请稍后再试。
          </p>
        )}

        {!loadError && total === 0 && (
          <div className="mt-10 flex flex-col items-center rounded-xl border border-dashed border-border py-16 text-center">
            <Skull className="mb-3 size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">暂无阵亡站点，所有在册站点近期探测正常。</p>
          </div>
        )}

        <GraveSection
          title="疑似跑路"
          desc="连续多日探测失败，尚未坐实。可能是宕机或维护，请谨慎对待。"
          icon={<TriangleAlert className="size-5 text-red-500" />}
          entries={suspected}
        />
        <GraveSection
          title="已确认阵亡"
          desc="长期探测失败，判定为停止服务。"
          icon={<Skull className="size-5 text-red-600" />}
          entries={dead}
        />
      </div>
    </SiteShell>
  );
}

function GraveSection({
  title,
  desc,
  icon,
  entries,
}: {
  title: string;
  desc: string;
  icon: React.ReactNode;
  entries: GraveyardEntry[];
}) {
  if (entries.length === 0) return null;
  return (
    <section className="mt-10">
      <div className="flex items-center gap-2">
        {icon}
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
        <span className="text-sm text-muted-foreground">（{entries.length}）</span>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{desc}</p>
      <div className="mt-4 grid gap-3">
        {entries.map((e) => (
          <GraveCard key={e.site_id} entry={e} />
        ))}
      </div>
    </section>
  );
}

function GraveCard({ entry }: { entry: GraveyardEntry }) {
  const meta = STATUS_META[entry.status] ?? {
    label: entry.status,
    className: "bg-muted text-muted-foreground",
    dot: "bg-muted-foreground",
  };
  const fail = failDays(entry);
  const lived = livedDays(entry);

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Link
            href={`/site/${entry.slug}`}
            className="font-medium hover:text-primary hover:underline"
          >
            {entry.name}
          </Link>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${meta.className}`}
          >
            <span className={`size-1.5 rounded-full ${meta.dot}`} />
            {meta.label}
          </span>
        </div>
        {fail !== null && (
          <span className="text-xs text-muted-foreground">
            连续探测失败 {fail} 天
          </span>
        )}
      </div>

      <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground">
        {lived !== null && (
          <div>
            曾存活 <span className="text-foreground">{lived}</span> 天
          </div>
        )}
        {entry.declared_models && entry.declared_models.length > 0 && (
          <div>
            声称模型 <span className="text-foreground">{entry.declared_models.join("、")}</span>
          </div>
        )}
      </dl>
    </div>
  );
}
