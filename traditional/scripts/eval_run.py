"""One-command eval: generate predictions on the SAMPLE → score → archive.

Each run = `results/runs/<YYYY-MM-DD_HHMM>_<solution>/` (isolated). Reuses the SAME
`eval/samples/sample_100.txt` as the hybrid run so the two solutions are scored on
identical images.

    %USERPROFILE%\.conda\envs\ocr-worker\python.exe scripts/eval_run.py --n 100

Generation runs here (ocr-worker env, PaddleOCR). Scoring shells out to the
`omnidocbench` conda env (py3.10) — same split as hybrid.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TRAD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TRAD_DIR / "src"))

import yaml  # noqa: E402

from idp_trad.batch import make_pipeline, run_batch  # noqa: E402

EVAL_DIR = TRAD_DIR.parent / "eval"
IMAGES_DIR = EVAL_DIR / "OmniDocBench_data" / "images"
GT_JSON = EVAL_DIR / "OmniDocBench_data" / "OmniDocBench.json"
ODB_EVAL = EVAL_DIR / "OmniDocBench_eval"
BASE_CFG = ODB_EVAL / "configs" / "end2end_local.yaml"
CONDA_PY = Path.home() / ".conda" / "envs" / "omnidocbench" / "python.exe"
RUNS_DIR = TRAD_DIR / "results" / "runs"
SAMPLE_DEFAULT = EVAL_DIR / "samples" / "sample_100.txt"


def read_sample(sample_file: Path, n: int) -> list[str]:
    names = [ln.strip() for ln in sample_file.read_text(encoding="utf-8").splitlines()
             if ln.strip()]
    return names[:n] if n else names


def write_filtered_gt(run_dir: Path, names: list[str]) -> Path:
    """Filter OmniDocBench.json down to exactly the sample images (else the scorer
    counts missing predictions as edit_dist=1.0)."""
    data = json.loads(GT_JSON.read_text(encoding="utf-8"))
    keep = set(names)
    subset = [r for r in data if r["page_info"]["image_path"] in keep]
    out = run_dir / "gt_subset.json"
    out.write_text(json.dumps(subset, ensure_ascii=False), encoding="utf-8")
    print(f"[gt] filtered {len(subset)}/{len(data)} images → {out.name}")
    return out


def write_run_config(run_cfg: Path, pred_dir: Path, gt_path: Path) -> None:
    cfg = yaml.safe_load(BASE_CFG.read_text(encoding="utf-8"))
    ds = cfg["end2end_eval"]["dataset"]
    ds["prediction"]["data_path"] = pred_dir.resolve().as_posix()
    ds["ground_truth"]["data_path"] = gt_path.resolve().as_posix()
    run_cfg.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")


def score(run_cfg: Path, log_file: Path) -> int:
    if not CONDA_PY.exists():
        print(f"[ERR] conda python not found: {CONDA_PY}", file=sys.stderr)
        return 1
    full_env = {**os.environ, "PYTHONUTF8": "1"}
    print(f"[score] {CONDA_PY.name} pdf_validation.py --config {run_cfg.name}")
    with log_file.open("w", encoding="utf-8") as lf:
        proc = subprocess.run(
            [str(CONDA_PY), "pdf_validation.py", "--config", str(run_cfg)],
            cwd=str(ODB_EVAL), env=full_env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace",
        )
        lf.write(proc.stdout or "")
    print("\n".join((proc.stdout or "").splitlines()[-8:]))
    return proc.returncode


def collect_results(run_dir: Path, prefix: str) -> Path | None:
    src = ODB_EVAL / "result"
    dst = run_dir / "result"
    dst.mkdir(parents=True, exist_ok=True)
    metric = None
    for f in src.glob(f"{prefix}_quick_match*.json"):
        target = dst / f.name
        target.write_bytes(f.read_bytes())
        if f.name.endswith("metric_result.json"):
            metric = target
    return metric


def _clean(v):
    if isinstance(v, str) and v.strip().lower() in ("nan", "inf", "-inf"):
        return None
    if isinstance(v, (int, float)):
        if math.isnan(v) or math.isinf(v):
            return None
        return round(v, 4)
    return v


def summarize(metric_file: Path) -> dict:
    d = json.loads(metric_file.read_text(encoding="utf-8"))
    out: dict = {"overall": {}, "by_source": {}}
    for cat, cd in d.items():
        if not isinstance(cd, dict):
            continue
        allm = cd.get("all", {})
        if not isinstance(allm, dict):
            continue
        for mname, mv in allm.items():
            if isinstance(mv, dict):
                val = mv.get("ALL_page_avg", mv.get("all", mv.get("edit_whole")))
                out["overall"][f"{cat}.{mname}"] = _clean(val)
    cols = [
        ("text_edit", "text_block", "Edit_dist"),
        ("formula_edit", "display_formula", "Edit_dist"),
        ("table_teds", "table", "TEDS"),
        ("table_edit", "table", "Edit_dist"),
        ("reading_edit", "reading_order", "Edit_dist"),
    ]

    def page_by_source(task: str, metric: str) -> dict:
        pg = d.get(task, {}).get("page", {}).get(metric, {})
        res = {}
        if isinstance(pg, dict):
            for k, v in pg.items():
                if k.startswith("data_source:") and isinstance(v, (int, float)):
                    res[k.replace("data_source: ", "")] = _clean(v)
        return res

    per = {col: page_by_source(task, metric) for col, task, metric in cols}
    sources = sorted(set().union(*[set(v) for v in per.values()])) if per else []
    out["matrix"] = {s: {col: per[col].get(s) for col, _, _ in cols} for s in sources}
    out["by_source"] = {s: out["matrix"][s]["text_edit"]
                        for s in sources if out["matrix"][s]["text_edit"] is not None}
    return out


def write_summary_md(run_dir: Path, meta: dict) -> None:
    m = meta.get("metrics", {})
    ov = m.get("overall", {})
    matrix = m.get("matrix", {})
    gs = meta.get("generate_stats", {})

    def cell(v) -> str:
        if v is None:
            return "–"
        return f"{v:.3f}" if isinstance(v, (int, float)) else str(v)

    overall_rows = []
    for k, v in ov.items():
        arrow = "↑ high=good" if "TEDS" in k else "↓ low=good"
        overall_rows.append(f"| {k} | {cell(v)} | {arrow} |")

    lines = [
        f"# Eval run — {meta.get('run_id','')}",
        "",
        f"- **Solution**: {meta.get('solution')}  ·  **Engine**: {meta.get('engine')}",
        f"- **Sample**: {meta.get('n_sample')} images  ·  "
        f"`{Path(meta.get('sample_file','')).name}`",
        f"- **Generation**: avg {gs.get('avg_latency_s')}s/img · p50 "
        f"{gs.get('p50_latency_s')}s · max {gs.get('max_latency_s')}s · "
        f"{gs.get('elapsed_s',0)/60:.1f} min · err {gs.get('n_error')}",
        "",
        "## Overall by task",
        "",
        "| Task.metric | Value | Dir |",
        "|---|---|---|",
        *overall_rows,
        "",
        "## Source × task matrix",
        "",
        "| data_source | text ↓ | formula ↓ | table TEDS ↑ | table edit ↓ | reading ↓ |",
        "|---|---|---|---|---|---|",
    ]

    def text_key(s):
        v = matrix[s].get("text_edit")
        return (v is None, v if v is not None else 0)

    for s in sorted(matrix, key=text_key):
        r = matrix[s]
        lines.append(
            f"| {s} | {cell(r.get('text_edit'))} | {cell(r.get('formula_edit'))} "
            f"| {cell(r.get('table_teds'))} | {cell(r.get('table_edit'))} "
            f"| {cell(r.get('reading_edit'))} |"
        )
    lines.append("")
    (run_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--solution", default="traditional-ocr")
    ap.add_argument("--sample-file", default=str(SAMPLE_DEFAULT))
    ap.add_argument("--lang", default="ch")
    ap.add_argument("--no-deskew", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--skip-generate", action="store_true")
    ap.add_argument("--skip-score", action="store_true")
    args = ap.parse_args()

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    run_id = f"{stamp}_{args.solution}"
    run_dir = RUNS_DIR / run_id
    pred_dir = run_dir / "predictions"
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"=== RUN {run_id} ===")

    sample_file = Path(args.sample_file)
    names = read_sample(sample_file, args.n)
    images = [IMAGES_DIR / nm for nm in names]
    missing = [im.name for im in images if not im.exists()]
    if missing:
        print(f"[WARN] {len(missing)} sample images missing on disk (e.g. {missing[:2]})")
    images = [im for im in images if im.exists()]
    print(f"[sample] {len(images)} images from {sample_file.name}")

    if not args.skip_generate:
        pipe = make_pipeline(lang=args.lang, use_gpu=False,
                             do_deskew=not args.no_deskew)
        try:
            stats = run_batch(images, pred_dir, pipe, overwrite=args.overwrite,
                              latency_out=run_dir / "latency.json")
        finally:
            pipe.close()
    else:
        stats = {"note": "skip-generate"}

    meta = {
        "run_id": run_id, "timestamp": stamp, "solution": args.solution,
        "engine": "paddleocr-ppstructure@cpu", "n_sample": len(images),
        "sample_file": str(sample_file), "generate_stats": stats,
    }

    if not args.skip_score:
        gt_path = write_filtered_gt(run_dir, [im.name for im in images])
        run_cfg = run_dir / "eval_config.yaml"
        write_run_config(run_cfg, pred_dir, gt_path)
        rc = score(run_cfg, run_dir / "score.log")
        if rc != 0:
            print(f"[WARN] scorer exit code {rc} — see {run_dir/'score.log'}")
        metric_file = collect_results(run_dir, pred_dir.name)
        if metric_file:
            summary = summarize(metric_file)
            meta["metrics"] = summary
            print("\n=== METRICS (overall) ===")
            for k, v in summary["overall"].items():
                print(f"  {k:42s} {v}")

    (run_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    if meta.get("metrics"):
        write_summary_md(run_dir, meta)
    print(f"\n[run dir] {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
