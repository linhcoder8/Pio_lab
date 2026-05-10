"""Access wrapper for vault/USER.md."""

from __future__ import annotations

from pathlib import Path

from pio_lab.memory.obsidian.vault import Vault


class UserMd:
    """Read and update the owner profile note."""

    filename = "USER.md"

    def __init__(self, vault: Vault | None = None) -> None:
        self.vault = vault or Vault()

    def get(self) -> str:
        """Return USER.md content."""
        return self.vault.read(self.filename)

    def set(self, content: str) -> Path:
        """Replace USER.md content."""
        return self.vault.write(self.filename, content)


__all__ = ["UserMd"]
