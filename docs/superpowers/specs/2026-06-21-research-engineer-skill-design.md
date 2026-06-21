# Research-Engineer Skill Design

## Overview

A superpowers skill that turns a real-world AI problem (LLMs, CV, image processing, image recognition) into a high-quality research + engineering deliverable. The agent follows an adaptive pipeline: search academic papers, score relevance, decide whether to implement from a paper, synthesize multiple papers, or derive from first principles — then implement and validate.

**Skill name:** `research-engineer`

## Domain

- LLMs (fine-tuning, architecture modification, training strategies)
- Computer vision / image processing / image recognition (detection, segmentation, restoration, filtering, recognition)

Not in scope: pure software engineering, hardware/robotics control, non-ML scientific computing.

## Deliverable

A research report + working implementation. Both are required at completion.

## Interaction Model

Autonomous execution within each phase, with two human decision gates:
- **Gate 1:** After literature search & scoring, human reviews the paper matrix and approves the direction
- **Gate 2:** After implementation & validation, human reviews results and approves the final report

The agent presents gate deliverables and pauses via the `ask` tool. The human response determines whether to proceed, revise, or abandon. The agent MUST NOT continue past a gate until the human responds.

## Pipeline Architecture

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

Produces a structured problem spec: mathematical notation, constraints, success criteria, data characteristics, evaluation metrics. Template: `templates/problem_spec.md`.

### Phase 2: Literature Search & Scoring

Multi-pass search across Semantic Scholar, arXiv, DBLP, Google Scholar. Extracts paper PDFs into structured text. Scores relevance 0–1 across five weighted dimensions (see below). Output: literature matrix.

### Phase 3: Method Design

Decision based on top paper scores:

- **3a (strong match, score ≥ 0.8):** Implement from paper. Production-grade code.
- **3b (partial match, score 0.4–0.8, composable subproblems):** Synthesize multiple papers. Research-grade initially, production-grade after validation.
- **3c (weak match, score < 0.4):** Derive from first principles. Theoretical derivation + experiment plan. Research-grade code.

Output: design doc with method choice, theoretical justification, architecture. Template: `templates/design_doc.md`.

### Phase 4: Implementation & Validation

Writes code, runs experiments locally (GPU assumed), tracks everything via `experiment_tracker.py`. Validation protocol depends on path:

- **3a:** Reproduce paper result on paper's dataset, then transfer to user's dataset
- **3b:** Ablation study per component, baseline comparison against best single paper
- **3c:** Ablation per assumption, sanity checks, baseline against simplest heuristic

### Phase 5: Final Report

Compiles all artifacts (problem spec, literature matrix, design doc, experiment results, code) into a unified report via `report_gen.py`. Markdown default, LaTeX optional.

## Paper Search Design

### Search Strategy (multi-pass)

1. **Keyword search** — broad net, 50–100 papers
2. **Citation graph traversal** — forward/backward from top hits
3. **Venue-scoped deep dive** — specific conference/journal search for niche gaps

### Tool: `tools/paper_search.py`

Wraps APIs in priority order:
1. Semantic Scholar API (primary — free, embeddings, citation graph)
2. arXiv API (cs.CV, cs.CL, cs.AI, cs.LG)
3. DBLP (author/venue)
4. Google Scholar (fallback)

Queries all in parallel, deduplicates by DOI + title fuzzy match.

### Tool: `tools/paper_extract.py`

Extracts structured text from PDFs using PyMuPDF:
- Title, abstract, method section, experiments, conclusion
- Figure/table captions and references
- Falls back to arXiv HTML abstract when PDF is paywalled

### Tool: `tools/relevance_scorer.py`

Weighted scoring across five dimensions:

| Dimension | Weight | Method |
|-----------|--------|--------|
| Problem similarity | 0.35 | Embedding cosine similarity: paper abstract ↔ formalized problem. Uses `sentence-transformers` (default: `all-mpnet-base-v2`) for local embedding generation. |

| Method applicability | 0.30 | LLM judge with structured rubric |
| Empirical strength | 0.15 | Dataset scale, metric improvements, ablation quality |
| Theoretical rigor | 0.10 | Theorems, proofs, convergence guarantees |
| Reproducibility | 0.10 | Code available, well-cited, results replicated |

Output: scored paper matrix with detailed extraction for top 3–5, summaries for the rest.

### Rigor Decay Rule

If a paper has high empirical strength but low theoretical rigor, the agent MUST either fill the gap (derive missing theory) or explicitly flag the gap in the design doc for the human to decide.

## Decision Logic (Phase 3 Branching)

