import json
import subprocess
import sys
from pathlib import Path

TOOL_DIR = Path(__file__).parent


def test_generate_markdown_report():
    """Generate a markdown report from section files."""
    # Create temp section files
    problem_file = TOOL_DIR / "_test_problem.md"
    matrix_file = TOOL_DIR / "_test_matrix.md"
    design_file = TOOL_DIR / "_test_design.md"
    exps_file = TOOL_DIR / "_test_exps.json"
    disc_file = TOOL_DIR / "_test_disc.md"
    output_file = TOOL_DIR / "_test_report.md"

    problem_file.write_text("# Problem\nBuild an image classifier.")
    matrix_file.write_text("# Literature\n| Paper | Score |\n|-------|-------|\n| ResNet | 0.9 |")
    design_file.write_text("# Design\nUse ResNet-50 with transfer learning.")
    exps_file.write_text(json.dumps([{"run_id": "abc", "final_loss": 0.3, "final_accuracy": 0.92}]))
    disc_file.write_text("# Discussion\nThe model performs well on test data.")

    result = subprocess.run(
        [sys.executable, str(TOOL_DIR / "report_gen.py"),
         "--problem", str(problem_file),
         "--lit-matrix", str(matrix_file),
         "--design", str(design_file),
         "--experiments", str(exps_file),
         "--discussion", str(disc_file),
         "--output", str(output_file)],
        capture_output=True, text=True, cwd=str(TOOL_DIR)
    )

    # Cleanup
    for f in [problem_file, matrix_file, design_file, exps_file, disc_file]:
        f.unlink(missing_ok=True)

    assert result.returncode == 0
    report = output_file.read_text()
    output_file.unlink(missing_ok=True)

    assert "# Research Report" in report
    assert "## Problem Statement" in report
    assert "## Literature Review" in report
    assert "## Method" in report
    assert "## Experiments" in report
    assert "## Results & Discussion" in report
    assert "## Code Delivery" in report


def test_generate_report_no_experiments():
    """Report generation works with minimal inputs (problem only)."""
    problem_file = TOOL_DIR / "_test_problem2.md"
    output_file = TOOL_DIR / "_test_report2.md"
    problem_file.write_text("# Problem\nTest problem.")

    result = subprocess.run(
        [sys.executable, str(TOOL_DIR / "report_gen.py"),
         "--problem", str(problem_file),
         "--output", str(output_file)],
        capture_output=True, text=True, cwd=str(TOOL_DIR)
    )
    problem_file.unlink(missing_ok=True)

    assert result.returncode == 0
    report = output_file.read_text()
    output_file.unlink(missing_ok=True)
    assert "# Research Report" in report


def test_cli_help():
    """--help prints usage."""
    result = subprocess.run(
        [sys.executable, str(TOOL_DIR / "report_gen.py"), "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "--problem" in result.stdout
    assert "--output" in result.stdout
