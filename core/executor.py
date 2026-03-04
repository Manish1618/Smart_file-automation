"""
Safe Execution Engine for the Agentic File Architect v3.0.

Executes approved file operations (MOVE, DELETE) with full error
handling, collision resolution, and JSONL audit logging.

Rules enforced: EXEC-01 through EXEC-09.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from models.file_entry import ActionType


class ExecutionEngine:
    """Executes approved file operations with full logging and rollback support.

    Uses shutil.move() for cross-volume moves (EXEC-03),
    handles filename collisions with numeric suffixes (EXEC-02),
    wraps every operation in try/except (EXEC-05),
    and logs every operation to JSONL (EXEC-06).
    """

    def __init__(self, log_path: Path, session_id: str = ""):
        """Initialize with log file path.

        Args:
            log_path: Path to the JSONL log file.
            session_id: Session identifier for this run.
        """
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id

    def execute(self, approved_actions: list, approval_mode: str = "Y") -> dict:
        """Execute all approved actions with full safety.

        Args:
            approved_actions: List of ProposedAction objects to execute.
            approval_mode: The approval mode used (Y, M, etc.).

        Returns:
            Dict with 'success', 'failed', 'skipped' lists.
        """
        results = {"success": [], "failed": [], "skipped": []}

        for action in approved_actions:
            # EXEC-07: Verify file still exists
            if not action.file.path.exists():
                action.error = "File no longer exists (stale manifest)"
                results["skipped"].append(action)
                self._log_operation(action, "skipped", approval_mode)
                continue

            try:
                if action.action == ActionType.MOVE:
                    self._safe_move(action)
                    results["success"].append(action)
                    self._log_operation(action, "success", approval_mode)
                elif action.action == ActionType.DELETE:
                    self._safe_delete(action)
                    results["success"].append(action)
                    self._log_operation(action, "success", approval_mode)
                else:
                    results["skipped"].append(action)
                    self._log_operation(action, "skipped", approval_mode)
            except PermissionError:
                # EXEC-08: File is locked
                action.error = "File is locked by another process"
                results["failed"].append(action)
                self._log_operation(action, "error", approval_mode)
            except Exception as e:
                # EXEC-05: One failure doesn't crash the batch
                action.error = str(e)
                results["failed"].append(action)
                self._log_operation(action, "error", approval_mode)

        return results

    def _safe_move(self, action) -> None:
        """Move a file with collision handling.

        EXEC-01: Creates destination directories automatically.
        EXEC-02: Handles collisions with numeric suffixes.
        EXEC-03: Uses shutil.move() for cross-volume support.
        """
        dest = action.destination
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Handle filename collisions (EXEC-02)
        if dest.exists():
            stem = dest.stem
            suffix = dest.suffix
            counter = 1
            while dest.exists():
                dest = dest.parent / f"{stem}_{counter}{suffix}"
                counter += 1
            action.destination = dest

        shutil.move(str(action.file.path), str(dest))

    def _safe_delete(self, action) -> None:
        """Delete a file or directory safely.

        EXEC-04: Uses shutil.rmtree() for directories,
                 Path.unlink() for files.
        """
        target = action.file.path
        if target.is_dir():
            shutil.rmtree(str(target))
        else:
            target.unlink()

    def _log_operation(
        self,
        action,
        status: str,
        approval_mode: str,
    ) -> None:
        """Log a single operation to the JSONL file.

        LOG-01: JSONL format.
        LOG-02: All required fields.
        LOG-03: Append-only.
        LOG-04: Error messages for failures.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "action": action.action.value,
            "source": str(action.file.path),
            "destination": str(action.destination) if action.destination else None,
            "size_bytes": action.file.size_bytes,
            "category": action.category if isinstance(action.category, str)
                        else action.category.value,
            "confidence": action.confidence,
            "reasoning": action.reasoning,
            "status": status,
            "error_message": getattr(action, 'error', None),
            "approval_mode": approval_mode,
        }

        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except OSError:
            pass  # Don't crash over logging failures

    def rollback_session(self, session_id: str) -> list[dict]:
        """Build rollback proposals from a previous session's log.

        WF-13: Reads operations.jsonl, filters by session_id,
        proposes reversing MOVE operations. DELETE operations
        cannot be rolled back (warning shown).

        Args:
            session_id: Session ID to roll back.

        Returns:
            List of rollback proposal dicts.
        """
        proposals = []

        if not self.log_path.exists():
            return proposals

        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                if entry.get("session_id") != session_id:
                    continue
                if entry.get("status") != "success":
                    continue

                if entry["action"] == "MOVE":
                    proposals.append({
                        "type": "ROLLBACK_MOVE",
                        "current_path": entry["destination"],
                        "original_path": entry["source"],
                        "size_bytes": entry["size_bytes"],
                        "category": entry["category"],
                    })
                elif entry["action"] == "DELETE":
                    proposals.append({
                        "type": "CANNOT_ROLLBACK",
                        "original_path": entry["source"],
                        "reason": "⚠️  Deleted files cannot be recovered by the agent.",
                    })

        return proposals
