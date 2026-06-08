"""Batch runner dùng chung: ảnh[] → Markdown .md vào pred_dir (resume, log, latency).

Dùng bởi `scripts/run_omnidocbench.py` (full) và `scripts/eval_run.py` (sample có timestamp).
"""

from __future__ import annotations

import functools
import json
import time
from pathlib import Path
from typing import Callable

from idp.pipeline import Pipeline
from idp.serialize.markdown import document_to_md

# print có flush → tiến độ hiện ngay cả khi stdout bị pipe (tee) buffer
_flush_print = functools.partial(print, flush=True)


def run_batch(
    images: list[Path],
    pred_dir: Path,
    pipe: Pipeline,
    *,
    overwrite: bool = False,
    latency_out: Path | None = None,
    log: Callable[[str], None] = _flush_print,
) -> dict:
    """Xử lý từng ảnh → ghi <stem>.md. Lỗi → KHÔNG ghi file (để resume thử lại).

    Trả dict thống kê: n_total, n_done, n_error, latencies, elapsed_s.
    """
    pred_dir.mkdir(parents=True, exist_ok=True)
    todo: list[tuple[Path, Path]] = []
    for img in images:
        out = pred_dir / (img.stem + ".md")
        if out.exists() and not overwrite:
            continue
        todo.append((img, out))

    total = len(todo)
    log(f"[info] {len(images)} ảnh, {total} cần xử lý → {pred_dir}")
    latencies: list[float] = []
    records: list[dict] = []
    errors = 0
    t_start = time.perf_counter()

    for i, (img, out) in enumerate(todo, 1):
        try:
            doc = pipe.process_file(str(img))
            err = pipe.traces[-1].error if pipe.traces else None
            lat = pipe.traces[-1].latency_s if pipe.traces else 0.0
            if err:
                errors += 1
                status = f"ERROR={err}"
                records.append({"image": img.name, "error": err})
            else:
                md = document_to_md(doc)
                out.write_text(md, encoding="utf-8")
                latencies.append(lat)
                status = f"{lat:.1f}s, {len(md)} chars"
                records.append({"image": img.name, "latency_s": round(lat, 2),
                                "chars": len(md)})
        except Exception as e:  # noqa: BLE001
            errors += 1
            status = f"FATAL={type(e).__name__}: {e}"
            records.append({"image": img.name, "error": status})

        avg = sum(latencies) / len(latencies) if latencies else 0.0
        eta = avg * (total - i)
        log(f"[{i}/{total}] {img.name[:58]:58s} {status} "
            f"| avg {avg:.1f}s eta {eta/60:.1f}m")

    elapsed = time.perf_counter() - t_start
    avg = sum(latencies) / len(latencies) if latencies else 0.0
    log(f"[done] {total} ảnh / {elapsed/60:.1f} phút | avg {avg:.1f}s | lỗi {errors}")

    stats = {
        "n_total": total,
        "n_done": len(latencies),
        "n_error": errors,
        "avg_latency_s": round(avg, 2),
        "p50_latency_s": round(sorted(latencies)[len(latencies)//2], 2) if latencies else 0,
        "max_latency_s": round(max(latencies), 2) if latencies else 0,
        "elapsed_s": round(elapsed, 1),
    }
    if latency_out is not None:
        latency_out.parent.mkdir(parents=True, exist_ok=True)
        latency_out.write_text(
            json.dumps({"stats": stats, "records": records}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return stats


def make_pipeline(base_url: str, model: str, max_tokens: int) -> Pipeline:
    return Pipeline(
        vlm_base_url=base_url, vlm_model=model,
        vlm_max_tokens=max_tokens, force_tier="B",
    )
