"""Orchestrator: ingest → preprocess → extract → DocumentResult.

A single traditional tier (Tier "A"): every page goes through CV preprocessing then
the PaddleOCR structure engine. Mirrors the hybrid Pipeline shape so scripts/eval
plumbing is familiar.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from idp_trad.extract.paddle_engine import PaddleStructureEngine
from idp_trad.ingest.loader import LoadedDocument, LoadedPage, load
from idp_trad.preprocess.cv_preprocess import preprocess
from idp_trad.schemas import Block, DocumentResult, PageResult


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

    _engine: PaddleStructureEngine | None = field(default=None, init=False, repr=False)
    traces: list[PageTrace] = field(default_factory=list, init=False, repr=False)

    @property
    def engine(self) -> PaddleStructureEngine:
        if self._engine is None:
            self._engine = PaddleStructureEngine(lang=self.lang, use_gpu=self.use_gpu)
        return self._engine

    def _process_page(self, page: LoadedPage) -> tuple[PageResult, PageTrace]:
        trace = PageTrace(page=page.index, engine=self.engine.name)
        blocks: list[Block] = []
        t0 = time.time()
        try:
            img, info = preprocess(
                page.image, do_deskew=self.do_deskew, do_denoise=self.do_denoise
            )
            trace.deskew_deg = info.get("deskew_deg", 0.0)
            page.image = img
            blocks = self.engine.parse(page)
        except Exception as e:  # noqa: BLE001 — one bad page must not kill the doc
            trace.error = f"{type(e).__name__}: {e}"
        trace.latency_s = time.time() - t0
        trace.n_blocks = len(blocks)
        return (
            PageResult(page=page.index, blocks=blocks, image_uri=page.source_path),
            trace,
        )

    def process_document(self, doc: LoadedDocument) -> DocumentResult:
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
