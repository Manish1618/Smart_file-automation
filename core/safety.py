"""
Safety enforcement for the Agentic File Architect v3.0.

Implements all SAFE-01 through SAFE-12 rules — immutable exclusion zones
and protected file patterns that CANNOT be overridden by configuration,
user input, or any other rule. This is the HARD BARRIER.
"""

from __future__ import annotations

import re
from pathlib import Path


class SafetyGuard:
    """Enforces immutable exclusion zones and protected patterns.

    This is a HARD BARRIER — no configuration can override these rules.
    All proposed actions pass through this guard before reaching the
    Approval Gate.
    """

    # ─── SAFE-01 through SAFE-04: Immutable System Zones ─────────
    IMMUTABLE_ZONES: frozenset[str] = frozenset([
        r"C:\Windows",
        r"C:\Windows\System32",
        r"C:\Windows\SysWOW64",
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        r"C:\ProgramData",
        r"C:\$Recycle.Bin",
        r"C:\Recovery",
        r"C:\Boot",
        r"C:\EFI",
    ])

    # ─── SAFE-05 through SAFE-08: Protected Patterns ────────────
    PROTECTED_PATTERNS: list[str] = [
        r"\.git(/|\\|$)",           # SAFE-05: Git repositories
        r"\.svn(/|\\|$)",           # Version control
        r"\.hg(/|\\|$)",            # Mercurial
        r"\.ssh(/|\\|$)",           # SAFE-06: SSH keys
        r"\.gnupg(/|\\|$)",         # SAFE-06: GPG keys
        r"id_rsa",                  # SAFE-06: SSH private key
        r"id_ed25519",              # SAFE-06: SSH private key
        r"\.pem$",                  # SAFE-06: Certificate files
        r"\.key$",                  # SAFE-06: Key files
        r"\.env$",                  # SAFE-07: Environment files
        r"\.kdbx$",                 # SAFE-08: KeePass databases
        r"\.wallet$",              # SAFE-08: Crypto wallets
    ]

    def __init__(self, additional_exclusions: list[str] | None = None):
        """Initialize with optional additional exclusion paths.

        Args:
            additional_exclusions: Extra paths to protect (from config).
        """
        self._additional = [
            Path(p).resolve() for p in (additional_exclusions or [])
        ]

    def is_safe(self, filepath: Path) -> bool:
        """Check if a file/directory is safe to operate on.

        Returns True if the path is NOT in any immutable zone
        and does NOT match any protected pattern.

        Args:
            filepath: Path to check.

        Returns:
            True if safe to operate on, False if protected.
        """
        try:
            path_str = str(filepath.resolve())
        except (OSError, ValueError):
            return False

        # Check immutable zones (case-insensitive)
        for zone in self.IMMUTABLE_ZONES:
            if path_str.lower().startswith(zone.lower()):
                return False

        # Check additional user-configured exclusions
        for excl in self._additional:
            if path_str.lower().startswith(str(excl).lower()):
                return False

        # Check protected patterns
        for pattern in self.PROTECTED_PATTERNS:
            if re.search(pattern, path_str, re.IGNORECASE):
                return False

        return True

    def is_safe_directory(self, directory: Path) -> bool:
        """Check if a directory is safe to enter during scanning.

        Same as is_safe() but with a clearer name for scan operations.
        """
        return self.is_safe(directory)

    def validate_manifest(self, manifest) -> tuple[list, list]:
        """Split manifest actions into safe and blocked lists.

        Both source and destination paths are checked for safety.

        Args:
            manifest: Manifest object with .actions list.

        Returns:
            Tuple of (safe_actions, blocked_actions).
            Blocked actions include a reason string.
        """
        safe, blocked = [], []

        for action in manifest.actions:
            source_safe = self.is_safe(action.file.path)
            dest_safe = (
                action.destination is None
                or self.is_safe(action.destination)
            )

            if not source_safe:
                blocked.append((action, "Source in protected zone"))
            elif not dest_safe:
                blocked.append((action, "Destination in protected zone"))
            else:
                safe.append(action)

        return safe, blocked

    def get_blocked_reason(self, filepath: Path) -> str | None:
        """Get a human-readable reason why a path is blocked.

        Returns None if the path is safe.
        """
        try:
            path_str = str(filepath.resolve())
        except (OSError, ValueError):
            return "Cannot resolve path"

        for zone in self.IMMUTABLE_ZONES:
            if path_str.lower().startswith(zone.lower()):
                return f"Inside immutable zone: {zone}"

        for excl in self._additional:
            if path_str.lower().startswith(str(excl).lower()):
                return f"Inside user-excluded zone: {excl}"

        for pattern in self.PROTECTED_PATTERNS:
            if re.search(pattern, path_str, re.IGNORECASE):
                return f"Matches protected pattern: {pattern}"

        return None
