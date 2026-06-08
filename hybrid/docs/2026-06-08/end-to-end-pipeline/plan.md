---
author: lytinh358@gmail.com
date: 2026-06-08
status: in-progress
agents: hybrid
summary: Triển khai end-to-end slice đầu (M0→M2) — Tier 0 (PyMuPDF) + Tier B (Qwen3-VL-8B @ LM Studio), đo trên OmniDocBench v1.5.
---

# Plan — End-to-end Hybrid IDP slice 1 (M0→M2)

## Problem statement
Hiện `hybrid/` mới có thiết kế (`architecture.md`, `implementation-plan.md`, `AGENT.md`), **chưa có code**, 0/1651 prediction. Cần dựng lõi chạy được: ảnh/PDF → Markdown, rồi đo baseline trên OmniDocBench v1.5 qua harness chung `../eval/`.

## Requirements
- Tuân thủ contract đóng băng: `schemas.py` (Pydantic v2) + `extract/base.py` (`ParseEngine` ABC) — mọi engine cắm vào đây.
- **Tier 0**: PDF digital-born → trích text-layer + bbox (PyMuPDF), bảng (pdfplumber). Zero hallucination.
- **Tier B**: ảnh/scan → Qwen3-VL-8B qua LM Studio (OpenAI-compatible `http://localhost:1234/v1`, ảnh base64).
- **Router** tối thiểu: digital-born → Tier 0; ngược lại → Tier B.
- **Serializer**: `Block[]` → Markdown (reading order) đúng format OmniDocBench (text + table HTML/MD + formula `$...$`).
- Output contract eval: 1 file `.md`/ảnh vào `../eval/predictions/end2end/`, cùng tên đổi đuôi.
- **Rule 4**: smoke test 1–2 ảnh trước, rồi full 1651.

## Decisions made
- **Runtime**: Python 3.13 + `uv` (env riêng, tách env scorer `omnidocbench` py3.10).
- **HTTP client**: `httpx` (sync) gọi LM Studio OpenAI-compatible API.
- **Tier 0 tables**: dùng `pdfplumber` (không cần Camelot/Ghostscript ở slice đầu) → giảm phụ thuộc hệ thống.
- **bbox optional**: Qwen3-VL không có grounding native → `Block.bbox` nullable; Tier B trả full-page Markdown trong 1 block, Tier 0 trả block có bbox thật.
- **Ingest**: ảnh PNG → 1 page (bytes gốc cho VLM); PDF → render mỗi trang ra PNG cho VLM + giữ page object cho Tier 0.

## Implementation approach (milestones)
- **M0** — scaffold uv + `schemas.py` + `extract/base.py` + `tests/test_schemas.py` xanh.
- **M1** — `tier0_direct.py` + `serialize/markdown.py`; test trên 1 PDF số.
- **M2** — `tier_b_lmstudio_vlm.py` + `router.py` + `ingest/loader.py` + `pipeline.py` + `scripts/{parse_one,run_omnidocbench}.py`. Smoke 1–2 ảnh → full 1651 → `run_eval.ps1` → ghi số vào `../eval/results/` + `AGENT.md`.

## Environment verified (2026-06-08)
- LM Studio server ON :1234, `qwen/qwen3-vl-8b` loaded, context **32768**, GPU max (RTX 5060 Ti 16GB).
- `uv 0.9.24`; OmniDocBench: 1651 ảnh đủ, 0 prediction.
- Scorer env `omnidocbench` py3.10 sẵn; `run_eval.ps1` tự bật PYTHONUTF8.
