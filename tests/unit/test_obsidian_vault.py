"""Tests for M2 Obsidian memory."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from pio_lab.memory.obsidian import AgentsMd, SoulMd, UserMd, Vault


def test_vault_write_read_and_list_notes(tmp_path) -> None:
    vault = Vault(tmp_path)

    written = vault.write("tasks/2026-05-04/abc.md", "# Task\n")
    vault.write("knowledge/optics/note.md", "# Optics\n")

    assert written.exists()
    assert vault.read("tasks/2026-05-04/abc.md") == "# Task\n"
    assert vault.list_notes("tasks") == ["tasks/2026-05-04/abc.md"]
    assert vault.list_notes() == [
        "knowledge/optics/note.md",
        "tasks/2026-05-04/abc.md",
    ]


def test_vault_rejects_paths_outside_root(tmp_path) -> None:
    vault = Vault(tmp_path)

    with pytest.raises(ValueError):
        vault.write("../outside.md", "blocked")

    with pytest.raises(ValueError):
        vault.read(tmp_path.parent / "outside.md")


def test_soul_and_user_md_get_set(tmp_path) -> None:
    vault = Vault(tmp_path)

    SoulMd(vault).set("soul content\n")
    UserMd(vault).set("user content\n")

    assert SoulMd(vault).get() == "soul content\n"
    assert UserMd(vault).get() == "user content\n"


def test_agents_md_get_set(tmp_path) -> None:
    vault = Vault(tmp_path)
    agents = AgentsMd(vault)

    agents.set("# Manual Agents\n")

    assert agents.get() == "# Manual Agents\n"


def test_agents_md_regenerate_from_mapping_registry(tmp_path) -> None:
    vault = Vault(tmp_path)
    agents = AgentsMd(vault)
    registry = {
        "departments": [
            {
                "id": "coder",
                "name": "CODER",
                "name_vi": "Phat trien ung dung",
                "enabled": True,
                "workers": ["frontend", "backend"],
            },
            {
                "id": "qa",
                "name": "QA",
                "enabled": False,
                "workers": [{"id": "qa_reviewer"}],
            },
        ]
    }

    content = agents.regenerate(registry)

    assert "# Agents Registry" in content
    assert "## CODER (`coder`)" in content
    assert "- Workers: frontend, backend" in content
    assert "## QA (`qa`)" in content
    assert "- Status: disabled" in content
    assert agents.get() == content


def test_agents_md_regenerate_from_object_registry(tmp_path) -> None:
    vault = Vault(tmp_path)
    agents = AgentsMd(vault)
    registry = SimpleNamespace(
        departments=[
            SimpleNamespace(
                id="research",
                name="RESEARCH",
                name_vi="Nghien cuu",
                enabled=True,
                workers=[SimpleNamespace(id="optics")],
            )
        ]
    )

    content = agents.regenerate(registry)

    assert "## RESEARCH (`research`)" in content
    assert "- Workers: optics" in content
