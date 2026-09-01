from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROUTES_PATH = ROOT / "docs/agent/context_routes.yml"
BENCHMARK_PATH = ROOT / "docs/agent/context_benchmark.yml"
DEFAULT_EAGER_DOCS = [
    "README.md",
    "AGENTS.md",
    "docs/strategy_benchmark.md",
    "docs/backtester_regression.md",
    "docs/tasks/ROADMAP.md",
    "docs/tasks/IN_PROGRESS.md",
    "docs/tasks/IDEAS.md",
    "docs/tasks/BACKLOG.md",
    "CHANGELOG.md",
]
IMAGE_PACK_ALLOWED_FILES = {
    "CHANGELOG_ARCHIVE.md",
}
IMAGE_PACK_ALLOWED_DIRS = {
    "docs/archive",
    "docs/decisions",
}


@dataclass(frozen=True)
class Budget:
    path: str
    chars: int
    words: int
    approx_tokens: int


@dataclass(frozen=True)
class RouteSelection:
    route: str
    score: int
    matched_terms: list[str]
    full_docs: list[str]


def _repo_path(raw: str) -> Path:
    path = ROOT / raw
    return path.resolve()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
    if not isinstance(loaded, dict):
        raise ValueError(f"{_relative(path)} must contain a YAML object")
    return loaded


def _text_budget(raw_path: str) -> Budget:
    path = _repo_path(raw_path)
    if path.is_dir():
        text = "\n".join(
            child.read_text(encoding="utf-8", errors="ignore")
            for child in sorted(path.rglob("*.md"))
            if child.is_file()
        )
    else:
        text = path.read_text(encoding="utf-8")
    return Budget(
        path=raw_path,
        chars=len(text),
        words=len(text.split()),
        approx_tokens=max(1, len(text) // 4),
    )


def _normalize_terms(text: str) -> set[str]:
    return {term for term in re.split(r"[^a-z0-9_]+", text.lower()) if term}


def _route_term_matches(route_term: str, question_terms: set[str]) -> bool:
    route_terms = _normalize_terms(route_term)
    return bool(route_terms) and route_terms.issubset(question_terms)


def _route_doc_paths(route_name: str) -> list[str]:
    routes = _load_yaml(ROUTES_PATH)
    selected = routes["routes"][route_name]
    paths = [item["path"] for item in routes["always"]]
    paths.extend(selected.get("full_docs", []))
    return list(dict.fromkeys(paths))


def select_route(question: str) -> RouteSelection:
    routes = _load_yaml(ROUTES_PATH)
    question_terms = _normalize_terms(question)
    best_name = "fallback"
    best_score = 0
    best_matches: list[str] = []
    best_route: dict[str, Any] = {}

    for route_name, route in routes.get("routes", {}).items():
        matches = [term for term in route.get("match", []) if _route_term_matches(term, question_terms)]
        score = len(matches)
        if score > best_score:
            best_name = route_name
            best_score = score
            best_matches = matches
            best_route = route

    if not best_route:
        fallback = routes.get("fallback", {})
        return RouteSelection(
            route=best_name,
            score=best_score,
            matched_terms=best_matches,
            full_docs=fallback.get("full_docs", []),
        )

    return RouteSelection(
        route=best_name,
        score=best_score,
        matched_terms=best_matches,
        full_docs=best_route.get("full_docs", []),
    )


def route_report(question: str) -> dict[str, Any]:
    routes = _load_yaml(ROUTES_PATH)
    selection = select_route(question)
    always = [item["path"] for item in routes.get("always", [])]
    initial_context = list(dict.fromkeys([*always, *selection.full_docs]))

    return {
        "question": question,
        "route": selection.route,
        "score": selection.score,
        "matched_terms": selection.matched_terms,
        "initial_context": initial_context,
        "full_doc_candidates": selection.full_docs,
        "budget": {
            "initial_context_approx_tokens": sum(_text_budget(path).approx_tokens for path in initial_context),
            "initial_context_paths": len(initial_context),
        },
    }


def validate_context() -> dict[str, Any]:
    routes = _load_yaml(ROUTES_PATH)
    benchmark = _load_yaml(BENCHMARK_PATH)
    route_paths: list[str] = []

    for item in routes.get("always", []):
        route_paths.append(item["path"])
    for route in routes.get("routes", {}).values():
        route_paths.extend(route.get("full_docs", []))
    route_paths.extend(routes.get("fallback", {}).get("full_docs", []))

    missing = []
    for raw_path in route_paths:
        path = _repo_path(raw_path)
        if raw_path.endswith("/"):
            if not path.is_dir():
                missing.append(raw_path)
        elif not path.is_file():
            missing.append(raw_path)

    questions = benchmark.get("questions", [])
    if not isinstance(questions, list):
        raise ValueError("docs/agent/context_benchmark.yml questions must be a list")

    return {
        "route_paths": len(route_paths),
        "missing_route_paths": missing,
        "benchmark_questions": len(questions),
        "ok": not missing and len(questions) > 0,
    }


def budget_report(route_name: str) -> dict[str, Any]:
    eager = [_text_budget(path) for path in DEFAULT_EAGER_DOCS if _repo_path(path).exists()]
    routed = [_text_budget(path) for path in _route_doc_paths(route_name)]
    eager_tokens = sum(item.approx_tokens for item in eager)
    routed_tokens = sum(item.approx_tokens for item in routed)
    savings_pct = round((1 - routed_tokens / eager_tokens) * 100, 2) if eager_tokens else 0.0

    return {
        "route": route_name,
        "eager": [item.__dict__ for item in eager],
        "routed": [item.__dict__ for item in routed],
        "eager_approx_tokens": eager_tokens,
        "routed_approx_tokens": routed_tokens,
        "approx_savings_pct": savings_pct,
    }


def retrieval_benchmark() -> dict[str, Any]:
    benchmark = _load_yaml(BENCHMARK_PATH)
    rows = []
    source_hits = 0
    term_hits = 0
    total = 0

    for question in benchmark["questions"]:
        total += 1
        selected = route_report(question["question"])
        candidate_sources = set(selected["initial_context"]) | set(selected["full_doc_candidates"])
        expected_sources = set(question["expected_sources"])
        required_terms = question["required_terms"]
        source_hit = bool(candidate_sources & expected_sources)
        terms_text = "\n".join(
            _repo_path(path).read_text(encoding="utf-8", errors="ignore")
            for path in candidate_sources
            if _repo_path(path).is_file()
        ).lower()
        required_terms_hit = all(str(term).lower() in terms_text for term in required_terms)

        source_hits += int(source_hit)
        term_hits += int(required_terms_hit)
        rows.append(
            {
                "id": question["id"],
                "route": selected["route"],
                "source_hit": source_hit,
                "required_terms_hit": required_terms_hit,
                "expected_sources": sorted(expected_sources),
                "candidate_sources": sorted(candidate_sources),
                "missing_terms": [
                    term for term in required_terms if str(term).lower() not in terms_text
                ],
            }
        )

    return {
        "questions": total,
        "source_hits": source_hits,
        "required_terms_hits": term_hits,
        "source_hit_rate": round(source_hits / total, 4) if total else 0.0,
        "required_terms_hit_rate": round(term_hits / total, 4) if total else 0.0,
        "ok": source_hits == total and term_hits == total,
        "rows": rows,
    }


def _is_image_pack_allowed(path: Path) -> bool:
    relative = _relative(path)
    if relative in IMAGE_PACK_ALLOWED_FILES:
        return True
    return any(relative == allowed or relative.startswith(f"{allowed}/") for allowed in IMAGE_PACK_ALLOWED_DIRS)


def _matplotlib_literal_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("$", r"\$")


def render_image_pack(
    *,
    source: Path,
    output_dir: Path,
    lines_per_page: int = 55,
    chars_per_line: int = 96,
) -> dict[str, Any]:
    source = source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if not _is_image_pack_allowed(source):
        raise ValueError(f"{_relative(source)} is not allowed for image-pack experiments")

    output_dir.mkdir(parents=True, exist_ok=True)
    lines = source.read_text(encoding="utf-8").splitlines()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    pages = []

    # Import lazily so normal validation/budget commands do not initialize Matplotlib.
    from matplotlib.figure import Figure

    for page_index, start in enumerate(range(0, len(lines), lines_per_page), start=1):
        raw_page_lines = lines[start : start + lines_per_page]
        wrapped_lines = []
        for line in raw_page_lines:
            wrapped_lines.extend(textwrap.wrap(line, width=chars_per_line) or [""])
        page_text = _matplotlib_literal_text("\n".join(wrapped_lines))
        image_path = output_dir / f"{source.stem}_page_{page_index:04d}.png"

        fig = Figure(figsize=(12, 16), dpi=150, facecolor="white")
        fig.text(
            0.04,
            0.98,
            page_text,
            va="top",
            ha="left",
            family="monospace",
            fontsize=8,
            color="#111111",
        )
        fig.savefig(image_path, format="png", facecolor="white")

        pages.append(
            {
                "page": page_index,
                "path": _display_path(image_path),
                "source_start_line": start + 1,
                "source_end_line": start + len(raw_page_lines),
            }
        )

    manifest = {
        "source": _relative(source),
        "source_sha256": digest,
        "lines_per_page": lines_per_page,
        "chars_per_line": chars_per_line,
        "pages": pages,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, default=_json_default, indent=2, sort_keys=True))


