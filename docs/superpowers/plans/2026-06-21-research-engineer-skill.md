# Research-Engineer Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `research-engineer` superpowers skill — an adaptive research-to-implementation pipeline for AI problems (LLMs, CV, image processing) with companion toolchain.

**Architecture:** A single skill directory (`skills/research-engineer/`) containing `SKILL.md` (pipeline workflow instructions), `tools/` (5 Python CLI tools for paper search/extraction/scoring/experiment tracking/report generation), and `templates/` (3 markdown output templates). Each tool is a standalone Python module with its own tests. The SKILL.md orchestrates the pipeline by referencing tools and templates.

**Tech Stack:** Python 3.10+, `requests` (API calls), `PyMuPDF` (PDF extraction), `sentence-transformers` (embeddings), `sqlite3` (experiment tracking), `pytest` (testing only — tools themselves are called via `subprocess` by the agent, not imported).

## Global Constraints

- Skill name: `research-engineer` (hyphenated, per agentskills.io spec)
- SKILL.md frontmatter: `name` + `description` required; description starts with "Use when..."
- All tools live under `skills/research-engineer/tools/`
- All templates live under `skills/research-engineer/templates/`
- Tools are CLI-callable with `--help`; they read/write JSON for structured I/O
- No external services required for experiment tracking or report generation
- Dependencies documented in a `requirements.txt` at skill root

---

### Task 1: Scaffold Directory Structure

**Files:**
- Create: `skills/research-engineer/requirements.txt`
- Create: `skills/research-engineer/tools/__init__.py` (empty)
- Create: `skills/research-engineer/templates/__init__.py` (empty, optional)

**Interfaces:**
- Consumes: nothing
- Produces: directory layout that Tasks 2–8 populate

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p skills/research-engineer/tools skills/research-engineer/templates
```

- [ ] **Step 2: Create requirements.txt**

```python
# skills/research-engineer/requirements.txt
requests>=2.28
PyMuPDF>=1.23.0
sentence-transformers>=2.2.0
```

- [ ] **Step 3: Create empty __init__.py files**

```bash
touch skills/research-engineer/tools/__init__.py
```

- [ ] **Step 4: Commit**

```bash
git add skills/
git commit -m "feat: scaffold research-engineer skill directory"
```

---

### Task 2: SKILL.md — Pipeline Workflow Instructions

**Files:**
- Create: `skills/research-engineer/SKILL.md`

**Interfaces:**
- Consumes: directory layout from Task 1
- Produces: the main skill file that the agent reads to understand the pipeline

- [ ] **Step 1: Write SKILL.md**

```markdown
---
name: research-engineer
description: Use when solving AI research problems (LLMs, computer vision, image processing, image recognition) that require literature review, paper-to-problem matching, and rigorous implementation — from reproducing established methods to deriving novel solutions from first principles
---

# Research-Engineer

## Overview

Turn a real-world AI problem into a high-quality research + engineering deliverable. Follow an adaptive pipeline: formalize the problem → search academic papers → score relevance → decide whether to implement from a paper, synthesize multiple papers, or derive from first principles → implement and validate → produce a final report.

## Core Pipeline

```
Phase 1: Problem Formalization → Phase 2: Literature Search & Scoring
                                          ↓
                                     Gate 1 (human)
                                          ↓
                               Phase 3: Method Design
                         ┌────────┬─────────┬──────────┐
                    3a. Implement  3b. Synthesize  3c. Derive
                         └────────┴─────────┴──────────┘
                                          ↓
                               Phase 4: Implementation & Validation
                                          ↓
                                     Gate 2 (human)
                                          ↓
                               Phase 5: Final Report
```

### Phase 1: Problem Formalization

Produce a structured problem spec using `templates/problem_spec.md`. Cover:
- Mathematical formulation (what is optimized? under what constraints?)
- Input/output specification
- Success criteria and evaluation metrics
- Data characteristics (size, modality, distribution)
- Domain constraints (latency, memory, interpretability)

### Phase 2: Literature Search & Scoring

**Multi-pass search.** Run `tools/paper_search.py` three times with increasing specificity:

1. **Keyword search** — broad terms from the problem spec, target 50–100 papers
2. **Citation graph traversal** — forward/backward from top hits of pass 1
3. **Venue-scoped deep dive** — restrict to specific conferences/journals for niche gaps

**Extract papers.** For each candidate: run `tools/paper_extract.py` to get structured text (title, abstract, method, experiments, conclusion). Falls back to arXiv abstract when PDF is unavailable.

**Score relevance.** Run `tools/relevance_scorer.py` on each extracted paper against the problem formalization. It scores 0–1 across five dimensions:

| Dimension | Weight | Method |
|-----------|--------|--------|
| Problem similarity | 0.35 | Embedding cosine similarity |
| Method applicability | 0.30 | LLM judge with structured rubric |
| Empirical strength | 0.15 | Dataset scale, metrics, ablations |
| Theoretical rigor | 0.10 | Theorems, proofs, guarantees |
| Reproducibility | 0.10 | Code available, well-cited |

**Output: literature matrix.** Fill `templates/lit_matrix.md` with top-scored papers (detailed extraction for top 3–5, summaries for rest).

**Rigor decay rule:** If a paper has high empirical strength but low theoretical rigor, you MUST either fill the gap (derive missing theory) or explicitly flag the gap in the design doc for the human to decide.

### Gate 1

Present the literature matrix to the user via the `ask` tool. Include:
- Top 3–5 scored papers with scores and method summaries
- Your recommendation: which path (3a/3b/3c) and why
- Any rigor gaps you've flagged

