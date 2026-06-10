"""Orchestrator V2 — modular layout-driven (S1→S5), song song với V1.

process_page: preprocess → layout detect → fan-out handlers theo group → reading
order/merge → PageResult. Khi `bundle` bật, mỗi step rơi artifact vào trace bundle.

Fan-out chạy TUẦN TỰ ở slice đầu (paddle CPU không đảm bảo thread-safe); kiến trúc
sẵn sàng song song hoá (ThreadPoolExecutor) khi tách worker — xem design mục 4.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from idp.extract.handlers.base import RegionHandler
from idp.extract.handlers.registry import default_handlers
from idp.layout.base import LayoutDetector
from idp.layout.ppstructure_layout import PPStructureLayoutDetector
from idp.preprocess.base import Preprocessor
from idp.preprocess.opencv_pre import OpenCVPreprocessor
from idp.reading_order.base import ReadingOrderer
from idp.reading_order.xycut import XYCutOrderer
from idp.schemas import BBox, Block, DocumentResult, PageResult, Region, RegionGroup
from idp.serialize.json import document_to_json
from idp.serialize.markdown import document_to_md, page_to_md
from idp.trace.bundle import TraceBundle


def _imread_unicode(path: Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Cannot decode image: {path}")
    return img


@dataclass
class PageOutcome:
    page_result: PageResult
    markdown: str
    n_regions: int
    latency_s: float
    warnings: list[str] = field(default_factory=list)


@dataclass
class PipelineV2:
    preprocessor: Preprocessor
    detector: LayoutDetector
    handlers: dict[RegionGroup, RegionHandler]
    orderer: ReadingOrderer

    @classmethod
    def default(
        cls,
        lang: str = "en",
        use_gpu: bool = False,
        enable_vlm: bool = True,
        vlm_base_url: str = "http://localhost:1234/v1",
        vlm_model: str = "qwen/qwen3-vl-8b",
    ) -> "PipelineV2":
        return cls(
            preprocessor=OpenCVPreprocessor(),
            detector=PPStructureLayoutDetector(lang=lang, use_gpu=use_gpu),
            handlers=default_handlers(
                lang=lang, use_gpu=use_gpu, enable_vlm=enable_vlm,
                vlm_base_url=vlm_base_url, vlm_model=vlm_model,
            ),
            orderer=XYCutOrderer(),
        )

    def process_page(
        self,
        image: np.ndarray,
        index: int,
        source_path: str,
        bundle: TraceBundle | None = None,
    ) -> PageOutcome:
        t0 = time.perf_counter()
        warnings: list[str] = []

        # S1
        pp = self.preprocessor.run(image, index, source_path)
        if bundle:
            bundle.save_input(image)
            bundle.save_preprocess(pp)

        # S2
        layout = self.detector.detect(pp)
        # Fallback: layout không có vùng nội dung xử lý được (vd ảnh chụp bị gom
        # cả trang thành 1 figure, hoặc rỗng) → thêm 1 vùng text phủ cả trang để
        # TextHandler OCR toàn trang (cơ chế đã chứng minh ở traditional/).
        usable = [
            r for r in layout.regions
            if r.group != "drop" and self.handlers.get(r.group) is not None
        ]
        if not usable:
            w, h = layout.image_size
            layout.regions.append(Region(
                label="text", group="text",
                bbox=BBox(quad=[0.0, 0.0, float(w), float(h)], page=index),
                score=0.0, region_id=len(layout.regions),
            ))
            warnings.append("layout fallback: no usable region → full-page OCR")
        if bundle:
            bundle.save_layout(layout, pp.image)

        # S3 — fan-out (tuần tự)
        blocks: list[Block] = []
        results: list[dict] = []
        for region in layout.regions:
            handler = self.handlers.get(region.group)
            if handler is None:  # drop hoặc group không có handler
                if region.group != "drop":
                    warnings.append(f"r{region.region_id}: no handler for '{region.group}'")
                continue
            block = handler.handle(region, pp)
            if handler.last_warning:
                warnings.append(f"r{region.region_id} ({region.group}): {handler.last_warning}")
            blocks.append(block)
            results.append({
                "region": region, "block": block,
                "engine": handler.last_engine,
                "latency_s": handler.last_latency_s,
                "warning": handler.last_warning,
            })
        if bundle:
            bundle.save_handlers(results, pp.image)

        # S4 — reading order / merge (barrier)
        ordered = self.orderer.order(blocks, layout)
        if bundle:
            bundle.save_reading_order(ordered, pp.image)

        # S5 — serialize
        page_result = PageResult(page=index, blocks=ordered, image_uri=source_path)
        markdown = page_to_md(page_result)
        if bundle:
            doc = DocumentResult(
                document_id=Path(source_path).stem, tier="B",
                engines_used=sorted({r["engine"] for r in results if r["engine"]}),
                pages=[page_result], warnings=warnings,
            )
            bundle.save_output(markdown, document_to_json(doc))

        return PageOutcome(
            page_result=page_result,
            markdown=markdown,
            n_regions=len(layout.regions),
            latency_s=time.perf_counter() - t0,
            warnings=warnings,
        )

    def process_image_file(
        self, path: str | Path, run_dir: Path | None = None, trace: bool = True
    ) -> PageOutcome:
        path = Path(path)
        image = _imread_unicode(path)
        bundle = (
            TraceBundle(run_dir, path.stem, enabled=True)
            if (trace and run_dir is not None)
            else None
        )
        outcome = self.process_page(image, 0, str(path), bundle)
        if bundle:
            bundle.finalize()
        return outcome

    def close(self) -> None:
        for h in self.handlers.values():
            close = getattr(h, "close", None)
            if callable(close):
                close()
