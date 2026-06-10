# Changelog — `traditional/`

All notable changes to the traditional OCR solution. Newest on top.
Follows [Semantic Versioning](https://semver.org/). Tags: `[traditional]`.

## [0.2.0] — 2026-06-10

Per-step tracing + output-quality upgrade. New capability, **no output-contract /
schema break** — OmniDocBench Markdown stays byte-compatible, so this is a MINOR bump.

### Added
- `[traditional]` Per-step tracing module `src/idp_trad/trace/` (`models.py` frozen
  Pydantic contract, `tracer.py`, `artifacts.py` renderers, `report.py`). Opt-in
  `Tracer` threaded through `Pipeline`; **zero overhead and unchanged output when off**
  (the default for eval/batch). Steps traced: ingest → preprocess → extract →
  reading_order → serialize, each with timing and a structured summary; the
  structure-vs-fallback decision is captured explicitly.
- `[traditional]` `scripts/parse_one.py --trace [DIR]` flag (default
  `results/traces`). Per document it writes a trace dir with `trace.json`
  (machine-readable) + `report.md` (per-step timing table, prominent FALLBACK callout,
  regions table), and per page `original.png`, `preprocessed.png`,
  `structure_raw.json` (raw regions + fallback decision), `layout_overlay.png` (bboxes
  colored by type + reading-order numbers), and `crops/` (per-block crops).
- `[traditional]` Low-contrast preprocessing `preprocess/enhance.py` — conservative
  gated CLAHE / adaptive-binarize for washed-out / aged pages (newspaper, historical).
  AND-gate (`std<40` & `p95−p5` spread `<110`) leaves clean / color pages untouched.
  Enhance info is surfaced into the trace under the `preprocess` step's `enhance` key.

### Changed
- `[traditional]` `do_enhance` defaults **ON** in `preprocess/cv_preprocess.py`
  (conservatively gated, so clean pages pass through unchanged).
- `[traditional]` Markdown serializer (`serialize/markdown.py`): formulas display-wrapped
  `$$…$$` (no double-wrap); `list` blocks rendered as `-` bullets.
- `[traditional]` Table HTML cleanup in `extract/paddle_engine.py`: cosmetic attributes
  scrubbed while `rowspan`/`colspan` + cell content are preserved.

### Note
- `[traditional]` LaTeXOCR formula recognizer is **fully wired behind `enable_formula`
  but DEFAULT OFF**: LaTeXOCR inference segfaults (`0xC0000005`) on this Blackwell
  sm_120 + paddle 3.x box (same hardware class as the known GPU bug). With the flag off
  the pipeline degrades to OCR'd text. Re-enable once a compatible wheel ships.
- `[traditional]` Verified: full test suite **57/57 pass**; live `--trace` run on 5
  OmniDocBench images confirmed all artifacts/steps + the fallback flag; enhance gating
  confirmed conservative; Markdown contract intact. **OmniDocBench metric delta is NOT
  yet measured** — a sample eval is pending.

## [0.1.0] — 2026-06-09

First runnable slice: end-to-end classic OCR pipeline scored on OmniDocBench
sample_100, comparable to the hybrid VLM baseline.

### Added
- `[traditional]` Docs-first plan `docs/2026-06-09/traditional-ocr-pipeline/plan.md`.
- `[traditional]` Contract copy (`schemas.py`, `extract/base.py`, `serialize/markdown.py`)
  kept byte-compatible with hybrid so eval numbers are apples-to-apples.
- `[traditional]` Image-native loader (`ingest/loader.py`) — BGR numpy, CJK-path safe,
  lazy PyMuPDF for PDF.
- `[traditional]` CV preprocess (`preprocess/cv_preprocess.py`) — conservative deskew
  (min-area-rect, 0.3–15° band) + optional denoise.
- `[traditional]` PaddleOCR engine (`extract/paddle_engine.py`) — PP-Structure primary
  (layout + table→HTML) with full-page PP-OCRv4 fallback on poor coverage.
- `[traditional]` Reading-order recovery (`layout/reading_order.py`) — recursive XY-cut.
- `[traditional]` Orchestrator + batch (`pipeline.py`, `batch.py`).
- `[traditional]` Scripts: `parse_one.py` (debug) + `eval_run.py` (generate→score→archive,
  reuses the shared `sample_100.txt`).
- `[traditional]` 31 unit tests (reading-order, serialize, schemas, loader, engine
  helpers, preprocess).

### Changed
- `[traditional]` Forced `use_gpu=False`: paddlepaddle-gpu 3.3.0 silently returns 0
  detections on this Blackwell (sm_120) GPU; CPU verified correct.

### Fixed
- `[traditional]` `eval_run.py` summary formatting robust to string `"NaN"` metrics on
  tiny samples; deskew angle normalized to `(-45, 45]` for OpenCV 4.11's convention.