The user approves, redirects search, or refines the problem. Do NOT proceed until the user responds.

### Phase 3: Method Design

Based on Gate 1 approval, follow the branching logic:

| Condition | Path | Code Quality |
|-----------|------|-------------|
| Top score ≥ 0.8 AND method applicability ≥ 0.7 | 3a: Implement from paper | Production-grade |
| Score 0.4–0.8 AND 2+ papers with composable subproblems | 3b: Synthesize | Research-grade → production-grade |
| Score 0.4–0.8 but NOT composable, or max score < 0.4 | 3c: Derive | Research-grade |

**Phase 3a (Implement from paper):** Reproduce the method. Adapt to user's data and constraints. Production-grade code.

**Phase 3b (Synthesize):** Extract core mechanisms from each paper. Design a unified architecture. Justify composition: why these pieces fit, what the interface contracts are.

**Phase 3c (Derive from first principles):**
1. Reduce problem to mathematical core
2. Search adjacent literature for reusable frameworks
3. Derive theoretically — state assumptions, prove properties
4. Design ablations — what proves the derivation works?
5. Build minimal viable experiment

Output: fill `templates/design_doc.md` with method choice, theoretical justification, and architecture.

### Phase 4: Implementation & Validation

**Write code** following the anti-reinvention rule. Before implementing any method from scratch, exhaust in order:
1. Official paper repository
2. OpenCV built-in (`cv2.*`) for any image pipeline step
3. HuggingFace `transformers` / `diffusers` / `timm`
4. Well-starred third-party implementation
5. Only then write from scratch

**Framework defaults:** OpenCV for image I/O/preprocessing. PyTorch + HuggingFace for deep learning. JAX/Flax only when the paper uses it.

**Code quality tiers:**

- **Research-grade:** Single-file scripts. Runs, reproduces key result, minimally documented. Hardcoded paths and magic numbers acceptable with comments. REQUIRED: README with reproduction commands.
- **Production-grade:** Modular package (`src/models.py`, `src/data.py`, `src/train.py`, `src/eval.py`). Type hints, docstrings. Config-driven (YAML/dataclass). Unit tests on data pipelines and loss functions. Pinned dependencies, seed control.

**Track experiments** with `tools/experiment_tracker.py`. Every run records: hyperparameters, git hash, dataset hash, per-epoch metrics, final metrics, model artifact path.

**Validation protocol:**

| Path | Validation |
|------|-----------|
| 3a (paper) | Reproduce paper result on paper's dataset, then transfer to user's dataset. Report both. |
| 3b (synthesize) | Ablation per component. Baseline: best single paper from matrix. Prove synthesis beats any individual. |
| 3c (derive) | Ablation per assumption. Baseline: simplest heuristic. Sanity checks: learns? beats random? Bar: "plausible and promising." |

### Gate 2

Present results via the `ask` tool:
- Key metrics table (paper baseline vs. our implementation vs. ablations)
- Failure analysis: what didn't work, hypotheses why
- Recommendation: production-ready, or needs iteration

User approves (→ Phase 5), requests revisions, or abandons.

### Phase 5: Final Report

Run `tools/report_gen.py` to compile all artifacts into a unified report:

| Section | Source |
|---------|--------|
| Problem statement | Phase 1 formalization |
| Literature review | Phase 2 paper matrix (condensed) |
| Method | Phase 3 design doc |
| Experiments | Phase 4 experiment tracker exports |
| Results & discussion | Gate 2 analysis + human feedback |
| Code delivery | Paths to final implementation, reproduction commands |

Markdown by default. Use `--format latex` for paper-ready output.

## Error Handling

| Failure mode | Mitigation |
|-------------|------------|
| Implements paper that doesn't fit | Relevance scoring; Gate 1 review |
| Claims "no paper exists" after shallow search | Multi-pass search mandatory; Pass 3 catches gaps |
| Writes code without checking existing libraries | Anti-reinvention rule with explicit check order |
| Loses experiment results | `experiment_tracker.py` integrated into training loop |
| Derives without empirical validation | Phase 4 always runs; Gate 2 rejects derivation without experiment |
| Hallucinates paper details | `paper_extract.py` requires actual PDF/abstract; cite specific sections |
| Problem too large for one session | Detect scope in Phase 1; propose decomposition |
```

- [ ] **Step 2: Commit**

```bash
git add skills/research-engineer/SKILL.md
git commit -m "feat: add SKILL.md with pipeline workflow"
```

---

### Task 3: Output Templates

**Files:**
- Create: `skills/research-engineer/templates/problem_spec.md`
- Create: `skills/research-engineer/templates/lit_matrix.md`
- Create: `skills/research-engineer/templates/design_doc.md`

**Interfaces:**
- Consumes: directory layout from Task 1
- Produces: three Markdown templates that the agent fills during Phases 1, 2, and 3

- [ ] **Step 1: Write problem_spec.md template**

```markdown
# Problem Specification

## Problem Statement

[One-paragraph description of the real-world problem]

## Mathematical Formulation

[What is being optimized? Under what constraints? Use LaTeX notation.]

## Input / Output

- **Input:** [data modality, shape, type, source]
- **Output:** [expected result type, shape, semantics]

## Success Criteria

- [ ] Criterion 1: [measurable condition]
- [ ] Criterion 2: [measurable condition]

## Evaluation Metrics

| Metric | Definition | Target |
|--------|-----------|--------|
| [metric_name] | [formula or description] | [threshold] |

