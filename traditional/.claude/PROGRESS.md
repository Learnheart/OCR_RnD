# PROGRESS — traditional/ (classic OCR pipeline)

_Last updated: 2026-06-10_

## 2026-06-10 — Tracing + output-quality upgrade landed (v0.2.0)

Per-step tracing + quality upgrade shipped (MINOR, **no output-contract break**).

- **Tracing:** new `src/idp_trad/trace/` module; opt-in `Tracer` threaded through
  `Pipeline`; `scripts/parse_one.py --trace [DIR]` (default `results/traces`). Per page:
  `original.png`, `preprocessed.png`, `structure_raw.json` (+ explicit fallback
  decision), `layout_overlay.png`, `crops/`; per doc: `trace.json` + `report.md`. Off
  by default → zero overhead, eval output unchanged. See `docs/sequences/trace-flow.md`.
- **Quality:** low-contrast enhance (`preprocess/enhance.py`, `do_enhance` ON,
  conservatively AND-gated); serializer formula `$$…$$` + `list` bullets; table HTML
  cleanup (rowspan/colspan preserved).
- **Blocker:** LaTeXOCR formula recognizer wired behind `enable_formula` but **DEFAULT
  OFF** — segfaults (`0xC0000005`) on Blackwell sm_120 + paddle 3.x; degrades to OCR text.
- **Tests:** **57/57 green**. Live `--trace` on 5 OmniDocBench images verified all
  artifacts/steps + fallback flag; enhance gating confirmed conservative.
- **Pending:** OmniDocBench **metric delta NOT yet measured** — next step is a
  small-sample eval (Rule 4) to quantify the enhance / serializer changes vs the
  v0.1.0 baseline before any full run.

## State: ✅ Slice 1 done & measured

End-to-end traditional (non-VLM) OCR pipeline, scored on OmniDocBench sample_100,
directly comparable to the hybrid VLM baseline (same scorer / config / 100 GT images).

### Result (run `2026-06-09_0106_traditional-ocr`)

Traditional **wins 5 of 7 metrics** and is **5.7× faster (CPU)**:

| metric | traditional | hybrid VLM | winner |
|---|---|---|---|
| text_block Edit_dist ↓ | **0.342** | 0.467 | traditional |
| reading_order Edit_dist ↓ | **0.367** | 0.410 | traditional |
| table TEDS_structure_only ↑ | **0.420** | 0.364 | traditional |
| table Edit_dist ↓ | **0.683** | 0.792 | traditional |
| latency s/img ↓ | **5.06** | 28.9 | traditional |
| display_formula Edit_dist ↓ | 0.839 | **0.538** | hybrid |
| table TEDS ↑ | 0.170 | **0.188** | hybrid |

Full table: `results/comparison.md`. Per-run: `results/runs/*/summary.md`.

## Architecture (built)

ingest (BGR numpy, CJK-safe) → preprocess (deskew) → PP-Structure (layout+table→HTML)
with PP-OCRv4 full-page fallback → XY-cut reading order → Markdown serializer
(byte-compatible with hybrid). Engine = PaddleOCR PP-OCRv4 + PP-StructureV2, **CPU only**
(Blackwell GPU returns 0 detections with paddle 3.3). 31/31 unit tests.

## How to re-run

```powershell
$PY = "$env:USERPROFILE\.conda\envs\ocr-worker\python.exe"; $env:PYTHONUTF8="1"
cd C:\Projects\ComputerVision\RnD_pipeline\traditional
& $PY scripts/eval_run.py --n 100 --solution traditional-ocr
& $PY scripts/compare_runs.py
```

## Chưa làm / Next

- **Formula:** enable PP-Structure LaTeX-OCR (real `$…$`) — biggest gap vs VLM (0.839 vs
  0.538). Needs Docker + CDM for proper scoring.
- **Tables (TEDS content):** improve cell recognition; structure_only already beats hybrid.
- **Per-source language:** use `en` rec model for English-only sources (newspaper weak 0.694).
- **Deskew direction:** verify sign on real skewed photos (currently no-op on clean renders).
- **Full 1651-page run** once slice is accepted (only sample_100 measured so far).
- **PDF path:** exercise multi-page (needs pymupdf in `ocr-worker`).
