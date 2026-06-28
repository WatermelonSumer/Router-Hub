"use client";

import * as React from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";

/** 亮/暗主题切换按钮。

   挂载前不渲染图标，避免 SSR 与客户端主题不一致导致的 hydration 警告。 */
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    // 仅在客户端挂载后翻转标记，避免 SSR/CSR 主题不一致的 hydration 警告
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const isDark = resolvedTheme === "dark";

  return (
    <Button
      variant="outline"
      size="icon"
      aria-label="切换主题"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="backdrop-blur-md bg-background/40"
    >
      {mounted ? (
        isDark ? (
          <Sun className="size-4" />
        ) : (
          <Moon className="size-4" />
        )
      ) : (
        <span className="size-4" />
      )}
    </Button>
  );
}
