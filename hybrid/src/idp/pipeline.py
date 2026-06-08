"""Orchestrator: ingest → route → extract → DocumentResult.

Slice đầu: Tier 0 (PDF digital-born) + Tier B (VLM cho ảnh/scan). Tier B được
khởi tạo lười (chỉ khi cần) → chạy Tier 0 không bắt buộc LM Studio.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from idp.classify.router import route
from idp.extract.tier0_direct import Tier0DirectEngine
from idp.extract.tier_b_lmstudio_vlm import LMStudioVLMEngine
from idp.ingest.loader import LoadedDocument, LoadedPage, load
from idp.schemas import Block, DocumentResult, PageResult


@dataclass
class PageTrace:
    """Thông tin chẩn đoán mỗi trang (latency/tier) — log ở M2."""

    page: int
    tier: str
    engine: str
    latency_s: float = 0.0
    n_blocks: int = 0
    error: str | None = None


@dataclass
class Pipeline:
    vlm_base_url: str = "http://localhost:1234/v1"
    vlm_model: str = "qwen/qwen3-vl-8b"
    vlm_max_tokens: int = 4096
    force_tier: str | None = None  # ép '0' hoặc 'B' (debug); None = auto-route

    _tier0: Tier0DirectEngine | None = field(default=None, init=False, repr=False)
    _tierb: LMStudioVLMEngine | None = field(default=None, init=False, repr=False)
    traces: list[PageTrace] = field(default_factory=list, init=False, repr=False)

    @property
    def tier0(self) -> Tier0DirectEngine:
        if self._tier0 is None:
            self._tier0 = Tier0DirectEngine()
        return self._tier0

    @property
    def tierb(self) -> LMStudioVLMEngine:
        if self._tierb is None:
            self._tierb = LMStudioVLMEngine(
                base_url=self.vlm_base_url,
                model=self.vlm_model,
                max_tokens=self.vlm_max_tokens,
            )
        return self._tierb

    def _process_page(self, page: LoadedPage) -> tuple[PageResult, PageTrace]:
        tier = self.force_tier or route(page)
        engine = self.tier0 if tier == "0" else self.tierb
        trace = PageTrace(page=page.index, tier=tier, engine=engine.name)
        blocks: list[Block] = []
        try:
            blocks = engine.parse(page)
            if tier == "B":
                trace.latency_s = self.tierb.last_latency_s
        except Exception as e:  # noqa: BLE001 — 1 trang lỗi không phá cả doc
            trace.error = f"{type(e).__name__}: {e}"
        trace.n_blocks = len(blocks)
        pr = PageResult(
            page=page.index,
            blocks=blocks,
            image_uri=page.source_path,
        )
        return pr, trace

    def process_document(self, doc: LoadedDocument) -> DocumentResult:
        pages: list[PageResult] = []
        engines_used: set[str] = set()
        warnings: list[str] = []
        tiers: set[str] = set()
        for page in doc.pages:
            pr, trace = self._process_page(page)
            self.traces.append(trace)
            tiers.add(trace.tier)
            engines_used.add(trace.engine)
            if trace.error:
                warnings.append(f"page {trace.page}: {trace.error}")
            pages.append(pr)

        # tier đại diện: nếu mọi trang cùng tier → tier đó; lẫn lộn → ưu tiên B
        tier = next(iter(tiers)) if len(tiers) == 1 else "B"
        return DocumentResult(
            document_id=doc.document_id,
            tier=tier,  # type: ignore[arg-type]
            engines_used=sorted(engines_used),
            pages=pages,
            warnings=warnings,
        )

    def process_file(self, path: str) -> DocumentResult:
        with load(path) as doc:
            return self.process_document(doc)

    def close(self) -> None:
        if self._tierb is not None:
            self._tierb.close()
