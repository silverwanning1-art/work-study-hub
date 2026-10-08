from pathlib import Path

import pytest

from hub.skills import load_skills, parse_skill


def test_parse_skill() -> None:
    skill = parse_skill("---\nname: a-b\ndescription: Desc\n---\nBody\n", "a-b")
    assert (skill.name, skill.description, skill.body) == ("a-b", "Desc", "Body\n")


@pytest.mark.parametrize(
    "text",
    [
        "no frontmatter",
        "---\nname: x\n---\nBody\n",
        "---\nname: Bad Name\ndescription: d\n---\nB\n",
    ],
)
def test_parse_skill_rejects_invalid(text: str) -> None:
    with pytest.raises(ValueError):
        parse_skill(text, "x")


def test_name_must_match_folder() -> None:
    with pytest.raises(ValueError):
        parse_skill("---\nname: a\ndescription: d\n---\nB\n", "b")


def test_load_skills_skips_invalid(tmp_path: Path) -> None:
    good = tmp_path / "skills" / "good"
    bad = tmp_path / "skills" / "bad"
    good.mkdir(parents=True)
    bad.mkdir(parents=True)
    (good / "SKILL.md").write_text("---\nname: good\ndescription: d\n---\nB\n")
    (bad / "SKILL.md").write_text("broken")
    assert list(load_skills(tmp_path)) == ["good"]


def test_no_skills_folder(tmp_path: Path) -> None:
    assert load_skills(tmp_path) == {}
