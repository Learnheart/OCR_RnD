"""Ingest & chuẩn hóa input đa định dạng → danh sách trang (LoadedPage).

- Ảnh (PNG/JPG/…): 1 LoadedPage, dùng bytes gốc cho VLM, không có text-layer.
- PDF: mỗi trang → render PNG (cho VLM) + giữ `pdf_page` (PyMuPDF Page) cho Tier 0.

Slice đầu giữ preprocess ở mức nhẹ (chỉ render). Deskew/orient/dewarp để M3.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from PIL import Image

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
PDF_EXTS = {".pdf"}

# DPI render PDF→ảnh cho VLM. 150 đủ nét cho doc-parsing, giữ token ảnh vừa phải.
RENDER_DPI = 150


@dataclass
class LoadedPage:
    """1 trang đã nạp. `pdf_page` chỉ có khi nguồn là PDF (cho Tier 0)."""

    index: int  # 0-based
    image_bytes: bytes  # PNG bytes — VLM dùng / provenance
    width: int
    height: int
    source_path: str
    pdf_page: Any | None = None  # fitz.Page hoặc None (ảnh thuần)
    meta: dict = field(default_factory=dict)

    @property
    def is_digital_candidate(self) -> bool:
        """Chỉ PDF mới có khả năng digital-born (có text-layer)."""
        return self.pdf_page is not None


@dataclass
class LoadedDocument:
    document_id: str
    source_path: str
    pages: list[LoadedPage]
    _fitz_doc: Any | None = None  # giữ ref để không bị GC khi còn dùng pdf_page

    def close(self) -> None:
        if self._fitz_doc is not None:
            self._fitz_doc.close()
            self._fitz_doc = None

    def __enter__(self) -> "LoadedDocument":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _image_to_png_bytes(img: Image.Image) -> bytes:
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def load(path: str | Path) -> LoadedDocument:
    """Nạp 1 file (ảnh hoặc PDF) → LoadedDocument.

    Dùng như context manager để giải phóng fitz doc:
        with load(p) as doc: ...
    """
    p = Path(path)
    ext = p.suffix.lower()
    document_id = p.stem

    if ext in IMAGE_EXTS:
        with Image.open(p) as img:
            img.load()
            png = _image_to_png_bytes(img)
            w, h = img.size
        page = LoadedPage(
            index=0, image_bytes=png, width=w, height=h, source_path=str(p)
        )
        return LoadedDocument(document_id=document_id, source_path=str(p), pages=[page])

    if ext in PDF_EXTS:
        doc = fitz.open(p)
        zoom = RENDER_DPI / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pages: list[LoadedPage] = []
        for i, pg in enumerate(doc):
            pix = pg.get_pixmap(matrix=mat, alpha=False)
            png = pix.tobytes("png")
            pages.append(
                LoadedPage(
                    index=i,
                    image_bytes=png,
                    width=pix.width,
                    height=pix.height,
                    source_path=str(p),
                    pdf_page=pg,
                )
            )
        return LoadedDocument(
            document_id=document_id, source_path=str(p), pages=pages, _fitz_doc=doc
        )

    raise ValueError(f"Định dạng không hỗ trợ: {ext} ({p})")
