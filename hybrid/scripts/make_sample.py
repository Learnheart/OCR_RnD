"""Tạo sample CỐ ĐỊNH, chia đều theo data_source từ OmniDocBench.json.

Sample này SHARED cho mọi solution → so sánh apples-to-apples trên cùng N ảnh.
Deterministic (không random): trong mỗi nguồn, lấy đều theo stride trên danh sách
đã sort. Apportion N theo largest-remainder.

    uv run python scripts/make_sample.py --n 100 --out ../eval/samples/sample_100.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HYBRID_DIR = Path(__file__).resolve().parent.parent
EVAL_DIR = HYBRID_DIR.parent / "eval"
GT_JSON = EVAL_DIR / "OmniDocBench_data" / "OmniDocBench.json"


def stratified_sample(gt_json: Path, n: int) -> list[str]:
    data = json.loads(gt_json.read_text(encoding="utf-8"))
    by_src: dict[str, list[str]] = defaultdict(list)
    for r in data:
        pi = r["page_info"]
        src = pi["page_attribute"]["data_source"]
        by_src[src].append(pi["image_path"])
    for src in by_src:
        by_src[src].sort()

    total = sum(len(v) for v in by_src.values())
    srcs = sorted(by_src)  # deterministic thứ tự nguồn

    # apportion theo largest-remainder, đảm bảo mỗi nguồn >=1 (nếu n đủ lớn)
    raw = {s: len(by_src[s]) / total * n for s in srcs}
    alloc = {s: int(raw[s]) for s in srcs}
    # đảm bảo nguồn nhỏ vẫn có mặt
    for s in srcs:
        if alloc[s] == 0 and len(by_src[s]) > 0:
            alloc[s] = 1
    # điều chỉnh cho khớp đúng n
    diff = n - sum(alloc.values())
    if diff > 0:  # thêm vào nguồn có remainder lớn nhất
        order = sorted(srcs, key=lambda s: raw[s] - int(raw[s]), reverse=True)
        for s in (order * (diff // len(order) + 1))[:diff]:
            alloc[s] += 1
    elif diff < 0:  # bớt ở nguồn được cấp nhiều nhất (giữ >=1)
        order = sorted(srcs, key=lambda s: alloc[s], reverse=True)
        i = 0
        while diff < 0:
            s = order[i % len(order)]
            if alloc[s] > 1:
                alloc[s] -= 1
                diff += 1
            i += 1

    picked: list[str] = []
    for s in srcs:
        items = by_src[s]
        k = min(alloc[s], len(items))
        if k <= 0:
            continue
        # lấy đều theo stride
        step = len(items) / k
        idxs = sorted({int(j * step) for j in range(k)})
        # bù nếu trùng index do làm tròn
        ii = 0
        while len(idxs) < k and ii < len(items):
            if ii not in idxs:
                idxs.append(ii)
            ii += 1
        idxs = sorted(idxs)[:k]
        picked.extend(items[j] for j in idxs)

    return sorted(picked)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--out", default=str(EVAL_DIR / "samples" / "sample_100.txt"))
    ap.add_argument("--gt", default=str(GT_JSON))
    args = ap.parse_args()

    picked = stratified_sample(Path(args.gt), args.n)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(picked) + "\n", encoding="utf-8")
    print(f"[make_sample] {len(picked)} ảnh → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
