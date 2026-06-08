"""Validation & Grounding Gate — STUB cho slice đầu.

Slice đầu (general doc-parsing) KHÔNG gate theo confidence (chưa calibrate, Qwen3-VL
không có bbox để round-trip). Đây là interface dựng sẵn để Phase 2 banking cắm:
checksum · đối chiếu số học · số-bằng-chữ · round-trip grounding · calibration.

Xem `architecture.md` mục 3.5.
"""

from __future__ import annotations

from idp.schemas import DocumentResult


def validate(doc: DocumentResult) -> DocumentResult:
    """No-op slice đầu: trả nguyên doc. Phase 2 sẽ thêm các lớp kiểm tra + cờ lỗi."""
    return doc
