"""Keyword-based pre-filter to drop obvious non-matches before LLM ranking.

Goal: keep recall high, kill cost. We're generous here — the LLM ranker
will do the precise sorting. Anything that mentions hardware, systems,
acceleration, efficiency, or specific accelerator concepts stays in.
"""

from __future__ import annotations

import re

# Lowercased keywords. Match as whole-word where useful.
# Grouped only for readability — all are OR'd together.
HARDWARE_KEYWORDS = {
    # Accelerators & architecture
    "gpu", "tpu", "npu", "ipu", "dpu", "fpga", "asic", "accelerator",
    "systolic", "tensor core", "matrix engine", "dataflow",
    "chiplet", "interconnect", "nvlink", "hbm", "sram", "dram",
    "in-memory computing", "compute-in-memory", "processing-in-memory",
    "near-memory", "pim ", "cim ", "rram", "memristor", "phase-change",
    "analog computing", "photonic", "optical computing",

    # Edge / embedded / efficient inference
    "edge inference", "edge ai", "on-device", "tinyml", "microcontroller",
    "embedded ml", "mobile inference", "low-power", "energy-efficient",
    "energy efficiency", "power efficiency",

    # Quantization & sparsity (hardware-driven)
    "quantization", "quantize", "int8", "int4", "fp8", "fp4", "mxfp",
    "bfloat", "mixed-precision", "low-precision", "post-training quantization",
    "sparsity", "sparse", "pruning", "structured sparsity", "2:4 sparsity",
    "n:m sparsity",

    # Compilers, kernels, systems
    "kernel fusion", "cuda kernel", "triton", "cutlass", "tvm", "mlir",
    "xla", "tensorrt", "vllm", "sglang", "tensor parallel", "pipeline parallel",
    "tensor parallelism", "pipeline parallelism", "model parallel",
    "speculative decoding", "kv cache", "kv-cache", "paged attention",
    "flash attention", "flashattention", "attention kernel",

    # Training systems
    "distributed training", "data parallel", "zero offload", "fsdp",
    "gradient checkpoint", "memory-efficient training", "activation checkpoint",

    # Neuromorphic / spiking / novel compute
    "neuromorphic", "spiking", "snn", "loihi", "truenorth", "event-driven",
    "stochastic computing", "approximate computing",

    # Inference engines / serving
    "inference engine", "model serving", "llm serving", "llm inference",
    "throughput", "latency", "tokens per second", "tokens/sec",

    # NAS / hardware-aware
    "hardware-aware", "hardware aware", "neural architecture search",
    "co-design", "hw-sw co-design", "hardware-software co-design",

    # DSP / signal processing on hardware
    "dsp ", "vector processor", "risc-v", "risc v",
}


def _build_pattern() -> re.Pattern:
    # Sort longer first so multi-word phrases match before substrings.
    kws = sorted(HARDWARE_KEYWORDS, key=len, reverse=True)
    escaped = [re.escape(k) for k in kws]
    return re.compile(r"(?:^|[^a-z0-9])(" + "|".join(escaped) + r")(?:[^a-z0-9]|$)", re.I)


_PATTERN = _build_pattern()

# Cheap category-based passthroughs — cs.AR papers are almost always relevant.
ALWAYS_KEEP_CATEGORIES = {"cs.AR", "cs.PF"}


def is_relevant(paper) -> tuple[bool, list[str]]:
    """Return (keep, matched_keywords). Keep if any keyword matches title/abstract,
    or if primary category is in the always-keep set."""
    if paper.primary_category in ALWAYS_KEEP_CATEGORIES:
        return True, [f"cat:{paper.primary_category}"]

    text = f"{paper.title}\n{paper.abstract}".lower()
    matches = _PATTERN.findall(text)
    if matches:
        # dedupe while preserving order
        seen = set()
        unique = []
        for m in matches:
            ml = m.lower()
            if ml not in seen:
                seen.add(ml)
                unique.append(ml)
        return True, unique
    return False, []


def filter_papers(papers):
    kept = []
    for p in papers:
        keep, matches = is_relevant(p)
        if keep:
            kept.append((p, matches))
    return kept
