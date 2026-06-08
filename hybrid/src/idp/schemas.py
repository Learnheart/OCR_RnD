"""★ CONTRACT (đóng băng trước) — Pydantic v2 models cho hybrid IDP pipeline.

Mọi tier/engine cắm vào các model này. `DocumentResult` là tiền thân của
Provenance Envelope (architecture mục 5); slice đầu chỉ dùng tới mức `blocks`
để serialize Markdown cho OmniDocBench.

Lưu ý grounding: Qwen3-VL (Tier B) KHÔNG có bbox/quad native → `Block.bbox`
nullable. Tier 0 (PyMuPDF) luôn gắn bbox thật.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BlockType = Literal[
    "text", "title", "table", "formula", "figure", "header", "footer", "list"
]
Tier = Literal["0", "A", "B", "C"]


class BBox(BaseModel):
    """Tọa độ nguồn (provenance). `quad` = 4 số axis-aligned [x0,y0,x1,y1]
    hoặc 8 số (4 điểm, PaddleOCR-VL). Tọa độ pixel theo ảnh/trang gốc."""

    quad: list[float]
    page: int = 0

    def as_xyxy(self) -> tuple[float, float, float, float]:
        """Trả [x0,y0,x1,y1] — bao đóng (bounding box) dù quad là 4 hay 8 số."""
        q = self.quad
        if len(q) == 4:
            return (q[0], q[1], q[2], q[3])
        xs = q[0::2]
        ys = q[1::2]
        return (min(xs), min(ys), max(xs), max(ys))


class Block(BaseModel):
    """Đơn vị nội dung có provenance. Một trong text/html/latex được set tùy type."""

    type: BlockType = "text"
    text: str | None = None
    html: str | None = None  # cho table (TEDS)
    latex: str | None = None  # cho formula (CDM/Edit_dist)
    bbox: BBox | None = None  # None khi engine không có grounding (Tier B VLM)
    confidence: float = 1.0
    reading_order: int = 0


class PageResult(BaseModel):
    page: int = 0
    blocks: list[Block] = Field(default_factory=list)
    image_uri: str = ""  # ảnh gốc (provenance + VLM dùng lại)


class DocumentResult(BaseModel):
    """Kết quả 1 tài liệu. Mở rộng dần thành Provenance Envelope ở Phase 2."""

    document_id: str
    doc_type: str | None = None
    doc_type_confidence: float | None = None
    tier: Tier = "B"
    engines_used: list[str] = Field(default_factory=list)
    pages: list[PageResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
