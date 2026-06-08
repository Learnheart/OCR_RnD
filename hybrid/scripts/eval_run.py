"""Orchestrator 1 lệnh: sinh prediction trên SAMPLE → chấm điểm → archive có timestamp.

Mỗi run = 1 thư mục `results/runs/<YYYY-MM-DD_HHMM>_<solution>/` (isolated, KHÔNG đụng
predictions chung) → loop back so sánh nhiều phương án trên cùng sample.

    uv run python scripts/eval_run.py --n 100 --solution hybrid-qwen3vl

Cần: LM Studio :1234 (sinh prediction) + conda env `omnidocbench` (chấm điểm).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# UTF-8 cho console Windows
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HYBRID_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HYBRID_DIR / "src"))

import yaml  # noqa: E402

from idp.batch import make_pipeline, run_batch  # noqa: E402

EVAL_DIR = HYBRID_DIR.parent / "eval"
IMAGES_DIR = EVAL_DIR / "OmniDocBench_data" / "images"
GT_JSON = EVAL_DIR / "OmniDocBench_data" / "OmniDocBench.json"
ODB_EVAL = EVAL_DIR / "OmniDocBench_eval"
BASE_CFG = ODB_EVAL / "configs" / "end2end_local.yaml"
CONDA_PY = Path.home() / ".conda" / "envs" / "omnidocbench" / "python.exe"
RUNS_DIR = HYBRID_DIR / "results" / "runs"


def ensure_sample(sample_file: Path, n: int) -> list[str]:
    if not sample_file.exists():
        from make_sample import stratified_sample  # type: ignore
        sys.path.insert(0, str(HYBRID_DIR / "scripts"))
        picked = stratified_sample(GT_JSON, n)
        sample_file.parent.mkdir(parents=True, exist_ok=True)
        sample_file.write_text("\n".join(picked) + "\n", encoding="utf-8")
        print(f"[sample] tạo mới {len(picked)} ảnh → {sample_file}")
    names = [ln.strip() for ln in sample_file.read_text(encoding="utf-8").splitlines()
             if ln.strip()]
    return names


def write_filtered_gt(run_dir: Path, names: list[str]) -> Path:
    """Lọc OmniDocBench.json xuống đúng các ảnh trong sample.

    BẮT BUỘC: scorer chấm trên TOÀN BỘ GT — ảnh không có prediction bị tính
    edit_dist=1.0. Muốn đánh giá đúng N ảnh sample, GT phải chỉ chứa N ảnh đó.
    """
    data = json.loads(GT_JSON.read_text(encoding="utf-8"))
    keep = set(names)
    subset = [r for r in data if r["page_info"]["image_path"] in keep]
    out = run_dir / "gt_subset.json"
    out.write_text(json.dumps(subset, ensure_ascii=False), encoding="utf-8")
    print(f"[gt] lọc {len(subset)}/{len(data)} ảnh → {out.name}")
    return out


def write_run_config(run_cfg: Path, pred_dir: Path, gt_path: Path) -> None:
    cfg = yaml.safe_load(BASE_CFG.read_text(encoding="utf-8"))
    ds = cfg["end2end_eval"]["dataset"]
    # path tuyệt đối (forward slash) → chạy đúng bất kể cwd
    ds["prediction"]["data_path"] = pred_dir.resolve().as_posix()
    ds["ground_truth"]["data_path"] = gt_path.resolve().as_posix()
    run_cfg.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")


def score(run_cfg: Path, log_file: Path) -> int:
    if not CONDA_PY.exists():
        print(f"[ERR] không thấy conda python: {CONDA_PY}", file=sys.stderr)
        return 1
    env = {"PYTHONUTF8": "1"}
    import os
    full_env = {**os.environ, **env}
    print(f"[score] {CONDA_PY.name} pdf_validation.py --config {run_cfg.name}")
    with log_file.open("w", encoding="utf-8") as lf:
        proc = subprocess.run(
            [str(CONDA_PY), "pdf_validation.py", "--config", str(run_cfg)],
            cwd=str(ODB_EVAL), env=full_env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace",
        )
        lf.write(proc.stdout or "")
    # in vài dòng cuối để theo dõi
    tail = "\n".join((proc.stdout or "").splitlines()[-8:])
    print(tail)
    return proc.returncode


def collect_results(run_dir: Path, prefix: str) -> Path | None:
    """Copy file result của RUN NÀY (theo prefix = tên pred dir) → run_dir/result."""
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
    """NaN/inf → None để meta.json hợp lệ (strict JSON)."""
    import math
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
                # Edit_dist→ALL_page_avg; TEDS→"all"; fallback edit_whole
                val = mv.get("ALL_page_avg", mv.get("all", mv.get("edit_whole")))
                out["overall"][f"{cat}.{mname}"] = _clean(val)
    # text_block per data_source (Edit_dist)
    tb_page = d.get("text_block", {}).get("page", {}).get("Edit_dist", {})
    for k, v in tb_page.items():
        if k.startswith("data_source:") and isinstance(v, (int, float)):
            cv = _clean(v)
            if cv is not None:
                out["by_source"][k.replace("data_source: ", "")] = cv
    return out


def write_summary_md(run_dir: Path, meta: dict) -> None:
    """Bảng tóm tắt human-readable cho loopback so sánh nhanh."""
    m = meta.get("metrics", {})
    ov = m.get("overall", {})
    gs = meta.get("generate_stats", {})
    lines = [
        f"# Eval run — {meta.get('run_id','')}",
        "",
        f"- **Solution**: {meta.get('solution')}  ·  **Engine**: {meta.get('engine')}  "
        f"·  **model**: {meta.get('model')}  ·  max_tokens={meta.get('max_tokens')}",
        f"- **Sample**: {meta.get('n_sample')} ảnh  ·  `{Path(meta.get('sample_file','')).name}`",
        f"- **Generation**: avg {gs.get('avg_latency_s')}s/ảnh · p50 {gs.get('p50_latency_s')}s "
        f"· max {gs.get('max_latency_s')}s · {gs.get('elapsed_s',0)/60:.1f} phút · lỗi {gs.get('n_error')}",
        "",
        "## Overall (Edit_dist: thấp=tốt · TEDS: cao=tốt)",
        "",
        "| Metric | Value |",
        "|---|---|",
    ]
    for k, v in ov.items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## text_block Edit_dist theo nguồn (thấp=tốt)", "",
              "| data_source | Edit_dist |", "|---|---|"]
    for k, v in sorted(m.get("by_source", {}).items(), key=lambda x: x[1]):
        lines.append(f"| {k} | {v} |")
    lines.append("")
    (run_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--solution", default="hybrid-qwen3vl")
    ap.add_argument("--sample-file", default=str(EVAL_DIR / "samples" / "sample_100.txt"))
    ap.add_argument("--base-url", default="http://localhost:1234/v1")
    ap.add_argument("--model", default="qwen/qwen3-vl-8b")
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--overwrite", action="store_true", help="ghi đè prediction trong run dir")
    ap.add_argument("--reuse-dir", action="append", default=None,
                    help="thư mục prediction để tái dùng (lặp được). Mặc định: "
                         "các run trước cùng solution + eval/predictions/end2end")
    ap.add_argument("--no-reuse", action="store_true", help="tắt tái dùng, sinh mới hết")
    ap.add_argument("--skip-generate", action="store_true", help="dùng lại prediction đã sinh")
    ap.add_argument("--skip-score", action="store_true", help="chỉ sinh, không chấm")
    args = ap.parse_args()

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    run_id = f"{stamp}_{args.solution}"
    run_dir = RUNS_DIR / run_id
    pred_dir = run_dir / "predictions"
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"=== RUN {run_id} ===")

    sample_file = Path(args.sample_file)
    names = ensure_sample(sample_file, args.n)
    images = [IMAGES_DIR / nm for nm in names]
    missing = [im.name for im in images if not im.exists()]
    if missing:
        print(f"[WARN] {len(missing)} ảnh sample không thấy trên đĩa (vd {missing[:2]})")
    images = [im for im in images if im.exists()]
    print(f"[sample] {len(images)} ảnh từ {sample_file.name}")

    # 0) tái dùng prediction từ run trước / shared dir (tiết kiệm GPU)
    reuse_seeded = 0
    if not args.no_reuse and not args.skip_generate:
        if args.reuse_dir:
            reuse_dirs = [Path(p) for p in args.reuse_dir]
        else:
            # ưu tiên run trước cùng solution (config nhất quán), rồi shared dir
            prior = sorted(
                (d / "predictions" for d in RUNS_DIR.glob(f"*_{args.solution}")
                 if (d / "predictions").is_dir() and d.name != run_id),
                reverse=True,
            )
            reuse_dirs = prior + [EVAL_DIR / "predictions" / "end2end"]
        pred_dir.mkdir(parents=True, exist_ok=True)
        for im in images:
            out = pred_dir / (im.stem + ".md")
            if out.exists():
                continue
            for rd in reuse_dirs:
                cand = rd / (im.stem + ".md")
                if cand.exists():
                    out.write_text(cand.read_text(encoding="utf-8"), encoding="utf-8")
                    reuse_seeded += 1
                    break
        print(f"[reuse] tái dùng {reuse_seeded}/{len(images)} prediction "
              f"từ {len(reuse_dirs)} thư mục → còn {len(images)-reuse_seeded} cần sinh")

    # 1) sinh prediction (phần còn thiếu)
    if not args.skip_generate:
        pipe = make_pipeline(args.base_url, args.model, args.max_tokens)
        try:
            stats = run_batch(images, pred_dir, pipe, overwrite=args.overwrite,
                              latency_out=run_dir / "latency.json")
        finally:
            pipe.close()
    else:
        stats = {"note": "skip-generate"}

    meta = {
        "run_id": run_id, "timestamp": stamp, "solution": args.solution,
        "engine": "qwen3-vl-8b@lmstudio", "model": args.model,
        "max_tokens": args.max_tokens, "n_sample": len(images),
        "sample_file": str(sample_file), "reuse_seeded": reuse_seeded,
        "generate_stats": stats,
    }

    # 2) chấm điểm (GT lọc xuống đúng sample)
    if not args.skip_score:
        gt_path = write_filtered_gt(run_dir, [im.name for im in images])
        run_cfg = run_dir / "eval_config.yaml"
        write_run_config(run_cfg, pred_dir, gt_path)
        rc = score(run_cfg, run_dir / "score.log")
        if rc != 0:
            print(f"[WARN] scorer exit code {rc} — xem {run_dir/'score.log'}")
        metric_file = collect_results(run_dir, pred_dir.name)
        if metric_file:
            summary = summarize(metric_file)
            meta["metrics"] = summary
            print("\n=== METRICS (overall) ===")
            for k, v in summary["overall"].items():
                print(f"  {k:42s} {v}")
            print("=== text_block Edit_dist theo nguồn (thấp=tốt) ===")
            for k, v in sorted(summary["by_source"].items(), key=lambda x: x[1]):
                print(f"  {k:28s} {v}")

    (run_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    if meta.get("metrics"):
        write_summary_md(run_dir, meta)
    print(f"\n[run dir] {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
