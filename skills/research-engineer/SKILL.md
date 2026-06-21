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
