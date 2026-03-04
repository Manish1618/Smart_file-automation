"""
ASCII Tree Proposal Renderer for the Agentic File Architect v3.0.

Renders the file organization proposal as a box-drawn ASCII layout
with MOVE, DELETE, and SKIP sections — confidence indicators,
FROM → TO paths, file sizes, and reasoning.

Rules enforced: COMM-01 through COMM-10.
"""

from __future__ import annotations

from models.file_entry import ActionType, Manifest

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False


def _c(text: str, color: str = "") -> str:
    """Apply color if colorama is available."""
    if not HAS_COLOR or not color:
        return text
    return f"{color}{text}{Style.RESET_ALL}"


def _confidence_indicator(confidence: float) -> str:
    """Return confidence emoji indicator (COMM-04)."""
    if confidence >= 0.85:
        return "✅"
    elif confidence >= 0.60:
        return "⚠️"
    return "⏭️"


def _format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024**3):.1f} GB"
    elif size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024**2):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def render_proposal(manifest: Manifest) -> None:
    """Render the full proposal to stdout.

    Displays MOVE, DELETE, and SKIP sections with confidence
    indicators, paths, reasoning, and a summary.

    Args:
        manifest: Complete Manifest with proposed actions.
    """
    moves = manifest.moves
    deletes = manifest.deletes
    skips = manifest.skips
    archives = manifest.archives

    total_freed = sum(a.file.size_bytes for a in deletes)
    total_moved_size = sum(a.file.size_bytes for a in moves)

    # ─── Header ─────────────────────────────────────────────
    print("╔" + "═" * 60 + "╗")
    print("║" + "  📊 FILE ARCHITECT PROPOSAL".center(60) + "║")
    print("╠" + "═" * 60 + "╣")
    print()

    # ─── MOVE Operations ────────────────────────────────────
    if moves:
        print(f"  🔄 MOVE OPERATIONS ({len(moves)} files)")
        print("  " + "─" * 57)
        for i, action in enumerate(moves, 1):
            indicator = _confidence_indicator(action.confidence)
            low_conf = " ⚠️ LOW CONFIDENCE" if action.confidence < 0.85 else ""
            print(f"  {indicator} [{action.confidence:.2f}] {action.file.path.name}{low_conf}")
            print(f"     FROM  {action.file.path.parent}")
            print(f"     TO    {action.destination}")
            print(f"     WHY   {action.reasoning}")
            if i < len(moves):
                print()

    # ─── DELETE Operations ──────────────────────────────────
    if deletes:
        print()
        print(f"  🗑️ DELETE OPERATIONS ({len(deletes)} items — {_format_size(total_freed)} freed)")
        print("  " + "─" * 57)
        for i, action in enumerate(deletes, 1):
            size = _format_size(action.file.size_bytes)
            print(f"  🗑️ [{action.confidence:.2f}] {action.file.path.name} ({size})")
            print(f"     PATH  {action.file.path}")
            print(f"     WHY   {action.reasoning}")
            if i < len(deletes):
                print()

    # ─── ARCHIVE Suggestions ───────────────────────────────
    if archives:
        print()
        print(f"  📦 ARCHIVE SUGGESTIONS ({len(archives)} files)")
        print("  " + "─" * 57)
        for i, action in enumerate(archives, 1):
            size = _format_size(action.file.size_bytes)
            print(f"  📦 [{action.confidence:.2f}] {action.file.path.name} ({size})")
            print(f"     PATH  {action.file.path}")
            print(f"     WHY   {action.reasoning}")
            if i < len(archives):
                print()

    # ─── SKIPPED Files ──────────────────────────────────────
    if skips:
        print()
        print(f"  ⏭️ SKIPPED ({len(skips)} files — below confidence threshold)")
        print("  " + "─" * 57)

    # ─── Summary ────────────────────────────────────────────
    print()
    print("╠" + "═" * 60 + "╣")
    parts = []
    if moves:
        parts.append(f"{len(moves)} moves")
    if deletes:
        parts.append(f"{len(deletes)} deletes")
    if archives:
        parts.append(f"{len(archives)} archives")
    if total_freed:
        parts.append(f"{_format_size(total_freed)} freed")
    if skips:
        parts.append(f"{len(skips)} skipped")
    summary = " | ".join(parts) if parts else "No actions proposed"
    print("║" + f"  SUMMARY: {summary}".ljust(60) + "║")
    print("╠" + "═" * 60 + "╣")
    print("║" + "  [Y] Approve  [N] Reject  [M] Modify  [E] Export".ljust(60) + "║")
    print("╚" + "═" * 60 + "╝")


def render_usage_brain_report(
    delete_recs: list,
    archive_recs: list,
    keep_count: int,
) -> None:
    """Render the Usage Brain analysis report.

    USAGE-10: Dedicated section for usage brain results.

    Args:
        delete_recs: List of UsageReport with recommendation=DELETE.
        archive_recs: List of UsageReport with recommendation=ARCHIVE.
        keep_count: Number of files recommended to keep.
    """
    total_del_size = sum(r.size_bytes for r in delete_recs)
    total_arc_size = sum(r.size_bytes for r in archive_recs)

    print("╔" + "═" * 62 + "╗")
    print("║" + "  🧠 SMART USAGE BRAIN — ANALYSIS RESULTS".center(62) + "║")
    print("╠" + "═" * 62 + "╣")
    print()

    # Delete recommendations
    if delete_recs:
        print(f"  🗑️ RECOMMENDED FOR DELETION ({len(delete_recs)} files — {_format_size(total_del_size)})")
        print("  " + "─" * 59)
        for r in delete_recs[:15]:  # Show top 15
            size = _format_size(r.size_bytes)
            print(f"  🗑️ [{r.staleness_score:.2f}] {r.path.name} ({size})")
            print(f"     PATH  {r.path}")
            print(f"     WHY   {r.reasoning}")
            print()

    # Archive suggestions
    if archive_recs:
        print(f"  📦 CONSIDER ARCHIVING ({len(archive_recs)} files — {_format_size(total_arc_size)})")
        print("  " + "─" * 59)
        for r in archive_recs[:10]:  # Show top 10
            size = _format_size(r.size_bytes)
            print(f"  📦 [{r.staleness_score:.2f}] {r.path.name} ({size})")
            print(f"     PATH  {r.path}")
            print(f"     WHY   {r.reasoning}")
            print()

    # Keep summary
    print(f"  ✅ KEPT ({keep_count} files — recently used or actively referenced)")
    print("  " + "─" * 59)

    # Footer
    total_freed = _format_size(total_del_size + total_arc_size)
    print()
    print("╠" + "═" * 62 + "╣")
    summary = f"  {len(delete_recs)} delete | {len(archive_recs)} archive | {keep_count} keep | {total_freed} reclaimable"
    print("║" + summary.ljust(62) + "║")
    print("╠" + "═" * 62 + "╣")
    print("║" + "  [Y] Approve  [N] Reject  [M] Modify  [E] Export".ljust(62) + "║")
    print("╚" + "═" * 62 + "╝")
