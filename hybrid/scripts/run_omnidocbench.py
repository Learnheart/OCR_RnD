"""Batch OmniDocBench (full hoặc theo sample) → predictions/end2end/<name>.md.

Dùng cho FULL run vào thư mục predictions chung. Để chạy sample CÓ timestamp +
chấm điểm + archive, dùng `scripts/eval_run.py`.

    uv run python scripts/run_omnidocbench.py --limit 2          # smoke
    uv run python scripts/run_omnidocbench.py                    # full 1651
    uv run python scripts/run_omnidocbench.py --sample-file ../eval/samples/sample_100.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HYBRID_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HYBRID_DIR / "src"))

from idp.batch import make_pipeline, run_batch  # noqa: E402

EVAL_DIR = HYBRID_DIR.parent / "eval"
IMAGES_DIR = EVAL_DIR / "OmniDocBench_data" / "images"
PRED_DIR = EVAL_DIR / "predictions" / "end2end"
IMG_EXTS = {".png", ".jpg", ".jpeg"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="chỉ N ảnh đầu (smoke)")
    ap.add_argument("--sample-file", default=None,
                    help="file liệt kê tên ảnh (1 dòng/ảnh) để chỉ chạy sample đó")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--images-dir", default=str(IMAGES_DIR))
    ap.add_argument("--pred-dir", default=str(PRED_DIR))
    ap.add_argument("--base-url", default="http://localhost:1234/v1")
    ap.add_argument("--model", default="qwen/qwen3-vl-8b")
    ap.add_argument("--max-tokens", type=int, default=4096)
    args = ap.parse_args()

    images_dir = Path(args.images_dir)
    pred_dir = Path(args.pred_dir)

    if args.sample_file:
        names = [ln.strip() for ln in Path(args.sample_file).read_text(
            encoding="utf-8").splitlines() if ln.strip()]
        images = [images_dir / nm for nm in names if (images_dir / nm).exists()]
    else:
        images = sorted(p for p in images_dir.iterdir()
                        if p.suffix.lower() in IMG_EXTS)
    if args.limit is not None:
        images = images[: args.limit]
    if not images:
        print(f"[ERR] không có ảnh ({images_dir})", file=sys.stderr)
        return 1

    pipe = make_pipeline(args.base_url, args.model, args.max_tokens)
    try:
        run_batch(images, pred_dir, pipe, overwrite=args.overwrite)
    finally:
        pipe.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
