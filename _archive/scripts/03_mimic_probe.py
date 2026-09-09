"""MIMIC-III-Ext-PPG 로드 테스트 + 질환/품질 라벨 프로파일.

1) WFDB 세그먼트 실제 로드 검증 (채널/샘플링/길이)
2) ICD-10 코드별 환자 수 -> reports/mimic_icd_census.csv
3) SQI 분포 -> reports/mimic_sqi_profile.csv
"""
import argparse
import ast
import collections
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ppg_fm.config import ds, out_dir  # noqa: E402

# 문서 7에서 지목된 관심 질환 (심혈관/혈역학 축)
FOCUS = {
    "I35": "대동맥판막 장애", "I34": "승모판 장애", "I50": "심부전",
    "I48": "심방세동·조동", "I25": "만성 허혈성심질환", "I21": "급성 심근경색",
    "I95": "저혈압", "I27": "폐성심·폐순환질환", "R57": "쇼크",
    "I46": "심정지", "I26": "폐색전증", "I49": "기타 부정맥",
    "I10": "본태성 고혈압", "N17": "급성 신부전", "J96": "호흡부전",
}


def probe_waveform(root: Path, n=3):
    import wfdb
    recs_file = root / "RECORDS"
    if not recs_file.exists():
        print("  ! RECORDS 없음")
        return
    with open(recs_file) as f:
        recs = [ln.strip() for ln in f if ln.strip()][:n]
    for r in recs:
        p = root / r
        try:
            rec = wfdb.rdrecord(str(p).replace(".hea", "").replace(".dat", ""))
            print(f"  {r}")
            print(f"    signals : {rec.sig_name}")
            print(f"    fs      : {rec.fs} Hz")
            print(f"    length  : {rec.sig_len} samples ({rec.sig_len/rec.fs:.1f}s)")
            print(f"    units   : {rec.units}")
        except Exception as e:
            print(f"  {r}  -> 로드 실패: {type(e).__name__}: {e}")


def profile_metadata(meta_path: Path):
    pat_icd, pat_demo = {}, {}
    seg_per_pat = collections.Counter()
    rhythm = collections.Counter()
    sqi_bins = collections.Counter()
    n = 0
    with open(meta_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            n += 1
            s = row["subject_id"]
            seg_per_pat[s] += 1
            rhythm[row.get("event_rhythm", "")] += 1
            if s not in pat_icd:
                try:
                    pat_icd[s] = set(ast.literal_eval(row.get("icd10_truncated", "[]")))
                except Exception:
                    pat_icd[s] = set()
                pat_demo[s] = (row.get("age", ""), row.get("gender", ""))
            # pleth SQI (10초 벡터의 첫 값으로 근사)
            v = row.get("vector_10s_pleth_sqi", "")
            try:
                val = float(ast.literal_eval(v)[0]) if v.startswith("[") else float(v)
                sqi_bins[round(val, 1)] += 1
            except Exception:
                pass
    return n, pat_icd, seg_per_pat, rhythm, sqi_bins


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-waveform", action="store_true")
    args = ap.parse_args()

    cfg = ds("mimic_ext_ppg")
    root, meta = Path(cfg["root"]), Path(cfg["metadata"])

    if not args.skip_waveform:
        print("=== [1] WFDB 세그먼트 로드 테스트 ===")
        probe_waveform(root)

    print("\n=== [2] 메타데이터 프로파일 ===")
    n, pat_icd, seg_per_pat, rhythm, sqi = profile_metadata(meta)
    N = len(pat_icd)
    print(f"  총 세그먼트 : {n:,}")
    print(f"  고유 환자   : {N:,}")
    print(f"  환자당 세그먼트 중앙값 : {sorted(seg_per_pat.values())[N//2]:,}")

    cnt = collections.Counter()
    for codes in pat_icd.values():
        for c in codes:
            cnt[c] += 1

    print(f"\n  고유 ICD-10 코드 : {len(cnt):,}")
    for thr in (200, 100, 50, 20):
        print(f"    환자 >={thr:3d}명 코드 수 : {sum(1 for v in cnt.values() if v >= thr)}")

    print("\n=== [3] 관심 질환 (문서 7 축) ===")
    rows = []
    for code, ko in FOCUS.items():
        v = cnt.get(code, 0)
        print(f"  {code:5s} {ko:16s} {v:>5,}명 ({100*v/N:5.1f}%)")
    for code, v in cnt.most_common():
        rows.append({"icd10": code, "n_patients": v,
                     "pct": round(100 * v / N, 2),
                     "label_ko": FOCUS.get(code, "")})

    out = out_dir() / "mimic_icd_census.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["icd10", "n_patients", "pct", "label_ko"])
        w.writeheader()
        w.writerows(rows)
    print(f"\n-> {out}")

    out2 = out_dir() / "mimic_rhythm_sqi.csv"
    with open(out2, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["kind", "value", "count"])
        for k, v in rhythm.most_common():
            w.writerow(["rhythm", k, v])
        for k, v in sorted(sqi.items()):
            w.writerow(["pleth_sqi_bin", k, v])
    print(f"-> {out2}")


if __name__ == "__main__":
    main()
