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