## Data

- **Source:** [dataset name, collection method, or "user-provided"]
- **Size:** [N samples, distribution info]
- **Modality:** [image / text / tabular / multimodal]
- **Preprocessing:** [required steps before model input]

## Constraints

- [ ] Latency: [max inference time if applicable]
- [ ] Memory: [max GPU/CPU memory]
- [ ] Interpretability: [required or optional]
- [ ] Other: [domain-specific constraints]
```

- [ ] **Step 2: Write lit_matrix.md template**

```markdown
# Literature Matrix

**Problem:** [one-line problem summary]
**Search date:** [YYYY-MM-DD]
**Papers found:** [N], **Scored:** [M]

## Top Papers

| # | Paper | Year | Score | Problem Match | Method | Strengths | Weaknesses | Code |
|---|-------|------|-------|---------------|--------|-----------|------------|------|
| 1 | [Title] ([Authors], [Venue]) | [YYYY] | [0.XX] | [High/Med/Low] — [why] | [one-sentence summary] | [key strength] | [key weakness] | [link or "none"] |
| 2 | ... | ... | ... | ... | ... | ... | ... | ... |

## Detailed Extraction

### Paper 1: [Title]

**Abstract:** [extracted abstract]

**Method:** [extracted method section summary]

**Key Results:** [extracted experiment results]

**Rigor Assessment:** [theoretical rigor score + notes]

**Relevance to Our Problem:** [specific mapping]

### Paper 2: ...

## Recommendation

**Path:** [3a / 3b / 3c]
**Rationale:** [why this path]
**Rigor gaps flagged:** [list or "none"]
```

- [ ] **Step 3: Write design_doc.md template**

```markdown
# Method Design

## Chosen Path

[3a: Implement from Paper / 3b: Synthesize / 3c: Derive]

## Source Papers

| Paper | Core Idea Used |
|-------|---------------|
| [Title] | [which aspect of the paper is used] |

## Architecture

[Diagram or description of the proposed method]

## Theoretical Justification

[For 3c: assumptions, theorems, proofs. For 3a/3b: why this method fits the problem.]

## Experiment Plan

### Reproduction (3a only)

