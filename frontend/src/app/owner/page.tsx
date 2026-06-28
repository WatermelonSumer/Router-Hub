"use client";

import * as React from "react";
import Link from "next/link";
import {
  Loader2,
  Plus,
  Server,
  ShieldAlert,
} from "lucide-react";

import {
  ApiError,
  siteApi,
  type SiteCreatePayload,
  type SiteOwnerView,
} from "@/lib/api";
import { getToken } from "@/lib/auth";
import { useAuth } from "@/components/auth-provider";
import { SiteShell } from "@/components/site-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

// 站点状态 → 中文标签 + 样式
const STATUS_META: Record<string, { label: string; className: string }> = {
  pending: { label: "待审核", className: "bg-amber-500/15 text-amber-600 dark:text-amber-400" },
  observing: { label: "观察区", className: "bg-sky-500/15 text-sky-600 dark:text-sky-400" },
  online: { label: "在线", className: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400" },
  abnormal: { label: "异常", className: "bg-orange-500/15 text-orange-600 dark:text-orange-400" },
  suspected_dead: { label: "疑似阵亡", className: "bg-red-500/15 text-red-600 dark:text-red-400" },
  dead: { label: "已阵亡", className: "bg-red-500/20 text-red-700 dark:text-red-400" },
  revived: { label: "复活", className: "bg-violet-500/15 text-violet-600 dark:text-violet-400" },
};

function StatusBadge({ status }: { status: string }) {
  const meta = STATUS_META[status] ?? {
    label: status,
    className: "bg-muted text-muted-foreground",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${meta.className}`}
    >
      {meta.label}
    </span>
  );
}

export default function OwnerPage() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <SiteShell>
        <div className="flex justify-center py-32">
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
        </div>
      </SiteShell>
    );
  }

  // 未登录或非站长：拦截并引导
  if (!user || user.role !== "owner") {
    return (
      <SiteShell>
        <div className="mx-auto flex max-w-md flex-col items-center px-4 py-32 text-center">
          <div className="mb-5 flex size-14 items-center justify-center rounded-2xl border border-border bg-muted/50 text-muted-foreground">
            <ShieldAlert className="size-7" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">站长专属页面</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {user ? "当前账号不是站长身份，无法上架中转站。" : "请先以站长身份登录。"}
          </p>
          <Button asChild className="mt-6">
            <Link href={user ? "/" : "/login"}>{user ? "返回首页" : "去登录"}</Link>
          </Button>
        </div>
      </SiteShell>
    );
  }

  return (
    <SiteShell>
      <OwnerConsole />
    </SiteShell>
  );
}

function OwnerConsole() {
  const [sites, setSites] = React.useState<SiteOwnerView[] | null>(null);
  const [listError, setListError] = React.useState<string | null>(null);
  const [showForm, setShowForm] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;

    async function load() {
      const token = getToken();
      if (!token) {
        if (!cancelled) setSites([]);
        return;
      }
      try {
        const data = await siteApi.mine(token);
        if (!cancelled) {
          setSites(data);
          setListError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setListError(err instanceof ApiError ? err.message : "加载失败");
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  function handleCreated(site: SiteOwnerView) {
    setSites((prev) => (prev ? [site, ...prev] : [site]));
    setShowForm(false);
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">站长控制台</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            上架你的中转站，平台将真实付费探测并纳入排行榜。
          </p>
        </div>
        <Button onClick={() => setShowForm((v) => !v)}>
          <Plus className="size-4" />
          上架中转站
        </Button>
      </div>

      {/* 上架表单 */}
      {showForm && (
        <div className="mt-6">
          <CreateSiteForm onCreated={handleCreated} onCancel={() => setShowForm(false)} />
        </div>
      )}

      {/* 站点列表 */}
      <div className="mt-8">
        {listError && (
          <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {listError}
          </p>
        )}

        {sites === null && !listError && (
          <div className="flex justify-center py-16">
            <Loader2 className="size-5 animate-spin text-muted-foreground" />
          </div>
        )}

        {sites !== null && sites.length === 0 && (
          <div className="flex flex-col items-center rounded-xl border border-dashed border-border py-16 text-center">
            <Server className="mb-3 size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">还没有上架任何中转站</p>
          </div>
        )}

        {sites && sites.length > 0 && (
          <div className="grid gap-3">
            {sites.map((site) => (
              <SiteCard key={site.site_id} site={site} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SiteCard({ site }: { site: SiteOwnerView }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold">{site.name}</h3>
          <StatusBadge status={site.status} />
        </div>
        <span className="font-mono text-xs text-muted-foreground">/{site.slug}</span>
      </div>
      <dl className="mt-3 grid gap-x-6 gap-y-1.5 text-sm sm:grid-cols-2">
        <div className="flex justify-between gap-2 sm:block">
          <dt className="text-muted-foreground">Base URL</dt>
          <dd className="truncate font-mono text-xs">{site.base_url}</dd>
        </div>
        <div className="flex justify-between gap-2 sm:block">
          <dt className="text-muted-foreground">API Key</dt>
          <dd className="font-mono text-xs">{site.key_hint}</dd>
        </div>
        {site.declared_models && site.declared_models.length > 0 && (
          <div className="flex justify-between gap-2 sm:col-span-2 sm:block">
            <dt className="text-muted-foreground">声称模型</dt>
            <dd className="text-xs">{site.declared_models.join("、")}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}

function CreateSiteForm({
  onCreated,
  onCancel,
}: {
  onCreated: (site: SiteOwnerView) => void;
  onCancel: () => void;
}) {
  const [name, setName] = React.useState("");
  const [baseUrl, setBaseUrl] = React.useState("");
  const [apiKey, setApiKey] = React.useState("");
  const [slug, setSlug] = React.useState("");
  const [siteUrl, setSiteUrl] = React.useState("");
  const [models, setModels] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!name.trim() || !baseUrl.trim() || !apiKey.trim()) {
      setError("请填写站点名称、Base URL 和 API Key");
      return;
    }

    const token = getToken();
    if (!token) {
      setError("登录已失效，请重新登录");
      return;
    }

    const payload: SiteCreatePayload = {
      name: name.trim(),
      base_url: baseUrl.trim(),
      api_key: apiKey.trim(),
    };
    if (slug.trim()) payload.slug = slug.trim();
    if (siteUrl.trim()) payload.site_url = siteUrl.trim();
    const modelList = models
      .split(",")
      .map((m) => m.trim())
      .filter(Boolean);
    if (modelList.length > 0) payload.declared_models = modelList;

    setSubmitting(true);
    try {
      const site = await siteApi.create(payload, token);
      onCreated(site);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "上架失败，请重试");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-border bg-card p-5"
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="站点名称" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="ClaudeHub" disabled={submitting} />
        </Field>
        <Field label="slug（可选，留空自动生成）">
          <Input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="claudehub" disabled={submitting} />
        </Field>
        <Field label="Base URL" required>
          <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://api.example.com/v1" disabled={submitting} />
        </Field>
        <Field label="展示主页（可选）">
          <Input value={siteUrl} onChange={(e) => setSiteUrl(e.target.value)} placeholder="https://example.com" disabled={submitting} />
        </Field>
        <Field label="API Key（加密保存，仅探测用）" required full>
          <Input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="sk-..." autoComplete="off" disabled={submitting} />
        </Field>
        <Field label="声称支持的模型（可选，逗号分隔）" full>
          <Input value={models} onChange={(e) => setModels(e.target.value)} placeholder="claude-3-5-sonnet, gpt-4o" disabled={submitting} />
        </Field>
      </div>

      {error && (
        <p className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {error}
        </p>
      )}

      <p className="mt-4 text-xs text-muted-foreground">
        API Key 将加密存储，绝不下发前端、不公开展示，仅用于平台后端探测。
      </p>

      <div className="mt-4 flex gap-2">
        <Button type="submit" disabled={submitting}>
          {submitting && <Loader2 className="size-4 animate-spin" />}
          提交上架
        </Button>
        <Button type="button" variant="outline" onClick={onCancel} disabled={submitting}>
          取消
        </Button>
      </div>
    </form>
  );
}

function Field({
  label,
  required,
  full,
  children,
}: {
  label: string;
  required?: boolean;
  full?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={`flex flex-col gap-2 ${full ? "sm:col-span-2" : ""}`}>
      <Label>
        {label}
        {required && <span className="ml-0.5 text-destructive">*</span>}
      </Label>
      {children}
    </div>
  );
}

