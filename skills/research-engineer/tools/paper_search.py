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
                "abstract": item.get("abstract") or "",
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
                if len(paper.get("abstract") or "") > len(existing.get("abstract") or ""):
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
