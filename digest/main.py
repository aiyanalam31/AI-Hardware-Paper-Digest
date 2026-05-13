"""Main entrypoint. Run as: python -m digest.main"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from digest.fetch import fetch_recent
from digest.keyword_filter import filter_papers
from digest.rank import rank_papers
from digest.email_sender import send_digest

SEEN_FILE = Path("seen.json")
SEEN_MAX = 500  # keep last N to bound size


def load_seen() -> set[str]:
    if not SEEN_FILE.exists():
        return set()
    try:
        return set(json.loads(SEEN_FILE.read_text()))
    except Exception:
        return set()


def save_seen(seen: set[str]) -> None:
    # keep most recent SEEN_MAX (arxiv IDs sort roughly chronologically)
    trimmed = sorted(seen, reverse=True)[:SEEN_MAX]
    SEEN_FILE.write_text(json.dumps(trimmed, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="skip email, print instead")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--window-hours", type=int, default=48)
    args = parser.parse_args()

    print(f"fetching papers from last {args.window_hours}h...")
    papers = fetch_recent(window_hours=args.window_hours)
    print(f"  got {len(papers)} unique papers")

    seen = load_seen()
    papers = [p for p in papers if p.arxiv_id not in seen]
    print(f"  {len(papers)} after dedupe against seen.json")

    candidates = filter_papers(papers)
    print(f"  {len(candidates)} after keyword filter")

    if not candidates:
        print("nothing to rank, sending empty digest")
        if not args.dry_run:
            send_digest([])
        return

    # Cap candidates sent to LLM — keep cost bounded.
    candidates = candidates[:40]

    print("ranking with Claude...")
    ranked = rank_papers(candidates, top_n=args.top_n)
    print(f"  {len(ranked)} papers scored >= 5")

    if args.dry_run:
        print("\n--- DIGEST (dry run) ---")
        for p in ranked:
            print(f"  [{p['score']}/10] {p['title'][:80]}")
            print(f"          {p['summary']}")
            print(f"          {p['url']}\n")
    else:
        send_digest(ranked)

    # Mark everything we considered as seen so we don't re-show
    for paper, _kw in candidates:
        seen.add(paper.arxiv_id)
    save_seen(seen)


if __name__ == "__main__":
    main()
