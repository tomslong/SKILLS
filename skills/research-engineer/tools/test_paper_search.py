import json
import subprocess
import sys
from pathlib import Path

TOOL_DIR = Path(__file__).parent

def run_search(query: str, sources: str = "semantic_scholar", limit: int = 5) -> list[dict]:
    """Run paper_search.py and return parsed results."""
    result = subprocess.run(
        [sys.executable, str(TOOL_DIR / "paper_search.py"),
         "--query", query,
         "--sources", sources,
         "--limit", str(limit)],
        capture_output=True, text=True, cwd=str(TOOL_DIR)
    )
    if result.returncode != 0:
        raise RuntimeError(f"paper_search.py failed: {result.stderr}")
    return json.loads(result.stdout)


def test_search_returns_list():
    """Search returns a list of paper dicts."""
    papers = run_search("transformer attention mechanism", limit=3)
    assert isinstance(papers, list)
    assert len(papers) > 0, "Expected at least one result"


def test_paper_dict_has_required_fields():
    """Each paper dict has title, authors, year, abstract, url, source."""
    papers = run_search("image segmentation CNN", limit=2)
    required = {"title", "authors", "year", "abstract", "url", "source"}
    for paper in papers:
        missing = required - set(paper.keys())
        assert not missing, f"Paper missing fields: {missing}"


def test_multiple_sources_dedup():
    """Papers from multiple sources are deduplicated by title similarity."""
    papers = run_search("ResNet image classification", sources="semantic_scholar,arxiv", limit=10)
    titles = [p["title"].lower().strip() for p in papers]
    # Check no near-duplicate titles (simple substring check)
    for i, t1 in enumerate(titles):
        for j, t2 in enumerate(titles):
            if i < j and (t1 in t2 or t2 in t1) and len(t1) > 20:
                assert False, f"Possible duplicate: '{t1}' vs '{t2}'"


def test_limit_respected():
    """Result count does not exceed limit."""
    papers = run_search("neural network", limit=3)
    assert len(papers) <= 3


def test_cli_help():
    """--help prints usage."""
    result = subprocess.run(
        [sys.executable, str(TOOL_DIR / "paper_search.py"), "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "--query" in result.stdout
    assert "--sources" in result.stdout
