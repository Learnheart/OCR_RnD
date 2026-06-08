"""Ingest input → list of pages (LoadedPage).

Traditional pipeline works on raster images: PaddleOCR consumes a numpy BGR
array. So unlike the hybrid loader (which keeps PNG bytes for a VLM), this loader
exposes each page as an `np.ndarray` (H, W, 3) BGR.

- Image (PNG/JPG/…): one LoadedPage.
- PDF: rendered to images via PyMuPDF *if installed* (lazy import). The benchmark
  is all images, so PDF is a graceful extension, not on the hot path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
PDF_EXTS = {".pdf"}

# DPI to render PDF→image (only used when pymupdf is available).
RENDER_DPI = 150


@dataclass
class LoadedPage:
    """One loaded page as a BGR numpy array (PaddleOCR's native input)."""

    index: int  # 0-based
    image: np.ndarray  # BGR uint8 (H, W, 3)
    source_path: str
    meta: dict = field(default_factory=dict)

    @property
    def width(self) -> int:
        return int(self.image.shape[1])

    @property
    def height(self) -> int:
        return int(self.image.shape[0])


@dataclass
class LoadedDocument:
    document_id: str
    source_path: str
    pages: list[LoadedPage]

    def __enter__(self) -> "LoadedDocument":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _imread_unicode(path: Path) -> np.ndarray:
    """cv2.imread chokes on non-ASCII Windows paths (and the benchmark has CJK
    filenames). Read bytes ourselves and decode."""
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Cannot decode image: {path}")
    return img


def _load_pdf(path: Path) -> list[LoadedPage]:
    try:
        import fitz  # PyMuPDF — optional
    except ImportError as e:  # pragma: no cover - env without pymupdf
        raise RuntimeError(
            "PDF input needs pymupdf (not installed in this env). "
            "Install pymupdf or pass raster images."
        ) from e
    doc = fitz.open(path)
    zoom = RENDER_DPI / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pages: list[LoadedPage] = []
    try:
        for i, pg in enumerate(doc):
            pix = pg.get_pixmap(matrix=mat, alpha=False)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            pages.append(
                LoadedPage(index=i, image=bgr.copy(), source_path=str(path))
            )
    finally:
        doc.close()
    return pages


def load(path: str | Path) -> LoadedDocument:
    """Load one file (image or PDF) → LoadedDocument."""
    p = Path(path)
    ext = p.suffix.lower()
    document_id = p.stem

    if ext in IMAGE_EXTS:
        img = _imread_unicode(p)
        page = LoadedPage(index=0, image=img, source_path=str(p))
        return LoadedDocument(document_id=document_id, source_path=str(p), pages=[page])

    if ext in PDF_EXTS:
        pages = _load_pdf(p)
        return LoadedDocument(document_id=document_id, source_path=str(p), pages=pages)

    raise ValueError(f"Unsupported format: {ext} ({p})")
