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
        line_count = len(card.read_text(encoding="utf-8").splitlines())
        if line_count > 80:
            oversized.append(f"{card.relative_to(ROOT)}: {line_count}")

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


def test_frontend_design_subsystem_has_onboarding_stop_gate() -> None:
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

    required_full_terms = [
        "Non-Negotiable Gates",
        "frontend memory is not established",
        "state-based gate, not only a new-site gate",
        "first serious frontend task",
        "owner answering the first onboarding round does not mean frontend memory is established",
        "First-time frontend onboarding is a deep multi-step discovery process",
        "asks at least 30 questions",
        "Uncertainty Check",
        "There is no fixed questionnaire",
        "Each Visual Direction Board is a rendered visual artifact plus short notes",
        "design onboarding interview",
        "five Visual Direction Boards",
        "grounded in owner answers, inferred existing product evidence, or explicit owner approval",
    ]
    required_card_terms = [
        "If frontend memory is not established",
        "first serious frontend task",
        "An owner's first answer to onboarding questions is not enough",
        "First-time frontend onboarding is deep",
        "at least 30 questions",
        "Uncertainty Check",
        "Visual Direction Boards are rendered direction studies plus notes",
        "Owner feedback selects, mixes, rejects, or iterates them",
    ]

    for term in required_full_terms:
        assert term in full
    for term in required_card_terms:
        assert term in card


def test_frontend_design_subsystem_requires_stack_and_interaction_qa() -> None:
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

    required_full_terms = [
        "minimum-30 / 5-question-round protocol",
        "remaining unknowns",
        "ask the next 5-question round",
        "implementation technology is also a gated decision",
        "Missing framework requirements are treated as unresolved stack input",
        "narrow mobile",
        "large desktop or wide monitor",
        "exercises every added interactive zone",
        "Click or activate every added button, link, tab, menu",
    ]
    required_card_terms = [
        "adaptive rounds of 5",
        "lightweight static stack or a framework/UI-library stack",
        "desktop, mobile, intermediate, and large viewport breakpoints",
        "Exercise every added interactive element",
    ]

    for term in required_full_terms:
        assert term in full
    for term in required_card_terms:
        assert term in card


def test_frontend_design_subsystem_requires_product_surface_model() -> None:
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
    model = " ".join(
        (ROOT / "docs/frontend/product-surface-model.md")
        .read_text(encoding="utf-8")
        .split()
    )

    required_full_terms = [
        "Product Knowledge Discovery",
        "Product Surface Model",
        "DISCOVER | INFER FROM EXISTING PRODUCT KNOWLEDGE",
        "Completeness comes before decoration",
        "Product Completeness Review",
        "visual direction serving that surface",
        "Functional QA: does it work?",
        "Visual QA: does it look and feel right",
    ]
    required_card_terms = [
        "discover existing product knowledge",
        "Build a Product Surface Model",
        "Product Completeness Review",
        "removing CSS would still leave a complete useful product surface",
    ]
    required_model_terms = [
        "Product Knowledge Sources",
        "User Capabilities And Goals",
        "Required Content And Features",
        "Information Architecture",
        "Completeness Review",
    ]

    for term in required_full_terms:
        assert term in full
    for term in required_card_terms:
        assert term in card
    for term in required_model_terms:
        assert term in model


def test_frontend_design_subsystem_requires_responsive_design_pass() -> None:
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

    required_full_terms = [
        "Responsive Design Pass",
        "Responsive design is intentional composition beyond layout survival",
        "designed composition of the same product",
        "Responsive Transformation Reasoning",
        "best preserves the function of the original element",
        "each important viewport as its own composition",
    ]
    required_card_terms = [
        "Responsive Design Pass",
        "Responsive design goes beyond layout survival",
        "each viewport feels intentionally composed",
        "responsive transformations preserve hierarchy",
    ]

    for term in required_full_terms:
        assert term in full
    for term in required_card_terms:
        assert term in card


