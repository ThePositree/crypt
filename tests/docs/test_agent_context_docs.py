from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SUBSYSTEM_PATH = ROOT / "docs/agent/frontend_design_subsystem.md"


def normalized(text: str) -> str:
    return " ".join(text.split())


def test_frontend_instruction_version_matches_current_state() -> None:
    current = yaml.safe_load((ROOT / "docs/state/current.yml").read_text())
    subsystem = normalized(SUBSYSTEM_PATH.read_text())

    version = current["canonical_docs"]["frontend_instruction_version"]
    assert f"Version: {version}" in subsystem


def test_independent_context_roles_and_boundaries_are_explicit() -> None:
    subsystem = normalized(SUBSYSTEM_PATH.read_text())

    required = (
        "### Independent Execution Contexts",
        "Contract Reviewer",
        "First-Use Reviewer",
        "Content Author",
        "Copy Reviewer",
        "Implementation QA Reviewer",
        "Explicitly forbid this reviewer from reading repository files",
        "Do not infer collaboration approval",
    )
    for phrase in required:
        assert phrase in subsystem


def test_wireframes_default_to_demonstration_not_production_behavior() -> None:
    subsystem = normalized(SUBSYSTEM_PATH.read_text())
    wireframe_template = normalized(
        (ROOT / "docs/frontend/wireframes/README.md").read_text()
    )

    assert "D2/D3 wireframes default to W1" in subsystem
    assert "W3: a functional prototype only after explicit owner approval" in subsystem
    assert "They are not early production applications" in subsystem
    assert "real full-text search or ranking" in subsystem
    assert "Behavior deferred to production" in normalized(
        (ROOT / "docs/frontend/screens/README.md").read_text()
    )
    assert "W3 functional prototypes require explicit owner approval" in wireframe_template
    assert "Every promised control must work" not in wireframe_template


def test_first_use_review_is_repository_blind() -> None:
    reviews = normalized((ROOT / "docs/frontend/reviews/README.md").read_text())

    assert "Independent First-Use Review" in reviews
    assert "must not read repository files" in reviews
    assert "two-to-five-sentence product description" in reviews
