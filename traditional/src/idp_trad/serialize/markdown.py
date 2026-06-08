"""Serialize Block[] → Markdown (in reading order) for OmniDocBench end2end.

OmniDocBench convention: plain text, titles as headings, tables as HTML
(`<table>…`) for TEDS, formulas as LaTeX `$$…$$`. Identical rules to the hybrid
serializer so output is comparable.
"""

from __future__ import annotations

from idp_trad.schemas import Block, DocumentResult, PageResult


def block_to_md(b: Block) -> str:
    t = b.type
    if t == "table":
        # prefer HTML (TEDS); fall back to text if engine produced no html
        return (b.html or b.text or "").strip()
    if t == "formula":
        latex = (b.latex or b.text or "").strip()
        if not latex:
            return ""
        if latex.startswith("$"):
            return latex
        return f"$$\n{latex}\n$$"
    if t == "title":
        return f"# {(b.text or '').strip()}"
    # text / list / figure / header / footer → plain text
    return (b.text or "").strip()


def page_to_md(page: PageResult) -> str:
    blocks = sorted(page.blocks, key=lambda b: b.reading_order)
    parts = [s for b in blocks if (s := block_to_md(b))]
    return "\n\n".join(parts).strip() + "\n"


def document_to_md(doc: DocumentResult) -> str:
    """Join Markdown of all pages. OmniDocBench is one-image-one-page so there is
    normally a single page; multi-page PDFs are concatenated."""
    pages_md = [page_to_md(p) for p in doc.pages]
    return "\n\n".join(pages_md).strip() + "\n"
