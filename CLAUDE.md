# RESEARCH WORKSPACE (RnD)

> This is the **R&D workspace** for evaluating document-parsing / OCR / IDP solutions.
> Each solution lives in its own folder under `RnD_pipeline/` and behaves like a **standalone Claude agent app** ("solution agent").
> The goal of every solution is the same: turn a document page into structured output, then **measure its quality against the shared OmniDocBench benchmark** in `eval/`.
> Each solution agent owns its own `AGENT.md` (source of truth for method/techstack) and `CHANGELOG.md` (full running log).

---

## 🎯 What this workspace is for

We are **researching and comparing** multiple approaches to the same problem (document → text / tables / formulas / key-values). The job in RnD is to:

1. Pick or design a solution approach (traditional OCR, end-to-end VLM, or hybrid tiered).
2. Build a thin runnable slice of it under its solution folder.
3. Run it over the **OmniDocBench eval set** (start with 1–2 samples, then full) to get an apples-to-apples number.
4. Record the number + trade-offs in the solution's `AGENT.md` / `CHANGELOG.md` and in the Agent Index below.

The first measured slice is **general document-parsing on OmniDocBench v1.5** (not domain-specific KYC) — chosen because it gives a baseline score within days.

---

## 🛑 IMPORTANT RULES

> **These rules are non-negotiable. AI agents and human contributors MUST follow them. Do NOT skip any step.**

### 1. Documentation-First: Plans BEFORE Code

All plans, design documents, and implementation specs **MUST** be stored in the `docs/` of each solution folder **BEFORE any implementation begins**. No exceptions.

```
<solution>/docs/
└── YYYY-MM-DD/
    └── <feature-name>/
        ├── plan.md           # Implementation plan (REQUIRED — write FIRST)
        ├── design.md         # Technical design (if needed)
        └── notes.md          # Research notes, decisions, eval numbers (if needed)
```

Every doc **MUST** start with this metadata block:

```markdown
---
author: <name or email>
date: YYYY-MM-DD
status: draft | in-progress | done | abandoned
agents: <comma-separated solution/agent IDs affected>
summary: <one-line description of what this is about>
---
```

- **ALWAYS** create `docs/YYYY-MM-DD/<feature-name>/plan.md` BEFORE writing any code
- Use the date the work started (ISO format: `YYYY-MM-DD`)
- Use kebab-case for feature names
- The plan must include: metadata block, problem statement, requirements, decisions made, and implementation approach
- If you are an AI agent: **stop and create the plan document first**, then proceed with implementation

### 2. Shared Benchmark & Solution Isolation

- `RnD_pipeline/end-to-end-VLM` is the **shared baseline benchmark** used to judge every other solution — changes here affect **ALL** comparisons. Coordinate before modifying.
- `RnD_pipeline/eval` is the **shared evaluation harness + ground truth** (OmniDocBench). Treat it as read-only infrastructure: drop predictions in, read scores out. Do not edit the scoring code.
- When researching a **new solution**, create a **new folder** in `RnD_pipeline/` — do not entangle it with another solution's code.
- A solution's own artifacts (intermediate outputs, models, logs) live inside **its own folder** under `results/`. Its OmniDocBench predictions go into the shared `eval/predictions/end2end/` only when you run the score.

### 3. Solution Agent Details Live in Each Agent's `AGENT.md`

- Each solution agent's full details (method/approach, techstack, architecture, deps, how to run) live in `RnD_pipeline/<solution>/AGENT.md`
- When changing a solution, update **its own** `AGENT.md` — that is the source of truth
- Do NOT duplicate solution details in this file — keep only the index table below
- If a solution folder has no `AGENT.md` yet, the first task when starting work on it is to create one

### 4. Evaluation — Small First, Then Full

