"""
Smart Usage Brain for the Agentic File Architect v3.0.

Intelligent document usage analyzer — identifies rarely-used files
using a multi-signal staleness algorithm that considers access patterns,
modification history, file size, and duplicate detection (SHA-256).

Rules enforced: USAGE-01 through USAGE-10.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime
from pathlib import Path

from models.file_entry import (
    ActionType,
    FileEntry,
    ProposedAction,
    UsageReport,
)


class UsageBrain:
    """Intelligent document usage analyzer — identifies rarely-used files.

    Scores documents on a 0.0–1.0 staleness scale using four weighted
    signals: access time, modification time, file size, and duplicates.

    USAGE-03: Never auto-deletes. All recommendations pass through
    the Approval Gate.
    """

    # Document extensions to analyze
    DOCUMENT_EXTENSIONS = frozenset([
        '.docx', '.xlsx', '.pptx', '.odt', '.ods', '.odp',
        '.pdf', '.txt', '.md', '.rtf',
        '.csv', '.json', '.xml',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv',
        '.zip', '.7z', '.rar', '.tar', '.gz',
        '.exe', '.msi', '.iso',
    ])

    # USAGE-01, USAGE-02: Protected from analysis
    PROTECTED_EXTENSIONS = frozenset([
        '.py', '.pyw', '.js', '.ts', '.jsx', '.tsx',
        '.cpp', '.c', '.h', '.hpp', '.cc', '.cxx',
        '.java', '.rs', '.go', '.rb', '.php', '.swift', '.kt',
        '.ino', '.pde', '.cs',
        '.yaml', '.yml', '.toml', '.ini', '.conf', '.cfg',
        '.env', '.pem', '.key', '.kdbx', '.wallet',
        '.db', '.sqlite', '.sqlite3',
        '.sh', '.bash', '.bat', '.ps1', '.cmd',
    ])

    # Signal weights (USAGE-04)
    WEIGHT_ACCESS = 0.40
    WEIGHT_MODIFY = 0.30
    WEIGHT_SIZE = 0.15
    WEIGHT_DUPE = 0.15

    def __init__(self, config: dict | None = None):
        """Initialize with optional configuration.

        Args:
            config: Dict with thresholds, weights, and settings.
        """
        self.config = config or {}
        self._hash_cache: dict[str, list[Path]] = {}

        # Configurable thresholds
        thresholds = self.config.get("staleness_thresholds", {})
        self.threshold_delete = thresholds.get("recommend_delete", 0.85)
        self.threshold_archive = thresholds.get("consider_archive", 0.60)

        # Configurable weights
        weights = self.config.get("signal_weights", {})
        if weights:
            self.WEIGHT_ACCESS = weights.get("days_since_access", 0.40)
            self.WEIGHT_MODIFY = weights.get("days_since_modify", 0.30)
            self.WEIGHT_SIZE = weights.get("file_size_waste", 0.15)
            self.WEIGHT_DUPE = weights.get("duplicate_score", 0.15)

        # Max file size for hashing (USAGE-09)
        self.max_hash_size = (
            self.config.get("max_hash_file_size_mb", 500) * 1024 * 1024
        )

    def analyze_directory(self, directory: Path) -> list[UsageReport]:
        """Analyze all documents in a directory tree for staleness.

        Args:
            directory: Root directory to analyze.

        Returns:
            List of UsageReport, sorted by staleness (highest first).
        """
        reports = []

        try:
            for filepath in directory.rglob("*"):
                if filepath.is_file() and self._should_analyze(filepath):
                    report = self._score_file(filepath)
                    if report:
                        reports.append(report)
        except (PermissionError, OSError):
            pass

        # Sort by staleness (highest first)
        reports.sort(key=lambda r: r.staleness_score, reverse=True)
        return reports

    def reports_to_actions(self, reports: list[UsageReport]) -> list[ProposedAction]:
        """Convert UsageReports into ProposedAction objects.

        Only converts DELETE and ARCHIVE recommendations.
        KEEP recommendations are not included.

        Args:
            reports: List of UsageReport objects.

        Returns:
            List of ProposedAction for the manifest.
        """
        actions = []

        for report in reports:
            if report.recommendation == "KEEP":
                continue

            action_type = (
                ActionType.DELETE if report.recommendation == "DELETE"
                else ActionType.ARCHIVE
            )

            entry = FileEntry(
                path=report.path,
                size_bytes=report.size_bytes,
                modified=datetime.fromtimestamp(
                    report.path.stat().st_mtime
                ) if report.path.exists() else datetime.now(),
            )

            actions.append(ProposedAction(
                file=entry,
                action=action_type,
                category=f"UsageBrain/{report.recommendation}",
                confidence=report.staleness_score,
                reasoning=report.reasoning,
                destination=None,
            ))

        return actions

    def _should_analyze(self, filepath: Path) -> bool:
        """Check if a file should be analyzed for staleness.

        USAGE-01: Never analyze source code.
        USAGE-02: Never analyze configuration files.
        """
        ext = filepath.suffix.lower()
        if ext in self.PROTECTED_EXTENSIONS:
            return False
        if ext not in self.DOCUMENT_EXTENSIONS:
            return False
        return True

    def _score_file(self, filepath: Path) -> UsageReport | None:
        """Compute staleness score for a single file.

        Uses the four-signal formula (USAGE-04).
        """
        try:
            stat = filepath.stat()
            now = datetime.now()

            days_access = (now - datetime.fromtimestamp(stat.st_atime)).days
            days_modify = (now - datetime.fromtimestamp(stat.st_mtime)).days
            size = stat.st_size

            # Compute weighted staleness score
            access_score = self._normalize_days(days_access)
            modify_score = self._normalize_days(days_modify)
            size_score = self._normalize_size(size)
            dupe_score = self._check_duplicate(filepath, size)

            staleness = (
                self.WEIGHT_ACCESS * access_score
                + self.WEIGHT_MODIFY * modify_score
                + self.WEIGHT_SIZE * size_score
                + self.WEIGHT_DUPE * dupe_score
            )
            staleness = round(min(staleness, 1.0), 3)

            # Determine recommendation (USAGE-05, USAGE-06, USAGE-07)
            if staleness >= self.threshold_delete:
                recommendation = "DELETE"
                size_mb = size / (1024 * 1024)
                reasoning = (
                    f"Not accessed in {days_access} days, not modified in "
                    f"{days_modify} days, {size_mb:.1f}MB. "
                    f"Highly stale — recommend deletion."
                )
            elif staleness >= self.threshold_archive:
                recommendation = "ARCHIVE"
                reasoning = (
                    f"Last access {days_access} days ago, last modified "
                    f"{days_modify} days ago. Consider archiving or "
                    f"moving to cloud storage."
                )
            else:
                recommendation = "KEEP"
                reasoning = "File is recent, small, or actively used."

            # Add duplicate info to reasoning
            if dupe_score > 0:
                reasoning += " Exact duplicate exists elsewhere."

            return UsageReport(
                path=filepath,
                staleness_score=staleness,
                days_since_access=days_access,
                days_since_modify=days_modify,
                size_bytes=size,
                has_duplicate=dupe_score > 0,
                recommendation=recommendation,
                reasoning=reasoning,
            )
        except (OSError, ValueError):
            return None

    @staticmethod
    def _normalize_days(days: int) -> float:
        """Normalize days into a 0.0–1.0 score.

        0 days → 0.0, 30 days → ~0.3, 90 days → ~0.7, 180+ days → 1.0
        """
        if days <= 0:
            return 0.0
        elif days <= 30:
            return days / 100
        elif days <= 90:
            return 0.3 + (days - 30) / 150
        elif days <= 180:
            return 0.7 + (days - 90) / 300
        return 1.0

    @staticmethod
    def _normalize_size(size_bytes: int) -> float:
        """Normalize file size into a waste-factor score.

        < 1MB → 0.1, 1–50MB → 0.3, 50–500MB → 0.6, > 500MB → 1.0
        """
        mb = size_bytes / (1024 * 1024)
        if mb < 1:
            return 0.1
        elif mb < 50:
            return 0.3
        elif mb < 500:
            return 0.6
        return 1.0

    def _check_duplicate(self, filepath: Path, size: int) -> float:
        """Check if an exact duplicate exists (by SHA-256 hash).

        USAGE-08: Uses SHA-256.
        USAGE-09: Skips files larger than max_hash_file_size_mb.
        """
        if size > self.max_hash_size:
            return 0.0

        try:
            file_hash = self._compute_hash(filepath)
            if file_hash in self._hash_cache:
                existing = self._hash_cache[file_hash]
                if filepath not in existing:
                    existing.append(filepath)
                    return 1.0  # Duplicate found
            else:
                self._hash_cache[file_hash] = [filepath]
            return 0.0
        except OSError:
            return 0.0

    @staticmethod
    def _compute_hash(filepath: Path, chunk_size: int = 8192) -> str:
        """Compute SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                sha256.update(chunk)
        return sha256.hexdigest()
