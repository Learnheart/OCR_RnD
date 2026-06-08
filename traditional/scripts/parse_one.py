"""Debug a single image → print Markdown (and a block summary) to stdout.

    python scripts/parse_one.py <image_path> [--blocks]

Run with the ocr-worker conda env (has PaddleOCR):
    %USERPROFILE%\.conda\envs\ocr-worker\python.exe scripts/parse_one.py <img>
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

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))

from idp_trad.pipeline import Pipeline  # noqa: E402
from idp_trad.serialize.markdown import document_to_md  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--blocks", action="store_true", help="print block summary")
    ap.add_argument("--no-deskew", action="store_true")
    args = ap.parse_args()

    pipe = Pipeline(do_deskew=not args.no_deskew)
    doc = pipe.process_file(args.image)

    if args.blocks:
        for p in doc.pages:
            for b in sorted(p.blocks, key=lambda x: x.reading_order):
                preview = (b.text or b.html or b.latex or "")[:60].replace("\n", " ")
                print(f"  [{b.reading_order:2d}] {b.type:7s} {preview!r}")
        for t in pipe.traces:
            print(f"  trace: {t.latency_s:.2f}s blocks={t.n_blocks} "
                  f"deskew={t.deskew_deg} err={t.error}")
        print("---")
    print(document_to_md(doc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
