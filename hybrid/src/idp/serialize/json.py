"""Serialize DocumentResult/PageResult → JSON (phụ phẩm của Block[] có bbox).

OmniDocBench chỉ cần `.md`; JSON phục vụ trace/debug/grounding (DOCX để sau).
"""

from __future__ import annotations

import json as _json

from idp.schemas import DocumentResult, PageResult


def page_to_dict(page: PageResult) -> dict:
    return page.model_dump(mode="json")


def document_to_json(doc: DocumentResult, indent: int = 2) -> str:
    return _json.dumps(doc.model_dump(mode="json"), ensure_ascii=False, indent=indent)
