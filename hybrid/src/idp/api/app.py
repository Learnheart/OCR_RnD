"""FastAPI service (M4) — POST /parse: upload file → DocumentResult JSON + Markdown.

    uv run uvicorn idp.api.app:app --reload
    curl -F "file=@page.png" http://localhost:8000/parse
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel

from idp.pipeline import Pipeline
from idp.schemas import DocumentResult
from idp.serialize.markdown import document_to_md

app = FastAPI(title="Hybrid IDP", version="0.1.0")

# 1 pipeline dùng chung (Tier B engine khởi tạo lười khi gặp ảnh đầu tiên)
_pipeline = Pipeline()


class ParseResponse(BaseModel):
    result: DocumentResult
    markdown: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/parse", response_model=ParseResponse)
async def parse(file: UploadFile = File(...)) -> ParseResponse:
    suffix = Path(file.filename or "upload").suffix or ".bin"
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        doc = _pipeline.process_file(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    # giữ document_id theo tên file gốc cho dễ truy vết
    doc.document_id = Path(file.filename or doc.document_id).stem
    return ParseResponse(result=doc, markdown=document_to_md(doc))
