"""Tái tóm tắt 1 run đã có (không cần chấm lại) → cập nhật meta.json + summary.md.

Dùng khi sửa logic summarize hoặc muốn xem lại run cũ.

    uv run python scripts/resummarize.py results/runs/<run_id>
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

HYBRID_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HYBRID_DIR / "scripts"))

from eval_run import summarize, write_summary_md  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: resummarize.py <run_dir>", file=sys.stderr)
        return 2
    run_dir = Path(sys.argv[1])
    result_dir = run_dir / "result"
    metric = next(result_dir.glob("*metric_result.json"), None)
    if metric is None:
        print(f"[ERR] không thấy metric_result.json trong {result_dir}", file=sys.stderr)
        return 1

    meta_path = run_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta["metrics"] = summarize(metric)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    write_summary_md(run_dir, meta)

    print(f"=== {run_dir.name} — overall ===")
    for k, v in meta["metrics"]["overall"].items():
        print(f"  {k:42s} {v}")
    print("=== text_block theo nguồn (thấp=tốt) ===")
    for k, v in sorted(meta["metrics"]["by_source"].items(), key=lambda x: x[1]):
        print(f"  {k:24s} {v}")
    print(f"[updated] {run_dir/'summary.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
