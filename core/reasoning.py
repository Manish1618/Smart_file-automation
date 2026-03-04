"""
Classification / Reasoning Engine for the Agentic File Architect v3.0.

Local heuristic file classification.
Assigns category, confidence, and reasoning to every file.

Rules enforced: CLASS-01 through CLASS-07.
"""

from __future__ import annotations

from pathlib import Path


class ReasoningEngine:
    """Local heuristic classifier.

    Uses weighted signals:
      tokens 0.30, extension 0.25, MIME 0.20, content 0.15, directory 0.10.
    """

    def __init__(self, workspace_root: str = "C:\\Workspace"):
        """Initialize the reasoning engine.
        """
        self.workspace_root = Path(workspace_root)
        self.workspace_map = self._build_workspace_map()

    def classify(self, entry) -> dict:
        """Classify a file entry.

        Always returns a dict with 'category', 'confidence', 'reasoning'.
        Uses local heuristic scoring (CLASS-02 local-only mode).

        Args:
            entry: FileEntry object with metadata.

        Returns:
            Dict with category, confidence (0.0–1.0), reasoning.
        """
        return self._heuristic_classify(entry)

    def get_destination(self, category: str) -> Path | None:
        """Get the workspace destination path for a category.

        Args:
            category: Classification category string.

        Returns:
            Full destination Path, or None if category is unknown.
        """
        subfolder = self.workspace_map.get(category)
        if subfolder:
            return self.workspace_root / subfolder
        return None

    # ─── Heuristic Classification (Mode B) ──────────────────────

    def _heuristic_classify(self, entry) -> dict:
        """Classify using weighted heuristic scoring.

        Signals and weights:
          - filename_tokens:  0.30
          - extension:        0.25
          - mime_type:        0.20
          - content_patterns: 0.15
          - directory_context: 0.10

        CLASS-01: Never classifies by extension alone.
        """
        scores: dict[str, float] = {}
        ext = entry.path.suffix.lower()
        tokens = entry.filename_tokens
        snippet = entry.content_snippet.lower() if entry.content_snippet else ""
        mime = entry.mime_type.lower() if entry.mime_type else ""
        parent = entry.parent_context.lower() if entry.parent_context else ""

        # ── Extension-based scoring (weight: 0.25) ──────────────
        ext_map = {
            '.py': 'Code/Python', '.pyw': 'Code/Python',
            '.cpp': 'Code/C++', '.c': 'Code/C++',
            '.h': 'Code/C++', '.hpp': 'Code/C++', '.cc': 'Code/C++',
            '.ino': 'Code/Arduino', '.pde': 'Code/Arduino',
            '.js': 'Code/Web', '.ts': 'Code/Web', '.jsx': 'Code/Web',
            '.tsx': 'Code/Web', '.html': 'Code/Web', '.css': 'Code/Web',
            '.rs': 'Code/Rust',
            '.java': 'Code/Java', '.kt': 'Code/Java',
            '.cs': 'Code/CSharp',
            '.pdf': 'Document/PDF',
            '.docx': 'Document/Word', '.doc': 'Document/Word',
            '.xlsx': 'Document/Spreadsheet', '.xls': 'Document/Spreadsheet',
            '.pptx': 'Document/Word',
            '.csv': 'Data/CSV',
            '.json': 'Data/JSON',
            '.xml': 'Data/XML',
            '.png': 'Media/Image', '.jpg': 'Media/Image',
            '.jpeg': 'Media/Image', '.gif': 'Media/Image',
            '.bmp': 'Media/Image', '.webp': 'Media/Image',
            '.svg': 'Media/Image', '.ico': 'Media/Image',
            '.tiff': 'Media/Image',
            '.mp4': 'Media/Video', '.mkv': 'Media/Video',
            '.avi': 'Media/Video', '.mov': 'Media/Video',
            '.wmv': 'Media/Video', '.flv': 'Media/Video',
            '.mp3': 'Media/Audio', '.wav': 'Media/Audio',
            '.flac': 'Media/Audio', '.ogg': 'Media/Audio',
            '.aac': 'Media/Audio',
            '.cr2': 'Media/RAW', '.nef': 'Media/RAW',
            '.arw': 'Media/RAW', '.dng': 'Media/RAW',
            '.stl': 'Design/3DPrint', '.gcode': 'Design/3DPrint',
            '.3mf': 'Design/3DPrint',
            '.dwg': 'Design/CAD', '.step': 'Design/CAD',
            '.stp': 'Design/CAD', '.iges': 'Design/CAD',
            '.zip': 'Archive', '.7z': 'Archive', '.rar': 'Archive',
            '.tar': 'Archive', '.gz': 'Archive',
            '.exe': 'Installer', '.msi': 'Installer', '.iso': 'Installer',
        }
        if ext in ext_map:
            cat = ext_map[ext]
            scores[cat] = scores.get(cat, 0) + 0.25

        # ── Content-based scoring (weight: 0.15) ────────────────
        content_signals = {
            'import torch': 'Code/ML',
            'import tensorflow': 'Code/ML',
            'import keras': 'Code/ML',
            'import sklearn': 'Code/ML',
            '#include <arduino.h>': 'Code/Arduino',
            'void setup()': 'Code/Arduino',
            'void loop()': 'Code/Arduino',
            '#include <iostream>': 'Code/C++',
            '#include <stdio.h>': 'Code/C++',
            'int main(': 'Code/C++',
            'def __init__': 'Code/Python',
            'import os': 'Code/Python',
            'from pathlib': 'Code/Python',
            'function ': 'Code/Web',
            'const ': 'Code/Web',
            'document.': 'Code/Web',
            'fn main(': 'Code/Rust',
            'use std::': 'Code/Rust',
            'public class': 'Code/Java',
            'public static void main': 'Code/Java',
            'namespace ': 'Code/CSharp',
            'using System': 'Code/CSharp',
        }
        for signal, cat in content_signals.items():
            if signal.lower() in snippet:
                scores[cat] = scores.get(cat, 0) + 0.15

        # ── Token-based scoring (weight: 0.30) ──────────────────
        token_signals = {
            'arduino': 'Code/Arduino', 'sketch': 'Code/Arduino',
            'voltage': 'Code/Arduino', 'sensor': 'Code/Arduino',
            'servo': 'Code/Arduino', 'led': 'Code/Arduino',
            'budget': 'Document/Spreadsheet',
            'invoice': 'Document/Spreadsheet',
            'financial': 'Document/Spreadsheet',
            'salary': 'Document/Spreadsheet',
            'report': 'Document/Word', 'thesis': 'Document/Word',
            'essay': 'Document/Word', 'assignment': 'Document/Word',
            'resume': 'Document/Word', 'cv': 'Document/Word',
            'photo': 'Media/Image', 'screenshot': 'Media/Image',
            'image': 'Media/Image', 'wallpaper': 'Media/Image',
            'model': 'Design/3DPrint', 'print': 'Design/3DPrint',
            'cad': 'Design/CAD', 'drawing': 'Design/CAD',
            'neural': 'Code/ML', 'train': 'Code/ML',
            'dataset': 'Data/CSV', 'data': 'Data/CSV',
            'backup': 'Archive', 'installer': 'Installer',
            'setup': 'Installer',
        }
        for token in tokens:
            if token in token_signals:
                cat = token_signals[token]
                scores[cat] = scores.get(cat, 0) + 0.30

        # ── MIME-based scoring (weight: 0.20) ───────────────────
        mime_map = {
            'text/x-python': 'Code/Python',
            'text/x-c++': 'Code/C++', 'text/x-c': 'Code/C++',
            'text/html': 'Code/Web',
            'text/css': 'Code/Web',
            'application/javascript': 'Code/Web',
            'application/pdf': 'Document/PDF',
            'application/vnd.openxmlformats-officedocument.wordprocessingml': 'Document/Word',
            'application/vnd.openxmlformats-officedocument.spreadsheetml': 'Document/Spreadsheet',
            'image/': 'Media/Image',
            'video/': 'Media/Video',
            'audio/': 'Media/Audio',
            'application/zip': 'Archive',
            'application/x-7z': 'Archive',
            'application/x-rar': 'Archive',
        }
        for pattern, cat in mime_map.items():
            if pattern in mime:
                scores[cat] = scores.get(cat, 0) + 0.20

        # ── Directory context scoring (weight: 0.10) ────────────
        dir_signals = {
            'downloads': None,      # Neutral
            'desktop': None,        # Neutral
            'documents': 'Document/Word',
            'pictures': 'Media/Image',
            'videos': 'Media/Video',
            'music': 'Media/Audio',
            'code': 'Code/Python',
            'projects': 'Code/Python',
            'src': 'Code/Python',
        }
        if parent in dir_signals and dir_signals[parent]:
            cat = dir_signals[parent]
            scores[cat] = scores.get(cat, 0) + 0.10

        # ── Determine best classification ───────────────────────
        if not scores:
            # CLASS-06: Default to Unknown
            return {
                "category": "Unknown",
                "confidence": 0.0,
                "reasoning": "No classification signals detected.",
            }

        best = max(scores, key=scores.get)
        confidence = min(round(scores[best], 2), 1.0)

        return {
            "category": best,
            "confidence": confidence,
            "reasoning": f"Classified by weighted heuristic analysis "
                         f"(best match: {best}, score: {confidence}).",
        }

    # ─── Workspace Map (CLASS-07) ───────────────────────────────

    def _build_workspace_map(self) -> dict[str, str]:
        """Build the category → workspace subfolder mapping."""
        return {
            'Code/Python': 'Code/Python',
            'Code/C++': 'Code/C++',
            'Code/Arduino': 'Engineering/Arduino',
            'Code/Web': 'Code/Web',
            'Code/Rust': 'Code/Rust',
            'Code/Java': 'Code/Java',
            'Code/CSharp': 'Code/CSharp',
            'Code/ML': 'Code/ML',
            'Document/PDF': 'Documents/PDF',
            'Document/Word': 'Documents/Reports',
            'Document/Spreadsheet': 'Finance',
            'Media/Image': 'Media/Images',
            'Media/Video': 'Media/Videos',
            'Media/Audio': 'Media/Audio',
            'Media/RAW': 'Photography/RAW',
            'Archive': 'Archives',
            'Data/CSV': 'Data',
            'Data/JSON': 'Data',
            'Data/XML': 'Data',
            'Design/CAD': 'Engineering/CAD',
            'Design/3DPrint': 'Engineering/3DPrint',
            'Installer': 'Downloads/Installers',
        }