- Dataset: [paper's dataset]
- Expected result: [paper's reported metric]
- Success if: [within X% of reported]

### Transfer to Target (3a/3b/3c)

- Dataset: [user's dataset]
- Baseline: [what to compare against]
- Metrics: [what to measure]

### Ablations (3b/3c)

| Ablation | Hypothesis | Expected outcome |
|----------|-----------|-----------------|
| Remove [component] | [what should degrade] | [metric direction] |

## Implementation Notes

- [ ] Check official repo: [link or "none found"]
- [ ] Check OpenCV built-in: [which functions]
- [ ] Check HuggingFace: [which models]
- [ ] Check third-party: [links]
```

- [ ] **Step 4: Commit**

```bash
git add skills/research-engineer/templates/
git commit -m "feat: add output templates for problem spec, lit matrix, design doc"
```

---

### Task 4: paper_search.py — Multi-API Paper Discovery

**Files:**
- Create: `skills/research-engineer/tools/paper_search.py`
- Create: `skills/research-engineer/tools/test_paper_search.py`

**Interfaces:**
- Consumes: nothing
- Produces: `search_papers(query: str, sources: list[str], limit: int) -> list[dict]` — each dict has `{title, authors, year, venue, doi, arxiv_id, abstract, url, source}`. CLI: `python paper_search.py --query "..." --sources semantic_scholar,arxiv --limit 50 --output results.json`

- [ ] **Step 1: Write failing test**

```python
# skills/research-engineer/tools/test_paper_search.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd skills/research-engineer/tools && python -m pytest test_paper_search.py -v
```
Expected: FAIL with "No such file" or "ModuleNotFoundError"

- [ ] **Step 3: Write minimal implementation**

```python
# skills/research-engineer/tools/paper_search.py
"""Multi-API academic paper search.

Usage:
    python paper_search.py --query "attention mechanism" --sources semantic_scholar,arxiv --limit 50 --output results.json

Sources:
    semantic_scholar  - Semantic Scholar API (primary, free, embeddings + citation graph)
    arxiv            - arXiv API (cs.CV, cs.CL, cs.AI, cs.LG)
    dblp             - DBLP API (author/venue search)
    google_scholar   - Google Scholar (fallback, rate-limited, may require scraping)

Output: JSON array of paper dicts with keys:
    title, authors (list), year, venue, doi, arxiv_id, abstract, url, source
"""

import argparse
import json
import sys
import time
from difflib import SequenceMatcher
from typing import Optional
from urllib.parse import quote, urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    sys.exit("Install requests: pip install requests")


def search_semantic_scholar(query: str, limit: int = 50) -> list[dict]:
    """Search Semantic Scholar API."""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": "title,authors,year,venue,externalIds,abstract,url"
    }
    headers = {"Accept": "application/json"}
    papers = []
    offset = 0
    while len(papers) < limit:
        params["offset"] = offset
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code == 429:
            time.sleep(1)
            continue
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("data", [])
        if not batch:
            break
        for item in batch:
            papers.append({
                "title": item.get("title", ""),
                "authors": [a.get("name", "") for a in item.get("authors", [])],
                "year": item.get("year"),
                "venue": item.get("venue", ""),
                "doi": (item.get("externalIds") or {}).get("DOI", ""),
                "arxiv_id": (item.get("externalIds") or {}).get("ArXiv", ""),
                "abstract": item.get("abstract", ""),
                "url": item.get("url", ""),
                "source": "semantic_scholar",
            })
        offset += len(batch)
    return papers[:limit]


def search_arxiv(query: str, limit: int = 50) -> list[dict]:
    """Search arXiv API across cs.CV, cs.CL, cs.AI, cs.LG."""
    base_url = "http://export.arxiv.org/api/query"
    categories = ["cs.CV", "cs.CL", "cs.AI", "cs.LG"]
    papers = []
    for cat in categories:
        if len(papers) >= limit:
            break
        params = {
            "search_query": f"({query}) AND cat:{cat}",
            "start": 0,
            "max_results": min(limit - len(papers), 25),
            "sortBy": "relevance",
        }
        resp = requests.get(base_url, params=params, timeout=30)
        if resp.status_code != 200:
            continue
        # Parse arXiv Atom XML response
        import xml.etree.ElementTree as ET
        ns = {"atom": "http://www.w3.org/2005/Atom",
              "arxiv": "http://arxiv.org/schemas/atom"}
        root = ET.fromstring(resp.text)
        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            summary_el = entry.find("atom:summary", ns)
            arxiv_id_el = entry.find("atom:id", ns)
            papers.append({
                "title": (title_el.text or "").strip().replace("\n", " "),
                "authors": [a.find("atom:name", ns).text
                           for a in entry.findall("atom:author", ns)],
                "year": int(entry.find("atom:published", ns).text[:4])
                        if entry.find("atom:published", ns) is not None else None,
                "venue": f"arXiv ({cat})",
                "doi": "",
                "arxiv_id": (arxiv_id_el.text or "").split("/abs/")[-1]
                            if arxiv_id_el is not None else "",
                "abstract": (summary_el.text or "").strip().replace("\n", " "),
                "url": (arxiv_id_el.text or "") if arxiv_id_el is not None else "",
                "source": "arxiv",
            })
    return papers[:limit]


def search_dblp(query: str, limit: int = 50) -> list[dict]:
    """Search DBLP API for author/venue lookups."""
    url = "https://dblp.org/search/publ/api"
    params = {"q": query, "format": "json", "h": min(limit, 30)}
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        return []
    data = resp.json()
    hits = data.get("result", {}).get("hits", {}).get("hit", [])
    papers = []
    for hit in hits:
        info = hit.get("info", {})
        authors_info = info.get("authors", {})
        author_list = authors_info.get("author", [])
        if isinstance(author_list, dict):
            author_list = [author_list]
        papers.append({
            "title": info.get("title", ""),
            "authors": [a.get("text", "") for a in author_list],
            "year": int(info.get("year", 0)) if info.get("year") else None,
            "venue": info.get("venue", ""),
            "doi": info.get("doi", ""),
            "arxiv_id": "",
            "abstract": "",
            "url": info.get("ee", info.get("url", "")),
            "source": "dblp",
        })
    return papers[:limit]


def title_similarity(a: str, b: str) -> float:
    """Fuzzy title match for deduplication."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def deduplicate(papers: list[dict], threshold: float = 0.85) -> list[dict]:
    """Remove near-duplicate papers by title similarity."""
    kept = []
    for paper in papers:
        is_dup = False
        for existing in kept:
            if title_similarity(paper["title"], existing["title"]) >= threshold:
                # Keep the one with more fields populated
                if len(paper.get("abstract", "")) > len(existing.get("abstract", "")):
                    existing.update(paper)
                is_dup = True
                break
        if not is_dup:
            kept.append(paper)
    return kept


SEARCHERS = {
    "semantic_scholar": search_semantic_scholar,
    "arxiv": search_arxiv,
    "dblp": search_dblp,
}


def search_papers(query: str, sources: Optional[list[str]] = None,
                  limit: int = 50) -> list[dict]:
    """Search papers across specified sources, deduplicate, return top results.

    Args:
        query: Search query string.
        sources: List of source names. Default: ["semantic_scholar", "arxiv"].
        limit: Maximum total results.

    Returns:
        List of paper dicts, sorted by source priority then relevance.
    """
    if sources is None:
        sources = ["semantic_scholar", "arxiv"]
    sources = [s for s in sources if s in SEARCHERS]
    if not sources:
        sources = ["semantic_scholar"]

    per_source_limit = max(limit // len(sources), 10)
    all_papers = []

    with ThreadPoolExecutor(max_workers=len(sources)) as executor:
        futures = {
            executor.submit(SEARCHERS[src], query, per_source_limit): src
            for src in sources
        }
        for future in as_completed(futures):
            src = futures[future]
            try:
                results = future.result()
                all_papers.extend(results)
            except Exception as e:
                print(f"Warning: {src} search failed: {e}", file=sys.stderr)

    all_papers = deduplicate(all_papers)
    return all_papers[:limit]


def main():
    parser = argparse.ArgumentParser(description="Multi-API academic paper search")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--sources", default="semantic_scholar,arxiv",
                        help="Comma-separated source names")
    parser.add_argument("--limit", type=int, default=50,
                        help="Maximum results (default: 50)")
    parser.add_argument("--output", help="Output JSON file path (default: stdout)")
    args = parser.parse_args()

    sources = [s.strip() for s in args.sources.split(",")]
    papers = search_papers(args.query, sources, args.limit)

    result_json = json.dumps(papers, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w") as f:
            f.write(result_json)
        print(f"Saved {len(papers)} papers to {args.output}", file=sys.stderr)
    else:
        print(result_json)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd skills/research-engineer/tools && python -m pytest test_paper_search.py -v
```
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add skills/research-engineer/tools/paper_search.py skills/research-engineer/tools/test_paper_search.py
git commit -m "feat: add paper_search.py with multi-API search and dedup"
```

---

### Task 5: paper_extract.py — PDF to Structured Text

**Files:**
- Create: `skills/research-engineer/tools/paper_extract.py`
- Create: `skills/research-engineer/tools/test_paper_extract.py`

**Interfaces:**
- Consumes: nothing
- Produces: `extract_paper(source: str) -> dict` with keys `{title, abstract, sections: {method, experiments, conclusion}, figures: list[str], references: list[str], source_type: "pdf"|"arxiv_abstract"}`. CLI: `python paper_extract.py --source path/to/paper.pdf --output extracted.json`

- [ ] **Step 1: Write failing test**

```python
# skills/research-engineer/tools/test_paper_extract.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd skills/research-engineer/tools && python -m pytest test_paper_extract.py -v
```
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# skills/research-engineer/tools/paper_extract.py
"""Extract structured text from academic paper PDFs or arXiv abstracts.

Usage:
    python paper_extract.py --source paper.pdf --output extracted.json
    python paper_extract.py --source https://arxiv.org/abs/1706.03762

Input: PDF file path or arXiv URL
Output: JSON dict with keys: title, abstract, sections, figures, references, source_type
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    requests = None


def extract_arxiv_abstract(arxiv_id: str) -> dict:
    """Fetch paper metadata from arXiv API using the paper ID."""
    if requests is None:
        raise RuntimeError("Install requests: pip install requests")
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    import xml.etree.ElementTree as ET
    ns = {"atom": "http://www.w3.org/2005/Atom",
          "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(resp.text)
    entry = root.find("atom:entry", ns)
    if entry is None:
        raise ValueError(f"No arXiv entry found for ID: {arxiv_id}")

    title_el = entry.find("atom:title", ns)
    summary_el = entry.find("atom:summary", ns)
    title = (title_el.text or "").strip().replace("\n", " ") if title_el is not None else ""
    abstract = (summary_el.text or "").strip().replace("\n", " ") if summary_el is not None else ""

    return {
        "title": title,
        "abstract": abstract,
        "sections": {
            "method": "",
            "experiments": "",
            "conclusion": "",
        },
        "figures": [],
        "references": [],
        "source_type": "arxiv_abstract",
    }


def extract_pdf(pdf_path: str) -> dict:
    """Extract structured text from a PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError("Install PyMuPDF: pip install PyMuPDF")

    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()

    # Simple heuristic section extraction
    title = ""
    abstract = ""
    method = ""
    experiments = ""
    conclusion = ""

    lines = full_text.split("\n")
    # Title: first non-empty line(s) before abstract
    title_lines = []
    for line in lines:
        if re.search(r'\babstract\b', line, re.IGNORECASE):
            break
        stripped = line.strip()
        if stripped:
            title_lines.append(stripped)
    title = " ".join(title_lines[:3])

    # Abstract
    in_abstract = False
    abstract_lines = []
    for line in lines:
        if re.search(r'\babstract\b', line, re.IGNORECASE) and not in_abstract:
            in_abstract = True
            continue
        if in_abstract:
            if re.search(r'\b(introduction|related work|background)\b',
                        line, re.IGNORECASE):
                break
            abstract_lines.append(line.strip())
    abstract = " ".join(abstract_lines)

    # Method (heuristic: between "method"/"approach" and "experiment"/"results")
    method = _extract_section(full_text, r'\b(method|approach|architecture|model)\b',
                              r'\b(experiment|results|evaluation)\b')

    # Experiments
    experiments = _extract_section(full_text, r'\b(experiment|results|evaluation)\b',
                                    r'\b(conclusion|discussion|related work)\b')

    # Conclusion
    conclusion = _extract_section(full_text, r'\b(conclusion|discussion)\b',
                                   r'\b(reference|bibliography|acknowledgment)\b')

    doc.close()
    return {
        "title": title,
        "abstract": abstract,
        "sections": {
            "method": method,
            "experiments": experiments,
            "conclusion": conclusion,
        },
        "figures": [],
        "references": [],
        "source_type": "pdf",
    }


def _extract_section(text: str, start_pattern: str, end_pattern: str) -> str:
    """Extract text between two section header patterns."""
    start_match = re.search(start_pattern, text, re.IGNORECASE)
    if not start_match:
        return ""
    start_pos = start_match.start()
    end_match = re.search(end_pattern, text[start_pos:], re.IGNORECASE)
    if end_match:
        end_pos = start_pos + end_match.start()
    else:
        end_pos = len(text)
    section_text = text[start_pos:end_pos]
    # Remove the header line itself
    lines = section_text.split("\n")[1:]
    return " ".join(l.strip() for l in lines if l.strip())


def extract_paper(source: str) -> dict:
    """Extract structured text from a paper source (PDF path or arXiv URL).

    Args:
        source: File path to PDF, or arXiv URL (e.g., https://arxiv.org/abs/1706.03762)

    Returns:
        Dict with keys: title, abstract, sections, figures, references, source_type
    """
    # Check if source is an arXiv URL
    parsed = urlparse(source)
    if "arxiv.org" in parsed.netloc:
        # Extract arXiv ID from URL
        match = re.search(r'(\d{4}\.\d{4,5}(?:v\d+)?)', source)
        if match:
            return extract_arxiv_abstract(match.group(1))

    # Treat as file path
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {source}")
    if path.suffix.lower() == ".pdf":
        return extract_pdf(str(path))
    raise ValueError(f"Unsupported file type: {path.suffix}. Only PDF is supported.")


def main():
    parser = argparse.ArgumentParser(
        description="Extract structured text from academic paper PDFs or arXiv URLs")
    parser.add_argument("--source", required=True,
                        help="PDF file path or arXiv URL (e.g., https://arxiv.org/abs/1706.03762)")
    parser.add_argument("--output", help="Output JSON file path (default: stdout)")
    args = parser.parse_args()

    try:
        paper = extract_paper(args.source)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    result_json = json.dumps(paper, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w") as f:
            f.write(result_json)
        print(f"Saved extraction to {args.output}", file=sys.stderr)
    else:
        print(result_json)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd skills/research-engineer/tools && python -m pytest test_paper_extract.py -v
```
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add skills/research-engineer/tools/paper_extract.py skills/research-engineer/tools/test_paper_extract.py
git commit -m "feat: add paper_extract.py for PDF and arXiv text extraction"
```

---

### Task 6: relevance_scorer.py — Paper-to-Problem Scoring

**Files:**
- Create: `skills/research-engineer/tools/relevance_scorer.py`
- Create: `skills/research-engineer/tools/test_relevance_scorer.py`

**Interfaces:**
- Consumes: nothing
- Produces: `score_papers(problem_spec: str, papers: list[dict]) -> list[dict]` — each paper dict augmented with `{score, dimensions: {problem_similarity, method_applicability, empirical_strength, theoretical_rigor, reproducibility}}`. CLI: `python relevance_scorer.py --problem problem.txt --papers results.json --output scored.json`

- [ ] **Step 1: Write failing test**

```python
# skills/research-engineer/tools/test_relevance_scorer.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd skills/research-engineer/tools && python -m pytest test_relevance_scorer.py -v
```
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# skills/research-engineer/tools/relevance_scorer.py
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

    global DEFAULT_MODEL
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd skills/research-engineer/tools && python -m pytest test_relevance_scorer.py -v
```
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add skills/research-engineer/tools/relevance_scorer.py skills/research-engineer/tools/test_relevance_scorer.py
git commit -m "feat: add relevance_scorer.py with five-dimension paper scoring"
```

---

### Task 7: experiment_tracker.py — Run Logging & Comparison

**Files:**
- Create: `skills/research-engineer/tools/experiment_tracker.py`
- Create: `skills/research-engineer/tools/test_experiment_tracker.py`

**Interfaces:**
- Consumes: nothing
- Produces: `ExperimentTracker` class. `start_run(config: dict) -> str` (run_id), `log_metrics(run_id: str, epoch: int, metrics: dict)`, `end_run(run_id: str, final_metrics: dict, artifact_path: str)`, `list_runs() -> list[dict]`, `compare_runs(run_ids: list[str]) -> dict`. CLI: `python experiment_tracker.py --action [start|log|end|list|compare] ...`

- [ ] **Step 1: Write failing test**

```python
# skills/research-engineer/tools/test_experiment_tracker.py
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

TOOL_DIR = Path(__file__).parent
DB_PATH = TOOL_DIR / "_test_experiments.db"


def cleanup():
    DB_PATH.unlink(missing_ok=True)
    (TOOL_DIR / "_test_experiments.json").unlink(missing_ok=True)


def run_tracker(*args: str) -> dict:
    """Run experiment_tracker.py with args and return parsed stdout."""
    result = subprocess.run(
        [sys.executable, str(TOOL_DIR / "experiment_tracker.py"),
         "--db", str(DB_PATH)] + list(args),
        capture_output=True, text=True, cwd=str(TOOL_DIR)
    )
    if result.returncode != 0:
        raise RuntimeError(f"experiment_tracker.py failed: {result.stderr}\nstdout: {result.stdout}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout}


def test_start_and_list_run():
    """Start a run, then list shows it."""
    cleanup()
    config = json.dumps({"model": "resnet50", "lr": 0.001, "batch_size": 32})
    start_result = subprocess.run(
        [sys.executable, str(TOOL_DIR / "experiment_tracker.py"),
         "--db", str(DB_PATH), "start", "--config", config],
        capture_output=True, text=True, cwd=str(TOOL_DIR)
    )
    assert start_result.returncode == 0
    run_data = json.loads(start_result.stdout)
    assert "run_id" in run_data

    list_result = run_tracker("list")
    assert isinstance(list_result, list)
    assert any(r["run_id"] == run_data["run_id"] for r in list_result)

    cleanup()


def test_log_and_end_run():
    """Log metrics then end the run."""
    cleanup()
    config = json.dumps({"model": "vit-base"})
    start_data = run_tracker("start", "--config", config)
    run_id = start_data["run_id"]

    # Log epoch metrics
    log_result = run_tracker(
        "log", "--run-id", run_id, "--epoch", "1",
        "--metrics", json.dumps({"loss": 0.5, "acc": 0.8}))
    assert "ok" in log_result.get("raw", "").lower() or log_result == {}

    # End run
    end_result = run_tracker(
        "end", "--run-id", run_id,
        "--metrics", json.dumps({"loss": 0.3, "acc": 0.92}),
        "--artifact", "models/best.pt")
    assert isinstance(end_result, dict)

    # Verify run is marked complete
    list_result = run_tracker("list")
    run = next(r for r in list_result if r["run_id"] == run_id)
    assert run["status"] == "completed"
    assert run["final_loss"] == 0.3

    cleanup()


def test_compare_runs():
    """Compare two runs returns comparison table."""
    cleanup()
    c1 = json.dumps({"model": "resnet18", "lr": 0.01})
    c2 = json.dumps({"model": "resnet50", "lr": 0.001})

    r1 = run_tracker("start", "--config", c1)
    run_tracker("end", "--run-id", r1["run_id"],
                "--metrics", json.dumps({"loss": 0.5, "acc": 0.85}),
                "--artifact", "m1.pt")

    r2 = run_tracker("start", "--config", c2)
    run_tracker("end", "--run-id", r2["run_id"],
                "--metrics", json.dumps({"loss": 0.3, "acc": 0.92}),
                "--artifact", "m2.pt")

    compare = run_tracker("compare", "--run-ids", f"{r1['run_id']},{r2['run_id']}")
    assert "runs" in compare or isinstance(compare, list)

    cleanup()


def test_cli_help():
    """--help prints usage with available actions."""
    result = subprocess.run(
        [sys.executable, str(TOOL_DIR / "experiment_tracker.py"), "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "start" in result.stdout
    assert "log" in result.stdout
    assert "end" in result.stdout
    assert "list" in result.stdout
    assert "compare" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd skills/research-engineer/tools && python -m pytest test_experiment_tracker.py -v
```
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# skills/research-engineer/tools/experiment_tracker.py
"""Lightweight experiment tracking with SQLite + JSON backing.

Usage:
    python experiment_tracker.py start --config '{"model":"resnet50","lr":0.001}'
    python experiment_tracker.py log --run-id <id> --epoch 1 --metrics '{"loss":0.5}'
    python experiment_tracker.py end --run-id <id> --metrics '{"loss":0.3}' --artifact model.pt
    python experiment_tracker.py list
    python experiment_tracker.py compare --run-ids id1,id2

Stores: SQLite database for structured queries, JSON file for full metric history.
"""

import argparse
import json
import os
import sqlite3
import sys
import time
import uuid
from pathlib import Path
from typing import Optional


class ExperimentTracker:
    """Tracks ML experiments with SQLite + JSON backing."""

    def __init__(self, db_path: str = "experiments.db"):
        self.db_path = Path(db_path)
        self.json_path = self.db_path.with_suffix(".json")
        self._init_db()
        self._load_json()

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                config TEXT,
                status TEXT DEFAULT 'running',
                created_at TEXT,
                final_metrics TEXT,
                artifact_path TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                epoch INTEGER,
                metrics TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)
        conn.commit()
        conn.close()

    def _load_json(self):
        """Load JSON history file."""
        if self.json_path.exists():
            with open(self.json_path) as f:
                self._json_data = json.load(f)
        else:
            self._json_data = {}

    def _save_json(self):
        """Persist JSON history file."""
        with open(self.json_path, "w") as f:
            json.dump(self._json_data, f, indent=2)

    def start_run(self, config: dict) -> str:
        """Start a new run. Returns run_id."""
        run_id = uuid.uuid4().hex[:12]
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT INTO runs (run_id, config, status, created_at) VALUES (?, ?, ?, ?)",
            (run_id, json.dumps(config), "running", now))
        conn.commit()
        conn.close()
        self._json_data[run_id] = {
            "config": config,
            "created_at": now,
            "epochs": [],
            "final_metrics": None,
            "artifact_path": None,
        }
        self._save_json()
        return run_id

    def log_metrics(self, run_id: str, epoch: int, metrics: dict):
        """Log metrics for a specific epoch."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT INTO metrics (run_id, epoch, metrics) VALUES (?, ?, ?)",
            (run_id, epoch, json.dumps(metrics)))
        conn.commit()
        conn.close()
        if run_id in self._json_data:
            self._json_data[run_id]["epochs"].append({"epoch": epoch, "metrics": metrics})
            self._save_json()

    def end_run(self, run_id: str, final_metrics: dict, artifact_path: str = ""):
        """Mark a run as completed with final metrics."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "UPDATE runs SET status = 'completed', final_metrics = ?, artifact_path = ? WHERE run_id = ?",
            (json.dumps(final_metrics), artifact_path, run_id))
        conn.commit()
        conn.close()
        if run_id in self._json_data:
            self._json_data[run_id]["final_metrics"] = final_metrics
            self._json_data[run_id]["artifact_path"] = artifact_path
            self._save_json()

    def list_runs(self) -> list[dict]:
        """List all runs with summary info."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT run_id, config, status, created_at, final_metrics, artifact_path FROM runs ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        result = []
        for row in rows:
            d = dict(row)
            d["config"] = json.loads(d["config"]) if d["config"] else {}
            d["final_metrics"] = json.loads(d["final_metrics"]) if d["final_metrics"] else {}
            # Flatten final_metrics for easy comparison
            if d["final_metrics"]:
                for k, v in d["final_metrics"].items():
                    d[f"final_{k}"] = v
            result.append(d)
        return result

    def compare_runs(self, run_ids: list[str]) -> dict:
        """Compare multiple runs side by side."""
        conn = sqlite3.connect(str(self.db_path))
        runs = []
        for rid in run_ids:
            row = conn.execute(
                "SELECT run_id, config, final_metrics FROM runs WHERE run_id = ?",
                (rid,)).fetchone()
            if row:
                config = json.loads(row[1]) if row[1] else {}
                metrics = json.loads(row[2]) if row[2] else {}
                runs.append({"run_id": row[0], "config": config, "final_metrics": metrics})
        conn.close()
        return {"runs": runs, "count": len(runs)}


def main():
    parser = argparse.ArgumentParser(description="Lightweight ML experiment tracker")
    parser.add_argument("--db", default="experiments.db", help="SQLite database path")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # start
    p_start = subparsers.add_parser("start", help="Start a new run")
    p_start.add_argument("--config", required=True, help="JSON config dict")

    # log
    p_log = subparsers.add_parser("log", help="Log epoch metrics")
    p_log.add_argument("--run-id", required=True)
    p_log.add_argument("--epoch", type=int, required=True)
    p_log.add_argument("--metrics", required=True, help="JSON metrics dict")

    # end
    p_end = subparsers.add_parser("end", help="End a run")
    p_end.add_argument("--run-id", required=True)
    p_end.add_argument("--metrics", required=True, help="JSON final metrics dict")
    p_end.add_argument("--artifact", default="", help="Model artifact path")

    # list
    p_list = subparsers.add_parser("list", help="List all runs")

    # compare
    p_compare = subparsers.add_parser("compare", help="Compare runs")
    p_compare.add_argument("--run-ids", required=True, help="Comma-separated run IDs")

    args = parser.parse_args()
    tracker = ExperimentTracker(args.db)

    if args.action == "start":
        config = json.loads(args.config)
        run_id = tracker.start_run(config)
        print(json.dumps({"run_id": run_id}))

    elif args.action == "log":
        metrics = json.loads(args.metrics)
        tracker.log_metrics(args.run_id, args.epoch, metrics)
        print(json.dumps({"status": "ok"}))

    elif args.action == "end":
        metrics = json.loads(args.metrics)
        tracker.end_run(args.run_id, metrics, args.artifact)
        print(json.dumps({"status": "completed", "run_id": args.run_id}))

    elif args.action == "list":
        runs = tracker.list_runs()
        print(json.dumps(runs, indent=2))

    elif args.action == "compare":
        run_ids = [r.strip() for r in args.run_ids.split(",")]
        result = tracker.compare_runs(run_ids)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd skills/research-engineer/tools && python -m pytest test_experiment_tracker.py -v
```
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add skills/research-engineer/tools/experiment_tracker.py skills/research-engineer/tools/test_experiment_tracker.py
git commit -m "feat: add experiment_tracker.py with SQLite + JSON run logging"
```

---

### Task 8: report_gen.py — Final Report Compilation

**Files:**
- Create: `skills/research-engineer/tools/report_gen.py`
- Create: `skills/research-engineer/tools/test_report_gen.py`

**Interfaces:**
- Consumes: nothing
- Produces: `generate_report(sections: dict, format: str = "markdown") -> str`. CLI: `python report_gen.py --problem problem.md --lit-matrix matrix.md --design design.md --experiments results.json --discussion notes.md --output report.md`

- [ ] **Step 1: Write failing test**

```python
# skills/research-engineer/tools/test_report_gen.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd skills/research-engineer/tools && python -m pytest test_report_gen.py -v
```
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# skills/research-engineer/tools/report_gen.py
"""Compile research artifacts into a unified report.

Usage:
    python report_gen.py --problem problem.md --lit-matrix matrix.md --design design.md \\
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd skills/research-engineer/tools && python -m pytest test_report_gen.py -v
```
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add skills/research-engineer/tools/report_gen.py skills/research-engineer/tools/test_report_gen.py
git commit -m "feat: add report_gen.py for markdown/latex report compilation"
```

---

### Task 9: Integration Smoke Test & Final Assembly

**Files:**
- Modify: `skills/research-engineer/requirements.txt` (add test deps)

**Interfaces:**
- Consumes: all previous tasks
- Produces: passing full test suite, verified skill structure

- [ ] **Step 1: Update requirements.txt with test dependencies**

Add to `skills/research-engineer/requirements.txt`:
```
pytest>=7.0
```

- [ ] **Step 2: Run full test suite**

```bash
cd skills/research-engineer/tools && python -m pytest test_*.py -v
```
Expected: 14–16 tests PASS (depending on network-dependent tests)

For tests that require network (paper_search, paper_extract), skip if offline:
```bash
cd skills/research-engineer/tools && python -m pytest test_*.py -v -k "not (test_search_returns_list or test_multiple_sources_dedup or test_extract_arxiv)" --ignore-glob="*network*"
```
Expected: all offline tests PASS

- [ ] **Step 3: Verify file structure**

```bash
find skills/research-engineer -type f | sort
```
Expected:
```
skills/research-engineer/SKILL.md
skills/research-engineer/requirements.txt
skills/research-engineer/templates/design_doc.md
skills/research-engineer/templates/lit_matrix.md
skills/research-engineer/templates/problem_spec.md
skills/research-engineer/tools/__init__.py
skills/research-engineer/tools/experiment_tracker.py
skills/research-engineer/tools/paper_extract.py
skills/research-engineer/tools/paper_search.py
skills/research-engineer/tools/relevance_scorer.py
skills/research-engineer/tools/report_gen.py
skills/research-engineer/tools/test_experiment_tracker.py
skills/research-engineer/tools/test_paper_extract.py
skills/research-engineer/tools/test_paper_search.py
skills/research-engineer/tools/test_relevance_scorer.py
skills/research-engineer/tools/test_report_gen.py
```

- [ ] **Step 4: Commit**

```bash
git add skills/research-engineer/requirements.txt
git commit -m "chore: add pytest dependency and verify full test suite"
```
