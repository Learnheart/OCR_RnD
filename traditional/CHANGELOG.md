# Changelog — `traditional/`

All notable changes to the traditional OCR solution. Newest on top.
Follows [Semantic Versioning](https://semver.org/). Tags: `[traditional]`.

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
