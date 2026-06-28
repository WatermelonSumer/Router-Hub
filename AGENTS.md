# AGENTS.md

This file defines the rules and expectations for AI coding agents working on this repository.

All AI agents must read and follow these instructions before making changes.

## Project Overview

This is a Python project.

Unless otherwise specified, assume:

- Python is the main programming language.
- Poetry is used for dependency management.
- pre-commit is used for code quality checks.
- Git commit messages follow Conventional Commits.
- Project progress and working context are recorded in the `proj-memory/` directory.
- Backend code comments should be written in Chinese whenever practical.

## General Principles

- Follow the existing architecture, naming style, and code patterns in the repository.
- Keep changes focused on the requested task.
- Do not perform unrelated refactors.
- Do not rewrite large parts of the project unless explicitly requested.
- Prefer readable, maintainable code over clever or overly abstract solutions.
- Avoid introducing new dependencies unless they are clearly necessary.
- Explain important tradeoffs when making non-obvious implementation decisions.
- Before starting work, read the relevant files in `proj-memory/` if they exist.

## Package Management

Use Poetry for Python package and environment management.

Do not use `pip install` directly unless explicitly requested.

Common commands:

```bash
poetry install
poetry add &lt;package&gt;
poetry add --group dev &lt;package&gt;
poetry run &lt;command&gt;
```

Examples:

```bash
poetry add requests
poetry add --group dev pytest
poetry run pytest
```

## Code Style

- Write clear, idiomatic Python.
- Follow the formatting and linting tools already configured in the project.
- Keep functions and modules focused.
- Prefer explicit names over vague abbreviations.
- Add comments only when they clarify non-obvious logic.
- Do not add noisy comments that simply repeat what the code does.

## Backend Code Comments

For backend code, write comments in Chinese whenever practical.

Comment requirements:

- Use Chinese comments for important business logic, functional behavior, workflows, and non-obvious decisions.
- Prefer Chinese docstrings for modules, classes, functions, services, handlers, jobs, and public methods.
- Add functional comments for backend features so future maintainers can quickly understand what the code does and why.
- Keep comments accurate and maintain them when code changes.
- Do not write meaningless comments that only repeat the code literally.
- Do not over-comment simple, self-explanatory code.
- Technical identifiers, framework names, protocol names, exception names, and third-party API names can remain in English.

Examples:

```python
def calculate_order_total(order: Order) -> Decimal:
    """计算订单应付总金额，包含商品金额、优惠和运费。"""
    ...
```

```python
# 订单已支付时不允许重复扣款，直接返回当前支付状态。
if order.status == OrderStatus.PAID:
    return payment.status
```

## Formatting, Linting, and pre-commit

This project uses pre-commit.

Before finishing a code change, run:

```bash
poetry run pre-commit run --all-files
```

If pre-commit modifies files, review the changes and run it again.

Do not ignore failing checks unless explicitly instructed.

## Testing

If tests exist, run them before finishing:

```bash
poetry run pytest
```

Testing expectations:

- Add or update tests when behavior changes.
- For bug fixes, add regression tests when practical.
- Do not remove or weaken existing tests unless explicitly requested.
- If tests cannot be run, explain why in the final response.

## Git Commit Rules

Use Conventional Commits for commit messages.

Commit messages must use a conventional English type, but the description must be written in Chinese.

Format:

```text
&lt;type&gt;[optional scope]: &lt;中文描述&gt;
```

Examples:

```text
feat: 添加用户注册功能
fix(auth): 修复登录过期处理
docs: 更新安装说明
test: 添加用户服务测试
refactor(api): 简化响应处理逻辑
chore: 更新开发依赖
```

Allowed commit types:

- `feat`: new feature
- `fix`: bug fix
- `docs`: documentation only
- `style`: formatting only, no logic change
- `refactor`: code change that neither fixes a bug nor adds a feature
- `test`: adding or updating tests
- `chore`: maintenance tasks
- `build`: build system or dependency changes
- `ci`: continuous integration changes
- `perf`: performance improvement

Commit message rules:

- Use lowercase type names.
- Keep the description short and clear.
- Write the description in Chinese.
- Do not end the description with a period.
- Prefer concise descriptions such as `修复用户登录失败问题`, not long explanations.
- If a body is needed, write the body in Chinese as well.

## Project Memory

The AI agent must maintain a project memory directory named:

```text
proj-memory/
```

This directory is used to preserve project context between AI sessions.

Before starting a new task, the AI agent must:

- Check whether `proj-memory/` exists.
- Read relevant memory files inside `proj-memory/`.
- Use the recorded context to continue from the previous state when appropriate.

After finishing any meaningful task, the AI agent must update `proj-memory/`.

Recommended files:

```text
proj-memory/
├── README.md
├── progress.md
├── decisions.md
├── todo.md
└── changelog.md
```

### proj-memory/README.md

Purpose:

- Explain what this memory directory is for.
- Describe how future AI agents should use it.
- Provide a short project summary.

### proj-memory/progress.md

Record current project progress.

Each update should include:

```md
## YYYY-MM-DD

### Completed

- ...

### Current State

- ...

### Next Steps

- ...
```

### proj-memory/decisions.md

Record important technical decisions.

Use this format:

```md
## YYYY-MM-DD - Decision Title

### Decision

...

### Reason

...

### Impact

...
```

### proj-memory/todo.md

Record unfinished work, follow-up tasks, and known issues.

Use this format:

```md
# TODO

## High Priority

- ...

## Medium Priority

- ...

## Low Priority

- ...
```

### proj-memory/changelog.md

Record meaningful changes made by the AI agent.

Use this format:

```md
## YYYY-MM-DD

- ...
```

Project memory rules:

- Keep memory concise and useful.
- Do not paste large code blocks into memory files.
- Do not store secrets, tokens, credentials, or private data.
- Do not treat memory files as a replacement for Git history.
- Update memory only with information that helps future work.
- If no meaningful project state changed, memory updates are optional.
- If the user says "继续", "接着做", or "开始工作", first read `proj-memory/` and continue from the recorded context.

## Dependency Rules

- Prefer the Python standard library when it is sufficient.
- Add third-party dependencies only when they provide clear value.
- When adding dependencies, use Poetry.
- Keep runtime and development dependencies separated.
- Do not manually edit lock files unless necessary; use Poetry commands.

## File Editing Rules

- Do not overwrite user changes.
- Do not modify unrelated files.
- Do not reformat the entire repository unless explicitly requested.
- Keep changes small and reviewable.
- Preserve existing public APIs unless the task requires changing them.
- Avoid moving files unless there is a clear reason.

## Documentation

Update documentation when changing:

- User-facing behavior
- Public APIs
- Configuration
- CLI commands
- Setup or installation steps
- Development workflow

Keep examples accurate and runnable.

## Security

- Do not commit secrets, tokens, passwords, API keys, private keys, or credentials.
- Use environment variables or documented secret-management mechanisms.
- If a secret-like value is found, do not copy it into code or documentation.
- Avoid logging sensitive information.
- Validate and sanitize external input where appropriate.

## Error Handling

- Prefer explicit error handling over silent failures.
- Raise meaningful exceptions or return clear error results.
- Avoid swallowing exceptions without explanation.
- Keep error messages useful for debugging without exposing sensitive data.

## Final Response Requirements

When finishing a task, summarize in Chinese:

- What changed
- What checks were run
- Whether `proj-memory/` was updated
- Any known limitations, skipped checks, or follow-up work

If no files were changed, say so clearly.
