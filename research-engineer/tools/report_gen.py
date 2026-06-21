"""Compile research artifacts into a unified report.

Usage:
    python report_gen.py --problem problem.md --lit-matrix matrix.md --design design.md \
        --experiments results.json --discussion notes.md --output report.md

Output: Markdown (default) or LaTeX (--format latex) research report.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


def load_section(path: Optional[str]) -> str:
    """Load a section file, return empty string if path is None or missing."""
    if path is None:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text()


def format_experiments_section(experiments_path: Optional[str]) -> str:
    """Format experiment results as a markdown table."""
    if experiments_path is None:
        return "_No experiments recorded._"
    p = Path(experiments_path)
    if not p.exists():
        return "_Experiment file not found._"
    data = json.loads(p.read_text())
    if not data:
        return "_No experiment runs recorded._"

    lines = ["| Run ID | Final Metrics |",
             "|--------|--------------|"]
    for run in data:
        metrics_str = ", ".join(
            f"{k}: {v}" for k, v in run.items()
            if k.startswith("final_") and k not in ("final_metrics",)
        ) or str(run.get("final_metrics", {}))
        lines.append(f"| {run.get('run_id', '?')} | {metrics_str} |")
    return "\n".join(lines)


def generate_report(problem: str = "", lit_matrix: str = "",
                    design: str = "", experiments: str = "",
                    discussion: str = "", output_format: str = "markdown") -> str:
    """Generate a unified research report.

    Args:
        problem: Problem statement markdown.
        lit_matrix: Literature matrix markdown.
        design: Method design markdown.
        experiments: Path to experiments JSON file.
        discussion: Results & discussion markdown.
        output_format: "markdown" or "latex".

    Returns:
        Complete report as string.
    """
    if output_format == "latex":
        return _generate_latex(problem, lit_matrix, design, experiments, discussion)
    return _generate_markdown(problem, lit_matrix, design, experiments, discussion)


def _generate_markdown(problem: str, lit_matrix: str, design: str,
                        experiments: str, discussion: str) -> str:
    """Generate Markdown report."""
    exps_table = format_experiments_section(experiments)
    return f"""# Research Report

## Problem Statement

{problem or "_No problem statement provided._"}

## Literature Review

{lit_matrix or "_No literature review provided._"}

## Method

{design or "_No method design provided._"}

## Experiments

{exps_table}

## Results & Discussion

{discussion or "_No discussion provided._"}

## Code Delivery

_Paths to implementation and reproduction commands go here._
"""


def _generate_latex(problem: str, lit_matrix: str, design: str,
                     experiments: str, discussion: str) -> str:
    """Generate LaTeX report stub."""
    exps_table = format_experiments_section(experiments)
    return f"""\\documentclass{{article}}
\\title{{Research Report}}
\\begin{{document}}
\\maketitle

\\section{{Problem Statement}}
{problem or "N/A"}

\\section{{Literature Review}}
{lit_matrix or "N/A"}

\\section{{Method}}
{design or "N/A"}

\\section{{Experiments}}
{exps_table}

\\section{{Results & Discussion}}
{discussion or "N/A"}

\\end{{document}}
"""


def main():
    parser = argparse.ArgumentParser(
        description="Compile research artifacts into a unified report")
    parser.add_argument("--problem", help="Path to problem spec markdown")
    parser.add_argument("--lit-matrix", help="Path to literature matrix markdown")
    parser.add_argument("--design", help="Path to design doc markdown")
    parser.add_argument("--experiments", help="Path to experiments JSON (from experiment_tracker)")
    parser.add_argument("--discussion", help="Path to discussion/analysis markdown")
    parser.add_argument("--output", required=True, help="Output report file path")
    parser.add_argument("--format", choices=["markdown", "latex"], default="markdown",
                        help="Output format (default: markdown)")
    args = parser.parse_args()

    problem = load_section(args.problem)
    lit_matrix = load_section(args.lit_matrix)
    design = load_section(args.design)
    discussion = load_section(args.discussion)

    report = generate_report(
        problem=problem,
        lit_matrix=lit_matrix,
        design=design,
        experiments=args.experiments,
        discussion=discussion,
        output_format=args.format,
    )

    with open(args.output, "w") as f:
        f.write(report)
    print(f"Report saved to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
