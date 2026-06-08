"""Traditional extraction engine — PaddleOCR PP-OCRv4 + PP-Structure (CPU).

Strategy:
  1. PP-Structure (primary): layout regions → text/title/table/equation/header/…
     Tables come back as HTML (for TEDS); text regions as recognized lines.
  2. PP-OCRv4 full-page det+rec (fallback): used when PP-Structure returns poor
     coverage (e.g. dense code pages where layout detection collapses to 1 region).
     Lines are grouped into paragraphs and ordered.
  3. Reading order recovered by XY-cut over block bounding boxes.

Runs on CPU — paddlepaddle-gpu 3.3.0 silently returns 0 detections on this
Blackwell (sm_120) GPU, so use_gpu is forced False. See docs/.../plan.md.
"""

from __future__ import annotations

import numpy as np

from idp_trad.extract.base import ParseEngine
from idp_trad.ingest.loader import LoadedPage
from idp_trad.layout.reading_order import order_boxes
from idp_trad.schemas import BBox, Block

# PP-Structure region label → our BlockType
_TYPE_MAP = {
    "title": "title",
    "text": "text",
    "reference": "text",
    "list": "list",
    "figure_caption": "text",
    "table_caption": "text",
    "header": "header",
    "footer": "footer",
    "table": "table",
    "equation": "formula",
}
# region types that carry no extractable text → dropped
_DROP_TYPES = {"figure"}

# Below this many recognized chars (across text+title regions) we distrust the
# structure pass and fall back to full-page OCR.
_MIN_STRUCT_CHARS = 20


def _quad_to_xyxy(quad) -> tuple[float, float, float, float]:
    pts = np.asarray(quad, dtype=float).reshape(-1, 2)
    xs, ys = pts[:, 0], pts[:, 1]
    return float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())


def _join_lines(items: list[dict]) -> str:
    """Order recognized sub-lines of a region top→bottom/left→right and join."""
    rows = []
    for it in items:
        box = it.get("text_region") or it.get("bbox")
        txt = (it.get("text") or "").strip()
        if not txt:
            continue
        if box is not None:
            x0, y0, x1, y1 = _quad_to_xyxy(box)
        else:
            x0 = y0 = x1 = y1 = 0.0
        rows.append((y0, x0, txt))
    rows.sort(key=lambda r: (round(r[0] / 8), r[1]))  # bucket y → reading order
    return " ".join(r[2] for r in rows).strip()


def _extract_table_html(res) -> str:
    html = ""
    if isinstance(res, dict):
        html = res.get("html", "") or ""
    if "<table" in html:
        start = html.find("<table")
        end = html.rfind("</table>")
        if end != -1:
            html = html[start : end + len("</table>")]
    return html.strip()


