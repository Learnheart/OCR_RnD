"""Debug a single image → print Markdown (and a block summary) to stdout.

    python scripts/parse_one.py <image_path> [--blocks] [--trace [DIR]]

Run with the ocr-worker conda env (has PaddleOCR):
    %USERPROFILE%\.conda\envs\ocr-worker\python.exe scripts/parse_one.py <img>
"""

from __future__ import annotations

import argparse
import sys
import time
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
    ap.add_argument(
        "--trace",
        nargs="?",
        const="results/traces",
        default=None,
        metavar="DIR",
        help="dump a per-step trace (trace.json + report.md + artifacts) to DIR "
        "(default: results/traces)",
    )
    args = ap.parse_args()

    tracer = None
    if args.trace is not None:
        from idp_trad.trace.tracer import Tracer  # noqa: E402

        tracer = Tracer(args.trace)

    pipe = Pipeline(do_deskew=not args.no_deskew, tracer=tracer)
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

    md = document_to_md(doc)

    if tracer is not None and tracer.doc is not None:
        from idp_trad.trace.models import StepRecord  # noqa: E402
        from idp_trad.trace.report import write_report  # noqa: E402

        # time + record the serialize step on the last page record
        t0 = time.time()
        _md2 = document_to_md(doc)
        ser_s = round(time.time() - t0, 4)
        if tracer.doc.pages:
            tracer.doc.pages[-1].steps.append(
                StepRecord(
                    step="serialize",
                    latency_s=ser_s,
                    summary={"md_chars": len(_md2)},
                )
            )
        trace_json = tracer.write()
        report_path = write_report(tracer.doc, tracer.doc_dir / "report.md")
        n_pages = len(tracer.doc.pages)
        n_fallback = sum(
            1
            for p in tracer.doc.pages
            if (p.step("extract").summary if p.step("extract") else {}).get(
                "fallback_used"
            )
        )
        print(f"[trace] dir: {tracer.doc_dir}", file=sys.stderr)
        print(f"[trace] {trace_json.name}, {report_path.name}", file=sys.stderr)
        print(
            f"[trace] pages={n_pages} fallback={n_fallback}",
            file=sys.stderr,
        )

    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
