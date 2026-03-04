"""
Action Planner for the Agentic File Architect v3.0.

Takes classified FileEntry objects and generates ProposedAction items
with confidence-based thresholds, then builds a complete Manifest.

Rules enforced: PLAN-01 through PLAN-08.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.reasoning import ReasoningEngine
from models.file_entry import (
    ActionType,
    FileEntry,
    Manifest,
    ProposedAction,
)


class ActionPlanner:
    """Generates an action plan (Manifest) from classified file entries.

    Applies confidence thresholds to determine MOVE, DELETE, or SKIP
    for each file, and computes workspace destination paths.
    """

    # Windows MAX_PATH limit
    MAX_PATH = 260

    # Cache categories that should trigger DELETE
    CACHE_CATEGORIES = frozenset([
        'Cache/Compiler', 'Cache/Runtime', 'Cache/System',
    ])

    def __init__(self, reasoning_engine: ReasoningEngine, config: dict):
        """Initialize with reasoning engine and config.

        Args:
            reasoning_engine: Classification engine.
            config: Application configuration dict.
        """
        self.engine = reasoning_engine
        self.workspace_root = Path(
            config.get("workspace_root", "C:\\Workspace")
        )
        # Override workspace map from config if provided
        config_map = config.get("workspace_map", {})
        if config_map:
            self.engine.workspace_map.update(config_map)

    def generate_manifest(self, entries: list[FileEntry]) -> Manifest:
        """Classify all entries and generate a complete Manifest.

        Args:
            entries: List of FileEntry objects from the scan.

        Returns:
            Manifest with ProposedAction for each entry.
        """
        manifest = Manifest(
            timestamp=datetime.now(),
            scan_directories=[],
        )

        total_freed = 0

        for entry in entries:
            # Classify the file
            result = self.engine.classify(entry)
            category = result.get("category", "Unknown")
            confidence = result.get("confidence", 0.0)
            reasoning = result.get("reasoning", "")

            # Determine action based on confidence (PLAN-01 through PLAN-06)
            action, destination = self._determine_action(
                entry, category, confidence
            )

            # PLAN-07: Check path length
            if destination and len(str(destination)) > self.MAX_PATH:
                action = ActionType.SKIP
                destination = None
                reasoning += " [Skipped: destination path exceeds MAX_PATH]"

            # PLAN-08: Check if file is locked
            if action != ActionType.SKIP and not self._is_accessible(entry.path):
                action = ActionType.SKIP
                reasoning += " [Skipped: file is locked by another process]"

            # Track space freed for DELETE actions
            if action == ActionType.DELETE:
                total_freed += entry.size_bytes

            proposed = ProposedAction(
                file=entry,
                action=action,
                category=category,
                confidence=confidence,
                reasoning=reasoning,
                destination=destination,
            )
            manifest.actions.append(proposed)

        manifest.total_size_freed = total_freed
        return manifest

    def _determine_action(
        self,
        entry: FileEntry,
        category: str,
        confidence: float,
    ) -> tuple[ActionType, Path | None]:
        """Determine the action type and destination for a file.

        Applies confidence thresholds (PLAN-01 through PLAN-05).

        Returns:
            Tuple of (ActionType, destination Path or None).
        """
        # PLAN-04: Cache categories → DELETE
        if category in self.CACHE_CATEGORIES:
            return ActionType.DELETE, None

        # PLAN-03: Low confidence → SKIP
        if confidence < 0.60:
            return ActionType.SKIP, None

        # Get destination from workspace map
        destination = self.engine.get_destination(category)
        if destination is None:
            return ActionType.SKIP, None

        # Build full destination path
        full_dest = destination / entry.path.name

        # PLAN-06: Already in correct location → SKIP
        try:
            if entry.path.parent.resolve() == destination.resolve():
                return ActionType.SKIP, None
        except (OSError, ValueError):
            pass

        # PLAN-01 / PLAN-02: Confidence determines MOVE
        # Confidence ≥ 0.60 → propose MOVE (with warning if < 0.85)
        return ActionType.MOVE, full_dest

    @staticmethod
    def _is_accessible(filepath: Path) -> bool:
        """Check if a file is accessible (not locked).

        Returns False if the file is locked by another process.
        """
        try:
            with open(filepath, 'rb'):
                return True
        except (PermissionError, OSError):
            return False

    def export_manifest(self, manifest: Manifest, path: Path) -> None:
        """Export manifest to a JSON file.

        Args:
            manifest: Manifest to export.
            path: Output file path.
        """
        data = {
            "timestamp": manifest.timestamp.isoformat(),
            "session_id": manifest.session_id,
            "total_actions": len(manifest.actions),
            "total_moves": len(manifest.moves),
            "total_deletes": len(manifest.deletes),
            "total_skips": len(manifest.skips),
            "total_size_freed_bytes": manifest.total_size_freed,
            "actions": [],
        }

        for action in manifest.actions:
            data["actions"].append({
                "file": str(action.file.path),
                "size_bytes": action.file.size_bytes,
                "action": action.action.value,
                "category": action.category,
                "confidence": action.confidence,
                "reasoning": action.reasoning,
                "destination": str(action.destination) if action.destination else None,
            })

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
