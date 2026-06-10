"""Serialize Block[] → Markdown (in reading order) for OmniDocBench end2end.

OmniDocBench convention: plain text, titles as headings, tables as HTML
(`<table>…`) for TEDS, formulas as LaTeX `$$…$$`. Identical rules to the hybrid
serializer so output is comparable.
"""

from __future__ import annotations

import re

from idp_trad.schemas import Block, DocumentResult, PageResult


def _format_formula(latex: str) -> str:
    """Wrap LaTeX in display math delimiters exactly once. Already-delimited
    input (``$…$`` / ``$$…$$`` / ``\\[…\\]`` / ``\\(…\\)``) is passed through
    as-is so we never double-wrap. OmniDocBench treats block formulas as display
    math, so undelimited LaTeX is wrapped in ``$$…$$``."""
    s = latex.strip()
    if not s:
        return ""
    if s.startswith("$") or s.startswith("\\[") or s.startswith("\\("):
        return s
    return f"$$\n{s}\n$$"


def _format_list(text: str) -> str:
    """Render a list region as Markdown bullet lines. Splits on existing
    newlines first; if it is a single line, splits on common in-line bullet
    markers (•, ·, ▪, –/— used as bullets). Conservative: if no reasonable
    split is found, returns the original text unchanged (one bullet) so the
    text-edit score is not harmed."""
    s = (text or "").strip()
    if not s:
        return ""
    parts = [p.strip() for p in s.splitlines() if p.strip()]
    if len(parts) <= 1:
        # try splitting a single line on inline bullet glyphs
        split = re.split(r"\s*[•·▪◦‣]\s*", s)
        parts = [p.strip() for p in split if p.strip()]
    if len(parts) <= 1:
        return s  # no confident split → keep plain (don't risk edit score)
    # strip a leading bullet glyph the recognizer may have kept on each item
    cleaned = [re.sub(r"^[•·▪◦‣\-\*]\s*", "", p) for p in parts]
    return "\n".join(f"- {p}" for p in cleaned if p)


def block_to_md(b: Block) -> str:
    t = b.type
    if t == "table":
        # prefer HTML (TEDS); fall back to text if engine produced no html
        return (b.html or b.text or "").strip()
    if t == "formula":
        return _format_formula((b.latex or b.text or "").strip())
    if t == "title":
        return f"# {(b.text or '').strip()}"
    if t == "list":
        return _format_list(b.text or "")
    # text / figure / header / footer → plain text
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
