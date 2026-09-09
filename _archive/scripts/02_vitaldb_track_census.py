"""VitalDB 트랙별 케이스 수 집계 (문서 7 부록 최우선 항목).

혈역학 라벨(EV1000/Vigileo)이 실제로 몇 케이스에 붙어 있는지가
연구 규모를 결정한다. 온라인 API와 로컬 .vital 파일 두 경로를 지원.
"""
import argparse
import collections
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ppg_fm.config import ds, out_dir  # noqa: E402

# 문서 7에서 우선순위로 지목된 트랙들
KEY_TRACKS = [
    "SNUADC/PLETH", "SNUADC/ART", "SNUADC/ECG_II", "SNUADC/ECG_V5", "SNUADC/CVP",
    "Solar8000/ART_SBP", "Solar8000/ART_DBP", "Solar8000/ART_MBP",
    "Solar8000/PLETH_HR", "Solar8000/PLETH_SPO2", "Solar8000/CVP",
    "Solar8000/ETCO2", "Solar8000/RR",
    "EV1000/SVV", "EV1000/SVI", "EV1000/CI", "EV1000/CO", "EV1000/SVRI", "EV1000/PPV",
    "Vigileo/SVV", "Vigileo/CI", "Vigileo/CO", "Vigileo/SVI",
    "Vigilance/CI", "Vigilance/CO", "Vigilance/SVO2",
    "CardioQ/SV", "CardioQ/CO", "CardioQ/FTc",
    "BIS/BIS", "Primus/ETCO2", "Orchestra/PPF20_RATE", "Orchestra/RFTN20_RATE",
]


def census_online():
    """vitaldb 패키지의 온라인 트랙 목록으로 집계 (권장, 빠름)."""
    import pandas as pd
    trks = pd.read_csv("https://api.vitaldb.net/trks")
    print(f"온라인 트랙 레코드: {len(trks):,}")
    g = trks.groupby("tname")["caseid"].nunique().sort_values(ascending=False)
    return g


def census_local(root: Path, limit=None):
    """로컬 .vital 파일 헤더에서 트랙명 추출 (오프라인, 느림)."""
    import vitaldb
    files = sorted(root.glob("*.vital"))
    if limit:
        files = files[:limit]
    cnt = collections.Counter()
    for i, f in enumerate(files, 1):
        try:
            vf = vitaldb.VitalFile(str(f))
            for t in vf.get_track_names():
                cnt[t] += 1
        except Exception:
            continue
        if i % 200 == 0:
            print(f"  {i}/{len(files)} ...", flush=True)
    return cnt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["online", "local"], default="online")
    ap.add_argument("--limit", type=int, default=None, help="local 모드 파일 수 제한")
    args = ap.parse_args()

    root = Path(ds("vitaldb")["root"])
    n_files = len(list(root.glob("*.vital")))
    print(f"로컬 .vital 파일: {n_files:,}\n")

    if args.mode == "online":
        s = census_online()
        counts = {k: int(v) for k, v in s.items()}
    else:
        counts = dict(census_local(root, args.limit))

    print("=== 핵심 트랙 케이스 수 ===")
    rows = []
    for t in KEY_TRACKS:
        c = counts.get(t, 0)
        flag = "" if c else "   <-- 없음"
        print(f"  {t:28s} {c:>6,}{flag}")
        rows.append({"track": t, "n_cases": c, "priority": "key"})

    print("\n=== 전체 상위 40 ===")
    for t, c in sorted(counts.items(), key=lambda x: -x[1])[:40]:
        print(f"  {t:28s} {c:>6,}")
        if t not in KEY_TRACKS:
            rows.append({"track": t, "n_cases": c, "priority": "top"})

    out = out_dir() / "vitaldb_track_census.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["track", "n_cases", "priority"])
        w.writeheader()
        w.writerows(rows)
    print(f"\n-> {out}")

    # 핵심 판정
    svv = max(counts.get("EV1000/SVV", 0), counts.get("Vigileo/SVV", 0))
    pleth = counts.get("SNUADC/PLETH", 0)
    art = counts.get("SNUADC/ART", 0)
    print("\n=== 연구 규모 판정 ===")
    print(f"  PLETH 보유       : {pleth:,} 케이스")
    print(f"  PLETH+ART 상한   : {min(pleth, art):,} 케이스 (교집합은 별도 확인 필요)")
    print(f"  SVV 라벨 상한    : {svv:,} 케이스")


if __name__ == "__main__":
    main()
