"""Access wrapper for vault/SOUL.md."""

from __future__ import annotations

from pathlib import Path

from pio_lab.memory.obsidian.vault import Vault


class SoulMd:
    """Read and update the bot personality note."""

    filename = "SOUL.md"

    def __init__(self, vault: Vault | None = None) -> None:
        self.vault = vault or Vault()

    def get(self) -> str:
        """Return SOUL.md content."""
        return self.vault.read(self.filename)

    def set(self, content: str) -> Path:
        """Replace SOUL.md content."""
        return self.vault.write(self.filename, content)


__all__ = ["SoulMd"]
