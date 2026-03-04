"""
System Cleanup Engine for the Agentic File Architect v3.0.

Detects and proposes cleanup for system-level caches:
browser caches, DirectX shader caches, and orphaned installers.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from models.file_entry import CleanupTarget


class SystemCleanupEngine:
    """Integrates Windows system cleanup with agentic intelligence.

    Targets browser caches, shader caches, and orphaned installers
    for cleanup with confidence-rated proposals.
    """

    CLEANUP_TARGETS = {
        "windows_temp": {
            "paths": ["%TEMP%", "%SYSTEMROOT%\\Temp"],
            "max_age_days": 7,
            "confidence": 0.95,
            "category": "System Temp Files",
        },
        "prefetch": {
            "paths": ["%SYSTEMROOT%\\Prefetch"],
            "max_age_days": 30,
            "confidence": 0.80,
            "category": "Prefetch Cache",
        },
        "shader_cache": {
            "paths": [
                "%LOCALAPPDATA%\\D3DSCache",
                "%LOCALAPPDATA%\\NVIDIA\\DXCache",
                "%LOCALAPPDATA%\\AMD\\DxCache",
            ],
            "max_age_days": 14,
            "confidence": 0.90,
            "category": "DirectX Shader Cache",
        },
        "browser_cache": {
            "paths": [
                "%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Cache",
                "%LOCALAPPDATA%\\Microsoft\\Edge\\User Data\\Default\\Cache",
                "%APPDATA%\\Mozilla\\Firefox\\Profiles",
            ],
            "max_age_days": 0,  # All cache is safe to delete
            "confidence": 0.92,
            "category": "Browser Cache",
        },
        "orphaned_installers": {
            "paths": ["%USERPROFILE%\\Downloads"],
            "extensions": [".exe", ".msi", ".iso"],
            "max_age_days": 30,
            "confidence": 0.75,
            "category": "Redundant Installers",
        },
    }

    def scan_system(self) -> list[CleanupTarget]:
        """Scan all system cleanup targets and return proposed deletions.

        Returns:
            List of CleanupTarget objects for the proposal.
        """
        targets = []

        for name, config in self.CLEANUP_TARGETS.items():
            for path_template in config["paths"]:
                resolved = Path(os.path.expandvars(path_template))
                if resolved.exists():
                    targets.extend(
                        self._scan_directory(resolved, config)
                    )

        return targets

    def _scan_directory(
        self,
        directory: Path,
        config: dict,
    ) -> list[CleanupTarget]:
        """Scan a single directory for cleanup candidates.

        Args:
            directory: Directory to scan.
            config: Target-specific configuration.

        Returns:
            List of CleanupTarget objects.
        """
        targets = []
        max_age = timedelta(days=config.get("max_age_days", 7))
        cutoff = datetime.now() - max_age
        extensions = config.get("extensions", None)

        try:
            for item in directory.iterdir():
                if item.is_file():
                    # Filter by extension if specified
                    if extensions and item.suffix.lower() not in extensions:
                        continue

                    try:
                        stat = item.stat()
                        modified = datetime.fromtimestamp(stat.st_mtime)

                        # Only include files older than max_age
                        if config["max_age_days"] > 0 and modified > cutoff:
                            continue

                        targets.append(CleanupTarget(
                            path=item,
                            category=config["category"],
                            size=stat.st_size,
                            confidence=config["confidence"],
                            reasoning=f"{config['category']}: "
                                      f"{'all cache safe to delete' if config['max_age_days'] == 0 else f'last modified {(datetime.now() - modified).days} days ago'}",
                        ))
                    except OSError:
                        continue
                elif item.is_dir() and config.get("max_age_days") == 0:
                    # For browser caches, entire directories are targets (CLEAN-09)
                    size = self._dir_size(item)
                    targets.append(CleanupTarget(
                        path=item,
                        category=config["category"],
                        size=size,
                        confidence=config["confidence"],
                        reasoning=f"{config['category']}: cache directory safe to delete entirely.",
                    ))
        except (PermissionError, OSError):
            pass

        return targets

    @staticmethod
    def _dir_size(directory: Path) -> int:
        """Calculate total size of a directory."""
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
