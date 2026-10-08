"""Agent skills: ``agents/<id>/skills/<name>/SKILL.md`` with a small YAML frontmatter."""

import logging
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)

MAX_SKILL_BYTES = 50_000
_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)


class Skill(BaseModel):
    """A skill an agent can load on demand via the ``load_skill`` tool."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    description: str = Field(min_length=1, max_length=300)
    body: str


def parse_skill(text: str, folder_name: str) -> Skill:
    """Parse one ``SKILL.md``; the frontmatter name must equal the folder name."""
    match = _FRONTMATTER.match(text)
    if match is None:
        raise ValueError("missing frontmatter")
    meta = yaml.safe_load(match.group(1))
    if not isinstance(meta, dict):
        raise ValueError("frontmatter must be a mapping")
    skill = Skill(name=meta.get("name", ""), description=meta.get("description", ""), body=match[2])
    if skill.name != folder_name:
        raise ValueError(f"name '{skill.name}' does not match folder '{folder_name}'")
    return skill


def load_skills(agent_dir: Path) -> dict[str, Skill]:
    """Load all valid skills of an agent; invalid ones are skipped and logged."""
    skills: dict[str, Skill] = {}
    for path in sorted((agent_dir / "skills").glob("*/SKILL.md")):
        try:
            if path.stat().st_size > MAX_SKILL_BYTES:
                raise ValueError("skill file is too large")
            skill = parse_skill(path.read_text(encoding="utf-8"), path.parent.name)
        except (OSError, yaml.YAMLError, ValidationError, ValueError) as exc:
            logger.error("Skipping invalid skill %s: %s", path, exc)
            continue
        skills[skill.name] = skill
    return skills
