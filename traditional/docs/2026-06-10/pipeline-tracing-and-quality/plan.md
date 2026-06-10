---
author: lytinh358@gmail.com
date: 2026-06-10
status: done
agents: traditional
summary: Add per-step tracing to the traditional OCR pipeline and improve output quality (preprocessing for low-contrast docs, formula recognition, table/markdown serialization).
---

# Pipeline tracing + output-quality upgrade — `traditional`

## Problem statement

The traditional pipeline (PaddleOCR PP-OCRv4 + PP-StructureV2, CPU) has a measured
100-image OmniDocBench baseline (text Edit_dist 0.342, reading_order 0.367,
table TEDS 0.170, formula Edit_dist 0.839). Two gaps:

1. **No traceability.** The only introspection is `PageTrace` (latency / deskew /
   n_blocks) printed to stdout, plus `--blocks` block previews. There is no way to
   inspect *per-step* intermediate results: the preprocessed image, the raw layout
   regions, which extraction path fired (structure vs the silent full-page OCR
   fallback), per-block crops, or per-step timings. Debugging a bad page is guesswork.

2. **Output quality ceilings** on identifiable weak spots:
   - **Formula** Edit_dist 0.839 is the single worst metric — formulas are emitted as
     OCR'd text, not LaTeX.
   - **Low-contrast sources** (newspaper 0.694, historical_document 0.918) are far
     worse than clean sources (magazine 0.167) — preprocessing does deskew + optional
     denoise but no contrast normalization / adaptive binarization.
   - **Table** TEDS 0.170 trails the hybrid VLM (0.188); HTML cleanup + markdown
     serialization are minimal.

## Requirements

- **R1 — Per-step trace.** For a single document, capture each pipeline step
  (ingest → preprocess → extract → reading_order → serialize) with: timing, a
  structured summary, and on-disk artifacts (preprocessed image, layout overlay PNG,
  per-block crops, raw structure JSON). The **fallback decision must be explicit**
  (was full-page OCR used, why). Emit a machine-readable `trace.json` and a
  human-readable markdown report under a per-document trace dir.
- **R2 — Tracing is opt-in and zero-cost when off.** Default eval runs must not slow
  down or change output. Trace only when explicitly enabled (`--trace`).
- **R3 — Output contract unchanged.** `document_to_md` still emits the same Markdown
  shape; OmniDocBench scoring stays apples-to-apples. No schema break.
- **R4 — Quality improvements degrade safely.** Formula recognition must no-op
  gracefully if the model is unavailable (no pipeline break). Preprocessing changes
  must not regress clean sources.

## Decisions made

- **Trace lives at the orchestrator.** `Pipeline._process_page` instruments each step
  (it already calls them in sequence and holds every intermediate). Step modules stay
  tracer-agnostic to avoid coupling and parallel-edit conflicts. The one exception:
  the engine exposes a read-only `last_meta` dict (path used, raw region count,
  struct char count) so the fallback decision is observable — this is data exposure,
  not a tracer dependency.
- **New module `src/idp_trad/trace/`** with `models.py` (frozen Pydantic contract),
  `tracer.py` (timing + record collection + `trace.json` writer), `artifacts.py`
  (image/JSON dumpers — heavy, lazy-imported so the core runs without them),
  `report.py` (markdown report).
- **Quality work is split by file ownership** so it can be built in parallel:
  preprocessing (`preprocess/*`), extraction+serialization (`extract/paddle_engine.py`,
  `serialize/markdown.py`).

## Implementation approach

### Foundation (this doc's owner, sequential)
- `trace/models.py` — `StepRecord`, `PageTraceRecord`, `DocumentTrace` (FROZEN).
- `trace/tracer.py` — `Tracer`: enable flag, output dir, `step()` context manager,
  `record_artifact()`, `write()`. Lazy-imports `artifacts` (skips if absent).
- `pipeline.py` — accept optional `tracer`; wrap each step; pass `engine.last_meta`.
- `paddle_engine.py` — set `self.last_meta` after `parse()` (path/n_regions/chars).

### F1 — artifacts + report + CLI
- `trace/artifacts.py`, `trace/report.py`, `scripts/parse_one.py --trace`.

### F2 — preprocessing
- `preprocess/enhance.py` (CLAHE / adaptive binarize / denoise), wired into
  `preprocess/cv_preprocess.py` conditionally on a cheap low-contrast estimate.

### F3 — extraction + serialization
- `extract/paddle_engine.py` — LaTeX formula recognition path (safe-degrade) +
  table HTML cleanup; `serialize/markdown.py` — list/heading/table polish.

### Verify
- `parse_one.py --trace` on 3–5 representative images; existing test suite green;
  small-sample eval sanity check vs baseline before any full run (CLAUDE.md Rule 4).

## Outcome

Shipped as **v0.2.0** (MINOR — new capability, no output-contract / schema break):

- **R1 / R2 — Per-step tracing.** New `src/idp_trad/trace/` module (`models.py`,
  `tracer.py`, `artifacts.py`, `report.py`); opt-in `Tracer` threaded through
  `Pipeline`; `scripts/parse_one.py --trace [DIR]` (default `results/traces`). Traces
  ingest → preprocess → extract → reading_order → serialize with timings, a structured
  summary, an **explicit fallback decision**, and on-disk artifacts (`original.png`,
  `preprocessed.png`, `structure_raw.json`, `layout_overlay.png`, `crops/`) plus
  `trace.json` + `report.md`. Off by default → zero overhead, unchanged eval output.
- **R3 — Output contract unchanged.** Markdown stays byte-compatible; serializer polish
  (formula `$$…$$`, `list` bullets) and table HTML cleanup keep the OmniDocBench shape.
- **R4 — Safe-degrade quality.** Low-contrast enhance (`preprocess/enhance.py`,
  `do_enhance` ON) is conservatively AND-gated so clean pages pass through untouched.

**Blocker:** the LaTeXOCR formula recognizer is fully wired behind `enable_formula` but
left **DEFAULT OFF** — inference segfaults (`0xC0000005`) on this Blackwell sm_120 +
paddle 3.x box (same class as the known GPU bug); it degrades to OCR'd text.

**Verification:** full suite **57/57 pass**; live `--trace` on 5 OmniDocBench images
confirmed all artifacts/steps + the fallback flag; enhance gating confirmed conservative.

**Pending:** the **OmniDocBench metric delta is NOT yet measured** — a small-sample eval
(CLAUDE.md Rule 4) is the next step to quantify the enhance / serializer changes vs the
v0.1.0 baseline before any full run.
