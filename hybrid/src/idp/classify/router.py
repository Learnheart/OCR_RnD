"""Routing layer (tối thiểu cho slice đầu).

PDF có text-layer thật (digital-born) → Tier 0 (free win, zero hallucination).
Còn lại (ảnh/scan, PDF chỉ chứa ảnh) → Tier B (Qwen3-VL @ LM Studio).

Phase 2+: thêm difficulty score → Tier A (template VN) / Tier C (viết tay/quan hệ).
"""

from __future__ import annotations

from idp.ingest.loader import LoadedPage

# ngưỡng ký tự text-layer để coi là digital-born
DIGITAL_MIN_CHARS = 50


def is_digital_born(page: LoadedPage) -> bool:
    """True nếu trang PDF có text-layer đủ dày (không phải scan-in-PDF)."""
    if page.pdf_page is None:
        return False
    try:
        text = page.pdf_page.get_text("text")
    except Exception:
        return False
    return len(text.strip()) >= DIGITAL_MIN_CHARS


def route(page: LoadedPage) -> str:
    """Trả tier: '0' (direct parse) hoặc 'B' (VLM)."""
    return "0" if is_digital_born(page) else "B"
