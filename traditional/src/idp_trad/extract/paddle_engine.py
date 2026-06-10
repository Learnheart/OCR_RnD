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

import re

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
    """Extract a single well-formed ``<table>…</table>`` from a PP-Structure
    table region. Strips the surrounding ``<html><body>`` wrapper and any stray
    attributes on the table/row/cell tags (style/class/id/border/… add TEDS noise
    — TEDS scores *structure*, so the cell skeleton is preserved while cosmetic
    attributes that don't carry structure are dropped). Conservative: never
    removes ``<tr>/<td>/<th>`` cells or their ``rowspan``/``colspan``."""
    html = ""
    if isinstance(res, dict):
        html = res.get("html", "") or ""
    if not isinstance(html, str):
        return ""
    if "<table" in html:
        start = html.find("<table")
        end = html.rfind("</table>")
        if end != -1:
            html = html[start : end + len("</table>")]
    html = html.strip()
    if not html:
        return ""
    return _clean_table_html(html)


# Structural attributes worth keeping on cells (drive TEDS structure scoring).
_KEEP_CELL_ATTRS = {"rowspan", "colspan"}


def _clean_table_html(html: str) -> str:
    """Drop cosmetic attributes from table tags, keeping rowspan/colspan."""

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
        # table / tr / thead / tbody / tfoot → strip all attributes
        return f"<{tag}>"

    # Only rewrite the opening tags we care about; leave content untouched.
    return re.sub(
        r"<(table|thead|tbody|tfoot|tr|td|th)\b([^>]*)>",
        _scrub,
        html,
        flags=re.IGNORECASE,
    )


# LaTeX delimiters a recognizer may wrap its output in; the serializer owns the
# final delimiters so we strip these to avoid double-wrapping.
def _clean_latex(latex: str) -> str:
    """Normalise recognizer LaTeX: strip a single surrounding ``$…$``/``$$…$$``
    or ``\\[ … \\]`` / ``\\( … \\)`` pair and trim whitespace. Leaves inner
    math untouched so the serializer controls the delimiters."""
    if not latex:
        return ""
    s = latex.strip()
    # Strip display \[ ... \] and inline \( ... \)
    for open_d, close_d in (("\\[", "\\]"), ("\\(", "\\)")):
        if s.startswith(open_d) and s.endswith(close_d) and len(s) > len(open_d) + len(close_d):
            s = s[len(open_d) : -len(close_d)].strip()
    # Strip $$ ... $$ then $ ... $ (single surrounding pair only)
    if s.startswith("$$") and s.endswith("$$") and len(s) > 4:
        s = s[2:-2].strip()
    elif s.startswith("$") and s.endswith("$") and len(s) > 2 and not s[1:-1].strip().startswith("$"):
        s = s[1:-1].strip()
    return s


def _crop_region(img: np.ndarray, region: dict) -> np.ndarray | None:
    """Crop a layout region's bbox from the page image. Prefers the ROI the
    structure engine already sliced (``region['img']``); else slices from bbox.
    Returns None when no valid crop is available."""
    roi = region.get("img")
    if isinstance(roi, np.ndarray) and roi.size:
        return roi
    bbox = region.get("bbox")
    if img is None or not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return None
    h, w = img.shape[:2]
    x1, y1, x2, y2 = (int(round(v)) for v in bbox)
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return None
    return img[y1:y2, x1:x2]


def _region_summary(b: Block) -> dict:
    """JSON-serialisable view of a final block, for the trace's structure dump."""
    return {
        "reading_order": b.reading_order,
        "type": b.type,
        "bbox": list(b.bbox.as_xyxy()) if b.bbox is not None else None,
        "text_len": len(b.text or ""),
        "html_len": len(b.html or ""),
        "latex_len": len(b.latex or ""),
        "text_preview": (b.text or "")[:80].replace("\n", " "),
    }


