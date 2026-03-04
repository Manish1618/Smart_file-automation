"""
Folder Context Analysis (FCA) engine for the Agentic File Architect v3.0.

Analyzes the contents of folders to determine their purpose —
detecting project types, media collections, cache folders, etc.
Used by DriveScanner during full-drive scans.

Rules enforced: DRIVE-04, DRIVE-05, DRIVE-06.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from models.file_entry import FolderContext


class FolderContextAnalyzer:
    """Reads folder contents to determine purpose via content analysis.

    Checks for project markers (package.json, Cargo.toml, .sln, etc.),
    samples file types, and assigns a category + confidence + action.
    """

    # Project markers → category mapping
    PROJECT_MARKERS: dict[str, str] = {
        "package.json": "Project/NodeJS",
        "Cargo.toml": "Project/Rust",
        "CMakeLists.txt": "Project/C++",
        "Makefile": "Project/C++",
        "requirements.txt": "Project/Python",
        "pyproject.toml": "Project/Python",
        "setup.py": "Project/Python",
        "pom.xml": "Project/Java",
        "build.gradle": "Project/Java",
        "go.mod": "Project/Go",
        "Gemfile": "Project/Ruby",
        "composer.json": "Project/PHP",
        "pubspec.yaml": "Project/Flutter",
    }

    # Extension markers for .sln, .csproj, .ino
    EXTENSION_MARKERS: dict[str, str] = {
        ".sln": "Project/CSharp",
        ".csproj": "Project/CSharp",
        ".ino": "Project/Arduino",
        ".pde": "Project/Arduino",
    }

    # Extension → broad category for dominant-type analysis
    EXT_CATEGORY_MAP: dict[str, str] = {
        '.py': 'Code/Python', '.pyw': 'Code/Python',
        '.js': 'Code/Web', '.ts': 'Code/Web', '.jsx': 'Code/Web',
        '.html': 'Code/Web', '.css': 'Code/Web',
        '.cpp': 'Code/C++', '.c': 'Code/C++', '.h': 'Code/C++',
        '.rs': 'Code/Rust', '.java': 'Code/Java',
        '.jpg': 'Media/Photography', '.jpeg': 'Media/Photography',
        '.png': 'Media/Photography', '.gif': 'Media/Photography',
        '.bmp': 'Media/Photography', '.tiff': 'Media/Photography',
        '.cr2': 'Media/Photography', '.nef': 'Media/Photography',
        '.webp': 'Media/Photography',
        '.mp4': 'Media/Video', '.mkv': 'Media/Video',
        '.avi': 'Media/Video', '.mov': 'Media/Video',
        '.mp3': 'Media/Audio', '.wav': 'Media/Audio',
        '.flac': 'Media/Audio', '.ogg': 'Media/Audio',
        '.pdf': 'Documents/Mixed', '.docx': 'Documents/Mixed',
        '.xlsx': 'Documents/Mixed', '.pptx': 'Documents/Mixed',
        '.txt': 'Documents/Mixed', '.md': 'Documents/Mixed',
        '.csv': 'Data/Mixed', '.json': 'Data/Mixed',
        '.xml': 'Data/Mixed',
        '.stl': 'Design/3DPrint', '.gcode': 'Design/3DPrint',
        '.dwg': 'Design/CAD', '.step': 'Design/CAD',
        '.h5': 'Data/ML_Models', '.onnx': 'Data/ML_Models',
        '.pt': 'Data/ML_Models', '.pth': 'Data/ML_Models',
        '.tmp': 'Cache/Disposable', '.log': 'Cache/Disposable',
        '.bak': 'Cache/Disposable',
    }

    def __init__(self, sample_size: int = 10):
        """Initialize with the number of files to sample per folder.

        Args:
            sample_size: Max files to sample for type analysis.
        """
        self.sample_size = sample_size

    def analyze(self, folder: Path) -> FolderContext:
        """Perform Folder Context Analysis on a directory.

        Checks project markers first, then falls back to
        dominant file type analysis.

        Args:
            folder: Directory to analyze.

        Returns:
            FolderContext with category, confidence, and action.
        """
        # 1. Check for project markers (files)
        for marker, category in self.PROJECT_MARKERS.items():
            try:
                if (folder / marker).exists():
                    return FolderContext(
                        path=folder,
                        category=category,
                        confidence=0.92,
                        reasoning=f"Contains {marker} — identified as {category}",
                        action="KEEP_IN_PLACE",
                    )
            except (PermissionError, OSError):
                # Corrupted ACL or access denied — skip this marker
                continue

        # 2. Check for extension-based project markers
        try:
            for item in folder.iterdir():
                if item.is_file():
                    ext = item.suffix.lower()
                    if ext in self.EXTENSION_MARKERS:
                        category = self.EXTENSION_MARKERS[ext]
                        return FolderContext(
                            path=folder,
                            category=category,
                            confidence=0.90,
                            reasoning=f"Contains {ext} file — identified as {category}",
                            action="KEEP_IN_PLACE",
                        )
        except (PermissionError, OSError):
            pass

        # 3. Check if folder is empty (DRIVE-06)
        try:
            children = list(folder.iterdir())
            if not children:
                return FolderContext(
                    path=folder,
                    category="Empty/Stale",
                    confidence=0.80,
                    reasoning="Empty folder with no files or subdirectories",
                    action="PROPOSE_CLEANUP",
                )
        except (PermissionError, OSError):
            return FolderContext(
                path=folder,
                category="Unknown",
                confidence=0.0,
                reasoning="Cannot access folder contents",
                action="SKIP",
            )

        # 4. Analyze dominant file types
        file_types = self._sample_file_types(folder)

        if not file_types:
            return FolderContext(
                path=folder,
                category="Unknown",
                confidence=0.0,
                reasoning="No classifiable files found in sample",
                action="SKIP",
            )

        dominant_cat, count = file_types.most_common(1)[0]
        total = sum(file_types.values())
        dominance = count / total if total > 0 else 0.0

        confidence = round(min(dominance, 1.0), 2)
        action = "PROPOSE_MOVE" if confidence >= 0.60 else "SKIP"

        return FolderContext(
            path=folder,
            category=dominant_cat,
            confidence=confidence,
            reasoning=f"Dominant file type: {dominant_cat} ({count}/{total} sampled files, {dominance:.0%})",
            action=action,
        )

    def _sample_file_types(self, folder: Path) -> Counter:
        """Sample up to N files in the folder and count categories.

        Args:
            folder: Directory to sample.

        Returns:
            Counter of category → count.
        """
        type_counts: Counter = Counter()
        count = 0

        try:
            for item in folder.iterdir():
                if count >= self.sample_size:
                    break
                if item.is_file():
                    ext = item.suffix.lower()
                    if ext in self.EXT_CATEGORY_MAP:
                        type_counts[self.EXT_CATEGORY_MAP[ext]] += 1
                    count += 1
        except (PermissionError, OSError):
            pass

        return type_counts
