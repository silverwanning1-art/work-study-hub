"""Loads and validates plugin and agent manifests from disk."""

import logging
from collections.abc import Callable
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from hub.manifests import AgentManifest, PluginManifest

logger = logging.getLogger(__name__)


class Registry(BaseModel):
    """All manifests the core found at startup."""

    plugins: list[PluginManifest] = []
    agents: list[AgentManifest] = []

    def get_plugin(self, plugin_id: str) -> PluginManifest | None:
        """Return the plugin with the given id, or ``None``."""
        return next((p for p in self.plugins if p.id == plugin_id), None)


def _load_dir[M: BaseModel](
    base: Path, filename: str, model: type[M], check: Callable[[M, Path], None]
) -> list[M]:
    manifests: list[M] = []
    if not base.is_dir():
        return manifests
    for path in sorted(base.glob(f"*/{filename}")):
        try:
            manifest = model.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
            check(manifest, path.parent)
        except (OSError, yaml.YAMLError, ValidationError, ValueError) as exc:
            # One broken manifest must not keep the core from starting.
            logger.error("Skipping invalid manifest %s: %s", path, exc)
            continue
        manifests.append(manifest)
    return manifests


def _check_plugin(manifest: PluginManifest, folder: Path) -> None:
    if manifest.id != folder.name:
        raise ValueError(f"id '{manifest.id}' does not match folder '{folder.name}'")


def _check_agent(manifest: AgentManifest, folder: Path) -> None:
    if manifest.id != folder.name:
        raise ValueError(f"id '{manifest.id}' does not match folder '{folder.name}'")
    if not (folder / manifest.prompt).is_file():
        raise ValueError(f"prompt file '{manifest.prompt}' not found")


def load_registry(plugins_dir: Path, agents_dir: Path) -> Registry:
    """Read all manifests below the given directories, skipping invalid ones."""
    plugins = _load_dir(plugins_dir, "plugin.yaml", PluginManifest, _check_plugin)
    agents = _load_dir(agents_dir, "agent.yaml", AgentManifest, _check_agent)
    duplicates = {p.id for p in plugins if [q.id for q in plugins].count(p.id) > 1}
    if duplicates:
        raise ValueError(f"duplicate plugin ids: {sorted(duplicates)}")
    return Registry(plugins=plugins, agents=agents)
