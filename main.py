#!/usr/bin/env python3
"""
Agentic File Architect v3.0
Intelligent, Local-First File Organization & System Optimization for Windows

Usage:
    python main.py                     # Interactive mode (scans configured paths)
    python main.py --full-drive        # Scan entire C:\\ and D:\\ drives
    python main.py --analyze-usage     # Run Smart Usage Brain analysis
    python main.py --scan-only         # Discovery mode (no proposals)
    python main.py --dry-run           # Generate proposal without execution
    python main.py --output mermaid    # Output as Mermaid.js diagram
    python main.py --rollback --session <id>  # Undo a previous session
    python main.py --reset-trust       # Clear learned approval patterns
"""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path

from core.scanner import ScanEngine
from core.drive_scanner import DriveScanner
from core.reasoning import ReasoningEngine
from core.safety import SafetyGuard
from core.planner import ActionPlanner
from core.executor import ExecutionEngine
from cleanup.detector import CleanupDetector
from intelligence.usage_brain import UsageBrain
from visualization.ascii_tree import render_proposal, render_usage_brain_report
from visualization.mermaid_builder import generate_mermaid


# ─── Banner ─────────────────────────────────────────────────────

BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║       ⚙️  AGENTIC FILE ARCHITECT v3.0                         ║
║       Intelligent, Local-First File Organization              ║
║       & System Optimization for Windows                       ║
║                                                               ║
║       Scan Drives → Analyze Usage → Clean & Organize          ║
║       Your files. Your rules. Zero surprises.                 ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""


# ─── Entry Point ────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Agentic File Architect v3.0 — Intelligent File Organization"
    )
    parser.add_argument('--config', type=str, default='config.yaml',
                        help='Path to configuration file')
    parser.add_argument('--scan-only', action='store_true',
                        help='Discovery mode — see what files the agent finds')
    parser.add_argument('--dry-run', action='store_true',
                        help='Generate proposal without execution')
    parser.add_argument('--full-drive', action='store_true',
                        help='Scan entire C:\\ and D:\\ drives')
    parser.add_argument('--analyze-usage', action='store_true',
                        help='Run Smart Usage Brain analysis')
    parser.add_argument('--output', choices=['ascii', 'mermaid', 'html', 'json'],
                        default='ascii', help='Output format for proposals')
    parser.add_argument('--rollback', action='store_true',
                        help='Undo a previous session')
    parser.add_argument('--session', type=str,
                        help='Session ID for rollback')
    parser.add_argument('--reset-trust', action='store_true',
                        help='Clear learned approval patterns')
    args = parser.parse_args()

    # ── Banner ──────────────────────────────────────────────
    print(BANNER)

    # ── WF-1.1: Initialize ──────────────────────────────────
    config = load_config(args.config)
    session_id = uuid.uuid4().hex[:8]

    # ── WF-1.2: Load Safety Rules ───────────────────────────
    additional_exclusions = config.get("additional_exclusions", [])
    guard = SafetyGuard(additional_exclusions=additional_exclusions)
    print("  🛡️  Safety rules loaded.")
    print(f"     Immutable zones: {len(guard.IMMUTABLE_ZONES)}")
    print(f"     Protected patterns: {len(guard.PROTECTED_PATTERNS)}")
    if additional_exclusions:
        print(f"     Additional exclusions: {len(additional_exclusions)}")

    # ── INIT-05: Detect OneDrive ────────────────────────────
    onedrive_path = Path.home() / "OneDrive"
    if onedrive_path.exists():
        print(f"     📁 OneDrive detected: {onedrive_path}")

    # ── Reset Trust Command ─────────────────────────────────
    if args.reset_trust:
        trust_path = Path("config/trust_scores.json")
        if trust_path.exists():
            trust_path.unlink()
            print("\n  ✅ Trust scores reset successfully.")
        else:
            print("\n  ⏭️  No trust scores file found.")
        return

    # ── Rollback Mode ───────────────────────────────────────
    if args.rollback:
        _handle_rollback(args, config, guard)
        return

    # ── Smart Usage Brain Mode ──────────────────────────────
    if args.analyze_usage:
        _handle_usage_analysis(config, guard, args)
        return

    # ── Main Workflow: Phase 1–3 ────────────────────────────
    _handle_main_workflow(args, config, guard, session_id)


