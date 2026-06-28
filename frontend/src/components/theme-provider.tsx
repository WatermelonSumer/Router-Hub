"use client";

import * as React from "react";
import { ThemeProvider as NextThemesProvider } from "next-themes";

/** 全局主题提供器：默认跟随系统，用户切换后由 next-themes 写入 localStorage 记忆。 */
export function ThemeProvider({
  children,
  ...props
}: React.ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
