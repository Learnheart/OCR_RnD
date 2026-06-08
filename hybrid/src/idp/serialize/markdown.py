"""Serialize Block[] → Markdown (theo reading order) cho OmniDocBench end2end.

Quy ước OmniDocBench: text thường, tiêu đề bằng heading, bảng dạng HTML
(`<table>…`) để chấm TEDS, công thức LaTeX `$$…$$`.

Tier B VLM trả nguyên 1 block markdown đầy đủ → serializer in verbatim.
"""

from __future__ import annotations

from idp.schemas import Block, DocumentResult, PageResult


def block_to_md(b: Block) -> str:
    t = b.type
    if t == "table":
        # ưu tiên HTML (TEDS); fallback text/markdown nếu engine không trả html
        return (b.html or b.text or "").strip()
    if t == "formula":
        latex = (b.latex or b.text or "").strip()
        if not latex:
            return ""
        # tránh bọc 2 lần nếu engine đã có $
        if latex.startswith("$"):
            return latex
        return f"$$\n{latex}\n$$"
    if t == "title":
        return f"# {(b.text or '').strip()}"
    # text / list / figure / header / footer → text thuần (đã chứa marker nếu có)
    return (b.text or "").strip()


def page_to_md(page: PageResult) -> str:
    blocks = sorted(page.blocks, key=lambda b: b.reading_order)
    parts = [s for b in blocks if (s := block_to_md(b))]
    return "\n\n".join(parts).strip() + "\n"


def document_to_md(doc: DocumentResult) -> str:
    """Ghép Markdown mọi trang. OmniDocBench eval theo từng ảnh-1-trang nên
    thường chỉ có 1 page; PDF nhiều trang ghép bằng dải phân cách trang."""
    pages_md = [page_to_md(p) for p in doc.pages]
    return "\n\n".join(pages_md).strip() + "\n"