# ─── Mode Handlers ──────────────────────────────────────────────


def _handle_usage_analysis(config: dict, guard: SafetyGuard, args) -> None:
    """Handle --analyze-usage mode."""
    print("\n🧠 Smart Usage Brain — Analyzing document usage patterns...")
    brain = UsageBrain(config.get("usage_brain", {}))
    scan_dirs = _get_scan_directories(config, args.full_drive)

    all_reports = []
    for directory in scan_dirs:
        if directory.exists() and guard.is_safe(directory):
            print(f"  🔍 Analyzing: {directory}")
            reports = brain.analyze_directory(directory)
            all_reports.extend(reports)

    # Categorize results
    delete_recs = [r for r in all_reports if r.recommendation == "DELETE"]
    archive_recs = [r for r in all_reports if r.recommendation == "ARCHIVE"]
    keep_recs = [r for r in all_reports if r.recommendation == "KEEP"]

    if not delete_recs and not archive_recs:
        print("\n  ✅ All documents are actively used — no recommendations.")
        return

    # USAGE-10: Render dedicated section
    render_usage_brain_report(delete_recs, archive_recs, len(keep_recs))

    # Approval gate for deletions
    if delete_recs:
        choice = input("\n  Approve deletions? [Y/N/M] → ").strip().upper()
        if choice == 'Y':
            executor = ExecutionEngine(log_path=Path("logs/operations.jsonl"))
            actions = brain.reports_to_actions(
                [r for r in all_reports if r.recommendation == "DELETE"]
            )
            print(f"\n  ⚡ Executing {len(actions)} approved deletions...")
            results = executor.execute(actions)
            print(f"\n  ✅ Success: {len(results['success'])}")
            print(f"  ❌ Failed:  {len(results['failed'])}")
            print(f"\n  📋 Full log: logs/operations.jsonl")
        elif choice == 'M':
            # Interactive modify
            actions = brain.reports_to_actions(
                [r for r in all_reports if r.recommendation == "DELETE"]
            )
            approved = _interactive_modify_actions(actions)
            if approved:
                executor = ExecutionEngine(log_path=Path("logs/operations.jsonl"))
                results = executor.execute(approved, approval_mode="M")
                print(f"\n  ✅ Success: {len(results['success'])}")
                print(f"  ❌ Failed:  {len(results['failed'])}")
                print(f"\n  📋 Full log: logs/operations.jsonl")
        else:
            print("\n  ❌ All deletions rejected.")


def _handle_rollback(args, config: dict, guard: SafetyGuard) -> None:
    """Handle --rollback mode."""
    if not args.session:
        print("\n  ⚠️  Please provide a session ID: --rollback --session <id>")
        return

    executor = ExecutionEngine(
        log_path=Path("logs/operations.jsonl"),
        session_id=f"rollback_{args.session}",
    )

    proposals = executor.rollback_session(args.session)
    if not proposals:
        print(f"\n  ⏭️  No operations found for session '{args.session}'.")
        return

    print(f"\n  🔄 Rollback Proposal for session: {args.session}")
    print("  " + "─" * 50)

    reversible = [p for p in proposals if p["type"] == "ROLLBACK_MOVE"]
    irreversible = [p for p in proposals if p["type"] == "CANNOT_ROLLBACK"]

    for p in reversible:
        print(f"  🔄 {Path(p['current_path']).name}")
        print(f"     FROM  {p['current_path']}")
        print(f"     TO    {p['original_path']}")
        print()

    for p in irreversible:
        print(f"  ⚠️  {Path(p['original_path']).name}")
        print(f"     {p['reason']}")
        print()

    if reversible:
        choice = input("  Approve rollback? [Y/N] → ").strip().upper()
        if choice == 'Y':
            print("  ⚡ Executing rollback...")
            for p in reversible:
                try:
                    import shutil
                    src = Path(p["current_path"])
                    dst = Path(p["original_path"])
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dst))
                    print(f"  ✅ {dst.name}")
                except Exception as e:
                    print(f"  ❌ {Path(p['current_path']).name}: {e}")
            print(f"\n  📋 Full log: logs/operations.jsonl")


