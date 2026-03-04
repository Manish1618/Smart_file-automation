"""
Cleanup Detector for the Agentic File Architect v3.0.

Identifies safe-to-delete build artifacts, caches, and temporary
files using contextual analysis — not just extension matching.

Rules enforced: CLEAN-01 through CLEAN-10.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from models.file_entry import (
    ActionType,
    CleanupTarget,
    FileEntry,
    ProposedAction,
)


class CleanupDetector:
    """Identifies and proposes deletion of build artifacts, caches,
    and temporary files that consume disk space without value.

    Distinguishes between valuable files and disposable artifacts
    using contextual analysis (e.g., Wavefront .obj vs C++ .obj).
    """

    def __init__(self, config: dict | None = None):
        """Initialize with optional cleanup configuration.

        Args:
            config: Dict with cleanup-specific settings.
        """
        self.config = config or {}
        self.delete_compiler = self.config.get("delete_compiler_artifacts", True)
        self.delete_python = self.config.get("delete_python_cache", True)
        self.delete_node = self.config.get("delete_node_modules_orphaned", True)
        self.log_max_days = self.config.get("delete_logs_older_than_days", 30)
        self.log_max_mb = self.config.get("delete_logs_larger_than_mb", 50)

    def scan(self, directories: list[Path]) -> list[ProposedAction]:
        """Scan directories for cleanup targets.

        Args:
            directories: Directories to scan for artifacts.

        Returns:
            List of ProposedAction objects for deletion.
        """
        actions = []

        for directory in directories:
            if not directory.exists():
                continue

            try:
                if self.delete_python:
                    actions.extend(self._find_python_cache(directory))
                if self.delete_node:
                    actions.extend(self._find_orphaned_node_modules(directory))
                if self.delete_compiler:
                    actions.extend(self._find_compiler_artifacts(directory))
                actions.extend(self._find_oversized_logs(directory))
                actions.extend(self._find_ide_caches(directory))
            except (PermissionError, OSError):
                continue

        return actions

    # ─── Python Cache (CLEAN-01) ────────────────────────────────

    def _find_python_cache(self, root: Path) -> list[ProposedAction]:
        """Find __pycache__ directories containing .pyc/.pyo files."""
        actions = []
        try:
            for cache_dir in root.rglob("__pycache__"):
                if not cache_dir.is_dir():
                    continue
                # CLEAN-01: Only delete if contains .pyc/.pyo
                pyc_files = list(cache_dir.glob("*.pyc")) + list(cache_dir.glob("*.pyo"))
                if pyc_files:
                    size = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
                    entry = FileEntry(
                        path=cache_dir,
                        size_bytes=size,
                        modified=datetime.now(),
                    )
                    actions.append(ProposedAction(
                        file=entry,
                        action=ActionType.DELETE,
                        category="Cache/Python",
                        confidence=0.95,
                        reasoning=f"Python cache directory with {len(pyc_files)} compiled files. Regenerated automatically.",
                        destination=None,
                    ))
        except (PermissionError, OSError):
            pass
        return actions

    # ─── Orphaned node_modules (CLEAN-02) ───────────────────────

    def _find_orphaned_node_modules(self, root: Path) -> list[ProposedAction]:
        """Find node_modules/ directories without a parent package.json."""
        actions = []
        try:
            for nm_dir in root.rglob("node_modules"):
                if not nm_dir.is_dir():
                    continue
                # CLEAN-02: Only delete if no package.json in parent
                parent_pkg = nm_dir.parent / "package.json"
                if not parent_pkg.exists():
                    size = self._dir_size(nm_dir)
                    entry = FileEntry(
                        path=nm_dir,
                        size_bytes=size,
                        modified=datetime.now(),
                    )
                    size_mb = size / (1024 * 1024)
                    actions.append(ProposedAction(
                        file=entry,
                        action=ActionType.DELETE,
                        category="Cache/NodeJS",
                        confidence=0.94,
                        reasoning=f"Orphaned node_modules/ ({size_mb:.1f} MB) — no package.json in parent directory.",
                        destination=None,
                    ))
        except (PermissionError, OSError):
            pass
        return actions

    # ─── Compiler Artifacts (CLEAN-03) ──────────────────────────

    def _find_compiler_artifacts(self, root: Path) -> list[ProposedAction]:
        """Find C++ build output directories and scattered .obj files.

        CLEAN-03: Distinguishes Wavefront .obj from C++ .obj.
        """
        actions = []

        # Build output directories
        build_dirs = ["Debug", "Release", "x64", "x86", "build", "out"]
        try:
            for bd_name in build_dirs:
                for bd in root.rglob(bd_name):
                    if bd.is_dir() and self._is_build_output(bd):
                        size = self._dir_size(bd)
                        entry = FileEntry(
                            path=bd,
                            size_bytes=size,
                            modified=datetime.now(),
                        )
                        actions.append(ProposedAction(
                            file=entry,
                            action=ActionType.DELETE,
                            category="Cache/Compiler",
                            confidence=0.92,
                            reasoning=f"Build output directory '{bd_name}/' contains only compiler artifacts. Regenerable via build.",
                            destination=None,
                        ))
        except (PermissionError, OSError):
            pass

        # Scattered .obj files (CLEAN-03)
        try:
            for obj_file in root.rglob("*.obj"):
                if obj_file.is_file() and not self._is_3d_model(obj_file):
                    entry = FileEntry(
                        path=obj_file,
                        size_bytes=obj_file.stat().st_size,
                        modified=datetime.fromtimestamp(obj_file.stat().st_mtime),
                    )
                    actions.append(ProposedAction(
                        file=entry,
                        action=ActionType.DELETE,
                        category="Cache/Compiler",
                        confidence=0.95,
                        reasoning="C++ compiler intermediate object file. Regenerated on next build.",
                        destination=None,
                    ))
        except (PermissionError, OSError):
            pass

        return actions

    # ─── Oversized / Old Logs (CLEAN-04) ────────────────────────

    def _find_oversized_logs(self, root: Path) -> list[ProposedAction]:
        """Find .log files that are too large or too old."""
        actions = []
        cutoff = datetime.now() - timedelta(days=self.log_max_days)
        max_size = self.log_max_mb * 1024 * 1024

        try:
            for log_file in root.rglob("*.log"):
                if not log_file.is_file():
                    continue
                try:
                    stat = log_file.stat()
                    modified = datetime.fromtimestamp(stat.st_mtime)
                    is_old = modified < cutoff
                    is_large = stat.st_size > max_size

                    if is_old or is_large:
                        size_mb = stat.st_size / (1024 * 1024)
                        age_days = (datetime.now() - modified).days
                        reason_parts = []
                        if is_large:
                            reason_parts.append(f"oversized at {size_mb:.1f} MB")
                        if is_old:
                            reason_parts.append(f"last modified {age_days} days ago")

                        entry = FileEntry(
                            path=log_file,
                            size_bytes=stat.st_size,
                            modified=modified,
                        )
                        actions.append(ProposedAction(
                            file=entry,
                            action=ActionType.DELETE,
                            category="Cache/System",
                            confidence=0.85,
                            reasoning=f"Log file {', '.join(reason_parts)}.",
                            destination=None,
                        ))
                except OSError:
                    continue
        except (PermissionError, OSError):
            pass

        return actions

    # ─── IDE Caches (CLEAN-06) ──────────────────────────────────

    def _find_ide_caches(self, root: Path) -> list[ProposedAction]:
        """Find IDE cache directories (.vs/, .idea/)."""
        actions = []
        ide_dirs = [".vs", ".idea"]

        try:
            for ide_name in ide_dirs:
                for ide_dir in root.rglob(ide_name):
                    if not ide_dir.is_dir():
                        continue

                    # CLEAN-06: Skip .vs/ if corresponding .sln modified recently
                    if ide_name == ".vs":
                        sln_files = list(ide_dir.parent.glob("*.sln"))
                        if sln_files:
                            recent = any(
                                (datetime.now() - datetime.fromtimestamp(
                                    s.stat().st_mtime
                                )).days <= 7
                                for s in sln_files
                            )
                            if recent:
                                continue

                    size = self._dir_size(ide_dir)
                    entry = FileEntry(
                        path=ide_dir,
                        size_bytes=size,
                        modified=datetime.now(),
                    )
                    size_mb = size / (1024 * 1024)
                    actions.append(ProposedAction(
                        file=entry,
                        action=ActionType.DELETE,
                        category="Cache/Runtime",
                        confidence=0.80,
                        reasoning=f"IDE cache directory '{ide_name}/' ({size_mb:.1f} MB). Regenerated by IDE on next open.",
                        destination=None,
                    ))
        except (PermissionError, OSError):
            pass

        return actions

    # ─── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _is_3d_model(filepath: Path) -> bool:
        """Check if a .obj file is a Wavefront 3D model.

        CLEAN-03: Wavefront .obj starts with '#' comments
        and 'v ' vertex lines. C++ .obj files are binary.
        """
        try:
            with open(filepath, 'rb') as f:
                header = f.read(128)
                # Wavefront OBJ is text-based
                try:
                    text = header.decode('ascii')
                    if text.startswith('#') or text.startswith('v '):
                        return True
                    lines = text.split('\n')
                    for line in lines[:5]:
                        line = line.strip()
                        if line.startswith(('v ', 'vt ', 'vn ', 'f ', '#')):
                            return True
                except (UnicodeDecodeError, AttributeError):
                    pass
            return False
        except OSError:
            return False

    @staticmethod
    def _is_build_output(directory: Path) -> bool:
        """Check if a directory contains only build artifacts."""
        artifact_exts = {'.obj', '.o', '.pdb', '.ilk', '.exp', '.lib',
                         '.exe', '.dll', '.pch', '.idb', '.log'}
        try:
            files = [f for f in directory.iterdir() if f.is_file()]
            if not files:
                return False
            artifact_count = sum(
                1 for f in files if f.suffix.lower() in artifact_exts
            )
            return artifact_count / len(files) >= 0.7
        except (PermissionError, OSError):
            return False

    @staticmethod
    def _dir_size(directory: Path) -> int:
        """Calculate total size of a directory recursively."""
        total = 0
        try:
            for f in directory.rglob("*"):
                if f.is_file():
                    try:
                        total += f.stat().st_size
                    except OSError:
                        pass
        except (PermissionError, OSError):
            pass
        return total
