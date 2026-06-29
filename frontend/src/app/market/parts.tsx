"use client";

/** 中转集市页的子组件：发帖表单、筛选条、帖子卡片（含履历名片）、对接列表。 */

import * as React from "react";
import Link from "next/link";
import { Award, Check, Loader2, Skull, Star, X } from "lucide-react";

import {
  ApiError,
  marketApi,
  type OwnerReputation,
  type PostCreatePayload,
  type PostView,
  type ResponseView,
} from "@/lib/api";
import { getToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

// ===== 枚举中文标签 =====
const POST_TYPE_LABEL: Record<string, string> = { supply: "供给（出货）", demand: "需求（进货）" };
const DIRECTION_LABEL: Record<string, string> = { upstream: "上游", downstream: "下游" };
const SETTLEMENT_LABEL: Record<string, string> = { daily: "日结", weekly: "周结", prepaid: "预付" };
const FAMILY_LABEL: Record<string, string> = { claude: "Claude", gpt: "GPT", gemini: "Gemini" };

export type Filter = {
  post_type?: string;
  direction?: string;
  model_family?: string;
  max_rate?: string;
};

// ===== 筛选条 =====
export function FilterBar({
  filter,
  onChange,
}: {
  filter: Filter;
  onChange: (f: Filter) => void;
}) {
  function set(key: keyof Filter, value: string) {
    onChange({ ...filter, [key]: value || undefined });
  }
  return (
    <div className="mt-4 flex flex-wrap items-end gap-3 rounded-lg border border-border bg-muted/30 p-3">
      <Select label="类型" value={filter.post_type ?? ""} onChange={(v) => set("post_type", v)}
        options={[["", "全部"], ["supply", "供给"], ["demand", "需求"]]} />
      <Select label="方向" value={filter.direction ?? ""} onChange={(v) => set("direction", v)}
        options={[["", "全部"], ["upstream", "上游"], ["downstream", "下游"]]} />
      <Select label="模型族" value={filter.model_family ?? ""} onChange={(v) => set("model_family", v)}
        options={[["", "全部"], ["claude", "Claude"], ["gpt", "GPT"], ["gemini", "Gemini"]]} />
      <div className="flex flex-col gap-1">
        <Label className="text-xs text-muted-foreground">倍率 ≤</Label>
        <Input
          type="number"
          step="0.01"
          min="0"
          value={filter.max_rate ?? ""}
          onChange={(e) => set("max_rate", e.target.value)}
          placeholder="如 0.10"
          className="h-9 w-24"
        />
      </div>
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: [string, string][];
}) {
  return (
    <div className="flex flex-col gap-1">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 rounded-md border border-input bg-background px-2 text-sm"
      >
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </div>
  );
}

// ===== 发帖表单（折叠） =====
export function CreatePostForm({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [form, setForm] = React.useState<PostCreatePayload>({
    post_type: "supply",
    direction: "upstream",
    model_family: "claude",
  });

  function upd<K extends keyof PostCreatePayload>(key: K, value: PostCreatePayload[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function submit() {
    const token = getToken();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await marketApi.create(form, token);
      setOpen(false);
      setForm({ post_type: "supply", direction: "upstream", model_family: "claude" });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "发布失败");
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <Button className="mt-4" onClick={() => setOpen(true)}>
        发布帖子
      </Button>
    );
  }

  return (
    <div className="mt-4 rounded-xl border border-border bg-card p-5">
      <h2 className="font-semibold">发布集市帖子</h2>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <Select label="类型" value={form.post_type} onChange={(v) => upd("post_type", v as PostCreatePayload["post_type"])}
          options={[["supply", "供给（出货）"], ["demand", "需求（进货）"]]} />
        <Select label="方向" value={form.direction} onChange={(v) => upd("direction", v as PostCreatePayload["direction"])}
          options={[["upstream", "上游"], ["downstream", "下游"]]} />
        <Select label="模型族" value={form.model_family} onChange={(v) => upd("model_family", v as PostCreatePayload["model_family"])}
          options={[["claude", "Claude"], ["gpt", "GPT"], ["gemini", "Gemini"]]} />
        <Field label="倍率">
          <Input type="number" step="0.0001" min="0" value={form.rate ?? ""} onChange={(e) => upd("rate", e.target.value)} placeholder="0.05" />
        </Field>
        <Field label="RPM">
          <Input type="number" min="0" value={form.rpm ?? ""} onChange={(e) => upd("rpm", e.target.value ? Number(e.target.value) : undefined)} placeholder="200" />
        </Field>
        <Select label="结算" value={form.settlement ?? ""} onChange={(v) => upd("settlement", (v || undefined) as PostCreatePayload["settlement"])}
          options={[["", "不限"], ["daily", "日结"], ["weekly", "周结"], ["prepaid", "预付"]]} />
        <Field label="量级" className="sm:col-span-3">
          <Input value={form.volume ?? ""} onChange={(e) => upd("volume", e.target.value)} placeholder="日均 100w 调用" />
        </Field>
        <Field label="补充说明" className="sm:col-span-3">
          <Input value={form.note ?? ""} onChange={(e) => upd("note", e.target.value)} placeholder="批发黑话写这里" />
        </Field>
      </div>

      {error && (
        <p className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {error}
        </p>
      )}

      <div className="mt-4 flex gap-2">
        <Button onClick={submit} disabled={busy}>
          {busy && <Loader2 className="size-4 animate-spin" />}
          发布
        </Button>
        <Button variant="outline" onClick={() => setOpen(false)} disabled={busy}>
          取消
        </Button>
      </div>
    </div>
  );
}

function Field({
  label,
  className,
  children,
}: {
  label: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`flex flex-col gap-1 ${className ?? ""}`}>
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}

// ===== 探测履历名片 =====
function ReputationBadge({ rep }: { rep: OwnerReputation }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
      <span className="flex items-center gap-1">
        <Award className="size-3.5" />
        最高分 <span className="text-foreground">{rep.best_composite !== null ? Math.round(rep.best_composite) : "暂无"}</span>
      </span>
      {rep.max_alive_days !== null && (
        <span>最长存活 <span className="text-foreground">{rep.max_alive_days}</span> 天</span>
      )}
      <span>在册 <span className="text-foreground">{rep.site_count}</span> 站</span>
      {rep.graveyard_count > 0 && (
        <span className="flex items-center gap-1 text-red-600 dark:text-red-400">
          <Skull className="size-3.5" />
          坟场 {rep.graveyard_count}
        </span>
      )}
    </div>
  );
}

// ===== 帖子卡片 =====
export function PostCard({
  post,
  isAdmin,
  onChanged,
}: {
  post: PostView;
  isAdmin?: boolean;
  onChanged: () => void;
}) {
  const [busy, setBusy] = React.useState(false);
  const [msg, setMsg] = React.useState<string | null>(null);
  const isClosed = post.status === "closed";

  async function respond() {
    const token = getToken();
    if (!token) return;
    setBusy(true);
    setMsg(null);
    try {
      await marketApi.respond(post.post_id, token);
      setMsg("已发起对接，等待发帖人确认");
      onChanged();
    } catch (err) {
      setMsg(err instanceof ApiError ? err.message : "操作失败");
    } finally {
      setBusy(false);
    }
  }

  async function close() {
    const token = getToken();
    if (!token) return;
    setBusy(true);
    try {
      await marketApi.close(post.post_id, token);
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
          {POST_TYPE_LABEL[post.post_type] ?? post.post_type}
        </span>
        <span className="rounded-md bg-muted px-2 py-0.5 text-xs">
          {FAMILY_LABEL[post.model_family] ?? post.model_family} · {DIRECTION_LABEL[post.direction] ?? post.direction}
        </span>
        {isClosed && <span className="rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground">已关闭</span>}
        {post.is_mine && <span className="rounded-md bg-sky-500/15 px-2 py-0.5 text-xs text-sky-600 dark:text-sky-400">我发布的</span>}
        {post.site_slug && post.site_name && (
          <Link
            href={`/site/${post.site_slug}`}
            className="rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground hover:text-primary hover:underline"
          >
            站点：{post.site_name}
          </Link>
        )}
      </div>

      <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
        {post.rate && <Spec label="倍率" value={post.rate} />}
        {post.rpm !== null && <Spec label="RPM" value={String(post.rpm)} />}
        {post.volume && <Spec label="量级" value={post.volume} />}
        {post.settlement && <Spec label="结算" value={SETTLEMENT_LABEL[post.settlement] ?? post.settlement} />}
      </dl>

      {post.note && <p className="mt-2 text-sm text-muted-foreground">{post.note}</p>}

      <div className="mt-3 border-t border-border pt-3">
        <ReputationBadge rep={post.author_reputation} />
      </div>

      {msg && <p className="mt-3 text-xs text-muted-foreground">{msg}</p>}

      <div className="mt-3 flex gap-2">
        {isAdmin ? (
          // 管理员：监管视角，仅可下架违规帖（不发帖、不对接）
          !isClosed && (
            <Button variant="destructive" size="sm" onClick={close} disabled={busy}>
              {busy ? <Loader2 className="size-4 animate-spin" /> : <X className="size-4" />}
              管理下架
            </Button>
          )
        ) : post.is_mine ? (
          !isClosed && (
            <Button variant="outline" size="sm" onClick={close} disabled={busy}>
              <X className="size-4" />
              关闭帖子
            </Button>
          )
        ) : (
          !isClosed && (
            <Button size="sm" onClick={respond} disabled={busy}>
              {busy && <Loader2 className="size-4 animate-spin" />}
              对接 / 报名
            </Button>
          )
        )}
      </div>
    </div>
  );
}

function Spec({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-muted-foreground">{label} </span>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  );
}

// ===== 对接列表（我的对接 + 收到的对接）=====
export function ResponseList({
  myResponses,
  incoming,
  onConfirmed,
}: {
  myResponses: ResponseView[];
  incoming: ResponseView[];
  onConfirmed: () => void;
}) {
  return (
    <div className="mt-6 grid gap-8">
      <section>
        <h2 className="text-lg font-semibold tracking-tight">收到的对接</h2>
        <p className="mt-1 text-xs text-muted-foreground">别人对你帖子的对接，确认后交换名片并解锁互评。</p>
        <div className="mt-3 grid gap-3">
          {incoming.length === 0 && <Empty text="暂无收到的对接" />}
          {incoming.map((r) => (
            <ResponseCard key={r.response_id} resp={r} confirmable onConfirmed={onConfirmed} />
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold tracking-tight">我发起的对接</h2>
        <p className="mt-1 text-xs text-muted-foreground">确认后这里显示对方名片。</p>
        <div className="mt-3 grid gap-3">
          {myResponses.length === 0 && <Empty text="还没有发起任何对接" />}
          {myResponses.map((r) => (
            <ResponseCard key={r.response_id} resp={r} onConfirmed={onConfirmed} />
          ))}
        </div>
      </section>
    </div>
  );
}

const RESP_STATUS_LABEL: Record<string, string> = {
  pending: "待确认",
  connected: "已联系",
  confirmed: "已确认",
};

function ResponseCard({
  resp,
  confirmable,
  onConfirmed,
}: {
  resp: ResponseView;
  confirmable?: boolean;
  onConfirmed: () => void;
}) {
  const [busy, setBusy] = React.useState(false);

  async function confirm() {
    const token = getToken();
    if (!token) return;
    setBusy(true);
    try {
      await marketApi.confirm(resp.response_id, token);
      onConfirmed();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          状态：<span className="font-medium text-foreground">{RESP_STATUS_LABEL[resp.status] ?? resp.status}</span>
        </span>
        {confirmable && resp.status !== "confirmed" && (
          <Button size="sm" onClick={confirm} disabled={busy}>
            {busy ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />}
            确认对接
          </Button>
        )}
      </div>

      {resp.contact && (
        <div className="mt-3 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm">
          <p className="font-medium text-emerald-700 dark:text-emerald-400">对方名片（已对接✓）</p>
          <dl className="mt-1 flex flex-wrap gap-x-6 gap-y-1 text-xs">
            <Spec label="邮箱" value={resp.contact.email} />
            {resp.contact.wechat && <Spec label="微信" value={resp.contact.wechat} />}
            {resp.contact.qq && <Spec label="QQ" value={resp.contact.qq} />}
          </dl>
        </div>
      )}

      {resp.status === "confirmed" && <ReviewWidget responseId={resp.response_id} />}
    </div>
  );
}

// 互评小部件：confirmed 对接后评价对方站点（星级 + 可选文字）
function ReviewWidget({ responseId }: { responseId: string }) {
  const [rating, setRating] = React.useState(0);
  const [content, setContent] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [done, setDone] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function submit() {
    if (rating < 1) {
      setError("请先选择星级");
      return;
    }
    const token = getToken();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await marketApi.review(responseId, { rating, content: content || undefined }, token);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "评价失败");
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <p className="mt-3 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-700 dark:text-emerald-400">
        已提交评价，感谢反馈。
      </p>
    );
  }

  return (
    <div className="mt-3 rounded-md border border-border bg-muted/30 px-3 py-2.5">
      <p className="text-xs font-medium text-muted-foreground">评价对方站点（已对接解锁）</p>
      <div className="mt-1.5 flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => setRating(n)}
            aria-label={`${n} 星`}
            className="text-amber-500 transition-transform hover:scale-110"
          >
            <Star className={`size-5 ${n <= rating ? "fill-amber-500" : "fill-transparent"}`} />
          </button>
        ))}
      </div>
      <Input
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="补充说明（可选）"
        className="mt-2 h-8 text-sm"
        disabled={busy}
      />
      {error && <p className="mt-1.5 text-xs text-destructive">{error}</p>}
      <Button size="sm" className="mt-2" onClick={submit} disabled={busy}>
        {busy && <Loader2 className="size-4 animate-spin" />}
        提交评价
      </Button>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <div className="rounded-xl border border-dashed border-border py-10 text-center text-sm text-muted-foreground">
      {text}
    </div>
  );
}
