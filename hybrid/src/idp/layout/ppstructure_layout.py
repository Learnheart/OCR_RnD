"""S2 detector — PPStructure 2.x ở chế độ LAYOUT-ONLY (CPU).

Chạy PPStructure với `layout=True, ocr=False, table=False` → chỉ trả vùng
{type, bbox} không kèm nhận dạng. Việc nhận dạng đẩy sang handler ở S3 (tách bạch
detect ↔ extract → trace/eval per-step, oracle-crop sau này).

CPU bắt buộc: paddle-gpu 3.3 trả 0 detection trên Blackwell (sm_120) → use_gpu=False
([[blackwell-paddle-gpu-broken]]). PP-DocLayout_plus-L (23 nhãn) cần paddleocr 3.x/
paddlex — chưa cài (sẽ phá API PPStructure 2.x của traditional) → để swap sau.
"""

from __future__ import annotations

from idp.layout.base import LayoutDetector, label_to_group
from idp.preprocess.base import PreprocessedPage
from idp.schemas import BBox, LayoutResult, Region


class PPStructureLayoutDetector(LayoutDetector):
    name = "ppstructure-layout@cpu"

    def __init__(self, lang: str = "en", use_gpu: bool = False) -> None:
        self.lang = lang
        self.use_gpu = use_gpu
        self._engine = None

    def _layout_engine(self):
        if self._engine is None:
            from paddleocr import PPStructure

            self._engine = PPStructure(
                show_log=False,
                lang=self.lang,
                use_gpu=self.use_gpu,
                layout=True,
                table=False,
                ocr=False,
                recovery=False,
            )
        return self._engine

    def detect(self, page: PreprocessedPage) -> LayoutResult:
        regions_raw = self._layout_engine()(page.image)
        regions: list[Region] = []
        for i, r in enumerate(regions_raw):
            bbox = r.get("bbox")
            if not (isinstance(bbox, (list, tuple)) and len(bbox) == 4):
                continue
            label = str(r.get("type", "text")).lower()
            score = float(r.get("score", 1.0) or 1.0)
            regions.append(
                Region(
                    label=label,
                    group=label_to_group(label),
                    bbox=BBox(quad=[float(v) for v in bbox], page=page.index),
                    score=score,
                    region_id=i,
                )
            )
        return LayoutResult(
            page=page.index,
            regions=regions,
            image_size=(page.width, page.height),
        )
