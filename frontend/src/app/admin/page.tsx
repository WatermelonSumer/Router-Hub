"use client";

import * as React from "react";
import Link from "next/link";
import { Check, Loader2, ShieldAlert, X } from "lucide-react";

import { ApiError, adminApi, type SiteAdminView } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { useAuth } from "@/components/auth-provider";
import { SiteShell } from "@/components/site-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function AdminPage() {
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

  // 非管理员一律拦截
  if (!user || user.role !== "admin") {
    return (
      <SiteShell>
        <div className="mx-auto flex max-w-md flex-col items-center px-4 py-32 text-center">
          <div className="mb-5 flex size-14 items-center justify-center rounded-2xl border border-border bg-muted/50 text-muted-foreground">
            <ShieldAlert className="size-7" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">管理员专属页面</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {user ? "当前账号没有管理员权限。" : "请先登录管理员账号。"}
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
      <AdminConsole />
    </SiteShell>
  );
}

// PLACEHOLDER_CONSOLE

function AdminConsole() {
  const [sites, setSites] = React.useState<SiteAdminView[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;

    async function load() {
      const token = getToken();
      if (!token) {
        if (!cancelled) setSites([]);
        return;
      }
      try {
        const data = await adminApi.pending(token);
        if (!cancelled) {
          setSites(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "加载失败");
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  // 审核完成后从待审列表移除
  function handleReviewed(siteId: string) {
    setSites((prev) => (prev ? prev.filter((s) => s.site_id !== siteId) : prev));
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">站点审核</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          通过的站点进入观察区开始探测；驳回需填写理由，站长可见。
        </p>
      </div>

      <div className="mt-8">
        {error && (
          <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </p>
        )}

        {sites === null && !error && (
          <div className="flex justify-center py-16">
            <Loader2 className="size-5 animate-spin text-muted-foreground" />
          </div>
        )}

        {sites !== null && sites.length === 0 && (
          <div className="flex flex-col items-center rounded-xl border border-dashed border-border py-16 text-center">
            <Check className="mb-3 size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">没有待审核的站点</p>
          </div>
        )}

        {sites && sites.length > 0 && (
          <div className="grid gap-3">
            {sites.map((site) => (
              <PendingCard key={site.site_id} site={site} onReviewed={handleReviewed} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// PLACEHOLDER_CARD

function PendingCard({
  site,
  onReviewed,
}: {
  site: SiteAdminView;
  onReviewed: (siteId: string) => void;
}) {
  const [busy, setBusy] = React.useState(false);
  const [rejecting, setRejecting] = React.useState(false);
  const [note, setNote] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);

  async function handleApprove() {
    const token = getToken();
    if (!token) return;
    setError(null);
    setBusy(true);
    try {
      await adminApi.approve(site.site_id, token);
      onReviewed(site.site_id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "操作失败");
      setBusy(false);
    }
  }

  async function handleReject() {
    if (!note.trim()) {
      setError("请填写驳回理由");
      return;
    }
    const token = getToken();
    if (!token) return;
    setError(null);
    setBusy(true);
    try {
      await adminApi.reject(site.site_id, note.trim(), token);
      onReviewed(site.site_id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "操作失败");
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">{site.name}</h3>
        <span className="font-mono text-xs text-muted-foreground">/{site.slug}</span>
      </div>

      <dl className="mt-3 grid gap-x-6 gap-y-1.5 text-sm sm:grid-cols-2">
        <Row label="Base URL" value={site.base_url} mono />
        <Row label="API Key" value={site.key_hint} mono />
        <Row label="站长邮箱" value={site.owner_email ?? "—"} />
        <Row label="微信 / QQ" value={`${site.owner_wechat ?? "—"} / ${site.owner_qq ?? "—"}`} />
        {site.declared_models && site.declared_models.length > 0 && (
          <div className="flex justify-between gap-2 sm:col-span-2 sm:block">
            <dt className="text-muted-foreground">声称模型</dt>
            <dd className="text-xs">{site.declared_models.join("、")}</dd>
          </div>
        )}
      </dl>

      {error && (
        <p className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {error}
        </p>
      )}

      {rejecting ? (
        <div className="mt-4 flex flex-col gap-2">
          <Label htmlFor={`note-${site.site_id}`}>驳回理由（站长可见）</Label>
          <Input
            id={`note-${site.site_id}`}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="例如：base_url 无法连通"
            disabled={busy}
          />
          <div className="flex gap-2">
            <Button variant="destructive" onClick={handleReject} disabled={busy}>
              {busy && <Loader2 className="size-4 animate-spin" />}
              确认驳回
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                setRejecting(false);
                setError(null);
              }}
              disabled={busy}
            >
              取消
            </Button>
          </div>
        </div>
      ) : (
        <div className="mt-4 flex gap-2">
          <Button onClick={handleApprove} disabled={busy}>
            {busy ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />}
            通过
          </Button>
          <Button variant="outline" onClick={() => setRejecting(true)} disabled={busy}>
            <X className="size-4" />
            驳回
          </Button>
        </div>
      )}
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-2 sm:block">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className={`truncate text-xs ${mono ? "font-mono" : ""}`}>{value}</dd>
    </div>
  );
}


