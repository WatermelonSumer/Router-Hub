# Changelog

## 2026-06-29

- 搭建前端骨架 frontend/：Next.js 16 + React 19 + Tailwind v4 + shadcn/ui + motion + next-themes。
- 双主题基建(全套语义 token + ThemeProvider/ThemeToggle)、shadcn 基础组件、登录页 /login(玻璃拟态/赛博风,角色切换)。
- 因网络限制改用：手动搭 shadcn(CLI 连不上 ui.shadcn.com)、自托管 geist 字体包(next/font/google 拉不到)。
- 完善 .pre-commit-config.yaml(rev 对齐 ruff 0.8.6、排除 migrations、补 check-toml 等)。

## 2026-06-28

- 搭建后端骨架 backend/：core 配置层、8 张表 Tortoise 模型（双键制/虚拟外键/软删除/uuid7）、
  health 路由、APScheduler 探测调度骨架（探测函数为桩）、pytest（sqlite 内存库）。
- 新增工程配置：backend/pyproject.toml(Poetry+aerich+ruff)、.env.example、backend/README.md。
- 根级：.gitattributes(统一 LF)、更新 .gitignore(Python)、.pre-commit-config.yaml(ruff)。
- frontend/ 占位 README；建立 proj-memory/（README/progress/decisions/todo/changelog）。
