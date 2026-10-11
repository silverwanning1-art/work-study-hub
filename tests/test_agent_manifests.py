from pathlib import Path

from hub.registry import load_registry
from hub.skills import load_skills

ROOT = Path(__file__).parents[1]


def test_repo_agents_and_plugins_are_valid() -> None:
    registry = load_registry(ROOT / "plugins", ROOT / "agents")
    assert {a.id for a in registry.agents} >= {"lern-coach"}
    assert {p.id for p in registry.plugins} >= {"source-rag", "source-vault", "action-study"}


def test_lern_coach_has_no_study_database_tools() -> None:
    """Agents must not reach the learning database (ADR-004)."""
    agent = next(a for a in load_registry(ROOT / "plugins", ROOT / "agents").agents)
    assert not any(pattern.startswith("action-study") for pattern in agent.tools)


def test_lern_coach_skills_load() -> None:
    skills = load_skills(ROOT / "agents" / "lern-coach")
    assert {"karteikarten-erstellen", "pruefung-nach-prof-profil", "antworten-bewerten"} <= set(
        skills
    )
    for name in ("karteikarten-erstellen", "pruefung-nach-prof-profil", "antworten-bewerten"):
        assert "```json" in skills[name].body
