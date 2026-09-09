"""D:/data 전수 스캔 -> reports/inventory.csv

각 최상위 폴더의 파일 수/총 용량/확장자 분포를 집계한다.
용량 집계는 오래 걸릴 수 있어 --quick 으로 건너뛸 수 있다.
"""
import argparse
import collections
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ppg_fm.config import load, out_dir  # noqa: E402


def scan(root: Path, quick: bool = False):
    n_files = 0
    total = 0
    ext = collections.Counter()
    for p in root.rglob("*"):
        try:
            if p.is_file():
                n_files += 1
                ext[p.suffix.lower() or "<none>"] += 1
                if not quick:
                    total += p.stat().st_size
        except OSError:
            continue
    return n_files, total, ext


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="용량 집계 생략")
    args = ap.parse_args()

    cfg = load()
    root = Path(cfg["data_root"])
    rows = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        n, size, ext = scan(child, args.quick)
        top = ", ".join(f"{k}:{v}" for k, v in ext.most_common(5))
        rows.append({
            "folder": child.name,
            "n_files": n,
            "size_gb": round(size / 1e9, 2) if not args.quick else "",
            "top_ext": top,
        })
        print(f"{child.name:60s} files={n:>9,}  {rows[-1]['size_gb']} GB")

    out = out_dir() / "inventory.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
