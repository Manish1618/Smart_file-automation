"""
Full-Drive Scanner for the Agentic File Architect v3.0.

Scans entire C:\\ and D:\\ drives with intelligent safety exclusions,
adaptive depth per zone, and integrated Folder Context Analysis (FCA).

Rules enforced: DRIVE-01 through DRIVE-08.
"""

from __future__ import annotations

from pathlib import Path

from core.safety import SafetyGuard
from core.scanner import ScanEngine
from core.folder_context import FolderContextAnalyzer
from models.file_entry import FileEntry, FolderContext


class DriveScanner:
    """Full-drive intelligence scanner with Folder Context Analysis.

    Discovers entry points across C:\\ and D:\\ drives, applies
    safety filters at the root level, and uses adaptive scan depth
    based on folder type.
    """

    # Default depth per zone type
    DEFAULT_DEPTHS: dict[str, int] = {
        "user_documents": 5,
        "user_desktop": 2,
        "user_downloads": 2,
        "user_appdata": 1,
        "data_drive": 4,
        "custom_roots": 3,
    }

    # Known user home subdirectory → zone mapping
    USER_ZONE_MAP: dict[str, str] = {
        "Documents": "user_documents",
        "Desktop": "user_desktop",
        "Downloads": "user_downloads",
        "AppData": "user_appdata",
        "Pictures": "user_documents",
        "Videos": "user_documents",
        "Music": "user_documents",
        "OneDrive": "user_documents",
    }

    def __init__(self, safety_guard: SafetyGuard):
        """Initialize with a SafetyGuard instance.

        Args:
            safety_guard: Safety enforcement layer.
        """
        self.guard = safety_guard
        self.fca = FolderContextAnalyzer()
        self.folder_contexts: list[FolderContext] = []

    def scan_drives(
        self,
        drives: list[str],
        config: dict,
    ) -> list[FileEntry]:
        """Scan all specified drives and return file entries.

        Args:
            drives: List of drive roots (e.g., ["C:\\\\", "D:\\\\"]).
            config: Full application config dict.

        Returns:
            List of FileEntry objects from all accessible directories.
        """
        depth_config = config.get("drive_scan", {}).get(
            "depth_per_zone", self.DEFAULT_DEPTHS
        )
        fca_sample = config.get("drive_scan", {}).get("fca_sample_size", 10)
        self.fca = FolderContextAnalyzer(sample_size=fca_sample)

        all_entries: list[FileEntry] = []

        for drive in drives:
            drive_root = Path(drive)

            # DRIVE-08: Handle missing drives
            if not drive_root.exists():
                print(f"   ⚠️  Drive {drive} not found — skipping.")
                continue

            print(f"   💿 Scanning drive: {drive}")
            entry_points = self._discover_entry_points(drive_root)
            print(f"      Found {len(entry_points)} accessible root folders.")

            for ep in entry_points:
                depth = self._get_depth(ep, drive, depth_config)
                scanner = ScanEngine({
                    "max_depth": depth,
                    "min_file_size": config.get("min_file_size", 0),
                    "max_file_size": config.get("max_file_size", 10 * 1024**3),
                })

                # Run FCA on the entry point
                if config.get("drive_scan", {}).get("folder_context_analysis", True):
                    try:
                        ctx = self.fca.analyze(ep)
                        self.folder_contexts.append(ctx)

                        # DRIVE-05: Skip scanning inside active project folders
                        if ctx.action == "KEEP_IN_PLACE":
                            print(f"      📂 {ep.name}/ — {ctx.category} (keeping in place)")
                            continue
                    except (PermissionError, OSError) as e:
                        print(f"      ⚠️  {ep.name}/ — skipped FCA (access error: {e})")
                        # Continue scanning without FCA context

                entries = scanner.scan([ep], safety_guard=self.guard)
                all_entries.extend(entries)

        return all_entries

    def _discover_entry_points(self, drive_root: Path) -> list[Path]:
        """Auto-discover scannable root folders on a drive.

        Filters through SafetyGuard (DRIVE-01, DRIVE-02).

        Args:
            drive_root: Root path of the drive (e.g., C:\\).

        Returns:
            List of safe, accessible directories at the drive root.
        """
        entry_points = []

        try:
            for item in sorted(drive_root.iterdir()):
                if item.is_dir() and self.guard.is_safe(item):
                    # Skip hidden/system folders
                    if item.name.startswith(('$', '.')):
                        continue
                    entry_points.append(item)
        except (PermissionError, OSError):
            pass

        return entry_points

    def _get_depth(
        self,
        path: Path,
        drive: str,
        depth_config: dict,
    ) -> int:
        """Determine scan depth for a path based on its zone.

        Uses adaptive depth per folder type (DRIVE-03).

        Args:
            path: Entry point path.
            drive: Drive letter string.
            depth_config: Zone → depth mapping from config.

        Returns:
            Max scan depth for this path.
        """
        user_home = Path.home()

        # Check if this is a known user home subdirectory
        try:
            relative = path.relative_to(user_home)
            top_folder = relative.parts[0] if relative.parts else ""
            zone = self.USER_ZONE_MAP.get(top_folder, "custom_roots")
            return depth_config.get(zone, 3)
        except ValueError:
            pass

        # Check if on data drive (non-C:)
        if drive.upper().startswith("D"):
            return depth_config.get("data_drive", 4)

        # Default for custom root-level folders
        return depth_config.get("custom_roots", 3)