class PaddleStructureEngine(ParseEngine):
    name = "paddleocr-ppstructure@cpu"

    def __init__(
        self,
        lang: str = "ch",
        use_gpu: bool = False,
        enable_formula: bool = False,
    ) -> None:
        self.lang = lang
        self.use_gpu = use_gpu
        # LaTeX formula recognition (PaddleOCR's LaTeXOCR head). The model weights
        # ship/are cached offline, but on this Blackwell (sm_120) + paddle 3.x box
        # the LaTeXOCR transformer-decoder inference *segfaults* the process
        # (uncatchable), which would kill parse() on any page with an equation.
        # So it is OFF by default → we degrade to plain OCR text for formulas.
        # Flip to True only on a machine where LaTeXOCR inference is stable; the
        # branch below already crops the equation ROI and runs the recognizer.
        self.enable_formula = enable_formula
        self._structure = None
        self._ocr = None
        self._formula = None
        # name of the formula engine actually used this parse() ("none" | "latexocr")
        self._formula_engine_name = "none"
        # Read-only trace data, refreshed every parse(). Consumed by the Tracer so
        # the extraction path (structure vs the otherwise-silent full-page OCR
        # fallback) and per-block layout are observable. Additive — do not remove.
        self.last_meta: dict = {}

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

    def _formula_engine(self):
        """Lazily build PaddleOCR's offline LaTeXOCR recognizer (TextRecognizer
        with rec_algorithm='LaTeXOCR' over the cached rec_latex_ocr_infer model).
        Returns a callable ``rec([roi]) -> ([(latex, conf)], time)`` or ``None``
        if it cannot be built offline. Mirrors the lazy pattern of the other
        engines. Never raises — a missing model / dependency degrades to None."""
        if self._formula is None:
            try:
                import os

                import paddleocr as _pp
                from paddleocr.tools.infer.predict_rec import TextRecognizer
                from paddleocr.tools.infer.utility import init_args

                base = os.path.expanduser(
                    os.path.join("~", ".paddleocr", "whl", "formula",
                                 "rec_latex_ocr_infer")
                )
                if not os.path.isdir(base):
                    return None  # weights not present offline → degrade
                dict_path = os.path.join(
                    os.path.dirname(_pp.__file__),
                    "ppocr", "utils", "dict", "latex_ocr_tokenizer.json",
                )
                args = init_args().parse_args([])
                args.rec_algorithm = "LaTeXOCR"
                args.rec_model_dir = base
                args.rec_char_dict_path = dict_path
                args.rec_batch_num = 1
                args.use_gpu = self.use_gpu
                args.use_onnx = False
                self._formula = TextRecognizer(args)
            except Exception:
                self._formula = None
        return self._formula

    def _recognize_formula(self, roi: np.ndarray) -> str | None:
        """Run the LaTeXOCR recognizer on a cropped equation ROI; return cleaned
        LaTeX or None. Guarded — any (catchable) failure degrades to None."""
        rec = self._formula_engine()
        if rec is None or roi is None or roi.size == 0:
            return None
        try:
            out, _ = rec([roi])
        except Exception:
            return None
        if not out:
            return None
        first = out[0]
        latex = first[0] if isinstance(first, (list, tuple)) else first
        if not isinstance(latex, str):
            return None
        cleaned = _clean_latex(latex)
        if cleaned:
            self._formula_engine_name = "latexocr"
        return cleaned or None

    # --- main entry ---
    def parse(self, page: LoadedPage) -> list[Block]:
        import time

        img = page.image
        meta: dict = {
            "path_used": "structure",
            "fallback_used": False,
            "fallback_reason": None,
        }
        t0 = time.time()
        self._formula_engine_name = "none"
        blocks = self._parse_structure(img)
        struct_chars = sum(
            len(b.text or "") for b in blocks if b.type in ("text", "title")
        )
        meta["struct_chars"] = struct_chars
        meta["n_regions"] = len(blocks)
        if struct_chars < _MIN_STRUCT_CHARS:
            fb = self._parse_fallback(img)
            fb_chars = sum(len(b.text or "") for b in fb)
            if fb_chars > struct_chars:
                blocks = fb
                meta["path_used"] = "fallback"
                meta["fallback_used"] = True
                meta["fallback_reason"] = (
                    f"structure chars {struct_chars} < {_MIN_STRUCT_CHARS}; "
                    f"full-page OCR recovered {fb_chars}"
                )
            else:
                meta["fallback_reason"] = (
                    f"structure chars {struct_chars} < {_MIN_STRUCT_CHARS} but "
                    f"fallback ({fb_chars}) not better — kept structure"
                )
        meta["extract_s"] = time.time() - t0
        t1 = time.time()
        ordered = self._assign_reading_order(blocks)
        meta["reading_order_s"] = time.time() - t1
        meta["n_blocks"] = len(ordered)
        meta["formula_engine"] = self._formula_engine_name
        meta["regions"] = [_region_summary(b) for b in ordered]
        self.last_meta = meta
        return ordered

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
            if btype == "formula":
                self._append_formula(blocks, r, img, box)
                continue
            text = _join_lines(res) if isinstance(res, list) else ""
            if not text:
                continue
            blocks.append(Block(type=btype, text=text, bbox=box))
        return blocks

    def _append_formula(
        self, blocks: list[Block], region: dict, img: np.ndarray, box
    ) -> None:
        """Emit a formula Block. Prefer real LaTeX from (a) the recognizer run on
        the cropped equation ROI when ``enable_formula`` is on, or (b) latex
        already present in the region ``res`` (PP-Structure ``{"latex": ...}``).
        Falls back to the region's plain OCR text (text==latex) so the formula is
        never dropped. ``Block.text`` always holds the OCR text; ``Block.latex``
        holds the best LaTeX available."""
        res = region.get("res")
        ocr_text = _join_lines(res) if isinstance(res, list) else ""

        # (a) latex already returned by PP-Structure for an equation region
        embedded = ""
        if isinstance(res, dict):
            cand = res.get("latex")
            if isinstance(cand, (list, tuple)) and cand:
                cand = cand[0]
            if isinstance(cand, str):
                embedded = _clean_latex(cand)

        latex = ""
        if self.enable_formula:
            roi = _crop_region(img, region)
            recognized = self._recognize_formula(roi)
            if recognized:
                latex = recognized
        if not latex and embedded:
            latex = embedded
            self._formula_engine_name = "embedded"

        text = ocr_text or latex
        latex = latex or text  # never empty when we have any content
        if not text and not latex:
            return
        blocks.append(Block(type="formula", text=text or None, latex=latex or None, bbox=box))

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
