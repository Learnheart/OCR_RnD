"""TextHandler — PP-OCRv4 (det+rec) trên crop vùng text (S3).

Crop ROI của region rồi chạy PaddleOCR det+rec → gom dòng theo thứ tự (y rồi x).
Engine khởi tạo lười, dùng chung cho cả run. CPU (use_gpu=False).
"""

from __future__ import annotations

import time

import numpy as np

from idp.extract.handlers.base import RegionHandler, crop_region
from idp.preprocess.base import PreprocessedPage
from idp.schemas import BBox, Block, BlockType, Region

# nhãn detector → BlockType (trong cùng nhánh "text")
_LABEL_TO_BTYPE: dict[str, BlockType] = {
    "title": "title",
    "doc_title": "title",
    "paragraph_title": "title",
    "header": "header",
    "footer": "footer",
    "list": "list",
}


def _quad_to_xyxy(quad) -> tuple[float, float, float, float]:
    pts = np.asarray(quad, dtype=float).reshape(-1, 2)
    xs, ys = pts[:, 0], pts[:, 1]
    return float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())


def _join_lines(ocr_page) -> str:
    rows: list[tuple[float, float, str]] = []
    for entry in ocr_page or []:
        box, (txt, _conf) = entry[0], entry[1]
        txt = (txt or "").strip()
        if not txt:
            continue
        x0, y0, _x1, _y1 = _quad_to_xyxy(box)
        rows.append((y0, x0, txt))
    rows.sort(key=lambda r: (round(r[0] / 8), r[1]))  # bucket y → reading order
    return " ".join(r[2] for r in rows).strip()


class TextHandler(RegionHandler):
    group = "text"
    name = "ppocrv4-rec@cpu"

    def __init__(self, lang: str = "en", use_gpu: bool = False) -> None:
        super().__init__()
        self.lang = lang
        self.use_gpu = use_gpu
        self._ocr = None

    def _ocr_engine(self):
        if self._ocr is None:
            from paddleocr import PaddleOCR

            self._ocr = PaddleOCR(
                show_log=False, lang=self.lang, use_gpu=self.use_gpu,
                use_angle_cls=True,
            )
        return self._ocr

    def handle(self, region: Region, page: PreprocessedPage) -> Block:
        self.last_warning = None
        self.last_engine = self.name
        btype = _LABEL_TO_BTYPE.get(region.label, "text")
        roi = crop_region(page.image, region)
        text = ""
        t0 = time.perf_counter()
        if roi is not None and roi.size:
            try:
                res = self._ocr_engine().ocr(roi, cls=True)
                text = _join_lines(res[0] if res else None)
            except Exception as e:  # noqa: BLE001
                self.last_warning = f"text OCR failed: {type(e).__name__}: {e}"
        else:
            self.last_warning = "empty crop"
        self.last_latency_s = time.perf_counter() - t0
        return Block(
            type=btype,
            text=text or None,
            bbox=BBox(quad=list(region.bbox.as_xyxy()), page=page.index),
            confidence=region.score,
            reading_order=region.region_id,
        )
