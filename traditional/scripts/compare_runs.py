"""Side-by-side comparison: traditional vs hybrid on OmniDocBench sample_100.

Reads the latest `meta.json` of each solution's runs and prints + writes a
comparison table to `results/comparison.md`.

    %USERPROFILE%\.conda\envs\ocr-worker\python.exe scripts/compare_runs.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TRAD_DIR = Path(__file__).resolve().parent.parent
RND = TRAD_DIR.parent

# (label, runs_glob_dir, run_suffix)
SOLUTIONS = [
    ("traditional (PP-OCRv4)", TRAD_DIR / "results" / "runs", "*_traditional-ocr"),
    ("hybrid (Qwen3-VL)", RND / "hybrid" / "results" / "runs", "*_hybrid-qwen3vl"),
]

# (key in overall, label, direction) — direction: "down" good low, "up" good high
METRICS = [
    ("text_block.Edit_dist", "text_block Edit_dist", "down"),
    ("display_formula.Edit_dist", "display_formula Edit_dist", "down"),
    ("table.TEDS", "table TEDS", "up"),
    ("table.TEDS_structure_only", "table TEDS_structure_only", "up"),
    ("table.Edit_dist", "table Edit_dist", "down"),
    ("reading_order.Edit_dist", "reading_order Edit_dist", "down"),
]


def latest_meta(runs_dir: Path, suffix: str) -> dict | None:
    if not runs_dir.exists():
        return None
    runs = sorted(runs_dir.glob(suffix), reverse=True)
    for r in runs:
        meta = r / "meta.json"
        if meta.exists():
            d = json.loads(meta.read_text(encoding="utf-8"))
            if d.get("metrics"):
                return d
    return None


def fmt(v) -> str:
    if v is None:
        return "–"
    return f"{v:.3f}" if isinstance(v, (int, float)) else str(v)


def winner(vals: list, direction: str) -> int | None:
    nums = [(i, v) for i, v in enumerate(vals) if isinstance(v, (int, float))]
    if len(nums) < 2:
        return None
    key = min if direction == "down" else max
    return key(nums, key=lambda t: t[1])[0]


def main() -> int:
    metas = [latest_meta(d, s) for _, d, s in SOLUTIONS]
    labels = [lbl for lbl, _, _ in SOLUTIONS]
    if not any(metas):
        print("No runs with metrics found.")
        return 1

    lines = [
        "# Comparison — traditional vs hybrid (OmniDocBench sample_100)",
        "",
        "| metric | dir | "
        + " | ".join(labels)
        + " | winner |",
        "|---|---|" + "---|" * (len(labels) + 1),
    ]
    for key, label, direction in METRICS:
        vals = [
            (m.get("metrics", {}).get("overall", {}).get(key) if m else None)
            for m in metas
        ]
        w = winner(vals, direction)
        arrow = "↓" if direction == "down" else "↑"
        win_lbl = labels[w] if w is not None else "–"
        row = (
            f"| {label} | {arrow} | "
            + " | ".join(
                (f"**{fmt(v)}**" if i == w else fmt(v)) for i, v in enumerate(vals)
            )
            + f" | {win_lbl} |"
        )
        lines.append(row)

    # latency row
    lat = [
        (m.get("generate_stats", {}).get("avg_latency_s") if m else None)
        for m in metas
    ]
    w = winner(lat, "down")
    lines.append(
        "| latency (s/img) | ↓ | "
        + " | ".join((f"**{fmt(v)}**" if i == w else fmt(v)) for i, v in enumerate(lat))
        + f" | {labels[w] if w is not None else '–'} |"
    )

    out = "\n".join(lines) + "\n"
    (TRAD_DIR / "results" / "comparison.md").write_text(out, encoding="utf-8")
    print(out)
    print(f"[written] {TRAD_DIR / 'results' / 'comparison.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
