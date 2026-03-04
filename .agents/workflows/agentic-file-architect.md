---
description: How to run the Agentic File Architect — the full scan, classify, propose, approve, execute pipeline
---

# Agentic File Architect — Complete Workflow

This workflow describes the end-to-end process for running the Agentic File Architect file organization agent.

---

## Prerequisites

1. **Python 3.11+** must be installed.
2. Install dependencies:
   ```bash
   pip install pyyaml python-magic-bin colorama
   ```
3. Ensure `config.yaml` exists in the project root (optional — built-in defaults are used if missing).
4. (Optional) Set `OPENAI_API_KEY` environment variable for LLM-powered classification:
   ```bash
   set OPENAI_API_KEY=sk-your-key-here
   ```

---

## Phase 1 — Discovery Scan (`WF-1.3`)

// turbo
1. Run a scan-only pass to see what files the agent detects (no actions taken):
   ```bash
   python main.py --scan-only
   ```
   - Agent scans `Desktop`, `Downloads`, and any `extra_paths` from `config.yaml`.
   - Respects `max_depth` (default: 3 levels).
   - Skips hidden directories (`.git`, `.vscode`, etc.).
   - Skips files in immutable exclusion zones (`C:\Windows`, `C:\Program Files`, etc.).
   - Output: list of discovered files with paths and sizes.

---

## Phase 2 — Classify & Propose (`WF-1.4` – `WF-1.7`)

// turbo
2. Run a dry-run to see the full proposal without executing anything:
   ```bash
   python main.py --dry-run
   ```
   - Every file is classified via the Reasoning Engine (LLM if available, heuristic fallback otherwise).
   - Each classification includes: `category`, `confidence` (0.0–1.0), and `reasoning`.
   - Actions assigned per confidence thresholds:
     - `≥ 0.85` → ✅ Propose `MOVE`
     - `0.60 – 0.84` → ⚠️ Propose `MOVE` with LOW CONFIDENCE flag
     - `< 0.60` → ⏭️ `SKIP` (manual review)
     - Cache/artifact patterns → 🗑️ Propose `DELETE`
   - Visual proposal rendered (ASCII tree by default, or Mermaid.js with `--output mermaid`).

// turbo
3. (Optional) Generate a Mermaid.js visual diagram:
   ```bash
   python main.py --dry-run --output mermaid > proposal.md
   ```

---

## Phase 3 — Approval Gate (`WF-1.8`)

4. Run the full interactive workflow:
   ```bash
   python main.py
   ```
   - After rendering the proposal, the agent **halts** and waits for your input.
   - Valid inputs:
     - **`Y`** — Approve all proposed actions
     - **`N`** — Reject all — no files are touched
     - **`M`** — Modify — review and approve/reject each action individually
     - **`E`** — Export manifest to `manifest_export.json` (no execution)
   - ⚠️ **The agent NEVER auto-approves.** It will wait indefinitely for your input.

---

## Phase 4 — Execution (`WF-1.9`)

5. After approval, the agent executes all approved operations:
   - `MOVE` operations use `shutil.move()` (cross-volume safe).
   - `DELETE` operations use `shutil.rmtree()` (directories) or `Path.unlink()` (files).
   - Filename collisions → numeric suffix appended (`main_1.cpp`, `main_2.cpp`).
   - Locked files → skipped with warning.
   - Each operation logged to `logs/operations.jsonl` in real-time.

---

## Phase 5 — Report & Log (`WF-1.10`)

6. After execution, the agent prints a summary:
   ```
   ✅ Success: N
   ❌ Failed:  N
   ⏭️  Skipped: N
   📋 Full log: logs/operations.jsonl
   ```

---

## Rollback

7. To undo a previous session's operations:
   ```bash
   python main.py --rollback --session <session_id>
   ```
   - Reads `logs/operations.jsonl` and proposes reversing all `MOVE` operations from that session.
   - `DELETE` operations **cannot** be rolled back (a warning is displayed).
   - Rollback follows the same Approval Gate before executing.

---

## Safety Checklist (Non-Negotiable)

Before every run, these rules are enforced automatically:

- [ ] Immutable zones loaded (`C:\Windows`, `C:\Program Files`, `C:\ProgramData`, `C:\Recovery`, `C:\Boot`, `C:\EFI`)
- [ ] Protected patterns active (`.git`, `.ssh`, `.env`, `.pem`, `.key`, `.kdbx`, `.wallet`)
- [ ] No elevation/admin requested
- [ ] All actions visible in proposal before approval
- [ ] Approval Gate blocks execution until user confirms
- [ ] Every operation logged to JSONL for audit trail

---

## Configuration Reference

Edit `config.yaml` to customize:

| Setting | Default | Description |
|---|---|---|
| `max_depth` | `3` | Max directory scan depth |
| `workspace_root` | `C:\Workspace` | Where organized files are moved to |
| `extra_paths` | `[]` | Additional directories to scan |
| `llm.provider` | `none` | LLM provider: `openai`, `anthropic`, `ollama`, `none` |
| `cleanup.delete_compiler_artifacts` | `true` | Auto-detect C++/Rust build artifacts |
| `cleanup.delete_python_cache` | `true` | Auto-detect `__pycache__/` directories |
| `cleanup.delete_node_modules_orphaned` | `true` | Detect orphaned `node_modules/` |
| `output_format` | `ascii` | Proposal format: `ascii`, `mermaid`, `html`, `json` |

---

## Quick Commands

| Command | Description |
|---|---|
| `python main.py --scan-only` | See what files the agent finds (no actions) |
| `python main.py --dry-run` | See the full proposal (no execution) |
| `python main.py` | Full interactive workflow with approval gate |
| `python main.py --dry-run --output mermaid > proposal.md` | Export Mermaid.js diagram |
| `python main.py --rollback --session <id>` | Undo a previous session |
| `python main.py --reset-trust` | Clear learned approval patterns |
