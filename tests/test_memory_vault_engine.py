"""
tests/test_memory_vault_engine.py — Unit tests for the local Markdown Memory Vault & Graph engine.
"""

import tempfile
import pytest
from pathlib import Path
from memory.vault_engine import VaultEngine


@pytest.fixture
def temp_vault():
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = VaultEngine(vault_dir=Path(tmpdir))
        yield engine


def test_vault_engine_bootstrap(temp_vault):
    notes = temp_vault.get_all_notes()
    assert len(notes) >= 3, "Vault must bootstrap default starter markdown notes"
    
    titles = [n["title"].lower() for n in notes]
    assert any("hamza" in t for t in titles), "User profile note must be created"
    assert any("zezo" in t for t in titles), "Project note must be created"


def test_vault_engine_wikilink_graph_extraction(temp_vault):
    graph = temp_vault.get_graph()
    assert graph["status"] == "success"
    assert len(graph["nodes"]) >= 3
    assert len(graph["links"]) >= 2
    
    # Check node structure
    first_node = graph["nodes"][0]
    assert "id" in first_node
    assert "label" in first_node
    assert "category" in first_node
    assert "color" in first_node


def test_vault_engine_crud(temp_vault):
    # 1. Create Note
    res = temp_vault.create_note(
        title="Custom Test Architecture",
        category="project",
        content="Testing connection to [[Hamza Bukhari]] and [[ZEZO OS]].",
        tags=["unit_test", "architecture"],
    )
    assert res["status"] == "success"
    file_name = res["file"]

    # 2. Read Note
    note = temp_vault.get_note_content(file_name)
    assert note is not None
    assert note["title"] == "Custom Test Architecture"
    assert "Hamza Bukhari" in note["outbound_links"]
    assert "ZEZO OS" in note["outbound_links"]

    # 3. Update Note
    save_res = temp_vault.save_note(file_name, "# Custom Architecture Updated\n\nNew edited content.")
    assert save_res["status"] == "success"
    updated_note = temp_vault.get_note_content(file_name)
    assert "Custom Architecture Updated" in updated_note["content"]

    # 4. Delete Note
    del_res = temp_vault.delete_note(file_name)
    assert del_res["status"] == "success"
    assert temp_vault.get_note_content(file_name) is None

