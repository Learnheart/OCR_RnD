# Solution Agent — `traditional/`

> Classic OCR pipeline (no VLM): CV preprocess → layout/structure → OCR → reading-order
> → Markdown. Scored on the shared OmniDocBench benchmark, apples-to-apples vs `hybrid/`.

## Method / approach

A staged traditional pipeline. Every page flows through:

1. **Ingest** (`ingest/loader.py`) — decode image to BGR numpy (handles CJK Windows
   paths via `np.fromfile`+`imdecode`). PDFs via lazy PyMuPDF (benchmark is all images).
2. **Preprocess** (`preprocess/cv_preprocess.py`) — conservative deskew (min-area-rect,
   only corrects 0.3–15° skew) + optional denoise. Clean renders pass through ~untouched.
3. **Structure + OCR** (`extract/paddle_engine.py`)
   - **Primary:** PaddleOCR **PP-Structure** → layout regions (text/title/table/equation/
     header/footer) with PP-OCRv4 text recognition; tables returned as **HTML** (for TEDS).
   - **Fallback:** if structure coverage is poor (e.g. dense code pages where layout
     collapses), full-page **PP-OCRv4** det+rec, lines grouped into paragraphs by
     vertical-gap heuristics. Guarantees text recall.
4. **Reading order** (`layout/reading_order.py`) — recursive **XY-cut** over block
   bounding boxes: peels full-width bands (headers) then splits columns.
5. **Serialize** (`serialize/markdown.py`) — Block[] → Markdown (titles `#`, tables HTML,
   formulas `$$…$$`). **Byte-compatible with the hybrid serializer** → comparable scores.

The `Block`/`PageResult`/`DocumentResult` contract and the `ParseEngine` ABC are *copied*
from `hybrid/` (CLAUDE.md Rule 2: solutions stay isolated) but kept identical in shape.

## Techstack

| Concern | Choice |
|---|---|
| OCR detection+recognition | PaddleOCR **PP-OCRv4** (DB detector + SVTR_LCNet recognizer) |
| Layout + table structure | **PP-StructureV2** (layout det + table structure → HTML) |
| Classic CV | OpenCV 4.11 (deskew, denoise) |
| Models | `ch` (Chinese+English) — benchmark is 765 SC / 755 EN / 116 mixed |
| Compute | **CPU only** — see GPU note below |
| Contract | pydantic v2 |

### ⚠️ GPU note (important)

`paddlepaddle-gpu 3.3.0` on the RTX 5060 Ti (Blackwell, sm_120) **silently returns 0
detections** — the compiled kernels predate this arch. Verified: GPU n_lines=0 vs CPU
n_lines=41/36/127 on identical images. **The pipeline forces `use_gpu=False`.** CPU OCR
is fast enough here (~1–4 s/img). Revisit if a Blackwell-compatible paddle wheel ships.

## Environment / deps

Runs in the **`ocr-worker` conda env** (Python 3.11), which already has:
`paddleocr 2.9.1`, `paddlepaddle-gpu 3.3.0`, `opencv 4.11`, `shapely`, `pyclipper`,
`scikit-image`, `pydantic`, `numpy 1.26`. Tests also need `pytest`.

Scoring uses the **`omnidocbench` conda env** (Python 3.10) — the shared scorer, same as
hybrid. Two-env split; no `conda activate` needed (scripts shell out by path).

## How to run

```powershell
$PY = "$env:USERPROFILE\.conda\envs\ocr-worker\python.exe"
$env:PYTHONUTF8 = "1"
cd C:\Projects\ComputerVision\RnD_pipeline\traditional

# debug one image (prints block summary + markdown)
& $PY scripts/parse_one.py "..\eval\OmniDocBench_data\images\<name>.jpg" --blocks

# full eval on the shared 100-image sample → score → results/runs/<ts>_traditional-ocr/
& $PY scripts/eval_run.py --n 100 --solution traditional-ocr

# tests
& $PY -m pytest tests/ -q
```

Each run lands in `results/runs/<YYYY-MM-DD_HHMM>_traditional-ocr/` with `summary.md`,
`meta.json`, `predictions/`, `gt_subset.json`, `score.log`, `result/`.

## Measured score (OmniDocBench sample_100) — run 2026-06-09_0106

Same 100 images as the hybrid baseline. **Traditional wins 5 of 7 metrics** and is
**5.7× faster on CPU.** Full breakdown: `results/comparison.md` and the run's `summary.md`.

| metric | traditional (PP-OCRv4) | hybrid (Qwen3-VL) | dir | winner |
|---|---|---|---|---|
| text_block Edit_dist | **0.342** | 0.467 | ↓ | traditional |
| display_formula Edit_dist | 0.839 | **0.538** | ↓ | hybrid |
| table TEDS | 0.170 | **0.188** | ↑ | hybrid |
| table TEDS_structure_only | **0.420** | 0.364 | ↑ | traditional |
| table Edit_dist | **0.683** | 0.792 | ↓ | traditional |
| reading_order Edit_dist | **0.367** | 0.410 | ↓ | traditional |
| latency (s/img) | **5.06** | 28.9 | ↓ | traditional |

**Reading:** classic OCR is *more accurate on plain text + reading order and far cheaper*;
the VLM's edge is **formulas** (true LaTeX vs our OCR'd text) and **table cell content**
(TEDS), where layout reasoning helps. Per-source: traditional is strongest on magazine /
research_report / PPT / textbook; weakest on newspaper + historical scripts.

## Trade-offs (vs hybrid VLM)

- **Speed/cost:** no GPU/LLM — runs on CPU, no LM Studio, no VLM tokens. Far cheaper.
- **Grounding:** every block has a real bbox (VLM tier has none) → enables XY-cut reading
  order and future provenance/validation.
- **Weak spots (this slice):** formulas are OCR'd text not true LaTeX (LaTeX-OCR + CDM
  scoring deferred to Docker); handwriting/historical scripts; heavy color backgrounds.

## Deferred / next

- Enable PP-Structure formula recognition (LaTeX-OCR) for real `$…$` output.
- Tune deskew direction + per-source language model (`en` vs `ch`).
- PDF multi-page path exercise (needs pymupdf in env).
