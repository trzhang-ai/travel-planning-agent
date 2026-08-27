#!/usr/bin/env python3
"""Run deterministic, offline checks on the submission notebook."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = PROJECT_ROOT / "project_starter.ipynb"


def require(condition: bool, message: str) -> None:
    """Raise an actionable validation error when a requirement is not met."""
    if not condition:
        raise AssertionError(message)


def main() -> None:
    """Validate notebook structure, Python syntax, prompt contracts, and hygiene."""
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    cells = notebook.get("cells", [])
    require(cells, "Notebook contains no cells.")

    code_cells = [cell for cell in cells if cell.get("cell_type") == "code"]
    markdown_cells = [cell for cell in cells if cell.get("cell_type") == "markdown"]
    require(len(cells) == 42, f"Expected 42 notebook cells, found {len(cells)}.")
    require(
        len(code_cells) == 32,
        f"Expected 32 code cells, found {len(code_cells)}.",
    )
    require(
        len(markdown_cells) == 10,
        f"Expected 10 Markdown cells, found {len(markdown_cells)}.",
    )
    source = "\n".join("".join(cell.get("source", [])) for cell in cells)

    for notebook_index, cell in enumerate(cells):
        if cell.get("cell_type") != "code":
            continue
        cell_source = "".join(cell.get("source", []))
        try:
            ast.parse(cell_source)
        except SyntaxError as exc:
            raise AssertionError(
                f"Invalid Python syntax in notebook cell {notebook_index}: {exc}"
            ) from exc

        require(
            not cell.get("outputs"),
            f"Notebook cell {notebook_index} still contains saved output or a trace.",
        )
        require(
            cell.get("execution_count") is None,
            f"Notebook cell {notebook_index} still has an execution count.",
        )

    required_markers = {
        "initial itinerary prompt": "ITINERARY_AGENT_SYSTEM_PROMPT",
        "weather evaluator prompt": "ACTIVITY_AND_WEATHER_ARE_COMPATIBLE_SYSTEM_PROMPT",
        "revision prompt": "ITINERARY_REVISION_AGENT_SYSTEM_PROMPT",
        "TravelPlan schema": "TravelPlan.model_json_schema()",
        "ReAct thought label": "THOUGHT:",
        "ReAct action label": "ACTION:",
        "ReAct observation label": "OBSERVATION:",
        "evaluation tool": "run_evals_tool",
        "final-answer tool": "final_answer_tool",
        "activity retrieval tool": "get_activities_by_date_tool",
    }
    for label, marker in required_markers.items():
        require(marker in source, f"Missing {label}: {marker!r}.")

    cell_contracts = {
        8: ["class Traveler", "class VacationInfo", "date_of_arrival", "budget"],
        10: ["start=vacation_info.date_of_arrival", "end=vacation_info.date_of_departure"],
        11: ["call_activities_api_mocked", "trip_dates"],
        14: [
            "ITINERARY_AGENT_SYSTEM_PROMPT",
            "## Role",
            "Plan the itinerary step by step",
            "FINAL OUTPUT:",
            "TravelPlan.model_json_schema()",
            "Weather Data:",
            "Activities Data:",
        ],
        22: [
            "ACTIVITY_AND_WEATHER_ARE_COMPATIBLE_SYSTEM_PROMPT",
            "IS_COMPATIBLE",
            "IS_INCOMPATIBLE",
            "## Examples",
        ],
        27: [
            "def get_activities_by_date_tool(date: str, city: str)",
            "YYYY-MM-DD",
            "AgentsVille",
        ],
        35: [
            "ITINERARY_REVISION_AGENT_SYSTEM_PROMPT",
            "get_tool_descriptions_string(ALL_TOOLS)",
            "THINK-ACT-OBSERVE",
            "THOUGHT:",
            "ACTION:",
            "run_evals_tool",
            "final_answer_tool",
            '"tool_name"',
            '"arguments"',
        ],
    }
    for notebook_index, markers in cell_contracts.items():
        cell_source = "".join(cells[notebook_index].get("source", []))
        for marker in markers:
            require(
                marker in cell_source,
                f"Notebook cell {notebook_index} is missing rubric marker {marker!r}.",
            )

    unwanted_markers = [
        "TODO: Fill in",
        "**********",
        "No changes needed",
        "CONGRATULATIONS",
        "just for fun",
        "# Add the ",
    ]
    for marker in unwanted_markers:
        require(marker not in source, f"Starter or informal marker remains: {marker!r}.")

    secret_patterns = {
        "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
        "absolute user path": re.compile(r"/Users/[^/\s]+/"),
    }
    for label, pattern in secret_patterns.items():
        require(not pattern.search(source), f"Potential {label} found in notebook source.")

    print(
        "Submission validation passed: "
        f"{len(cells)} cells ({len(code_cells)} code, {len(markdown_cells)} Markdown), "
        "no saved outputs, valid Python syntax, cell-specific rubric contracts "
        "present, and no obvious secrets."
    )


if __name__ == "__main__":
    main()
