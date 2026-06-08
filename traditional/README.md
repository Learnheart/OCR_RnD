# traditional/ — Classic OCR pipeline (no VLM)

Document page → Markdown via a staged traditional pipeline, scored on the shared
**OmniDocBench** benchmark for an apples-to-apples comparison with `hybrid/` (VLM).

```
ingest → preprocess (deskew/denoise) → PP-Structure layout + PP-OCRv4 OCR
       → XY-cut reading order → Markdown
```

- **Engine:** PaddleOCR PP-OCRv4 + PP-StructureV2 (tables → HTML), **CPU only**
  (GPU broken on this Blackwell card — see `AGENT.md`).
- **Fallback:** full-page PP-OCRv4 when layout detection collapses (e.g. code pages).
- **Output contract:** one `.md` per image (tables HTML, formulas `$$…$$`), identical
  to hybrid's serializer.

## Quickstart

```powershell
$PY = "$env:USERPROFILE\.conda\envs\ocr-worker\python.exe"
$env:PYTHONUTF8 = "1"
cd C:\Projects\ComputerVision\RnD_pipeline\traditional

& $PY -m pytest tests/ -q                                   # 31 tests
& $PY scripts/parse_one.py "<image>" --blocks               # debug one page
& $PY scripts/eval_run.py --n 100 --solution traditional-ocr # eval + score
& $PY scripts/compare_runs.py                               # vs hybrid baseline
```

See **`AGENT.md`** for method/stack/scores and **`docs/`** for the design plan.

## Layout

```
src/idp_trad/      pipeline package (ingest, preprocess, extract, layout, serialize)
scripts/           parse_one · eval_run · compare_runs
tests/             unit tests
results/runs/      per-run eval outputs (summary.md, meta.json, predictions/)
docs/              plan / design notes (docs-first per workspace rules)
```
