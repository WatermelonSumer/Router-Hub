# Router-Hub Frontend

AI 中转站 Rank 系统前端：**Next.js 16(App Router)+ TypeScript + Tailwind v4 + shadcn/ui + Framer Motion(motion)+ next-themes**。

> 设计与约定见 `../docs/dev/features.md` 第 11 节、`../docs/dev/blueprint.md` 第十二节。

## 强制约定

- **双主题(light/dark)**：所有颜色走语义 CSS 变量(`bg-background`/`text-foreground`/`primary`/`muted`/`border`…)，
  **禁止硬编码颜色**(不写 `bg-white`/`#fff`/`zinc-50`)。主题切换走 next-themes(class 策略)，默认跟随系统。
- 字体用自托管 `geist` 包(非 `next/font/google`)，避免构建时联网拉 Google Fonts 失败。
- shadcn 组件以源码形式放在 `src/components/ui/`，完全可控。

## 目录

```
src/
├── app/
│   ├── layout.tsx        # 根布局 + ThemeProvider(next-themes)
│   ├── globals.css       # Tailwind v4 + 全套语义 token(light/dark)
│   ├── page.tsx          # 首页占位
│   └── login/page.tsx    # 登录页(玻璃拟态/赛博风,角色：用户/站长)
├── components/
│   ├── ui/               # shadcn 基础组件(button/input/label/card)
│   ├── theme-provider.tsx
│   └── theme-toggle.tsx  # 亮/暗切换按钮
└── lib/utils.ts          # cn() 合并 class
```

## 开发

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000  —— 登录页在 /login
npm run build      # 生产构建(已验证可过)
npm run lint
```

## 当前进度

骨架阶段：脚手架 + 双主题基建 + shadcn 基础组件 + 登录页 UI(纯前端，未接后端鉴权)。
榜单/详情/坟场/集市等页面尚未开始。
