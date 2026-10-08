import asyncio
from pathlib import Path

import pytest
import server
from mcp import Client
from server import VaultError, iter_notes, obsidian_uri, resolve_note, search_notes


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "vault"
    (root / "02-Areas" / "Logistik").mkdir(parents=True)
    (root / ".obsidian").mkdir()
    (root / "02-Areas" / "Logistik" / "Lager.md").write_text("Das Lager nutzt FIFO und LIFO.")
    (root / "02-Areas" / "Notiz.md").write_text("Lagerhaltung: Bestellpunkt und FIFO.\n" * 2)
    (root / ".obsidian" / "secret.md").write_text("FIFO versteckt")
    (root / "bild.png").write_bytes(b"\x89PNG")
    outside = tmp_path / "outside.md"
    outside.write_text("FIFO geheim")
    (root / "link.md").symlink_to(outside)
    monkeypatch.setattr(server, "VAULT_ROOT", root)
    return root


def test_list_skips_hidden_symlinks_and_non_notes(vault: Path) -> None:
    names = [p.as_posix() for p in iter_notes(root=vault)]
    assert names == ["02-Areas/Logistik/Lager.md", "02-Areas/Notiz.md"]


def test_list_in_folder(vault: Path) -> None:
    assert [p.name for p in iter_notes("02-Areas/Logistik", root=vault)] == ["Lager.md"]


@pytest.mark.parametrize(
    "bad", ["../outside.md", "/etc/passwd", ".obsidian/secret.md", "link.md", "bild.png", "x.md"]
)
def test_read_rejects_unsafe_or_unknown_paths(vault: Path, bad: str) -> None:
    with pytest.raises(VaultError):
        resolve_note(bad, root=vault)


def test_list_rejects_traversal_and_hidden(vault: Path) -> None:
    for bad in ["..", "../..", ".obsidian", "/etc"]:
        with pytest.raises(VaultError):
            iter_notes(bad, root=vault)


def test_search_finds_all_terms_and_ranks(vault: Path) -> None:
    hits = search_notes("fifo lager", root=vault)
    assert [h["path"] for h in hits] == ["02-Areas/Notiz.md", "02-Areas/Logistik/Lager.md"]
    assert "FIFO" in hits[0]["snippet"]
    assert hits[1]["citation"] == "[Quelle: Lager.md]"
    assert search_notes("gibtesnicht", root=vault) == []


def test_search_never_returns_hidden_or_symlinked_content(vault: Path) -> None:
    paths = [h["path"] for h in search_notes("geheim versteckt fifo", root=vault)]
    assert paths == []


@pytest.mark.parametrize(("query", "limit"), [("", 5), ("   ", 5), ("x", 0), ("x", 51)])
def test_search_rejects_bad_input(vault: Path, query: str, limit: int) -> None:
    with pytest.raises(VaultError):
        search_notes(query, limit, root=vault)


def test_obsidian_uri_encodes_path() -> None:
    uri = obsidian_uri(Path("02-Areas/Mein Fach/Notiz.md"))
    assert uri == "obsidian://open?vault=WiIng-Vault&file=02-Areas/Mein%20Fach/Notiz"


def test_tools_are_read_only_and_exposed_over_mcp(vault: Path) -> None:
    async def run() -> tuple[list[str], str]:
        async with Client(server.server) as client:
            tools = await client.list_tools()
            result = await client.call_tool("read_note", {"path": "02-Areas/Logistik/Lager.md"})
        return [t.name for t in tools.tools], result.content[0].text  # type: ignore[union-attr]

    names, text = asyncio.run(run())
    assert sorted(names) == ["list_notes", "read_note", "search"]
    assert "FIFO und LIFO" in text