- **ALWAYS** run the eval with **1–2 sample pages first** to prove the pipeline end-to-end (prediction format, file naming, scoring runs without crashing). Only after that passes, run the **full 1651-page set**.
- See **[How to run the eval](#-how-to-run-the-eval)** below for the exact commands.

### 5. Changelog — Log Every Update Before Commit

- **ALWAYS** update the solution's `CHANGELOG.md` **BEFORE committing code** — the changelog entry and the code change go in the **same commit**
- Keep the running log format — one entry per update, newest on top
- Follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`
  - **MAJOR** — breaking changes (output contract / schema changes, removed approach)
  - **MINOR** — new capability, new shared component, new eval slice
  - **PATCH** — bug fixes, prompt tuning, doc updates, eval-number refresh
- Group entries under: `Added`, `Changed`, `Fixed`, `Removed`
- Tag each entry with the affected area in brackets, e.g. `[hybrid]`, `[eval]`, `[traditional]`, `[all]`
- If you are an AI agent: **stop and update `CHANGELOG.md` before staging the commit**, then commit both together

---

## 🧪 How to run the eval

The benchmark is **OmniDocBench v1.5** (1651 real document pages). The harness + ground truth live in `RnD_pipeline/eval/`. Full details and gotchas are in `eval/README.md` — this is the quick operational summary.

**Output contract every solution must produce:** for each input image in `eval/OmniDocBench_data/images/`, emit **one Markdown file** into `eval/predictions/end2end/`, named the same as the image but with a `.md` extension. The `.md` holds the full page as Markdown (text + tables as HTML/Markdown + formulas as LaTeX `$...$`).

```
images/page-d1561665-....png   ->   predictions/end2end/page-d1561665-....md
```

### Environment (one-time, already set up)

The scorer needs **Python 3.10/3.11** (it does NOT run on the machine's default Python 3.12), and **`PYTHONUTF8=1`** on Windows (its JSON reads have no declared encoding → crash on CJK/Vietnamese). A conda env `omnidocbench` (py3.10) is already created at `%USERPROFILE%\.conda\envs\omnidocbench\python.exe`. The `run_eval.ps1` wrapper handles both automatically — you do not need `conda activate`.

### Step A — verify ground truth is present

```powershell
cd C:\Projects\ComputerVision\RnD_pipeline\eval
python check_setup.py
# expect: "Ảnh THIẾU: 0" and "[OK] Ground truth đầy đủ."
```

### Step B — smoke test on 1–2 samples FIRST (Rule 4)

Before processing all 1651 pages, prove the whole loop on a tiny subset.

1. Run your solution on just **1–2 images** and write their `.md` files into `eval/predictions/end2end/`. Grab a couple of filenames to target:
   ```powershell
   cd C:\Projects\ComputerVision\RnD_pipeline\eval
   Get-ChildItem .\OmniDocBench_data\images\*.png | Select-Object -First 2
   ```
2. Confirm the harness itself runs end-to-end with the bundled demo (proves env + UTF-8 + config are healthy):
   ```powershell
   .\run_eval.ps1 end2end_demo_local
   ```
3. Check prediction coverage for your real samples:
   ```powershell
   python check_setup.py --preds end2end
   ```

If the demo scores and your 1–2 predictions are picked up without crashing, the pipeline is proven — proceed to the full run.

### Step C — full run (all 1651 pages)

1. Get the list of images still missing a prediction, then have your solution process them:
   ```powershell
   python check_setup.py --list-todo end2end > todo_images.txt
   ```
2. Once `predictions/end2end/` is fully populated, score it:
   ```powershell
   cd C:\Projects\ComputerVision\RnD_pipeline\eval
   .\run_eval.ps1                       # uses configs/end2end_local.yaml
   ```

**Results:** `OmniDocBench_eval/result/end2end_quick_match_*_metric_result.json` (aggregate score, broken down by language / doc source / layout / background); a summary copy lands in `eval/results/`.

**Metrics:** Edit Distance (text / formula / reading-order — **lower is better**), TEDS (table — **higher is better**).

> Full-formula scoring (CDM) needs TeX Live + Ghostscript + ImageMagick → not available on Windows native. Use the Docker image with `configs/end2end_full.yaml` when you need it (see `eval/README.md`).

---

## 🗂️ Agent Index

The solution agents currently in this workspace. For full details on any agent, see its `AGENT.md`.

| Solution (folder) | Role | Approach | Engine / stack | Status | `AGENT.md` |
|---|---|---|---|---|---|
| `end-to-end-VLM/` | **Shared baseline benchmark** — single VLM, page-in → markdown-out; the yardstick all other solutions are compared against | Pure end-to-end VLM (no pre/post pipeline) | TBD (baseline VLM) | 🟡 scaffolding — empty, needs `AGENT.md` + runnable slice | _todo_ |
| `hybrid/` | Tiered IDP pipeline — cheap deterministic extractors first, VLM only when needed | **Tier 0** PyMuPDF / pdfplumber / Camelot (no GPU) → **Tier B** VLM fallback. Slice 1 = general doc-parsing on OmniDocBench | Tier B = **Qwen3-VL-8B** via **LM Studio** (OpenAI-compatible API `:1234`). Future accuracy target: PaddleOCR-VL on vLLM, same `ParseEngine` interface | ✅ M0–M2 done, 14/14 tests; **baseline 100-img** (text_block Edit_dist **0.467**, table TEDS **0.188**, 28.7s/img). Timestamped eval-runs in `hybrid/results/runs/` | [`hybrid/AGENT.md`](hybrid/AGENT.md) |
| `traditional/` | Classic OCR pipeline (no VLM) — layout detection + OCR + table/structure recovery | Traditional CV/OCR stack (detect → recognize → assemble) | TBD (e.g. PaddleOCR / Tesseract-class) | 🔴 empty — not started | _todo_ |

> Status legend: 🔴 not started · 🟡 scaffolding · 🟢 in progress · ✅ has a measured OmniDocBench score.
> When a solution gets its first OmniDocBench number, record it here (and in its `AGENT.md`) so approaches stay comparable at a glance.

---

## ➕ Adding / researching a new solution

1. **Create the folder** `RnD_pipeline/<solution>/` and add it to the Agent Index above.
2. **Plan first** — `docs/YYYY-MM-DD/<feature-name>/plan.md` with the metadata block BEFORE writing code (Rule 1).
3. **Write `AGENT.md`** — capture the approach, techstack, deps, and how to run it (Rule 3).
4. Implement the thin runnable slice under the solution folder; keep solution-specific outputs in its own `results/`.
5. **Smoke-test on 1–2 samples**, then run the **full** OmniDocBench eval (Rule 4 + the eval section above).
6. Record the measured score in `AGENT.md` and the Agent Index; note trade-offs (speed, VRAM, accuracy gaps).
7. **Update `CHANGELOG.md` BEFORE committing** — changelog entry + code change in the same commit (Rule 5).