| Condition | Path | Code Quality |
|-----------|------|-------------|
| Top score ≥ 0.8 AND method applicability ≥ 0.7 | 3a: Implement | Production-grade |
| Score 0.4–0.8 AND 2+ papers cover different subproblems with composable interfaces | 3b: Synthesize | Research-grade → production-grade |
| Score 0.4–0.8 but subproblems NOT composable, or max score < 0.4 | 3c: Derive | Research-grade |


### Phase 3c Detail: Derive from First Principles

1. Reduce problem to mathematical core (what is optimized? under what constraints?)
2. Search adjacent literature for reusable frameworks
3. Derive theoretically — state assumptions, prove properties
4. Design ablations — what proves the derivation works?
5. Build minimal viable experiment

## Implementation Standards

### Code Quality Tiers

**Research-grade:**
- Single-file scripts or small packages
- Runs, reproduces key result, minimal documentation
- Acceptable: hardcoded paths, magic numbers with comments, minimal error handling
- Required: README with reproduction commands

**Production-grade:**
- Modular package structure (`src/models.py`, `src/data.py`, `src/train.py`, `src/eval.py`)
- Type hints, docstrings on public APIs
- Config-driven (YAML/dataclass)
- Unit tests on data pipelines and loss functions
- Pinned dependencies, seed control, logged hyperparameters

### Framework Defaults

- **Primary (CV):** OpenCV (`cv2`) — image I/O, preprocessing, filtering, feature extraction
- **Primary (DL):** PyTorch + HuggingFace ecosystem (transformers, diffusers, timm, datasets)
- **Secondary:** JAX/Flax when the paper uses it

### Anti-Reinvention Rule

Before implementing any method from scratch, exhaust in order:
1. Official paper repository
2. OpenCV built-in (`cv2.*`) for any image pipeline step
3. HuggingFace `transformers` / `diffusers` / `timm`
4. Well-starred third-party implementation
5. Only then write from scratch

## Experiment Tracking

### Tool: `tools/experiment_tracker.py`

Wraps the training loop. Each run records:
- Run ID, hyperparameters, git hash, dataset hash
- Per-epoch metrics (loss, accuracy, custom)
- Final metrics + model artifact path
- Comparison table against prior runs

Stored as SQLite + JSON, no external service required.

## Validation Protocol

| Path | Validation |
|------|-----------|
| 3a (paper) | Reproduce paper result on paper's dataset, then transfer to user's dataset. Report both. |
| 3b (synthesize) | Ablation per component. Baseline: best single paper from matrix. Prove synthesis beats any individual. |
| 3c (derive) | Ablation per assumption/theoretical component. Baseline: simplest heuristic. Sanity checks: learns? beats random? more data helps? Bar: "plausible and promising." |

Gate 2 deliverables: metrics table, failure analysis, recommendation (production-ready or needs iteration).

## Final Report

### Tool: `tools/report_gen.py`

Compiles structured artifacts into unified document:

| Section | Source |
|---------|--------|
| Problem statement | Phase 1 formalization |
| Literature review | Phase 2 paper matrix (condensed) |
| Method | Phase 3 design doc (theorems, architecture) |
| Experiments | Phase 4 experiment tracker exports |
| Results & discussion | Gate 2 analysis + human feedback |
| Code delivery | Paths to final implementation, reproduction commands |

Format: Markdown default, LaTeX optional.

## File Structure

```
skills/research-engineer/
├── SKILL.md                    # Pipeline instructions + decision heuristics
├── tools/
│   ├── paper_search.py         # Multi-API paper discovery
│   ├── paper_extract.py        # PDF → structured text
│   ├── relevance_scorer.py     # Embedding-based similarity scoring
│   ├── experiment_tracker.py   # Run logging, metrics, ablations
│   └── report_gen.py           # Markdown/LaTeX report compilation
└── templates/
    ├── problem_spec.md         # Phase 1 output template
    ├── lit_matrix.md           # Phase 2 output template
    └── design_doc.md           # Phase 3 output template
```

## Error Handling & Edge Cases

| Failure mode | Mitigation |
|-------------|------------|
| Agent implements a paper that doesn't actually fit | Relevance scoring with problem similarity dimension; Gate 1 review |
| Agent claims "no paper exists" after shallow search | Multi-pass search is mandatory; Pass 3 catches missed papers |
| Agent writes code without checking existing libraries | Anti-reinvention rule with explicit check order |
| Agent runs experiments without tracking, loses results | `experiment_tracker.py` integrated into training loop |
| Agent produces novel derivation without empirical validation | Phase 4 always runs; derivation without experiment rejected at Gate 2 |
| Agent hallucinates paper details | `paper_extract.py` requires actual PDF or abstract text; must cite specific sections |
| Problem is too large for one session | Agent detects scope in Phase 1, proposes decomposition into sub-problems |
