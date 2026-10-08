"""Source plugin: a read-only MCP server for an Obsidian vault.

The vault is mounted read-only into the container (ADR-003). On top of that, every path is
resolved against the vault root and rejected if it leaves it, is hidden, or is not a note.
"""

import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

from mcp.server.mcpserver import MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse

VAULT_ROOT = Path(os.environ.get("VAULT_PATH", "/vault"))
VAULT_NAME = os.environ.get("VAULT_NAME", "WiIng-Vault")
NOTE_SUFFIX = ".md"
MAX_NOTE_BYTES = 1_000_000
MAX_RESULTS = 50
SNIPPET_RADIUS = 120

server = MCPServer("source-vault")


class VaultError(ValueError):
    """Raised for paths or queries the vault server refuses to handle."""


def _is_hidden(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)


def resolve_note(relative: str, root: Path | None = None) -> Path:
    """Resolve ``relative`` to a note inside the vault, or raise ``VaultError``."""
    base = (root or VAULT_ROOT).resolve()
    rel = Path(relative)
    if rel.is_absolute() or _is_hidden(rel):
        raise VaultError("path is not allowed")
    target = (base / rel).resolve()
    if not target.is_relative_to(base):
        raise VaultError("path is outside the vault")
    if target.suffix != NOTE_SUFFIX or not target.is_file():
        raise VaultError("note not found")
    return target


def iter_notes(folder: str = "", root: Path | None = None) -> list[Path]:
    """Return note paths relative to the vault, sorted; hidden folders and symlinks are skipped."""
    base = (root or VAULT_ROOT).resolve()
    start = base
    if folder:
        rel = Path(folder)
        start = (base / rel).resolve()
        if rel.is_absolute() or _is_hidden(rel) or not start.is_relative_to(base):
            raise VaultError("path is not allowed")
        if not start.is_dir():
            raise VaultError("folder not found")
    notes: list[Path] = []
    for current, dirs, files in os.walk(start, followlinks=False):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            path = Path(current) / name
            if name.endswith(NOTE_SUFFIX) and not name.startswith(".") and not path.is_symlink():
                notes.append(path.relative_to(base))
    return sorted(notes)


def obsidian_uri(relative: Path) -> str:
    """Link that opens the note in the Obsidian app."""
    file = quote(str(relative.with_suffix("")))
    return f"obsidian://open?vault={quote(VAULT_NAME)}&file={file}"


def _read(path: Path) -> str:
    if path.stat().st_size > MAX_NOTE_BYTES:
        raise VaultError("note is too large")
    return path.read_text(encoding="utf-8", errors="replace")


def _snippet(text: str, term: str) -> str:
    index = text.lower().find(term)
    if index < 0:
        return text[: 2 * SNIPPET_RADIUS].strip()
    start = max(0, index - SNIPPET_RADIUS)
    return text[start : index + len(term) + SNIPPET_RADIUS].strip()


def search_notes(query: str, limit: int = 10, root: Path | None = None) -> list[dict[str, Any]]:
    """Case-insensitive search; every word of ``query`` must occur in the note or its path."""
    terms = query.lower().split()
    if not terms:
        raise VaultError("query must not be empty")
    if not 1 <= limit <= MAX_RESULTS:
        raise VaultError(f"limit must be between 1 and {MAX_RESULTS}")
    base = (root or VAULT_ROOT).resolve()
    hits: list[tuple[int, Path, str]] = []
    for relative in iter_notes(root=base):
        try:
            text = _read(base / relative)
        except (VaultError, OSError):
            continue
        haystack = f"{relative.as_posix()}\n{text}".lower()
        if all(term in haystack for term in terms):
            score = sum(haystack.count(term) for term in terms)
            hits.append((score, relative, _snippet(text, terms[0])))
    hits.sort(key=lambda hit: (-hit[0], hit[1]))
    return [
        {
            "path": relative.as_posix(),
            "snippet": snippet,
            "score": score,
            "obsidian_uri": obsidian_uri(relative),
            "citation": f"[Quelle: {relative.name}]",
        }
        for score, relative, snippet in hits[:limit]
    ]


@server.tool()
def search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search the vault notes; returns path, snippet, Obsidian link and a citation."""
    return search_notes(query, limit)


@server.tool()
def read_note(path: str) -> dict[str, Any]:
    """Read one note by its vault-relative path, e.g. ``02-Areas/Fach/Notiz.md``."""
    note = resolve_note(path)
    relative = note.relative_to(VAULT_ROOT.resolve())
    return {
        "path": relative.as_posix(),
        "content": _read(note),
        "obsidian_uri": obsidian_uri(relative),
        "citation": f"[Quelle: {relative.name}]",
    }


@server.tool()
def list_notes(folder: str = "", limit: int = 200) -> list[str]:
    """List note paths, optionally below a vault-relative ``folder``."""
    return [p.as_posix() for p in iter_notes(folder)[:limit]]


@server.custom_route("/health", methods=["GET"])  # type: ignore[untyped-decorator]
async def health(_request: Request) -> JSONResponse:
    """Liveness check for the container runtime."""
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    server.run("streamable-http", host="0.0.0.0", port=8000)  # noqa: S104 - container-internal
