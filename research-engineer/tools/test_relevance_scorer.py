import json
import subprocess
import sys
from pathlib import Path

TOOL_DIR = Path(__file__).parent


def run_score(problem_text: str, papers: list[dict]) -> dict:
    """Run relevance_scorer.py with problem text and paper list."""
    # Write inputs to temp files
    problem_file = TOOL_DIR / "_test_problem.txt"
    papers_file = TOOL_DIR / "_test_papers.json"
    output_file = TOOL_DIR / "_test_scored.json"

    problem_file.write_text(problem_text)
    papers_file.write_text(json.dumps(papers))

    result = subprocess.run(
        [sys.executable, str(TOOL_DIR / "relevance_scorer.py"),
         "--problem", str(problem_file),
         "--papers", str(papers_file),
         "--output", str(output_file)],
        capture_output=True, text=True, cwd=str(TOOL_DIR)
    )
    # Cleanup
    problem_file.unlink(missing_ok=True)
    papers_file.unlink(missing_ok=True)

    if result.returncode != 0:
        raise RuntimeError(f"relevance_scorer.py failed: {result.stderr}")

    scored = json.loads(output_file.read_text())
    output_file.unlink(missing_ok=True)
    return scored


def test_scored_papers_have_score_field():
    """Each paper in output has a top-level 'score' between 0 and 1."""
    papers = [
        {"title": "Test Paper 1", "abstract": "We propose a novel image classification method using deep CNNs."},
        {"title": "Test Paper 2", "abstract": "A study of transformer architectures for NLP tasks."},
    ]
    problem = "Build an image classification model for medical X-ray diagnosis."
    result = run_score(problem, papers)
    assert isinstance(result, list)
    for paper in result:
        assert "score" in paper, f"Missing 'score' in {paper['title']}"
        assert 0 <= paper["score"] <= 1, f"Score out of range: {paper['score']}"


def test_scored_papers_have_dimension_breakdown():
    """Each paper has a 'dimensions' dict with the five scoring dimensions."""
    papers = [
        {"title": "Test Paper", "abstract": "Image classification with ResNet on medical data."}
    ]
    problem = "Medical image classification for X-ray diagnosis."
    result = run_score(problem, papers)
    dims = result[0].get("dimensions", {})
    required_dims = {"problem_similarity", "method_applicability",
                     "empirical_strength", "theoretical_rigor", "reproducibility"}
    missing = required_dims - set(dims.keys())
    assert not missing, f"Missing dimensions: {missing}"
    for k, v in dims.items():
        assert 0 <= v <= 1, f"Dimension {k} out of range: {v}"


def test_higher_similarity_for_relevant_paper():
    """A paper about the problem domain scores higher than an unrelated paper."""
    relevant = {"title": "CNN for Medical Imaging", "abstract": "Deep convolutional networks for medical image diagnosis and classification."}
    irrelevant = {"title": "Attention for Text", "abstract": "Transformer attention mechanisms for natural language processing and machine translation."}
    problem = "Build an image classification model for medical X-ray diagnosis using CNNs."
    result = run_score(problem, [relevant, irrelevant])
    # The CNN medical paper should score higher
    scores = {p["title"]: p["score"] for p in result}
    assert scores["CNN for Medical Imaging"] > scores["Attention for Text"], \
        f"Expected medical paper to score higher: {scores}"


def test_cli_help():
    """--help prints usage."""
    result = subprocess.run(
        [sys.executable, str(TOOL_DIR / "relevance_scorer.py"), "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "--problem" in result.stdout
    assert "--papers" in result.stdout
