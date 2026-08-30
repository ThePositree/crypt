from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _load_routes() -> dict[str, Any]:
    with (ROOT / "docs/agent/context_routes.yml").open(encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
    assert isinstance(loaded, dict)
    return loaded


def _iter_route_paths(routes: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for item in routes.get("always", []):
        paths.append(item["path"])
    for route in routes.get("routes", {}).values():
        paths.extend(route.get("cards", []))
        paths.extend(route.get("full_docs", []))
    paths.extend(routes.get("fallback", {}).get("cards", []))
    return paths


def test_agent_context_routes_have_required_shape() -> None:
    routes = _load_routes()

    for route_name, route in routes["routes"].items():
        assert route.get("match"), f"{route_name} must define match terms"
        assert route.get("cards"), f"{route_name} must define card entry points"
        assert route.get("full_docs"), f"{route_name} must define full docs"
        for card in route["cards"]:
            assert card.endswith(".card.md"), f"{route_name} card must be .card.md: {card}"


def test_agent_context_routes_reference_existing_paths() -> None:
    routes = _load_routes()

    missing: list[str] = []
    for raw_path in _iter_route_paths(routes):
        path = ROOT / raw_path
        if raw_path.endswith("/"):
            if not path.is_dir():
                missing.append(raw_path)
        elif not path.is_file():
            missing.append(raw_path)

    assert missing == []


def test_agent_cards_point_to_their_full_source_docs() -> None:
    cards = sorted((ROOT / "docs").rglob("*.card.md"))
    assert cards, "expected at least one agent context card"

    missing_sources: list[str] = []
    for card in cards:
        text = card.read_text(encoding="utf-8")
        source_lines = [line for line in text.splitlines() if line.startswith("Full source: `")]
        assert len(source_lines) == 1, f"{card.relative_to(ROOT)} must declare one Full source"
        source = source_lines[0].removeprefix("Full source: `").removesuffix("`")
        if not (ROOT / source).is_file():
            missing_sources.append(f"{card.relative_to(ROOT)} -> {source}")

    assert missing_sources == []


def test_agent_cards_stay_compact() -> None:
    oversized = []
    for card in sorted((ROOT / "docs").rglob("*.card.md")):
        text = card.read_text(encoding="utf-8")
        source_line = next(
            line for line in text.splitlines() if line.startswith("Full source: `")
        )
        source = source_line.removeprefix("Full source: `").removesuffix("`")
        source_lines = len((ROOT / source).read_text(encoding="utf-8").splitlines())
        card_lines = len(text.splitlines())
        max_lines = max(40, int(source_lines * 0.45))
        if card_lines > max_lines or card_lines >= source_lines:
            oversized.append(
                f"{card.relative_to(ROOT)}: {card_lines}/{source_lines}, max {max_lines}"
            )

    assert oversized == []


def test_bootstrap_stays_small_and_points_to_routes() -> None:
    agents = ROOT / "AGENTS.md"
    text = agents.read_text(encoding="utf-8")

    assert len(text.splitlines()) <= 120
    assert "docs/agent/context_routes.yml" in text
    assert "docs/state/current.yml" in text


def test_agent_context_benchmark_has_twenty_questions() -> None:
    benchmark = ROOT / "docs/agent/context_benchmark.md"
    lines = benchmark.read_text(encoding="utf-8").splitlines()
    questions = [line for line in lines if re.match(r"^\d+\. ", line)]

    assert len(questions) == 20


def test_agent_context_machine_readable_benchmark_has_twenty_questions() -> None:
    with (ROOT / "docs/agent/context_benchmark.yml").open(encoding="utf-8") as f:
        loaded = yaml.safe_load(f)

    questions = loaded["questions"]
    assert len(questions) == 20
    assert {question["id"] for question in questions}
    for question in questions:
        assert question["expected_sources"]
        assert question["required_terms"]


def test_critical_context_has_benchmark_coverage() -> None:
    with (ROOT / "docs/agent/context_benchmark.yml").open(encoding="utf-8") as f:
        loaded = yaml.safe_load(f)

    all_sources = {
        source for question in loaded["questions"] for source in question["expected_sources"]
    }
    critical_sources = {
        "AGENTS.md",
        "docs/state/current.yml",
        "docs/agent/context_routes.yml",
        "docs/backtester_regression.md",
        "docs/strategy_benchmark.md",
        "docs/agent/ai_context_system.md",
    }

    assert critical_sources <= all_sources


def test_agent_context_cli_validate_and_budget() -> None:
    validate = subprocess.run(
        [sys.executable, "scripts/agent_context.py", "validate"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    budget = subprocess.run(
        [sys.executable, "scripts/agent_context.py", "budget", "--route", "backtester_regression"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    validate_payload = yaml.safe_load(validate.stdout)
    budget_payload = yaml.safe_load(budget.stdout)

    assert validate_payload["ok"] is True
    assert validate_payload["benchmark_questions"] == 20
    assert budget_payload["routed_approx_tokens"] < budget_payload["eager_approx_tokens"]


def test_agent_context_cli_route_and_benchmark() -> None:
    route = subprocess.run(
        [
            sys.executable,
            "scripts/agent_context.py",
            "route",
            "phase-c backtester regression replay drift",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    benchmark = subprocess.run(
        [sys.executable, "scripts/agent_context.py", "benchmark"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    route_payload = yaml.safe_load(route.stdout)
    benchmark_payload = yaml.safe_load(benchmark.stdout)

    assert route_payload["route"] == "backtester_regression"
    assert "docs/backtester_regression.card.md" in route_payload["initial_context"]
    assert benchmark_payload["ok"] is True
    assert benchmark_payload["source_hit_rate"] == 1.0
    assert benchmark_payload["required_terms_hit_rate"] == 1.0


def test_agent_context_image_pack_refuses_hard_rule_docs(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/agent_context.py",
            "image-pack",
            "--source",
            "AGENTS.md",
            "--output",
            str(tmp_path / "images"),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "not allowed for image-pack experiments" in result.stderr


def _frontend_docs() -> tuple[str, str]:
    full = " ".join(
        (ROOT / "docs/agent/frontend_design_subsystem.md")
        .read_text(encoding="utf-8")
        .split()
    )
    card = " ".join(
        (ROOT / "docs/agent/frontend_design_subsystem.card.md")
        .read_text(encoding="utf-8")
        .split()
    )
    return full, card


def test_frontend_prompt_contract_and_depth_are_explicit() -> None:
    full, card = _frontend_docs()

    for term in [
        "## Instruction Model",
        "**Outcome**",
        "**Scope**",
        "**Sources of truth**",
        "**Constraints**",
        "**Acceptance evidence**",
        "**Unknowns**",
        "## Depth Classification",
        "| D0 |",
        "| D1 |",
        "| D2 |",
        "| D3 |",
    ]:
        assert term in full
    assert "## Start With A Task Contract" in card
    assert "Classify depth" in card


def test_frontend_owner_can_redirect_onboarding_and_work_at_any_time() -> None:
    full, card = _frontend_docs()

    for term in [
        "## Owner Steering Contract",
        "they may interrupt, correct an assumption, reject a proposal",
        "skip a question",
        "provide their own alternative",
        "Do not force the owner back into the questionnaire format",
        "questions are navigation, not a form they must obey",
    ]:
        assert term in full
    assert "may interrupt, correct assumptions" in card
    assert "questions are navigation, not a form" in card


def test_frontend_subagents_require_availability_check_and_owner_choice() -> None:
    full, card = _frontend_docs()

    for term in [
        "## Collaboration Check",
        "available: yes / no / unknown",
        "required interface or orchestration system",
        "available agent/provider/model choices",
        "ask the owner whether subagents should be used",
        "Silence is not approval",
        "A decline does not block progress",
        "Do not create a worker before the owner answers",
    ]:
        assert term in full
    assert "run a Collaboration Check" in card
    assert "Ask the owner whether to use subagents" in card
    assert "Silence is not approval" in card


def test_frontend_established_practices_remain_covered() -> None:
    full, card = _frontend_docs()

    required_sections = [
        "## First-Use Discovery",
        "## Product Knowledge Discovery",
        "## Product Surface Model",
        "## Design Onboarding",
        "## Visual Exploration",
        "## Final Design Identity And Design System",
        "## UX Flows",
        "## Wireframes",
        "## Screen Contracts",
        "## Action Contract",
        "## Responsive Design Pass",
        "## Functional QA",
        "## Visual QA And Review Protocol",
        "## Product Completeness Review",
        "## Phase Handoffs And Independent Review",
        "## Persistent Frontend Memory",
    ]
    for section in required_sections:
        assert section in full

    assert "at least 30 questions in adaptive rounds of five" in full
    assert "five rendered Visual Direction Boards" in full
    assert "component-primitives area" in full
    assert "five separate rendered HTML board pages" in full
    assert "Orca Browser" in full
    assert "Context7" in full
    assert "minimum of 30 adaptive questions" in card
    assert "five rendered Visual Direction Boards" in card


def test_frontend_owner_gates_and_scoped_waivers_remain_explicit() -> None:
    full, card = _frontend_docs()

    for gate in [
        "### Product Surface Approval",
        "### Visual Direction Approval",
        "### Wireframe Approval",
        "## Final Implementation Approval",
    ]:
        assert gate in full
    assert "scoped waiver" in full.lower()
    for gate_name in [
        "Product Surface Approval",
        "Visual Direction Approval",
        "Wireframe Approval",
        "Final Implementation Approval",
    ]:
        assert gate_name in card


def test_frontend_artifacts_have_task_proportional_triggers() -> None:
    full, _ = _frontend_docs()

    assert "Use the smallest depth" in full
    assert "A purely visual D0 change may reference an unchanged flow" in full
    assert "For D0 changes that do not affect those properties" in full
    assert "Safety risk is independent of design depth" in full
    assert "Action Contract even when its design depth is D0" in full


def test_frontend_prompt_guidance_avoids_unverifiable_rituals() -> None:
    full, card = _frontend_docs()

    for term in [
        "Do not rely on role-play, magic wording, forced chain-of-thought",
        "Separate instructions from quoted content",
        "Use examples when they define a format, state, boundary, or quality bar",
        "model/tool identity and date",
        "Do not claim a check was completed without its evidence",
    ]:
        assert term in full
    assert "Avoid role-play, magic wording, forced chain-of-thought" in card


def test_frontend_qa_requires_observable_evidence() -> None:
    full, card = _frontend_docs()

    for term in [
        "## QA Evidence Record",
        "- Viewports and screenshots:",
        "- Interactions exercised:",
        "- Automated checks:",
        "- Console/network status:",
        "- Accessibility checks:",
        "- Functional QA verdict:",
        "- Visual QA verdict:",
        "- Product Completeness verdict:",
    ]:
        assert term in full
    assert "evidence under `docs/frontend/reviews/`" in card


def test_frontend_memory_templates_capture_evidence_and_revisions() -> None:
    required_terms_by_file = {
        "context.md": ["Last verified:", "Sources Inspected", "Confidence:"],
        "design-identity.md": ["Revision:", "Evidence:", "Model and tools used:"],
        "design-system.md": ["Revision:", "## Validation", "Known exceptions:"],
        "component-registry.md": ["Accessibility behavior:", "Validation evidence:"],
        "product-surface-model.md": [
            "Revision:",
            "Scope Contract",
            "Approval Record",
            "Collaboration Record",
            "Owner decision: pending / approved / declined",
        ],
    }

    for relative_path, terms in required_terms_by_file.items():
        text = (ROOT / "docs/frontend" / relative_path).read_text(encoding="utf-8")
        for term in terms:
            assert term in text


def test_frontend_flow_wireframe_and_screen_contracts_stay_routed() -> None:
    flows = " ".join(
        (ROOT / "docs/frontend/flows/README.md").read_text(encoding="utf-8").split()
    )
    wireframes = " ".join(
        (ROOT / "docs/frontend/wireframes/README.md")
        .read_text(encoding="utf-8")
        .split()
    )
    screens = " ".join(
        (ROOT / "docs/frontend/screens/README.md")
        .read_text(encoding="utf-8")
        .split()
    )

    assert "Mermaid is the default" in flows
    assert "failure and recovery path" in flows
    assert "persistent HTML/CSS/JS wireframes" in wireframes
    assert "labeled gray blocks" in wireframes
    assert "relevant project breakpoints" in wireframes
    assert "## Data Sources And Trust Boundaries" in screens
    assert "## Acceptance Criteria" in screens

    routes = _load_routes()
    frontend_full_docs = routes["routes"]["frontend_design"]["full_docs"]
    for path in [
        "docs/frontend/flows/",
        "docs/frontend/wireframes/",
        "docs/frontend/screens/",
    ]:
        assert path in frontend_full_docs
