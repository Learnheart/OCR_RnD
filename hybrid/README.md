# Hybrid Tiered IDP Pipeline

Pipeline IDP **hybrid, phân tầng** — engine rẻ & deterministic trước, "leo thang" lên VLM cho phần khó. Slice đầu: **Tier 0** (PyMuPDF, PDF digital-born) + **Tier B** (Qwen3-VL-8B qua LM Studio), đo trên **OmniDocBench v1.5**.

> Source of truth method/techstack: [`AGENT.md`](AGENT.md). Thiết kế: [`architecture.md`](architecture.md). Lộ trình: [`implementation-plan.md`](implementation-plan.md).

## Setup

```powershell
cd C:\Projects\ComputerVision\RnD_pipeline\hybrid
uv sync --extra dev
```

Bật LM Studio (cho Tier B):

```powershell
& "$env:USERPROFILE\.lmstudio\bin\lms.exe" server start
& "$env:USERPROFILE\.lmstudio\bin\lms.exe" load qwen/qwen3-vl-8b --context-length 32768 --gpu max -y
```

## Chạy

```powershell
# Parse 1 file (debug) → in DocumentResult JSON + Markdown
uv run python scripts/parse_one.py <path-to-pdf-or-image>

# Sinh predictions OmniDocBench (Rule 4: nhỏ trước)
uv run python scripts/run_omnidocbench.py --limit 2      # smoke test
uv run python scripts/run_omnidocbench.py                # full 1651

# Chấm điểm (env scorer riêng)
cd ..\eval; .\run_eval.ps1
```

## Test

```powershell
uv run pytest
```

## Kiến trúc code

```
src/idp/
├── schemas.py              # ★ contract (Pydantic v2): BBox, Block, PageResult, DocumentResult
├── pipeline.py             # orchestrator: ingest → route → extract → DocumentResult
├── ingest/loader.py        # PDF/ảnh → LoadedPage (render + text-layer)
├── classify/router.py      # digital-born? → Tier 0 / Tier B
├── extract/
│   ├── base.py             # ★ ParseEngine ABC
│   ├── tier0_direct.py     # PyMuPDF text+bbox + pdfplumber tables
│   └── tier_b_lmstudio_vlm.py  # Qwen3-VL-8B @ LM Studio (OpenAI-compatible)
├── serialize/markdown.py   # Block[] → Markdown (reading order) cho OmniDocBench
└── api/app.py              # FastAPI POST /parse
```
