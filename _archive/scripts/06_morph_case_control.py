"""I35(대동맥판막) vs 연령매칭 대조군 — 박동 단위 형태학 전 특징 분석.

분석 단위를 명시적으로 분리한다.
  박동 단위 : 분포·변동성 기술 (통계적 추론에 쓰지 않음)
  환자 단위 : 중앙값/IQR 로 요약 후 추론 (연령·심박수 보정)
결과는 환자별 CSV 로 증분 저장하므로 중단되어도 이어서 쓸 수 있다.
"""
import os, sys, warnings, argparse
import numpy as np, pandas as pd, wfdb
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ppg_fm.morph.features import extract, FEATURE_NAMES

AP = argparse.ArgumentParser()
AP.add_argument("--n-seg", type=int, default=4, help="환자당 세그먼트 수")
AP.add_argument("--out", default=None)
A = AP.parse_args()

HOME = os.path.expanduser("~/mnt/ppg_fm")
IDX  = f"{HOME}/data/interim/seg_index.parquet"
OUT  = A.out or f"{HOME}/data/interim/beat_features.csv"
DATA = os.path.expanduser("~/mnt/data/mimic_iii_ext_ppg/DESTINATION")

d = pd.read_parquet(IDX)
h = d[d.hq & (d.rhythm == 'SR')]
case, pool = h[h.I35], h[~h.cardiac]
cp = case.groupby('subject').agg(age=('age','first')).dropna()
pp = pool.groupby('subject').agg(age=('age','first')).dropna()
used, pairs = set(), []
for s, a in cp.age.items():
    cand = pp[(pp.age.sub(a).abs() <= 3) & (~pp.index.isin(used))]
    take = list(cand.index[:2]); used.update(take)
    pairs += [(s,'case',a)] + [(t,'ctrl',pp.age[t]) for t in take]
mt = pd.DataFrame(pairs, columns=['subject','grp','age'])
src = pd.concat([case, pool])

done = set()
if os.path.exists(OUT):
    done = set(pd.read_csv(OUT, usecols=['subject']).subject.astype(str))
    print(f"기존 결과 {len(done)}명 이어서 진행")

os.chdir(DATA)
first = not os.path.exists(OUT)
for k, (_, r) in enumerate(mt.iterrows(), 1):
    if str(r.subject) in done: continue
    segs = src[src.subject == r.subject]
    segs = segs.sample(min(A.n_seg, len(segs)), random_state=1)
    rows = []
    for fp in segs.folder_path:
        try:
            rec = wfdb.rdrecord(fp); i = rec.sig_name.index('PLETH')
            F, _ = extract(rec.p_signal[:, i], rec.fs)
            rows += F
        except Exception:
            pass
    if len(rows) < 20: continue
    df = pd.DataFrame(rows)
    df.insert(0, 'subject', r.subject); df.insert(1, 'grp', r.grp); df.insert(2, 'age', r.age)
    df.to_csv(OUT, mode='a', header=first, index=False); first = False
    if k % 40 == 0: print(f"  {k}/{len(mt)} ...", flush=True)
print(f"-> {OUT}")
