"""Safe file operations for the Obsidian vault."""

from __future__ import annotations

from pathlib import Path

from pio_lab.utils.env import get_settings


class Vault:
    """Read and write markdown notes inside a configured vault root."""

    def __init__(self, root_path: str | Path | None = None) -> None:
        configured_root = root_path or get_settings().obsidian_vault_path
        self.root_path = Path(configured_root).expanduser().resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

    def write(self, relative_path: str | Path, content: str, *, overwrite: bool = True) -> Path:
        """Write a note below the vault root and return the absolute path."""
        target = self._resolve_note_path(relative_path)
        if target.exists() and not overwrite:
            raise FileExistsError(f"Vault note already exists: {relative_path}")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def read(self, relative_path: str | Path) -> str:
        """Read a note below the vault root."""
        target = self._resolve_note_path(relative_path)
        return target.read_text(encoding="utf-8")

    def list_notes(self, prefix: str | Path = "") -> list[str]:
        """List markdown notes under a vault prefix using POSIX-style relative paths."""
        directory = self._resolve_directory(prefix)
        if not directory.exists():
            return []
        if not directory.is_dir():
            raise NotADirectoryError(f"Vault prefix is not a directory: {prefix}")

        notes = [
            path.relative_to(self.root_path).as_posix()
            for path in directory.rglob("*.md")
            if path.is_file()
        ]
        return sorted(notes)

    def exists(self, relative_path: str | Path) -> bool:
        """Return whether a safe vault path exists."""
        return self._resolve_note_path(relative_path).exists()

    def _resolve_note_path(self, relative_path: str | Path) -> Path:
        path = self._resolve(relative_path)
        if path.exists() and path.is_dir():
            raise IsADirectoryError(f"Vault path is a directory: {relative_path}")
        return path

    def _resolve_directory(self, relative_path: str | Path) -> Path:
        return self._resolve(relative_path)

    def _resolve(self, relative_path: str | Path) -> Path:
        path = Path(relative_path)
        if path.is_absolute():
            raise ValueError(f"Vault path must be relative: {relative_path}")

        resolved = (self.root_path / path).resolve()
        if not resolved.is_relative_to(self.root_path):
            raise ValueError(f"Vault path escapes root: {relative_path}")
        return resolved


__all__ = ["Vault"]