def _handle_main_workflow(
    args,
    config: dict,
    guard: SafetyGuard,
    session_id: str,
) -> None:
    """Handle the main scan → classify → propose → execute workflow."""

    # ── Phase 1: Discovery ──────────────────────────────────
    print("\n🔍 Phase 1: Scanning directories...")
    scan_targets = _get_scan_directories(config, args.full_drive)

    if args.full_drive:
        print("  💿 FULL DRIVE MODE — Scanning C:\\ and D:\\ drives")
        drive_scanner = DriveScanner(guard)
        drives = config.get("drive_scan", {}).get("drives", ["C:\\", "D:\\"])
        entries = drive_scanner.scan_drives(drives, config)
    else:
        scanner = ScanEngine(config)
        entries = scanner.scan(scan_targets, safety_guard=guard)

    print(f"\n   📦 Found {len(entries)} files across {len(scan_targets)} directories.")

    if args.scan_only:
        print("\n  [SCAN ONLY MODE] Listing discovered files:\n")
        for e in entries:
            size_kb = e.size_bytes / 1024
            print(f"   {e.path} ({size_kb:.1f} KB)")
        print(f"\n  📋 Total: {len(entries)} files")
        return

    # ── Safety Filtering ────────────────────────────────────
    safe_entries = [e for e in entries if guard.is_safe(e.path)]
    blocked = len(entries) - len(safe_entries)
    if blocked:
        print(f"   🛡️  {blocked} files in protected zones — excluded.")

    # ── Phase 2: Reasoning & Planning ───────────────────────
    print("\n🧠 Phase 2: Classifying files...")
    workspace_root = config.get("workspace_root", "C:\\Workspace")
    engine = ReasoningEngine(
        workspace_root=workspace_root,
    )
    planner = ActionPlanner(engine, config)
    manifest = planner.generate_manifest(safe_entries)
    manifest.session_id = session_id

    # ── Cleanup Detection ───────────────────────────────────
    print("  🧹 Detecting cleanup targets...")
    cleanup_config = config.get("cleanup", {})
    cleanup = CleanupDetector(cleanup_config)
    cleanup_actions = cleanup.scan(scan_targets)
    manifest.actions.extend(cleanup_actions)
    if cleanup_actions:
        print(f"     Found {len(cleanup_actions)} cleanup targets.")

    # ── Usage Brain Integration ─────────────────────────────
    usage_config = config.get("usage_brain", {})
    if usage_config.get("enabled", True):
        print("  🧠 Running Smart Usage Brain analysis...")
        brain = UsageBrain(usage_config)
        for directory in scan_targets:
            if directory.exists():
                usage_reports = brain.analyze_directory(directory)
                stale_actions = brain.reports_to_actions(usage_reports)
                manifest.actions.extend(stale_actions)
        stale_count = len([a for a in manifest.actions if "UsageBrain" in str(a.category)])
        if stale_count:
            print(f"     Found {stale_count} stale document recommendations.")

    # Recalculate total freed
    from models.file_entry import ActionType
    manifest.total_size_freed = sum(
        a.file.size_bytes for a in manifest.actions
        if a.action == ActionType.DELETE
    )

    # ── Visual Proposal (COMM-02) ───────────────────────────
    print(f"\n📊 Phase 2: Generating proposal...\n")
    if args.output == 'mermaid':
        print(generate_mermaid(manifest))
    elif args.output == 'json':
        export_path = Path("manifest_export.json")
        planner.export_manifest(manifest, export_path)
        print(f"  📄 Manifest exported to {export_path}")
        return
    else:
        render_proposal(manifest)

    if args.dry_run:
        print("\n  [DRY RUN] No actions executed.")
        return

    # Check if there's anything to do
    actionable = [
        a for a in manifest.actions
        if a.action in (ActionType.MOVE, ActionType.DELETE)
    ]
    if not actionable:
        print("\n  ⏭️  No actionable proposals. All files are already organized.")
        return

    # ── Phase 3: Approval Gate (WF-1.8) ─────────────────────
    print()
    choice = _get_approval()

    if choice == 'N':
        # GATE-07: Clean exit
        print("\n  ❌ All actions rejected. No files were modified.")
        manifest.approval_mode = 'N'
        return
    elif choice == 'E':
        # GATE-06: Export manifest
        export_path = Path("manifest_export.json")
        planner.export_manifest(manifest, export_path)
        print(f"\n  📄 Manifest exported to {export_path}")
        manifest.approval_mode = 'E'
        return
    elif choice == 'M':
        # GATE-04: Interactive modify
        manifest.approval_mode = 'M'
        manifest.actions = _interactive_modify_actions(manifest.actions)
    else:
        manifest.approval_mode = 'Y'

    # ── Execution (WF-1.9) ──────────────────────────────────
    safe_actions, blocked_actions = guard.validate_manifest(manifest)

    if blocked_actions:
        print(f"\n  🛡️  {len(blocked_actions)} actions blocked by safety rules.")

    executor = ExecutionEngine(
        log_path=Path("logs/operations.jsonl"),
        session_id=session_id,
    )

    print(f"\n⚡ Executing {len(safe_actions)} approved actions...")
    results = executor.execute(safe_actions, approval_mode=choice)

    # ── Report (WF-1.10) ────────────────────────────────────
    print(f"\n  ✅ Success: {len(results['success'])}")
    print(f"  ❌ Failed:  {len(results['failed'])}")
    print(f"  ⏭️  Skipped: {len(results['skipped'])}")
    print(f"\n  🏷️  Session ID: {session_id}")
    print(f"  📋 Full log: logs/operations.jsonl")


