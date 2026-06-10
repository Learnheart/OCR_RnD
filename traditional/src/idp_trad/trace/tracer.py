"""Tracer — collects per-step records for one run and writes `trace.json`.

The tracer is deliberately thin: it owns the output directory, accumulates
`PageTraceRecord`s, and serialises them. Rendering heavy artifacts (overlay PNGs,
block crops) is delegated to `idp_trad.trace.artifacts`, imported lazily so the core
pipeline runs even if that module (or its image deps) is absent — in that case the
records are still written, just without the picture files.

Contract for the artifacts module (implemented by feature F1):

    artifacts.dump_page(
        page_dir: Path,
        *,
        original,        # np.ndarray | None  — image as ingested
        preprocessed,    # np.ndarray | None  — image after preprocess
        blocks,          # list[Block]         — final ordered blocks
        last_meta,       # dict                — engine.last_meta (path/regions/fallback)
    ) -> dict[str, list[Artifact]]

It returns a mapping {step_name: [Artifact, ...]} that the pipeline attaches to the
matching StepRecord. Any exception inside it is swallowed (tracing must never break
a run).
"""

from __future__ import annotations

import json
from pathlib import Path

from idp_trad.trace.models import DocumentTrace, PageTraceRecord


def _safe_stem(document_id: str) -> str:
    keep = "-_."
    s = "".join(c if (c.isalnum() or c in keep) else "_" for c in document_id)
    return s.strip("_") or "doc"


class Tracer:
    """Opt-in run tracer. Construct with the base dir where traces should land."""

    def __init__(self, base_dir: str | Path, *, dump_artifacts: bool = True) -> None:
        self.base_dir = Path(base_dir)
        self.dump_artifacts = dump_artifacts
        self.doc: DocumentTrace | None = None
        self._doc_dir: Path | None = None

    # --- lifecycle ---
    def begin_document(self, document_id: str, source_path: str = "") -> Path:
        stem = _safe_stem(document_id)
        self._doc_dir = self.base_dir / stem
        self._doc_dir.mkdir(parents=True, exist_ok=True)
        self.doc = DocumentTrace(
            document_id=document_id,
            source_path=source_path,
            output_dir=str(self._doc_dir),
        )
        return self._doc_dir

    @property
    def doc_dir(self) -> Path:
        if self._doc_dir is None:
            raise RuntimeError("Tracer.begin_document must be called first")
        return self._doc_dir

    def add_page(self, page: int, engine: str) -> PageTraceRecord:
        if self.doc is None:
            raise RuntimeError("Tracer.begin_document must be called first")
        rec = PageTraceRecord(page=page, engine=engine)
        self.doc.pages.append(rec)
        return rec

    # --- artifact dumping (delegated, never raises) ---
    def dump_page_artifacts(
        self,
        rec: PageTraceRecord,
        *,
        original=None,
        preprocessed=None,
        blocks=None,
        last_meta=None,
    ) -> None:
        if not self.dump_artifacts:
            return
        try:
            from idp_trad.trace import artifacts
        except Exception:  # noqa: BLE001 — artifacts module/deps optional
            return
        page_dir = self.doc_dir / f"page_{rec.page:03d}"
        try:
            page_dir.mkdir(parents=True, exist_ok=True)
            by_step = artifacts.dump_page(
                page_dir,
                original=original,
                preprocessed=preprocessed,
                blocks=blocks or [],
                last_meta=last_meta or {},
            )
        except Exception as e:  # noqa: BLE001 — tracing must not break a run
            rec_step = rec.step("extract")
            if rec_step is not None:
                rec_step.summary.setdefault("artifact_error", f"{type(e).__name__}: {e}")
            return
        # attach produced artifacts to their step records (paths relative to doc dir)
        for step_name, arts in (by_step or {}).items():
            step_rec = rec.step(step_name)
            if step_rec is None:
                continue
            for a in arts:
                try:
                    a.path = Path(a.path).relative_to(self.doc_dir).as_posix()
                except ValueError:
                    pass
                step_rec.artifacts.append(a)

    # --- finalise ---
    def write(self) -> Path:
        if self.doc is None:
            raise RuntimeError("Tracer.begin_document must be called first")
        out = self.doc_dir / "trace.json"
        out.write_text(
            json.dumps(self.doc.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return out
