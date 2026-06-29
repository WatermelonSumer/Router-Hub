"use client";

/**
 * 中转集市（B 端批发撮合）：登录墙后，刻意不 SEO（保护批发底价）。
 * 仅站长可见；普通用户/游客拦截。
 *
 * 三块：发帖表单 + 筛选浏览（帖子旁挂发帖人探测履历名片）+ 我的对接/收到的对接（confirmed 换名片）。
 */

import * as React from "react";
import Link from "next/link";
import { Loader2, ShieldAlert, Store } from "lucide-react";

import {
  ApiError,
  marketApi,
  type PostView,
  type ResponseView,
} from "@/lib/api";
import { getToken } from "@/lib/auth";
import { useAuth } from "@/components/auth-provider";
import { SiteShell } from "@/components/site-shell";
import { Button } from "@/components/ui/button";

import { PostCard, CreatePostForm, FilterBar, ResponseList } from "./parts";
import type { Filter } from "./parts";

export default function MarketPage() {
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

  // 登录墙：站长（交易）或管理员（监管）可进
  const isOwner = user?.role === "owner";
  const isAdmin = user?.role === "admin";
  if (!user || (!isOwner && !isAdmin)) {
    return (
      <SiteShell>
        <div className="mx-auto flex max-w-md flex-col items-center px-4 py-32 text-center">
          <div className="mb-5 flex size-14 items-center justify-center rounded-2xl border border-border bg-muted/50 text-muted-foreground">
            <ShieldAlert className="size-7" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">中转集市仅对站长开放</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {user
              ? "集市是站长间的批发撮合市场，需以站长身份登录。"
              : "请先登录站长账号进入集市。"}
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
      <MarketConsole isAdmin={isAdmin} />
    </SiteShell>
  );
}

function MarketConsole({ isAdmin }: { isAdmin: boolean }) {
  const [posts, setPosts] = React.useState<PostView[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [filter, setFilter] = React.useState<Filter>({});
  const [tab, setTab] = React.useState<"browse" | "deals">("browse");
  const [myResponses, setMyResponses] = React.useState<ResponseView[]>([]);
  const [incoming, setIncoming] = React.useState<ResponseView[]>([]);

  const loadPosts = React.useCallback(async () => {
    const token = getToken();
    if (!token) return;
    setError(null);
    try {
      const data = await marketApi.list(filter, token);
      setPosts(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "加载失败");
    }
  }, [filter]);

  const loadDeals = React.useCallback(async () => {
    if (isAdmin) return; // 管理员无交易，不拉对接
    const token = getToken();
    if (!token) return;
    try {
      const [mine, inc] = await Promise.all([
        marketApi.myResponses(token),
        marketApi.incomingResponses(token),
      ]);
      setMyResponses(mine);
      setIncoming(inc);
    } catch {
      // 对接列表加载失败不致命，留空
    }
  }, [isAdmin]);

  React.useEffect(() => {
    const id = setTimeout(() => void loadPosts(), 0);
    return () => clearTimeout(id);
  }, [loadPosts]);

  React.useEffect(() => {
    const id = setTimeout(() => void loadDeals(), 0);
    return () => clearTimeout(id);
  }, [loadDeals]);

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <header className="flex items-center gap-2">
        <Store className="size-6 text-primary" />
        <h1 className="text-2xl font-semibold tracking-tight">中转集市</h1>
      </header>
      <p className="mt-1.5 text-sm text-muted-foreground">
        {isAdmin
          ? "管理员监管视角：浏览全部帖子，可下架违规内容。发帖与对接为站长交易动作。"
          : "站长间批发倒卖 API 产能：找上游=进货，找下游=出货。对接确认后交换名片。"}
      </p>

      {/* 顶部 tab：管理员无交易，不显示「我的对接」 */}
      {!isAdmin && (
        <nav className="mt-6 flex gap-1 rounded-lg border border-border bg-muted/40 p-1">
          {[
            { key: "browse", label: "浏览 / 发帖" },
            { key: "deals", label: "我的对接" },
          ].map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key as "browse" | "deals")}
              className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                tab === t.key
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      )}

      {tab === "browse" || isAdmin ? (
        <>
          {/* 发帖仅站长 */}
          {!isAdmin && (
            <CreatePostForm
              onCreated={() => {
                void loadPosts();
              }}
            />
          )}
          <FilterBar filter={filter} onChange={setFilter} />

          {error && (
            <p className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}

          {posts === null && !error && (
            <div className="flex justify-center py-16">
              <Loader2 className="size-5 animate-spin text-muted-foreground" />
            </div>
          )}

          {posts !== null && posts.length === 0 && (
            <div className="mt-6 flex flex-col items-center rounded-xl border border-dashed border-border py-16 text-center">
              <Store className="mb-3 size-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">暂无符合条件的帖子。</p>
            </div>
          )}

          {posts && posts.length > 0 && (
            <div className="mt-4 grid gap-3">
              {posts.map((p) => (
                <PostCard
                  key={p.post_id}
                  post={p}
                  isAdmin={isAdmin}
                  onChanged={() => {
                    void loadPosts();
                    void loadDeals();
                  }}
                />
              ))}
            </div>
          )}
        </>
      ) : (
        <ResponseList
          myResponses={myResponses}
          incoming={incoming}
          onConfirmed={() => {
            void loadDeals();
          }}
        />
      )}
    </div>
  );
}
