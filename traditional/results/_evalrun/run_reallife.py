"""Throwaway: trace all real-life eval/sample pages with ONE model load."""
import sys
import time
from pathlib import Path

HERE = Path(r"C:\Projects\ComputerVision\RnD_pipeline\traditional")
sys.path.insert(0, str(HERE / "src"))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from idp_trad.pipeline import Pipeline  # noqa: E402
from idp_trad.serialize.markdown import document_to_md  # noqa: E402
from idp_trad.trace.models import StepRecord  # noqa: E402
from idp_trad.trace.report import write_report  # noqa: E402
from idp_trad.trace.tracer import Tracer  # noqa: E402

sample_dir = Path(r"C:\Projects\ComputerVision\RnD_pipeline\eval\sample")
out_md = HERE / "results" / "reallife_md"
out_md.mkdir(parents=True, exist_ok=True)
tracer_base = HERE / "results" / "reallife_traces"

pipe = Pipeline()
for img in sorted(sample_dir.glob("page*.jpg")):
    tr = Tracer(tracer_base)
    pipe.tracer = tr
    t0 = time.time()
    try:
        doc = pipe.process_file(str(img))
        md = document_to_md(doc)
        if tr.doc and tr.doc.pages:
            tr.doc.pages[-1].steps.append(
                StepRecord(step="serialize", summary={"md_chars": len(md)})
            )
        tr.write()
        write_report(tr.doc, tr.doc_dir / "report.md")
        (out_md / (img.stem + ".md")).write_text(md, encoding="utf-8")
        p0 = tr.doc.pages[0]
        ex = p0.step("extract")
        pp = p0.step("preprocess")
        fb = ex.summary.get("fallback_used") if ex else None
        path = ex.summary.get("path_used") if ex else None
        lc = (pp.summary.get("enhance") or {}).get("low_contrast") if pp else None
        print(
            f"{img.name}: blocks={len(doc.pages[0].blocks)} path={path} "
            f"fallback={fb} low_contrast={lc} md_chars={len(md)} "
            f"{time.time() - t0:.1f}s"
        )
    except Exception as e:  # noqa: BLE001
        print(f"{img.name}: ERROR {type(e).__name__}: {e}")
print("REALLIFE_DONE")
