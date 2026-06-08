"""Tier 0 — Direct parse cho PDF digital-born (KHÔNG OCR).

Trích thẳng text-layer + bbox (PyMuPDF) → provenance miễn phí, zero hallucination.
Bảng dùng pdfplumber (lattice/stream) → HTML cho TEDS. Text nằm trong vùng bảng
bị loại để tránh trùng lặp.

Lưu ý: OmniDocBench v1.5 toàn ảnh scan nên Tier 0 hầu như không chạy trên benchmark
— nó phục vụ luồng PDF số thực tế (sao kê e-banking, e-contract…) và DoD M1.
"""

from __future__ import annotations

import html as _html

import pdfplumber

from idp.extract.base import ParseEngine
from idp.ingest.loader import LoadedPage
from idp.schemas import BBox, Block

# bỏ qua text-block rỗng/nhiễu ngắn hơn ngưỡng này (ký tự)
_MIN_CHARS = 1


def _rows_to_html(rows: list[list[str | None]]) -> str:
    out = ["<table>"]
    for row in rows:
        out.append("<tr>")
        for cell in row:
            txt = _html.escape((cell or "").strip())
            out.append(f"<td>{txt}</td>")
        out.append("</tr>")
    out.append("</table>")
    return "".join(out)


def _inside(inner: tuple[float, float, float, float],
            outer: tuple[float, float, float, float]) -> bool:
    ix0, iy0, ix1, iy1 = inner
    ox0, oy0, ox1, oy1 = outer
    cx = (ix0 + ix1) / 2
    cy = (iy0 + iy1) / 2
    return ox0 <= cx <= ox1 and oy0 <= cy <= oy1


class Tier0DirectEngine(ParseEngine):
    name = "tier0-pymupdf"

    def parse(self, page: LoadedPage) -> list[Block]:
        if page.pdf_page is None:
            raise ValueError("Tier0 chỉ chạy trên trang PDF (cần text-layer).")

        fitz_page = page.pdf_page
        page_no = page.index

        # --- bảng (pdfplumber) ---
        table_blocks: list[Block] = []
        table_bboxes: list[tuple[float, float, float, float]] = []
        try:
            with pdfplumber.open(page.source_path) as pdf:
                pp = pdf.pages[page_no]
                for tbl in pp.find_tables():
                    rows = tbl.extract()
                    if not rows:
                        continue
                    bbox = tuple(float(v) for v in tbl.bbox)  # (x0,top,x1,bottom)
                    table_bboxes.append(bbox)
                    table_blocks.append(
                        Block(
                            type="table",
                            html=_rows_to_html(rows),
                            bbox=BBox(quad=list(bbox), page=page_no),
                            confidence=1.0,
                        )
                    )
        except Exception:  # pdfplumber lỗi không được chặn cả trang
            pass

        # --- text blocks (PyMuPDF) ---
        text_blocks: list[Block] = []
        data = fitz_page.get_text("dict")
        for blk in data.get("blocks", []):
            if blk.get("type", 0) != 0:  # bỏ image block
                continue
            bx = tuple(float(v) for v in blk["bbox"])
            if any(_inside(bx, tb) for tb in table_bboxes):
                continue  # text nằm trong bảng → đã có trong table HTML
            lines: list[str] = []
            for ln in blk.get("lines", []):
                spans = ln.get("spans", [])
                line_txt = "".join(s.get("text", "") for s in spans)
                if line_txt.strip():
                    lines.append(line_txt)
            text = "\n".join(lines).strip()
            if len(text) < _MIN_CHARS:
                continue
            text_blocks.append(
                Block(
                    type="text",
                    text=text,
                    bbox=BBox(quad=list(bx), page=page_no),
                    confidence=1.0,
                )
            )

        # --- reading order: trên→dưới, trái→phải ---
        blocks = text_blocks + table_blocks
        blocks.sort(key=lambda b: (b.bbox.as_xyxy()[1], b.bbox.as_xyxy()[0]))
        for i, b in enumerate(blocks):
            b.reading_order = i
        return blocks
