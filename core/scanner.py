"""
Phase 1 — Discovery Scan Engine for the Agentic File Architect v3.0.

Recursively walks target directories, extracts file metadata,
reads content snippets, and builds FileEntry objects for classification.

Rules enforced: SCAN-01 through SCAN-08.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

try:
    import magic  # python-magic-bin for MIME detection
except ImportError:
    magic = None

from models.file_entry import FileEntry


class ScanEngine:
    """Phase 1: Discovers and catalogs files across target directories.

    Respects depth limits, skips hidden directories, handles
    permission errors gracefully, and extracts metadata + content
    snippets for each discovered file.
    """

    SNIPPET_SIZE = 512  # SCAN-06: Max bytes to read for content analysis

    # Text-safe extensions for content snippet reading (SCAN-05)
    TEXT_EXTENSIONS: frozenset[str] = frozenset([
        '.py', '.pyw', '.js', '.ts', '.jsx', '.tsx',
        '.cpp', '.c', '.h', '.hpp', '.cc', '.cxx',
        '.java', '.rs', '.go', '.rb', '.php', '.swift', '.kt',
        '.ino', '.pde',
        '.txt', '.md', '.rst', '.rtf',
        '.csv', '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg',
        '.html', '.htm', '.css', '.scss', '.sass', '.less',
        '.sql', '.sh', '.bash', '.bat', '.ps1', '.cmd',
        '.r', '.R', '.m', '.lua', '.pl', '.pm',
        '.dockerfile', '.makefile', '.cmake',
        '.env.example', '.gitignore', '.editorconfig',
    ])

    def __init__(self, config: dict):
        """Initialize with scan configuration.

        Args:
            config: Dict with max_depth, min_file_size, max_file_size.
        """
        self.max_depth = config.get("max_depth", 3)
        self.min_file_size = config.get("min_file_size", 0)
        self.max_file_size = config.get("max_file_size", 10 * 1024**3)  # 10GB

    def scan(self, directories: list[Path], safety_guard=None) -> list[FileEntry]:
        """Scan multiple directories and return file entries.

        Args:
            directories: List of directories to scan.
            safety_guard: Optional SafetyGuard for path validation.

        Returns:
            List of FileEntry objects with full metadata.
        """
        entries = []
        for directory in directories:
            if not directory.exists():
                print(f"   ⏭️  {directory} — does not exist, skipping.")
                continue
            if safety_guard and not safety_guard.is_safe(directory):
                print(f"   🛡️  {directory} — protected zone, skipping.")
                continue
            print(f"   🔍 Scanning: {directory}")
            entries.extend(self._walk(directory, current_depth=0, safety_guard=safety_guard))
        return entries

    def _walk(
        self,
        directory: Path,
        current_depth: int,
        safety_guard=None,
    ) -> list[FileEntry]:
        """Recursively walk a directory up to max_depth.

        Handles PermissionError gracefully (SCAN-04).
        Skips hidden directories (SCAN-03).
        """
        entries = []
        if current_depth > self.max_depth:
            return entries

        try:
            for item in sorted(directory.iterdir()):
                if item.is_file():
                    # EDGE-01: Skip symbolic links
                    if item.is_symlink():
                        continue
                    entry = self._build_entry(item)
                    if entry:
                        entries.append(entry)
                elif item.is_dir():
                    # SCAN-03: Skip hidden directories
                    if item.name.startswith('.'):
                        continue
                    # Skip protected directories
                    if safety_guard and not safety_guard.is_safe(item):
                        continue
                    entries.extend(
                        self._walk(item, current_depth + 1, safety_guard)
                    )
        except PermissionError:
            pass  # SCAN-04: Graceful handling
        except OSError:
            pass

        return entries

    def _build_entry(self, filepath: Path) -> FileEntry | None:
        """Build a FileEntry from a file path.

        Skips files outside size bounds (SCAN-07).
        Skips empty files (EDGE-02).
        Skips symlinks (EDGE-01).
        """
        try:
            stat = filepath.stat()

            # EDGE-02: Skip empty files
            if stat.st_size == 0:
                return None

            # SCAN-07: Skip oversized files
            if not (self.min_file_size <= stat.st_size <= self.max_file_size):
                return None

            return FileEntry(
                path=filepath,
                size_bytes=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime),
                mime_type=self._detect_mime(filepath),
                content_snippet=self._read_snippet(filepath),
                filename_tokens=self._tokenize(filepath.stem),
                parent_context=filepath.parent.name,
            )
        except (OSError, ValueError):
            return None

    def _detect_mime(self, filepath: Path) -> str:
        """Detect MIME type using python-magic.

        Falls back gracefully if magic is not installed.
        """
        if magic:
            try:
                return magic.from_file(str(filepath), mime=True)
            except Exception:
                pass
        return ""

    def _read_snippet(self, filepath: Path) -> str:
        """Read first 512 bytes of text files for content analysis.

        Only reads from known text-safe extensions (SCAN-05).
        Limits to SNIPPET_SIZE bytes (SCAN-06).
        """
        if filepath.suffix.lower() in self.TEXT_EXTENSIONS:
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read(self.SNIPPET_SIZE)
            except Exception:
                pass
        # Also try files with no extension that might be text
        if not filepath.suffix:
            try:
                with open(filepath, 'rb') as f:
                    chunk = f.read(64)
                    if chunk and all(
                        b < 128 for b in chunk if b not in (0x0A, 0x0D, 0x09)
                    ):
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            return f.read(self.SNIPPET_SIZE)
            except Exception:
                pass
        return ""

    @staticmethod
    def _tokenize(stem: str) -> list[str]:
        """Split filename stem into semantic tokens.

        Handles CamelCase, underscores, hyphens, dots (SCAN-08).
        """
        # Split on CamelCase boundaries
        tokens = re.sub(r'([a-z])([A-Z])', r'\1 \2', stem)
        # Split on delimiters
        parts = re.split(r'[_\-.\s]+', tokens.lower())
        # Filter empty tokens
        return [t for t in parts if t]
