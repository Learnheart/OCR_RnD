"""Batch runner: process an image list → write one Markdown per image + latency.

Mirrors hybrid's batch interface (make_pipeline / run_batch) so the eval
orchestrator is near-identical.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from idp_trad.pipeline import Pipeline
from idp_trad.serialize.markdown import document_to_md


def make_pipeline(lang: str = "ch", use_gpu: bool = False,
                  do_deskew: bool = True) -> Pipeline:
    return Pipeline(lang=lang, use_gpu=use_gpu, do_deskew=do_deskew)


def run_batch(
    images: list[Path],
    pred_dir: Path,
    pipe: Pipeline,
    overwrite: bool = False,
    latency_out: Path | None = None,
) -> dict:
    pred_dir.mkdir(parents=True, exist_ok=True)
    latencies: list[float] = []
    n_error = 0
    n_done = 0
    t_start = time.time()
    for k, img in enumerate(images, 1):
        out = pred_dir / (img.stem + ".md")
        if out.exists() and not overwrite:
            continue
        t0 = time.time()
        try:
            doc = pipe.process_file(str(img))
            md = document_to_md(doc)
            if doc.warnings:
                n_error += 1
        except Exception as e:  # noqa: BLE001
            md = ""
            n_error += 1
            print(f"  [ERR] {img.name}: {type(e).__name__}: {e}")
        dt = time.time() - t0
        latencies.append(dt)
        out.write_text(md, encoding="utf-8")
        n_done += 1
        if k % 10 == 0 or k == len(images):
            print(f"  [{k}/{len(images)}] {img.name[:40]} {dt:.2f}s")

    latencies_sorted = sorted(latencies)
    stats = {
        "n_images": len(images),
        "n_generated": n_done,
        "n_error": n_error,
        "elapsed_s": round(time.time() - t_start, 1),
        "avg_latency_s": round(sum(latencies) / len(latencies), 2) if latencies else 0,
        "p50_latency_s": round(latencies_sorted[len(latencies_sorted) // 2], 2)
        if latencies_sorted else 0,
        "max_latency_s": round(max(latencies), 2) if latencies else 0,
    }
    if latency_out is not None:
        latency_out.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats
