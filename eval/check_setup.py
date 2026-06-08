#!/usr/bin/env python
"""
Kiểm tra setup ground-truth OmniDocBench và độ phủ prediction.

Cách dùng:
    python check_setup.py                 # kiểm tra GT + thống kê
    python check_setup.py --preds end2end # kiểm tra thêm độ phủ predictions/end2end
    python check_setup.py --list-todo end2end > todo.txt  # liệt kê ảnh CHƯA có prediction

Quy ước prediction: mỗi trang 1 file .md, TÊN = tên ảnh đổi đuôi sang .md
    ảnh  images/page-xxx.png   ->   prediction  page-xxx.md
"""
import argparse
import json
import os
import sys
from collections import Counter

# Console Windows mặc định cp1252 không in được tiếng Việt -> ép UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
GT_JSON = os.path.join(HERE, "OmniDocBench_data", "OmniDocBench.json")
IMG_DIR = os.path.join(HERE, "OmniDocBench_data", "images")
PRED_ROOT = os.path.join(HERE, "predictions")


def load_gt():
    if not os.path.exists(GT_JSON):
        sys.exit(f"[X] Không thấy ground truth: {GT_JSON}\n    -> chạy lệnh download trong README trước.")
    with open(GT_JSON, encoding="utf-8") as f:
        return json.load(f)


def check_gt(d):
    gt_imgs = [p["page_info"]["image_path"] for p in d]
    have = set(os.listdir(IMG_DIR)) if os.path.isdir(IMG_DIR) else set()
    missing = [i for i in gt_imgs if i not in have]
    print("=== GROUND TRUTH ===")
    print(f"  Trang trong JSON : {len(gt_imgs)}")
    print(f"  Ảnh có trên đĩa  : {len(have)}")
    print(f"  Ảnh THIẾU        : {len(missing)}")
    if missing:
        print(f"  [!] Thiếu {len(missing)} ảnh — chạy lại bước download. Ví dụ thiếu: {missing[:3]}")
    else:
        print("  [OK] Ground truth đầy đủ.")

    langs = Counter(p["page_info"].get("page_attribute", {}).get("language") for p in d)
    srcs = Counter(p["page_info"].get("page_attribute", {}).get("data_source") for p in d)
    print("\n  Theo ngôn ngữ :", dict(langs))
    print("  Theo nguồn    :", dict(srcs.most_common()))
    return gt_imgs, missing


def check_preds(d, subset):
    pred_dir = os.path.join(PRED_ROOT, subset)
    print(f"\n=== PREDICTIONS: predictions/{subset} ===")
    if not os.path.isdir(pred_dir):
        print(f"  [X] Chưa có thư mục {pred_dir}")
        return
    gt_stems = {os.path.splitext(p["page_info"]["image_path"])[0] for p in d}
    pred_stems = {os.path.splitext(f)[0] for f in os.listdir(pred_dir) if f.endswith(".md")}
    covered = gt_stems & pred_stems
    missing = gt_stems - pred_stems
    orphan = pred_stems - gt_stems
    print(f"  Đã có prediction : {len(covered)}/{len(gt_stems)} trang ({100*len(covered)/len(gt_stems):.1f}%)")
    print(f"  CHƯA xử lý       : {len(missing)} trang")
    if orphan:
        print(f"  [!] {len(orphan)} file .md không khớp ảnh GT (sai tên?): {list(orphan)[:3]}")
    if not missing:
        print("  [OK] Đủ prediction cho toàn bộ GT — sẵn sàng chấm điểm.")


def list_todo(d, subset):
    pred_dir = os.path.join(PRED_ROOT, subset)
    pred_stems = set()
    if os.path.isdir(pred_dir):
        pred_stems = {os.path.splitext(f)[0] for f in os.listdir(pred_dir) if f.endswith(".md")}
    for p in d:
        img = p["page_info"]["image_path"]
        if os.path.splitext(img)[0] not in pred_stems:
            print(os.path.join(IMG_DIR, img))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", help="tên subset trong predictions/ để kiểm tra độ phủ, vd: end2end")
    ap.add_argument("--list-todo", help="in ra đường dẫn ảnh CHƯA có prediction (cho subset này)")
    args = ap.parse_args()

    d = load_gt()
    if args.list_todo:
        list_todo(d, args.list_todo)
    else:
        check_gt(d)
        if args.preds:
            check_preds(d, args.preds)
