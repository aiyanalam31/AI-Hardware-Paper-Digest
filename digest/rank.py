"""LLM-based ranker using Google Gemini's free tier.

Gemini 2.5 Flash on AI Studio gives ~1,500 requests/day free, no card required.
This digest makes 1 request/day, so we'll never come close to the limit.

Sign up: https://aistudio.google.com/app/apikey
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

MODEL = "gemini-2.5-flash"
ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
)

SYSTEM_PROMPT = """You are a research assistant filtering arXiv papers for a \
computer engineering student deeply interested in AI hardware. Their interests \
span: AI accelerators (GPU/TPU/NPU/FPGA/ASIC), chip architecture, in-memory \
and analog computing, neuromorphic systems, edge/embedded ML, quantization and \
sparsity for hardware, ML systems (kernels, compilers, distributed training, \
LLM serving), and hardware-software co-design.

For each paper, score relevance 0-10 on this rubric:
  9-10: Directly about AI hardware design, accelerator architecture, in-memory \
        compute, neuromorphic chips, or novel hardware for ML.
  7-8:  ML systems work with strong hardware angle (kernels, serving, \
        quantization with real hardware impact, hardware-aware methods).
  5-6:  Tangentially hardware-relevant (efficient ML methods without explicit \
        hardware focus, theoretical efficiency results).
  3-4:  Pure ML/algorithms paper with no hardware angle.
  0-2:  Off-topic.

Write a one-sentence "why it matters" summary (max 25 words) explaining the \
hardware/systems angle.

Return ONLY valid JSON, no markdown fences, no preamble. Format:
{"rankings": [{"id": "2405.12345", "score": 8, "summary": "..."}, ...]}
Include EVERY paper from the input, in the same order."""


def _call_gemini(api_key: str, system_prompt: str, user_text: str) -> str:
    body = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8000,
            "responseMimeType": "application/json",
        },
    }
    req = urllib.request.Request(
        f"{ENDPOINT}?key={api_key}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API {e.code}: {err_body}") from e

    candidates = payload.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"Gemini returned no candidates: {payload}")
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()


def rank_papers(candidates: list[tuple], top_n: int = 10) -> list[dict]:
    """Rank papers via Gemini. `candidates` is list of (Paper, matched_keywords).
    Returns top_n papers as dicts with added 'score' and 'summary' fields."""
    if not candidates:
        return []

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    items = []
    for paper, _kw in candidates:
        items.append({
            "id": paper.arxiv_id,
            "title": paper.title,
            "abstract": paper.abstract[:800],
            "primary_category": paper.primary_category,
        })

    user_message = (
        f"Rank these {len(items)} papers:\n\n"
        + json.dumps(items, indent=2)
    )

    raw = _call_gemini(api_key, SYSTEM_PROMPT, user_message)

    # Be lenient if model wraps in fences despite responseMimeType
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[error] could not parse ranker output: {e}")
        print(f"raw: {raw[:500]}")
        return []

    rankings = {r["id"]: r for r in parsed.get("rankings", [])}

    enriched = []
    for paper, kw in candidates:
        r = rankings.get(paper.arxiv_id)
        if not r:
            continue
        enriched.append({
            **paper.as_dict(),
            "score": r.get("score", 0),
            "summary": r.get("summary", ""),
            "matched_keywords": kw[:5],
        })

    enriched.sort(key=lambda x: x["score"], reverse=True)
    enriched = [e for e in enriched if e["score"] >= 5]
    return enriched[:top_n]
