"""Batch runner cho Pipeline V2 — chạy 1 thư mục ảnh, sinh trace bundle.

Pha 1 (R10): QA trực quan trên ../eval/sample (9 ảnh, KHÔNG GT).
  python scripts/run_v2.py --images ../eval/sample --run-name sample-visual

Sinh: results/v2_runs/<YYYY-MM-DD_HHMM>_<run_name>/ với 1 folder/trang + index.html.
Tùy chọn --preds-out để đồng thời ghi .md (cho OmniDocBench sau).
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

# cho phép `import idp` khi chạy trực tiếp
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from idp.pipeline_v2 import PipelineV2  # noqa: E402
from idp.trace.bundle import write_run_index  # noqa: E402

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Hybrid V2 batch runner")
    ap.add_argument("--images", required=True, help="thư mục ảnh đầu vào")
    ap.add_argument("--run-name", default="v2", help="tên run")
    ap.add_argument("--lang", default="en", help="ngôn ngữ PaddleOCR (en/ch)")
    ap.add_argument("--no-vlm", action="store_true", help="tắt nhánh VLM (formula/chart/seal)")
    ap.add_argument("--no-trace", action="store_true", help="không ghi trace bundle")
    ap.add_argument("--vlm-base-url", default="http://localhost:1234/v1")
    ap.add_argument("--vlm-model", default="qwen/qwen3-vl-8b")
    ap.add_argument("--preds-out", default=None, help="ghi .md vào thư mục này (OmniDocBench)")
    ap.add_argument("--limit", type=int, default=0, help="chỉ chạy N ảnh đầu (0=tất cả)")
    args = ap.parse_args()

    img_dir = Path(args.images).resolve()
    images = sorted(p for p in img_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if args.limit:
        images = images[: args.limit]
    if not images:
        print(f"Không có ảnh trong {img_dir}", file=sys.stderr)
        return 1

    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    run_dir = Path(__file__).resolve().parent.parent / "results" / "v2_runs" / f"{ts}_{args.run_name}"
    run_dir.mkdir(parents=True, exist_ok=True)
    preds_out = Path(args.preds_out).resolve() if args.preds_out else None
    if preds_out:
        preds_out.mkdir(parents=True, exist_ok=True)

    print(f"[V2] {len(images)} ảnh → {run_dir}")
    pipe = PipelineV2.default(
        lang=args.lang, enable_vlm=not args.no_vlm,
        vlm_base_url=args.vlm_base_url, vlm_model=args.vlm_model,
    )

    pages_meta: list[dict] = []
    t_start = time.perf_counter()
    try:
        for i, img in enumerate(images, 1):
            t0 = time.perf_counter()
            outcome = pipe.process_image_file(img, run_dir=run_dir, trace=not args.no_trace)
            dt = time.perf_counter() - t0
            if preds_out:
                (preds_out / f"{img.stem}.md").write_text(outcome.markdown, encoding="utf-8")
            pages_meta.append({
                "page_stem": img.stem, "n_regions": outcome.n_regions,
                "latency_s": round(dt, 2), "n_warnings": len(outcome.warnings),
            })
            print(f"  [{i}/{len(images)}] {img.name}: {outcome.n_regions} regions, "
                  f"{dt:.1f}s, {len(outcome.warnings)} warn")
    finally:
        pipe.close()

    meta = {
        "run_name": args.run_name, "timestamp": ts, "n_images": len(images),
        "lang": args.lang, "vlm": (not args.no_vlm), "vlm_model": args.vlm_model,
        "detector": pipe.detector.name, "elapsed_s": round(time.perf_counter() - t_start, 1),
    }
    if not args.no_trace:
        write_run_index(run_dir, pages_meta, meta)
    print(f"[V2] xong {meta['elapsed_s']}s → {run_dir / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
