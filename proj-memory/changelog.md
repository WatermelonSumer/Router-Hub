# Changelog

## 2026-06-28

- 搭建后端骨架 backend/：core 配置层、8 张表 Tortoise 模型（双键制/虚拟外键/软删除/uuid7）、
  health 路由、APScheduler 探测调度骨架（探测函数为桩）、pytest（sqlite 内存库）。
- 新增工程配置：backend/pyproject.toml(Poetry+aerich+ruff)、.env.example、backend/README.md。
- 根级：.gitattributes(统一 LF)、更新 .gitignore(Python)、.pre-commit-config.yaml(ruff)。
- frontend/ 占位 README；建立 proj-memory/（README/progress/decisions/todo/changelog）。
