from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")


def write_dataframe(path: Path, df: pd.DataFrame) -> None:
    df.to_csv(path, index=False)


def write_markdown_table(path: Path, df: pd.DataFrame) -> None:
    path.write_text(_to_markdown_table(df) + "\n")


def _to_markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    columns = [str(col) for col in df.columns]
    rows = [[_format_cell(value) for value in row] for row in df.to_numpy()]
    widths = [
        max(len(columns[index]), *(len(row[index]) for row in rows))
        for index in range(len(columns))
    ]
    header = (
        "| "
        + " | ".join(columns[index].ljust(widths[index]) for index in range(len(columns)))
        + " |"
    )
    separator = "| " + " | ".join("-" * widths[index] for index in range(len(columns))) + " |"
    body = [
        "| " + " | ".join(row[index].ljust(widths[index]) for index in range(len(columns))) + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def _format_cell(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)
