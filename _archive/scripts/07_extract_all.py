"""전체 코호트 박동 단위 형태학 특징 추출 (phenome-wide 분석용).

고품질 + 정상동율동 세그먼트를 환자당 N개 샘플링해 특징을 뽑고
환자별로 CSV 에 증분 저장한다. 중단되어도 이어서 실행된다.
"""
import os, sys, argparse, warnings
import numpy as np, pandas as pd, wfdb
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from ppg_fm.morph.features import extract

ap = argparse.ArgumentParser()
ap.add_argument("--n-seg", type=int, default=4)
ap.add_argument("--min-beats", type=int, default=20)
A = ap.parse_args()

HOME = os.path.expanduser("~/mnt/ppg_fm")
DATA = os.path.expanduser("~/mnt/data/mimic_iii_ext_ppg/DESTINATION")
OUT  = f"{HOME}/data/interim/beat_features_all.csv"

d = pd.read_parquet(f"{HOME}/data/interim/seg_index.parquet")
d['subject'] = d.subject.astype(str)
h = d[d.hq & (d.rhythm == 'SR')]
subs = sorted(h.subject.unique())

done = set()
if os.path.exists(OUT):
    done = set(pd.read_csv(OUT, usecols=['subject'], dtype={'subject': str}).subject.unique())
print(f"대상 환자 {len(subs)} / 완료 {len(done)} / 남은 {len(subs)-len(done)}", flush=True)

os.chdir(DATA)
first = not os.path.exists(OUT)
for k, s in enumerate(subs, 1):
    if s in done: continue
    ss = h[h.subject == s]
    segs = ss.sample(min(A.n_seg, len(ss)), random_state=1)
    rows = []
    for fp in segs.folder_path:
        try:
            rec = wfdb.rdrecord(fp)
            i = rec.sig_name.index('PLETH')
            rows += extract(rec.p_signal[:, i], rec.fs)[0]
        except Exception:
            pass
    if len(rows) < A.min_beats: continue
    df = pd.DataFrame(rows)
    df.insert(0, 'subject', s)
    df.to_csv(OUT, mode='a', header=first, index=False)
    first = False
    if k % 100 == 0: print(f"  {k}/{len(subs)}", flush=True)
print("완료", flush=True)