def test_frontend_design_subsystem_requires_phase_handoff_strategy() -> None:
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

    required_full_terms = [
        "Phase Handoff Strategy",
        "Large frontend tasks are split into phases",
        "durable handoff artifact",
        "Handoff files are temporary technical artifacts",
        "delete the consumed handoff file",
        "Canonical files are the source of truth after each phase",
        "isolated subagent",
        "fresh user session handoff",
        "Already loaded conversation history remains physically present",
        "continue in the current session only if context remains manageable",
    ]
    required_card_terms = [
        "Large frontend tasks must be split into phases",
        "Phase Handoff Strategy",
        "durable handoff artifact",
        "Handoff is temporary",
        "canonical files are source of truth",
        "consumed handoff files are deleted",
        "isolated subagent if supported and reliable",
        "fresh user session handoff",
        "Loaded conversation remains until compaction/replacement",
        "current session only if context remains manageable",
    ]

    for term in required_full_terms:
        assert term in full
    for term in required_card_terms:
        assert term in card


def test_frontend_design_subsystem_requires_owner_decision_gates() -> None:
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

    required_full_terms = [
        "Owner Decision Gates",
        "Interview completed != Onboarding completed != Design approved != Ready for implementation",
        "Stack Gate",
        "Product Surface Gate",
        "Visual Direction Gate",
        "Scope/Completeness Gate",
        "Final Pre-Implementation Gate",
        "collect owner feedback",
        "rendered Visual Direction Boards",
        "Final Pre-Implementation Gate",
        "Implementation begins after owner confirmation",
    ]
    required_card_terms = [
        "Interview completed is not onboarding completed",
        "Owner Decision Gates",
        "Owner feedback selects, mixes, rejects, or iterates them",
        "rendered direction studies",
        "Final Design Identity, Design System, and implementation follow the required owner gates",
    ]

    for term in required_full_terms:
        assert term in full
    for term in required_card_terms:
        assert term in card


def test_frontend_design_subsystem_requires_mermaid_and_wireframe_contracts() -> None:
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
    flows = " ".join(
        (ROOT / "docs/frontend/flows/README.md").read_text(encoding="utf-8").split()
    )
    wireframes = " ".join(
        (ROOT / "docs/frontend/wireframes/README.md")
        .read_text(encoding="utf-8")
        .split()
    )
    screens = " ".join(
        (ROOT / "docs/frontend/screens/README.md").read_text(encoding="utf-8").split()
    )

    required_full_terms = [
        "UI Contract Gate",
        "Mermaid flow contracts and HTML/CSS/JS wireframes",
        "Mermaid is the default format for user flows, navigation maps, and state diagrams",
        "Wireframes are persistent screen contracts",
        "render gray-box page layouts",
        "block-level descriptions for complex elements",
        "interaction notes for accordions, tabs, collapses",
        "responsive states for the important viewport widths",
        "Owner feedback updates the wireframes",
        "owner approval",
    ]
    required_card_terms = [
        "UI Contract Gate",
        "Mermaid user flow, navigation, or state diagrams",
        "HTML/CSS/JS wireframes",
        "get owner approval before production UI code changes",
    ]
    required_route_paths = [
        "docs/frontend/wireframes/",
    ]

    for term in required_full_terms:
        assert term in full
    for term in required_card_terms:
        assert term in card
    for term in [
        "Mermaid is the default format for user flows, navigation maps, and state diagrams",
        "Keep them current with related wireframes and screen contracts",
    ]:
        assert term in flows
    for term in [
        "persistent HTML/CSS/JS wireframes",
        "durable UI contracts",
        "labeled blocks",
        "Show rendered wireframes to the owner",
    ]:
        assert term in wireframes
    assert "related Mermaid flows and HTML/CSS/JS wireframes" in screens

    routes = _load_routes()
    frontend_full_docs = routes["routes"]["frontend_design"]["full_docs"]
    for path in required_route_paths:
        assert path in frontend_full_docs