# ─── Helpers ────────────────────────────────────────────────────

def _get_scan_directories(config: dict, full_drive: bool) -> list[Path]:
    """Determine scan targets based on mode."""
    user_home = Path.home()

    if full_drive:
        return [Path("C:\\"), Path("D:\\")]

    return [
        user_home / "Desktop",
        user_home / "Downloads",
        user_home / "Documents",
        *[Path(p) for p in config.get("extra_paths", [])],
    ]


def _get_approval() -> str:
    """Get user approval with input validation (GATE-03)."""
    valid = {'Y', 'N', 'M', 'E'}
    while True:
        choice = input(
            "  [Y] Approve  [N] Reject  [M] Modify  [E] Export → "
        ).strip().upper()
        if choice in valid:
            return choice
        print("  ⚠️  Invalid input. Please enter Y, N, M, or E.")


def _interactive_modify_actions(actions: list) -> list:
    """Allow user to approve/reject individual actions (GATE-04)."""
    from models.file_entry import ActionType

    approved = []
    actionable = [
        a for a in actions
        if a.action in (ActionType.MOVE, ActionType.DELETE, ActionType.ARCHIVE)
    ]

    for i, action in enumerate(actionable):
        symbol = "🔄" if action.action == ActionType.MOVE else "🗑️"
        if action.action == ActionType.ARCHIVE:
            symbol = "📦"

        print(f"\n  {symbol} [{i+1}/{len(actionable)}] {action.file.path.name}")
        dest_str = str(action.destination) if action.destination else action.action.value
        print(f"     {action.action.value} → {dest_str}")
        print(f"     Confidence: {action.confidence:.2f} | {action.reasoning}")

        choice = input("     [Y] Approve / [N] Skip → ").strip().upper()
        if choice == 'Y':
            approved.append(action)

    return approved


def load_config(path: str) -> dict:
    """Load configuration from YAML file with fallback defaults (INIT-04)."""
    config_path = Path(path)
    if config_path.exists():
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded = yaml.safe_load(f) or {}
            print(f"  ⚙️  Configuration loaded from: {config_path}")
            return loaded
        except ImportError:
            print("  ⚠️  PyYAML not installed — using built-in defaults.")
        except Exception as e:
            print(f"  ⚠️  Error loading config: {e} — using built-in defaults.")
    else:
        print(f"  ⚙️  No config file found at '{config_path}' — using built-in defaults.")

    # Built-in defaults
    return {
        "max_depth": 3,
        "min_file_size": 0,
        "max_file_size": 10 * 1024**3,
        "extra_paths": [],
        "workspace_root": "C:\\Workspace",
        "classifier": {"mode": "local"},
        "cleanup": {
            "delete_compiler_artifacts": True,
            "delete_python_cache": True,
            "delete_node_modules_orphaned": True,
            "delete_logs_older_than_days": 30,
            "delete_logs_larger_than_mb": 50,
        },
        "usage_brain": {"enabled": True},
        "output_format": "ascii",
    }


if __name__ == "__main__":
    main()