def _json_default(value: Any) -> str:
    if isinstance(value, dt.date | dt.datetime):
        return value.isoformat()
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI context routing utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate", help="validate context routes and benchmark")

    route = subparsers.add_parser("route", help="select a context route for a question")
    route.add_argument("question")

    budget = subparsers.add_parser("budget", help="estimate eager-vs-routed token budgets")
    budget.add_argument("--route", default="backtester_regression")

    subparsers.add_parser("benchmark", help="run deterministic source/term retrieval benchmark")

    image_pack = subparsers.add_parser("image-pack", help="render an allowed archive doc as PNG pages")
    image_pack.add_argument("--source", required=True)
    image_pack.add_argument("--output", required=True)
    image_pack.add_argument("--lines-per-page", type=int, default=55)
    image_pack.add_argument("--chars-per-line", type=int, default=96)

    args = parser.parse_args()
    if args.command == "validate":
        _print_json(validate_context())
    elif args.command == "route":
        _print_json(route_report(args.question))
    elif args.command == "budget":
        _print_json(budget_report(args.route))
    elif args.command == "benchmark":
        _print_json(retrieval_benchmark())
    elif args.command == "image-pack":
        _print_json(
            render_image_pack(
                source=_repo_path(args.source),
                output_dir=_repo_path(args.output),
                lines_per_page=args.lines_per_page,
                chars_per_line=args.chars_per_line,
            )
        )


if __name__ == "__main__":
    main()
