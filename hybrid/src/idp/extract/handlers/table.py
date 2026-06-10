"""TableHandler — PP-Structure (SLANet) trên crop vùng table → HTML (S3).

Chạy PPStructure table-only (`table=True, layout=False, ocr=True`) trên ROI bảng
→ HTML cho TEDS. Làm sạch attribute trang trí, giữ rowspan/colspan (logic port từ
traditional). CPU.
"""

from __future__ import annotations

import re
import time

import numpy as np

from idp.extract.handlers.base import RegionHandler, crop_region
from idp.preprocess.base import PreprocessedPage
from idp.schemas import BBox, Block, Region

_KEEP_CELL_ATTRS = {"rowspan", "colspan"}


def _clean_table_html(html: str) -> str:
    def _scrub(m: re.Match) -> str:
        tag = m.group(1).lower()
        attrs = m.group(2) or ""
        if tag in ("td", "th"):
            kept = []
            for am in re.finditer(
                r'([A-Za-z_:][-\w:]*)\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)', attrs
            ):
                if am.group(1).lower() in _KEEP_CELL_ATTRS:
                    kept.append(f" {am.group(1).lower()}={am.group(2)}")
            return f"<{tag}{''.join(kept)}>"
        return f"<{tag}>"

    return re.sub(
        r"<(table|thead|tbody|tfoot|tr|td|th)\b([^>]*)>",
        _scrub, html, flags=re.IGNORECASE,
    )


def _extract_table_html(res) -> str:
    html = res.get("html", "") if isinstance(res, dict) else ""
    if not isinstance(html, str) or not html:
        return ""
    if "<table" in html:
        start = html.find("<table")
        end = html.rfind("</table>")
        if end != -1:
            html = html[start : end + len("</table>")]
    html = html.strip()
    return _clean_table_html(html) if html else ""


class TableHandler(RegionHandler):
    group = "table"
    name = "ppstructure-table@cpu"

    def __init__(self, lang: str = "en", use_gpu: bool = False) -> None:
        super().__init__()
        self.lang = lang
        self.use_gpu = use_gpu
        self._engine = None

    def _table_engine(self):
        if self._engine is None:
            from paddleocr import PPStructure

            self._engine = PPStructure(
                show_log=False, lang=self.lang, use_gpu=self.use_gpu,
                layout=False, table=True, ocr=True, recovery=False,
            )
        return self._engine

    def handle(self, region: Region, page: PreprocessedPage) -> Block:
        self.last_warning = None
        self.last_engine = self.name
        roi = crop_region(page.image, region)
        html = ""
        t0 = time.perf_counter()
        if roi is not None and roi.size:
            try:
                out = self._table_engine()(roi)
                for r in out:
                    html = _extract_table_html(r.get("res"))
                    if html:
                        break
            except Exception as e:  # noqa: BLE001
                self.last_warning = f"table parse failed: {type(e).__name__}: {e}"
        else:
            self.last_warning = "empty crop"
        if not html:
            self.last_warning = self.last_warning or "no table html recovered"
        self.last_latency_s = time.perf_counter() - t0
        return Block(
            type="table",
            html=html or None,
            bbox=BBox(quad=list(region.bbox.as_xyxy()), page=page.index),
            confidence=region.score,
            reading_order=region.region_id,
        )
