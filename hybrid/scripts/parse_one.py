"""Debug 1 file: in DocumentResult JSON (rút gọn) + Markdown + trace latency/tier.

    uv run python scripts/parse_one.py <path> [--tier 0|B] [--md-out out.md]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Windows console cp1252 crash với CJK/tiếng Việt → ép UTF-8.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from idp.pipeline import Pipeline  # noqa: E402
from idp.serialize.markdown import document_to_md  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--tier", choices=["0", "B"], default=None,
                    help="ép tier (mặc định auto-route)")
    ap.add_argument("--md-out", default=None)
    args = ap.parse_args()

    pipe = Pipeline(force_tier=args.tier)
    try:
        doc = pipe.process_file(args.path)
    finally:
        pipe.close()

    md = document_to_md(doc)

    print("=== DocumentResult (meta) ===")
    print(f"document_id : {doc.document_id}")
    print(f"tier        : {doc.tier}")
    print(f"engines     : {doc.engines_used}")
    print(f"pages       : {len(doc.pages)}  blocks/page: "
          f"{[len(p.blocks) for p in doc.pages]}")
    if doc.warnings:
        print(f"warnings    : {doc.warnings}")
    print("=== traces ===")
    for t in pipe.traces:
        print(f"  page {t.page}: tier={t.tier} engine={t.engine} "
              f"latency={t.latency_s:.2f}s blocks={t.n_blocks}"
              + (f" ERROR={t.error}" if t.error else ""))
    print("=== Markdown (first 2000 chars) ===")
    print(md[:2000])

    if args.md_out:
        Path(args.md_out).write_text(md, encoding="utf-8")
        print(f"\n[written] {args.md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
