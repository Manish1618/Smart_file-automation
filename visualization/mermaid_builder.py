"""
Mermaid.js Diagram Generator for the Agentic File Architect v3.0.

Generates Mermaid.js topology diagrams showing current state →
proposed state transitions, styled with confidence-based colors.
"""

from __future__ import annotations

from models.file_entry import ActionType, Manifest


def _sanitize(text: str) -> str:
    """Sanitize text for Mermaid node labels."""
    return text.replace('"', "'").replace("\\", "/").replace("(", "[").replace(")", "]")


def _format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024**3):.1f}GB"
    elif size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024**2):.1f}MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f}KB"
    return f"{size_bytes}B"


def generate_mermaid(manifest: Manifest) -> str:
    """Generate a Mermaid.js topology diagram from a manifest.

    Shows Current State → Proposed State with confidence scores
    on the edges.

    Args:
        manifest: Complete Manifest with proposed actions.

    Returns:
        Mermaid.js diagram as a string.
    """
    moves = manifest.moves
    deletes = manifest.deletes

    if not moves and not deletes:
        return "```mermaid\ngraph LR\n    EMPTY[\"No actions proposed\"]\n```"

    lines = ["```mermaid", "graph LR"]

    # ─── Current State Subgraph ─────────────────────────────
    lines.append('    subgraph Current["📁 Current State"]')

    # Group files by source directory
    source_dirs: dict[str, list] = {}
    for action in moves + deletes:
        parent = str(action.file.path.parent)
        if parent not in source_dirs:
            source_dirs[parent] = []
        source_dirs[parent].append(action)

    node_id = 0
    source_nodes: dict[int, object] = {}  # node_id → action

    for dir_path, actions in source_dirs.items():
        dir_name = _sanitize(dir_path.split("\\")[-1] if "\\" in dir_path else dir_path.split("/")[-1])
        dir_node = f"D{node_id}"
        lines.append(f'        {dir_node}["{dir_name}/"]')
        node_id += 1

        for action in actions:
            fname = _sanitize(action.file.path.name)
            size = _format_size(action.file.size_bytes)
            fnode = f"F{node_id}"
            label = f"{fname}"
            if action.action == ActionType.DELETE:
                label += f" [{size}]"
            lines.append(f'        {dir_node} --> {fnode}["{label}"]')
            source_nodes[node_id] = action
            node_id += 1

    lines.append("    end")
    lines.append("")

    # ─── Proposed State Subgraph ────────────────────────────
    lines.append('    subgraph Proposed["📂 Proposed State"]')

    # Group moves by destination
    dest_dirs: dict[str, str] = {}  # dest_path → node_id

    for action in moves:
        if action.destination:
            dest_parent = str(action.destination.parent)
            if dest_parent not in dest_dirs:
                dest_name = _sanitize(
                    dest_parent.split("\\")[-1]
                    if "\\" in dest_parent
                    else dest_parent.split("/")[-1]
                )
                dnode = f"W{node_id}"
                lines.append(f'        {dnode}["{dest_name}/"]')
                dest_dirs[dest_parent] = dnode
                node_id += 1

    if deletes:
        trash_node = f"TR{node_id}"
        lines.append(f'        {trash_node}["🗑️ Recycle Bin"]')
        node_id += 1

    lines.append("    end")
    lines.append("")

    # ─── Edges ──────────────────────────────────────────────
    for src_id, action in source_nodes.items():
        fnode = f"F{src_id}"

        if action.action == ActionType.MOVE and action.destination:
            dest_parent = str(action.destination.parent)
            dnode = dest_dirs.get(dest_parent, "UNKNOWN")
            indicator = "✅" if action.confidence >= 0.85 else "⚠️"
            lines.append(f'    {fnode} -- "MOVE {indicator} [{action.confidence:.2f}]" --> {dnode}')
        elif action.action == ActionType.DELETE:
            lines.append(f'    {fnode} -- "DELETE 🗑️ [{action.confidence:.2f}]" --> {trash_node}')

    # ─── Styles ─────────────────────────────────────────────
    lines.append("")
    lines.append('    style Current fill:#1a1a2e,stroke:#e94560,color:#eee')
    lines.append('    style Proposed fill:#0f3460,stroke:#00b4d8,color:#eee')
    if deletes:
        lines.append(f'    style {trash_node} fill:#8B0000,stroke:#ff6b6b,color:#fff')

    lines.append("```")

    return "\n".join(lines)
