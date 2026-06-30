"use client";

import * as React from "react";
import Link from "next/link";
import { Loader2, Star } from "lucide-react";

import { useAuth } from "@/components/auth-provider";
import { ApiError, siteApi } from "@/lib/api";
import { getToken } from "@/lib/auth";

type SubmitState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "success" }
  | { status: "error"; message: string };

export function ReviewForm({ slug }: { slug: string }) {
  const { user, loading: authLoading } = useAuth();
  const [apiKey, setApiKey] = React.useState("");
  const [rating, setRating] = React.useState(5);
  const [content, setContent] = React.useState("");
  const [state, setState] = React.useState<SubmitState>({ status: "idle" });

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = getToken();
    if (!token) {
      setState({ status: "error", message: "请先登录后再提交评价" });
      return;
    }

    const trimmedKey = apiKey.trim();
    if (trimmedKey.length < 8) {
      setState({ status: "error", message: "请输入该站点可用的 API key" });
      return;
    }

    setState({ status: "submitting" });
    try {
      await siteApi.createReview(
        slug,
        { api_key: trimmedKey, rating, content: content.trim() || undefined },
        token,
      );
      setApiKey("");
      setContent("");
      setState({ status: "success" });
    } catch (err) {
      setState({
        status: "error",
        message: err instanceof ApiError ? err.message : "评价提交失败",
      });
    }
  }

  if (authLoading) {
    return (
      <div className="mt-4 flex items-center justify-center rounded-xl border border-border bg-card py-6 text-muted-foreground">
        <Loader2 className="size-5 animate-spin" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="mt-4 rounded-xl border border-dashed border-border bg-card px-4 py-5 text-sm text-muted-foreground">
        登录后可用你在该站的 key 验证充值/用量，并提交已验证评价。
        <Link href="/login" className="ml-2 font-medium text-primary hover:underline">
          登录 / 注册
        </Link>
      </div>
    );
  }

  if (state.status === "success") {
    return (
      <div className="mt-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-4 text-sm text-emerald-700 dark:text-emerald-300">
        评价已提交并验证通过。刷新页面后会出现在已验证评价列表。
      </div>
    );
  }

  const submitting = state.status === "submitting";

  return (
    <form onSubmit={onSubmit} className="mt-4 rounded-xl border border-border bg-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium">提交充值用户评价</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            key 只用于本次后端验证，不会保存或展示。
          </p>
        </div>
        <div className="flex items-center gap-1" aria-label={String(rating) + " 星"}>
          {Array.from({ length: 5 }, (_, index) => {
            const value = index + 1;
            return (
              <button
                key={value}
                type="button"
                onClick={() => setRating(value)}
                className="rounded-md p-1 text-muted-foreground transition-colors hover:text-primary"
                aria-label={String(value) + " 星"}
              >
                <Star
                  className={
                    value <= rating
                      ? "size-5 fill-primary text-primary"
                      : "size-5 text-muted-foreground/35"
                  }
                />
              </button>
            );
          })}
        </div>
      </div>

      <label className="mt-4 block text-xs font-medium text-muted-foreground" htmlFor="review-api-key">
        该站点 API key
      </label>
      <input
        id="review-api-key"
        value={apiKey}
        onChange={(event) => setApiKey(event.target.value)}
        type="password"
        autoComplete="off"
        placeholder="sk-..."
        className="mt-1 h-10 w-full rounded-lg border border-input bg-background px-3 text-sm outline-none transition-colors focus:border-primary"
      />

      <label className="mt-3 block text-xs font-medium text-muted-foreground" htmlFor="review-content">
        文字评价
      </label>
      <textarea
        id="review-content"
        value={content}
        onChange={(event) => setContent(event.target.value)}
        maxLength={1000}
        rows={3}
        placeholder="可选，写下实际使用体验"
        className="mt-1 w-full resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none transition-colors focus:border-primary"
      />

      {state.status === "error" && <p className="mt-3 text-sm text-destructive">{state.message}</p>}

      <div className="mt-4 flex justify-end">
        <button
          type="submit"
          disabled={submitting}
          className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting && <Loader2 className="size-4 animate-spin" />}
          提交评价
        </button>
      </div>
    </form>
  );
}
