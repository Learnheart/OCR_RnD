"""★ CONTRACT (copied from hybrid, kept byte-compatible) — output models.

The traditional engine populates the SAME models as the hybrid pipeline so that
`document_to_md` produces an identical Markdown shape and the two solutions are
scored apples-to-apples on OmniDocBench.

Unlike the VLM tier, the traditional engine DOES have grounding: every Block
carries a real `bbox` (pixel coords on the page), which also drives reading order.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BlockType = Literal[
    "text", "title", "table", "formula", "figure", "header", "footer", "list"
]
Tier = Literal["0", "A", "B", "C"]


class BBox(BaseModel):
    """Source coords (provenance). `quad` = 4 numbers axis-aligned [x0,y0,x1,y1]
    or 8 numbers (4 points). Pixel coords on the original page image."""

    quad: list[float]
    page: int = 0

    def as_xyxy(self) -> tuple[float, float, float, float]:
        """Return [x0,y0,x1,y1] bounding box whether quad has 4 or 8 numbers."""
        q = self.quad
        if len(q) == 4:
            return (q[0], q[1], q[2], q[3])
        xs = q[0::2]
        ys = q[1::2]
        return (min(xs), min(ys), max(xs), max(ys))


class Block(BaseModel):
    """A content unit with provenance. One of text/html/latex set per type."""

    type: BlockType = "text"
    text: str | None = None
    html: str | None = None  # for table (TEDS)
    latex: str | None = None  # for formula (CDM/Edit_dist)
    bbox: BBox | None = None
    confidence: float = 1.0
    reading_order: int = 0


class PageResult(BaseModel):
    page: int = 0
    blocks: list[Block] = Field(default_factory=list)
    image_uri: str = ""


class DocumentResult(BaseModel):
    """Result of one document. Mirrors the hybrid contract."""

    document_id: str
    doc_type: str | None = None
    doc_type_confidence: float | None = None
    tier: Tier = "A"  # traditional pipeline reports tier "A"
    engines_used: list[str] = Field(default_factory=list)
    pages: list[PageResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
