"""Orchestrator: ingest → preprocess → extract → reading_order → DocumentResult.

A single traditional tier (Tier "A"): every page goes through CV preprocessing then
the PaddleOCR structure engine. Mirrors the hybrid Pipeline shape so scripts/eval
plumbing is familiar.

Tracing: pass a `Tracer` (see idp_trad.trace) to capture every step's timing, a
structured summary, and on-disk artifacts. When `tracer is None` (the default, used
by eval/batch) the pipeline runs exactly as before with zero overhead.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from idp_trad.extract.paddle_engine import PaddleStructureEngine
from idp_trad.ingest.loader import LoadedDocument, LoadedPage, load
from idp_trad.preprocess.cv_preprocess import preprocess
from idp_trad.schemas import Block, DocumentResult, PageResult
from idp_trad.trace.models import PageTraceRecord, StepRecord
from idp_trad.trace.tracer import Tracer


@dataclass
class PageTrace:
    page: int
    engine: str
    latency_s: float = 0.0
    n_blocks: int = 0
    deskew_deg: float = 0.0
    error: str | None = None


@dataclass
class Pipeline:
    lang: str = "ch"
    use_gpu: bool = False
    do_deskew: bool = True
    do_denoise: bool = False
    tracer: Tracer | None = None

    _engine: PaddleStructureEngine | None = field(default=None, init=False, repr=False)
    traces: list[PageTrace] = field(default_factory=list, init=False, repr=False)

    @property
    def engine(self) -> PaddleStructureEngine:
        if self._engine is None:
            self._engine = PaddleStructureEngine(lang=self.lang, use_gpu=self.use_gpu)
        return self._engine

    def _process_page(self, page: LoadedPage) -> tuple[PageResult, PageTrace]:
        trace = PageTrace(page=page.index, engine=self.engine.name)
        rec = self.tracer.add_page(page.index, self.engine.name) if self.tracer else None
        blocks: list[Block] = []
        original = page.image.copy() if self.tracer else None
        t_page = time.time()
        try:
            # --- ingest (image already loaded upstream; record provenance) ---
            if rec is not None:
                h, w = page.image.shape[:2]
                ch = 1 if page.image.ndim == 2 else page.image.shape[2]
                rec.steps.append(
                    StepRecord(
                        step="ingest",
                        summary={
                            "source_path": page.source_path,
                            "height": int(h),
                            "width": int(w),
                            "channels": int(ch),
                        },
                    )
                )

            # --- preprocess ---
            t0 = time.time()
            img, info = preprocess(
                page.image, do_deskew=self.do_deskew, do_denoise=self.do_denoise
            )
            trace.deskew_deg = info.get("deskew_deg", 0.0)
            page.image = img
            if rec is not None:
                rec.steps.append(
                    StepRecord(
                        step="preprocess",
                        latency_s=round(time.time() - t0, 4),
                        summary={k: info.get(k) for k in info},
                    )
                )

            # --- extract (structure / fallback) + reading order ---
            blocks = self.engine.parse(page)
            if rec is not None:
                meta = dict(getattr(self.engine, "last_meta", {}) or {})
                rec.steps.append(
                    StepRecord(
                        step="extract",
                        latency_s=round(float(meta.get("extract_s", 0.0)), 4),
                        summary={
                            "path_used": meta.get("path_used"),
                            "fallback_used": meta.get("fallback_used"),
                            "fallback_reason": meta.get("fallback_reason"),
                            "struct_chars": meta.get("struct_chars"),
                            "n_regions": meta.get("n_regions"),
                            "regions": meta.get("regions"),
                        },
                    )
                )
                rec.steps.append(
                    StepRecord(
                        step="reading_order",
                        latency_s=round(float(meta.get("reading_order_s", 0.0)), 4),
                        summary={"n_blocks": len(blocks)},
                    )
                )
        except Exception as e:  # noqa: BLE001 — one bad page must not kill the doc
            trace.error = f"{type(e).__name__}: {e}"
            if rec is not None:
                target = rec.steps[-1] if rec.steps else None
                if target is not None:
                    target.error = trace.error
        trace.latency_s = time.time() - t_page
        trace.n_blocks = len(blocks)

        if rec is not None:
            rec.total_latency_s = round(trace.latency_s, 4)
            rec.n_blocks = len(blocks)
            self.tracer.dump_page_artifacts(  # type: ignore[union-attr]
                rec,
                original=original,
                preprocessed=page.image,
                blocks=blocks,
                last_meta=getattr(self.engine, "last_meta", {}),
            )

        return (
            PageResult(page=page.index, blocks=blocks, image_uri=page.source_path),
            trace,
        )

    def process_document(self, doc: LoadedDocument) -> DocumentResult:
        if self.tracer is not None:
            self.tracer.begin_document(doc.document_id, source_path=doc.source_path)
        pages: list[PageResult] = []
        warnings: list[str] = []
        for page in doc.pages:
            pr, trace = self._process_page(page)
            self.traces.append(trace)
            if trace.error:
                warnings.append(f"page {trace.page}: {trace.error}")
            pages.append(pr)
        return DocumentResult(
            document_id=doc.document_id,
            tier="A",
            engines_used=[self.engine.name],
            pages=pages,
            warnings=warnings,
        )

    def process_file(self, path: str) -> DocumentResult:
        with load(path) as doc:
            return self.process_document(doc)

    def close(self) -> None:
        return None
