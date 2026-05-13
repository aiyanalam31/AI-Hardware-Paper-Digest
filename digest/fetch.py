"""Fetch recent papers from arXiv across hardware-adjacent AI categories."""

from __future__ import annotations

import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

ARXIV_API = "http://export.arxiv.org/api/query"

# Categories that capture "everything hardware-adjacent in AI".
# cs.AR  = hardware architecture
# cs.DC  = distributed/parallel computing (training systems, kernels)
# cs.NE  = neural / evolutionary (neuromorphic, spiking nets)
# cs.LG  = machine learning (filtered hard by keywords)
# cs.AI  = AI (filtered hard by keywords)
# cs.PF  = performance
# cs.OS  = operating systems (rare but relevant for ML systems)
# eess.SP = signal processing (DSP / edge inference)
CATEGORIES = ["cs.AR", "cs.DC", "cs.NE", "cs.LG", "cs.AI", "cs.PF", "cs.OS", "eess.SP"]

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


@dataclass
class Paper:
    arxiv_id: str
    title: str
    abstract: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: datetime
    updated: datetime
    url: str

    def as_dict(self) -> dict:
        return {
            "arxiv_id": self.arxiv_id,
            "title": self.title,
            "abstract": self.abstract,
            "authors": self.authors,
            "categories": self.categories,
            "primary_category": self.primary_category,
            "published": self.published.isoformat(),
            "updated": self.updated.isoformat(),
            "url": self.url,
        }


def _query_category(category: str, max_results: int = 200) -> list[Paper]:
    """Query a single arXiv category, sorted by submission date desc."""
    params = {
        "search_query": f"cat:{category}",
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": str(max_results),
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "ai-hardware-digest/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")

    root = ET.fromstring(raw)
    papers: list[Paper] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        arxiv_url = entry.find("atom:id", ATOM_NS).text.strip()
        arxiv_id = arxiv_url.rsplit("/", 1)[-1]
        # strip version suffix (e.g. v2) for stable dedupe key
        arxiv_id_base = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id

        title = " ".join(entry.find("atom:title", ATOM_NS).text.split())
        abstract = " ".join(entry.find("atom:summary", ATOM_NS).text.split())

        authors = [
            a.find("atom:name", ATOM_NS).text
            for a in entry.findall("atom:author", ATOM_NS)
        ]

        cats = [
            c.attrib["term"]
            for c in entry.findall("{http://arxiv.org/schemas/atom}category")
        ]
        primary_el = entry.find("{http://arxiv.org/schemas/atom}primary_category")
        primary = primary_el.attrib["term"] if primary_el is not None else cats[0]

        published = datetime.fromisoformat(
            entry.find("atom:published", ATOM_NS).text.replace("Z", "+00:00")
        )
        updated = datetime.fromisoformat(
            entry.find("atom:updated", ATOM_NS).text.replace("Z", "+00:00")
        )

        papers.append(
            Paper(
                arxiv_id=arxiv_id_base,
                title=title,
                abstract=abstract,
                authors=authors,
                categories=cats,
                primary_category=primary,
                published=published,
                updated=updated,
                url=f"https://arxiv.org/abs/{arxiv_id_base}",
            )
        )
    return papers


def fetch_recent(window_hours: int = 48) -> list[Paper]:
    """Fetch papers submitted within the last `window_hours`, deduped."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    seen: dict[str, Paper] = {}

    for cat in CATEGORIES:
        try:
            for p in _query_category(cat):
                if p.published < cutoff:
                    continue
                if p.arxiv_id not in seen:
                    seen[p.arxiv_id] = p
        except Exception as e:
            print(f"[warn] failed to fetch {cat}: {e}")
        # arXiv asks for ~3s between requests
        time.sleep(3)

    return sorted(seen.values(), key=lambda p: p.published, reverse=True)


if __name__ == "__main__":
    papers = fetch_recent()
    print(f"fetched {len(papers)} unique papers in window")
    for p in papers[:5]:
        print(f"  {p.arxiv_id}  [{p.primary_category}]  {p.title[:80]}")
