"""S1 재추출 v2 — 전 리듬 · 환자당 10세그먼트 (문서 14).

계획표(extract_plan.csv)만 읽으므로 메모리 사용이 작다. 증분 저장 + 재개.
"""
import os, sys, time, argparse, warnings
import numpy as np, pandas as pd, wfdb
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from ppg_fm.morph.features import extract

ap = argparse.ArgumentParser()
ap.add_argument("--min-beats", type=int, default=20)
ap.add_argument("--budget", type=int, default=100000)
A = ap.parse_args()

H = os.path.expanduser("~/mnt/ppg_fm")
DATA = os.path.expanduser("~/mnt/data/mimic_iii_ext_ppg/DESTINATION")
OUT = f"{H}/data/interim/beat_features_v2.csv"

plan = pd.read_csv(f"{H}/data/interim/extract_plan.csv", dtype={"subject": str})
done = set()
if os.path.exists(OUT) and os.path.getsize(OUT) > 10:
    done = set(pd.read_csv(OUT, usecols=['subject'], dtype={'subject': str}).subject.unique())
todo = [s for s in sorted(plan.subject.unique()) if s not in done]
print(f"대상 {plan.subject.nunique()} / 완료 {len(done)} / 남은 {len(todo)}", flush=True)
if not todo:
    print("ALLDONE", flush=True); sys.exit()

G = {k: v for k, v in plan.groupby("subject", sort=False).indices.items()}
os.chdir(DATA)
first = (not os.path.exists(OUT)) or os.path.getsize(OUT) <= 10
t0 = time.time(); nseg = 0; npat = 0
for s in todo:
    if time.time() - t0 > A.budget: break
    ss = plan.iloc[G[s]]
    rows = []
    for fp, rhy, hab in zip(ss.folder_path, ss.rhythm, ss.has_abp):
        try:
            rec = wfdb.rdrecord(fp)
            i = rec.sig_name.index('PLETH')
            for f in extract(rec.p_signal[:, i], rec.fs)[0]:
                f['rhythm'] = rhy; f['has_abp'] = bool(hab)
                rows.append(f)
            nseg += 1
        except Exception:
            pass
    if len(rows) < A.min_beats: continue
    df = pd.DataFrame(rows); df.insert(0, 'subject', s)
    df.to_csv(OUT, mode='a', header=first, index=False)
    first = False; npat += 1
el = max(time.time() - t0, 1)
print(f"환자 {npat} · 세그먼트 {nseg} · {el:.0f}s ({npat/el*3600:.0f} 환자/시간)", flush=True)
