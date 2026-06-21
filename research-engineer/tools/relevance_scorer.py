"""Score paper relevance to a problem statement across five dimensions.

Usage:
    python relevance_scorer.py --problem problem.txt --papers results.json --output scored.json

Input:
    --problem: path to text file with problem description
    --papers: path to JSON file with paper list (from paper_search.py or paper_extract.py)

Output: JSON array of papers augmented with:
    score (float 0-1), dimensions (dict of five sub-scores)
"""

import argparse
import json
import sys
from typing import Optional


# Weights from the spec
WEIGHTS = {
    "problem_similarity": 0.35,
    "method_applicability": 0.30,
    "empirical_strength": 0.15,
    "theoretical_rigor": 0.10,
    "reproducibility": 0.10,
}

# Default embedding model for problem similarity
DEFAULT_MODEL = "all-mpnet-base-v2"


def compute_problem_similarity(problem: str, paper_abstract: str) -> float:
    """Compute cosine similarity between problem and paper abstract embeddings."""
    if not paper_abstract:
        return 0.0
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(DEFAULT_MODEL)
        emb_problem = model.encode([problem])
        emb_paper = model.encode([paper_abstract])
        from numpy import dot
        from numpy.linalg import norm
        sim = dot(emb_problem[0], emb_paper[0]) / (norm(emb_problem[0]) * norm(emb_paper[0]))
        return float(max(0.0, sim))
    except ImportError:
        # Fallback: simple word overlap ratio
        problem_words = set(problem.lower().split())
        abstract_words = set(paper_abstract.lower().split())
        if not problem_words:
            return 0.0
        overlap = problem_words & abstract_words
        return len(overlap) / len(problem_words)


def compute_method_applicability(problem: str, paper: dict) -> float:
    """Heuristic: check if paper title/abstract shares method keywords with problem.

    In practice, this is where an LLM judge call would happen.
    The tool provides the heuristic; the agent supplements with LLM judgment.
    """
    method_keywords = [
        "method", "approach", "framework", "architecture", "model",
        "algorithm", "technique", "scheme", "paradigm", "pipeline"
    ]
    text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
    problem_lower = problem.lower()
    score = 0.0
    for kw in method_keywords:
        if kw in text and kw in problem_lower:
            score += 0.15
    return min(score, 1.0)


def compute_empirical_strength(paper: dict) -> float:
    """Heuristic based on available signals about empirical quality."""
    score = 0.5  # neutral default
    text = (paper.get("abstract", "") + " " +
            " ".join(paper.get("sections", {}).get("experiments", "").split()[:100])).lower()
    # Signal: multiple datasets mentioned
    dataset_indicators = ["dataset", "benchmark", "coco", "imagenet", "pascal", "cityscapes",
                          "squad", "glue", "superglue", "mnist", "cifar", "imagenet"]
    for di in dataset_indicators:
        if di in text:
            score += 0.05
    # Signal: metric improvements reported
    metric_indicators = ["improve", "outperform", "state-of-the-art", "sota",
                         "achieve", "boost", "+", "%"]
    for mi in metric_indicators:
        if mi in text:
            score += 0.03
    # Signal: ablation mentioned
    if "ablation" in text:
        score += 0.1
    return min(score, 1.0)


def compute_theoretical_rigor(paper: dict) -> float:
    """Heuristic based on presence of theoretical content signals."""
    score = 0.0
    text = (paper.get("abstract", "") + " " +
            " ".join(paper.get("sections", {}).get("method", "").split()[:200])).lower()
    theory_indicators = [
        "theorem", "proof", "lemma", "corollary", "proposition",
        "convergence", "bound", "guarantee", "optimal", "convex",
        "convergence rate", "complexity", "closed form"
    ]
    for ti in theory_indicators:
        if ti in text:
            score += 0.1
    return min(score, 1.0)


def compute_reproducibility(paper: dict) -> float:
    """Heuristic based on code availability and citation signals."""
    score = 0.0
    if paper.get("url", ""):
        score += 0.3
    code_indicators = ["github", "code", "implementation", "repo"]
    text = (paper.get("abstract", "") + " " + paper.get("url", "")).lower()
    for ci in code_indicators:
        if ci in text:
            score += 0.2
    return min(score, 1.0)


def score_paper(problem: str, paper: dict) -> dict:
    """Score a single paper against a problem statement.

    Args:
        problem: Problem description text.
        paper: Paper dict with at least 'abstract' key.

    Returns:
        Paper dict augmented with 'score' and 'dimensions'.
    """
    dims = {
        "problem_similarity": compute_problem_similarity(
            problem, paper.get("abstract", "")),
        "method_applicability": compute_method_applicability(problem, paper),
        "empirical_strength": compute_empirical_strength(paper),
        "theoretical_rigor": compute_theoretical_rigor(paper),
        "reproducibility": compute_reproducibility(paper),
    }
    score = sum(WEIGHTS[k] * dims[k] for k in WEIGHTS)
    paper["score"] = round(score, 4)
    paper["dimensions"] = {k: round(v, 4) for k, v in dims.items()}
    return paper


def score_papers(problem: str, papers: list[dict]) -> list[dict]:
    """Score a list of papers against a problem statement.

    Args:
        problem: Problem description text.
        papers: List of paper dicts.

    Returns:
        Papers sorted by score descending, each augmented with score and dimensions.
    """
    scored = [score_paper(problem, p) for p in papers]
    scored.sort(key=lambda p: p["score"], reverse=True)
    return scored


def main():
    global DEFAULT_MODEL

    parser = argparse.ArgumentParser(
        description="Score paper relevance to a problem statement")
    parser.add_argument("--problem", required=True,
                        help="Path to text file with problem description")
    parser.add_argument("--papers", required=True,
                        help="Path to JSON file with paper list")
    parser.add_argument("--output", help="Output JSON file path (default: stdout)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Embedding model for problem similarity (default: {DEFAULT_MODEL})")
    args = parser.parse_args()

    DEFAULT_MODEL = args.model

    with open(args.problem) as f:
        problem_text = f.read()
    with open(args.papers) as f:
        papers = json.load(f)

    scored = score_papers(problem_text, papers)

    result_json = json.dumps(scored, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w") as f:
            f.write(result_json)
        print(f"Saved {len(scored)} scored papers to {args.output}", file=sys.stderr)
    else:
        print(result_json)


if __name__ == "__main__":
    main()
