import json
import subprocess
import sys
from pathlib import Path

TOOL_DIR = Path(__file__).parent


def run_extract(source: str) -> dict:
    """Run paper_extract.py and return parsed output."""
    result = subprocess.run(
        [sys.executable, str(TOOL_DIR / "paper_extract.py"),
         "--source", source],
        capture_output=True, text=True, cwd=str(TOOL_DIR)
    )
    if result.returncode != 0:
        raise RuntimeError(f"paper_extract.py failed: {result.stderr}")
    return json.loads(result.stdout)


def test_extract_arxiv_abstract_fallback():
    """Extract from arXiv URL returns structured dict with abstract."""
    result = run_extract("https://arxiv.org/abs/1706.03762")  # Attention Is All You Need
    assert "title" in result
    assert "abstract" in result
    assert isinstance(result.get("sections"), dict)
    assert result["source_type"] == "arxiv_abstract"


def test_extract_has_required_keys():
    """Output dict has all expected top-level keys."""
    result = run_extract("https://arxiv.org/abs/1512.03385")  # ResNet
    required = {"title", "abstract", "sections", "figures", "references", "source_type"}
    missing = required - set(result.keys())
    assert not missing, f"Missing keys: {missing}"


def test_extract_rejects_invalid_source():
    """Non-existent file returns error."""
    result = subprocess.run(
        [sys.executable, str(TOOL_DIR / "paper_extract.py"),
         "--source", "/nonexistent/path.pdf"],
        capture_output=True, text=True
    )
    assert result.returncode != 0


def test_cli_help():
    """--help prints usage."""
    result = subprocess.run(
        [sys.executable, str(TOOL_DIR / "paper_extract.py"), "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "--source" in result.stdout
    assert "--output" in result.stdout
