# Contributing Guide

> Read this before pushing any code. Main branch is protected — direct pushes will be rejected.

---

## The Golden Rule

**Never push directly to `main`.** Always work on your own branch and open a Pull Request.

---

## Step-by-Step: How to Push Your Work

### 1. Get the latest code
```bash
git checkout main
git pull origin main
```

### 2. Create your own branch
Name it after what you are working on:
```bash
git checkout -b your-name/what-you-did
# examples:
# git checkout -b ridho/kafka-consumer
# git checkout -b jiho/api-endpoint
# git checkout -b afif/model-test
```

### 3. Make your changes, then stage and commit
```bash
git add .
git commit -m "short description of what you did"
```

### 4. Push your branch to GitHub
```bash
git push origin your-name/what-you-did
```

### 5. Open a Pull Request
After pushing, GitHub will print a link in the terminal. Open it and click **Create Pull Request**.

Or go to: https://github.com/rzrizaldy/fundamental_ai_crypto_volatile/pulls → **New pull request**

---

## If You Use an AI Agent (Claude / Codex / etc.)

When you ask the agent to write or change code, tell it at the end:

> "Push this to a new branch called `your-name/feature-name` and open a pull request."

The agent will:
1. Create a branch
2. Commit the changes
3. Push to GitHub
4. Open a PR for review

**Do not tell the agent to push to `main` directly** — it will be blocked anyway.

Example prompt for the agent:
```
Fix the bug in service/replay_api.py where the threshold is hardcoded.
When done, push to a new branch called ridho/fix-threshold and open a PR.
```

---

## Branch Naming Convention

| Who | Format | Example |
|-----|--------|---------|
| Rizaldy | `rizaldy/<topic>` | `rizaldy/model-retrain` |
| Ridho | `ridho/<topic>` | `ridho/kafka-fix` |
| Jiho | `jiho/<topic>` | `jiho/api-docs` |
| Afif | `afif/<topic>` | `afif/test-coverage` |

---

## PR Rules

- At least **1 approval** is required before merging
- The reviewer will be Rizaldy (repo owner) unless agreed otherwise
- Keep PRs small — one feature or fix per PR is easier to review

---

## Quick Cheat Sheet

```
git checkout main              # go to main
git pull origin main           # get latest
git checkout -b name/feature   # create branch
# ... make your changes ...
git add .
git commit -m "what I did"
git push origin name/feature   # push branch
# open PR on GitHub
```

---

## Cross-Agent Collaboration

When multiple teammates work with different agents (Claude Code, Codex, Cursor) at the same time, follow these rules to avoid stepping on each other.

### Before starting any work

Always give your agent the latest context:

```
@CONTRIBUTING.md
@docs/team_charter.md
```

This tells the agent:
- which files belong to which person (W4 roles, W5-W7 splits)
- the branch naming convention
- what already exists so it does not rewrite someone else's work

### Claim your area before you start

Post in Google Chat what you are working on before you let your agent write code. Example:

> "taking W5 kafka reconnect, branch jiho/w5-kafka-reconnect"

This prevents two agents from editing the same file at the same time.

### If there is a merge conflict

Do not let your agent force-push or overwrite. Tell it:

> "There is a conflict in `<filename>`. Pull the latest from main, rebase my branch, and resolve the conflict by keeping both changes."

```bash
git fetch origin
git rebase origin/main
# agent resolves conflicts
git rebase --continue
git push origin your-branch --force-with-lease
```

### Recommended prompt to start any session

Paste this at the start of every agent session:

```
Read @CONTRIBUTING.md and @docs/team_charter.md first.
My name is <yourname>. I am responsible for <your area from team_charter>.
Work only in files relevant to my area. Push to branch <yourname>/<topic> and open a PR when done.
```

---

## Common Errors

| Error | Fix |
|-------|-----|
| `rejected — protected branch` | You tried to push to main. Create a branch first. |
| `failed to push — tip behind` | Run `git pull origin main` then push again. |
| `nothing to commit` | You forgot to `git add .` before committing. |