class PaddleStructureEngine(ParseEngine):
    name = "paddleocr-ppstructure@cpu"

    def __init__(self, lang: str = "ch", use_gpu: bool = False) -> None:
        self.lang = lang
        self.use_gpu = use_gpu
        self._structure = None
        self._ocr = None

    # --- lazy model loading (heavy) ---
    def _structure_engine(self):
        if self._structure is None:
            from paddleocr import PPStructure

            self._structure = PPStructure(
                show_log=False, lang=self.lang, use_gpu=self.use_gpu,
                layout=True, table=True, ocr=True, recovery=False,
            )
        return self._structure

    def _ocr_engine(self):
        if self._ocr is None:
            from paddleocr import PaddleOCR

            self._ocr = PaddleOCR(
                show_log=False, lang=self.lang, use_gpu=self.use_gpu,
                use_angle_cls=True,
            )
        return self._ocr

    # --- main entry ---
    def parse(self, page: LoadedPage) -> list[Block]:
        img = page.image
        blocks = self._parse_structure(img)
        struct_chars = sum(
            len(b.text or "") for b in blocks if b.type in ("text", "title")
        )
        if struct_chars < _MIN_STRUCT_CHARS:
            fb = self._parse_fallback(img)
            if sum(len(b.text or "") for b in fb) > struct_chars:
                blocks = fb
        return self._assign_reading_order(blocks)

    # --- PP-Structure primary path ---
    def _parse_structure(self, img: np.ndarray) -> list[Block]:
        regions = self._structure_engine()(img)
        blocks: list[Block] = []
        for r in regions:
            rtype = r.get("type", "text")
            if rtype in _DROP_TYPES:
                continue
            btype = _TYPE_MAP.get(rtype, "text")
            bbox = r.get("bbox")
            box = (
                BBox(quad=[float(v) for v in bbox])
                if bbox is not None and len(bbox) == 4
                else None
            )
            res = r.get("res")
            if btype == "table":
                html = _extract_table_html(res)
                if not html:
                    continue
                blocks.append(Block(type="table", html=html, bbox=box))
                continue
            text = _join_lines(res) if isinstance(res, list) else ""
            if not text:
                continue
            if btype == "formula":
                blocks.append(Block(type="formula", text=text, latex=text, bbox=box))
            else:
                blocks.append(Block(type=btype, text=text, bbox=box))
        return blocks

    # --- raw PP-OCRv4 fallback path ---
    def _parse_fallback(self, img: np.ndarray) -> list[Block]:
        result = self._ocr_engine().ocr(img, cls=True)
        page = result[0] if result else None
        if not page:
            return []
        lines: list[tuple[tuple[float, float, float, float], str]] = []
        for entry in page:
            box, (txt, _conf) = entry[0], entry[1]
            txt = (txt or "").strip()
            if txt:
                lines.append((_quad_to_xyxy(box), txt))
        if not lines:
            return []
        return _group_lines_to_blocks(lines)

    def _assign_reading_order(self, blocks: list[Block]) -> list[Block]:
        boxed = [b for b in blocks if b.bbox is not None]
        unboxed = [b for b in blocks if b.bbox is None]
        if boxed:
            boxes = [b.bbox.as_xyxy() for b in boxed]
            order = order_boxes(boxes)
            for rank, i in enumerate(order):
                boxed[i].reading_order = rank
        for j, b in enumerate(unboxed):
            b.reading_order = len(boxed) + j
        return boxed + unboxed


def _group_lines_to_blocks(
    lines: list[tuple[tuple[float, float, float, float], str]],
) -> list[Block]:
    """Group OCR lines into paragraph blocks: order by XY-cut, then start a new
    block on a large vertical gap. Used only by the fallback path."""
    boxes = [ln[0] for ln in lines]
    order = order_boxes(boxes)
    heights = sorted((b[3] - b[1]) for b in boxes)
    med_h = heights[len(heights) // 2] or 1.0

    blocks: list[Block] = []
    cur_txt: list[str] = []
    cur_box: list[float] | None = None
    prev_y1: float | None = None
    for i in order:
        (x0, y0, x1, y1), txt = lines[i]
        gap = (y0 - prev_y1) if prev_y1 is not None else 0.0
        new_block = prev_y1 is not None and gap > 1.6 * med_h
        if new_block and cur_txt:
            blocks.append(_mk_text_block(cur_txt, cur_box))
            cur_txt, cur_box = [], None
        cur_txt.append(txt)
        cur_box = (
            [x0, y0, x1, y1]
            if cur_box is None
            else [min(cur_box[0], x0), min(cur_box[1], y0),
                  max(cur_box[2], x1), max(cur_box[3], y1)]
        )
        prev_y1 = y1
    if cur_txt:
        blocks.append(_mk_text_block(cur_txt, cur_box))
    return blocks


def _mk_text_block(txts: list[str], box: list[float] | None) -> Block:
    return Block(
        type="text",
        text=" ".join(txts).strip(),
        bbox=BBox(quad=box) if box else None,
    )
