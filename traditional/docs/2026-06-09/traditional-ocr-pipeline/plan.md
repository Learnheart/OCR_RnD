---
author: lytinh358@gmail.com
date: 2026-06-09
status: in-progress
agents: traditional
summary: Traditional (non-VLM) OCR pipeline on OmniDocBench, apples-to-apples vs hybrid VLM
---

# Traditional OCR Pipeline — Slice 1 (OmniDocBench general doc-parsing)

## Problem statement

The RnD workspace compares document-parsing approaches on the shared **OmniDocBench
v1.5** benchmark. `hybrid/` (Tier 0 deterministic + Tier B Qwen3-VL VLM) has a
measured baseline; `end-to-end-VLM/` is the yardstick. The `traditional/` slot — a
**classic OCR pipeline with no VLM** — is empty. This slice builds it end-to-end and
scores it on the **same 100-image sample** the hybrid run used, so the two approaches
are directly comparable.

**Hybrid baseline to compare against (sample_100):**

| metric | hybrid VLM | dir |
|---|---|---|
| text_block Edit_dist | 0.467 | ↓ |
| display_formula Edit_dist | 0.538 | ↓ |
| table TEDS | 0.188 | ↑ |
| table TEDS_structure_only | 0.364 | ↑ |
| reading_order Edit_dist | 0.410 | ↓ |
| latency | 28.9 s/img | ↓ |

## Requirements

- **No VLM.** Detection + recognition + structure must be classic CV/OCR models.
- **Same output contract** as every solution: one Markdown file per input image into
  the run's `predictions/` dir, named `<image_stem>.md`. Tables as HTML (TEDS),
  formulas as LaTeX `$$…$$`, titles as `#`, text plain, in reading order.
- **Self-contained** under `traditional/` — do not import `hybrid/`'s code (CLAUDE.md
  Rule 2). The frozen contract (`Block`/`PageResult`/`DocumentResult`, the serializer,
  the `ParseEngine` ABC) is *copied*, not imported, so the output format is identical.
- **Runs on this machine.** `ocr-worker` conda env (py3.11) already has PaddleOCR
  2.9.1 + paddlepaddle-gpu 3.3.0 + OpenCV + Tesseract.

## Decisions made

1. **Engine = PaddleOCR PP-OCRv4 (det+rec) + PP-Structure (layout+table), CPU only.**
   - *Why CPU:* the RTX 5060 Ti is Blackwell (sm_120); paddlepaddle-gpu 3.3.0 kernels
     silently return **0 detections** on this arch (verified: GPU n_lines=0 vs CPU
     n_lines=41/36/127 on the same images). Forcing CPU is correct, not a perf choice.
   - *Why PaddleOCR over Tesseract/EasyOCR:* PP-Structure gives layout regions + table
     HTML out of the box (needed for TEDS), handles CJK+EN (benchmark is 765 SC / 755
     EN / 116 mixed), and is the canonical "traditional OCR" reference. Tesseract is
     weak on CJK + has no table structure; EasyOCR has no layout/table model.
2. **PP-Structure primary, raw PP-OCRv4 fallback.** PP-Structure occasionally returns
   near-empty layout on dense/code pages (verified: a code-listing page → 1 region).
   When structure coverage is poor, fall back to full-page PP-OCRv4 det+rec with our
   own line→block grouping so no text is lost.
3. **Own reading-order (column-aware XY-cut)** on region bboxes rather than trusting the
   structure model's order — classic traditional reading-order recovery, full control.
4. **Preprocess stage** (deskew via min-area-rect, light denoise) — a hallmark of
   traditional OCR; mobile-photo/scan robustness per `data_requirements.md`.
5. **Formula recognition left as text fallback** (PP-Structure `formula=False`). Full
   LaTeX-OCR + CDM scoring needs Docker (per eval README); deferred. `equation` regions
   are emitted as recognized text — formula Edit_dist will be present but not optimal.
6. **PDF support** via lazy `pymupdf` import (absent in `ocr-worker`); benchmark is all
   images so this is a graceful extension, not on the hot path for this slice.

## Implementation approach

```
traditional/
  docs/2026-06-09/traditional-ocr-pipeline/plan.md   ← this
  AGENT.md            source of truth: method/stack/how-to-run
  CHANGELOG.md
  src/idp_trad/
    schemas.py        Block / PageResult / DocumentResult (contract copy)
    ingest/loader.py  image-native LoadedPage (+ lazy pymupdf)
    preprocess/cv_preprocess.py   deskew + denoise (OpenCV)
    extract/base.py   ParseEngine ABC
    extract/paddle_engine.py      PP-Structure primary + PP-OCRv4 fallback → Block[]
    layout/reading_order.py       column-aware XY-cut ordering
    serialize/markdown.py         Block[] → Markdown (contract copy)
    pipeline.py       ingest → preprocess → extract → DocumentResult
    batch.py          run over image list → write predictions + latency.json
  scripts/
    parse_one.py      debug a single image → stdout markdown
    eval_run.py       generate predictions on sample → score via conda → summary.md
  tests/              co-located unit tests (reading-order, serialize, pipeline smoke)
  results/runs/<ts>_traditional-ocr/   isolated eval outputs
```

**Run model:** generation runs in `ocr-worker` (py3.11, PaddleOCR); scoring runs in
`omnidocbench` (py3.10) — same two-env split as hybrid. `scripts/eval_run.py` mirrors
hybrid's: reuse `eval/samples/sample_100.txt`, filter GT to the sample, score with
`OmniDocBench_eval/pdf_validation.py`, write `summary.md` + `meta.json`.

**Verification:** smoke on 2 images first (Rule 4) → full 100 → compare table to hybrid
baseline → record numbers in AGENT.md + CLAUDE.md Agent Index.

## Risks / mitigations

- *GPU broken* → forced CPU (decided). CPU ~0.1–1 s/img det+rec; 100 imgs minutes.
- *Sparse layout on some pages* → PP-OCRv4 fallback (decided).
- *First-run model download* (~15 MB det+rec, +table model) → one-time, cached in
  `~/.paddleocr`.
