"""앙상블 평균 박동 추출 — 환자별로 박동 파형을 겹쳐 평균한 대표 파형.

각 박동을 100점으로 시간 정규화하고 진폭 min-max 정규화한 뒤 평균한다.
홀/짝 박동으로 나눈 반쪽 앙상블도 함께 저장해 재현성을 잴 수 있게 한다.
"""
import os, sys, time, argparse, warnings
import numpy as np, pandas as pd, wfdb
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from ppg_fm.morph.features import bandpass, segment_beats

ap = argparse.ArgumentParser()
ap.add_argument("--budget", type=int, default=150)
ap.add_argument("--min-beats", type=int, default=20)
A = ap.parse_args()

H = os.path.expanduser("~/mnt/ppg_fm")
DATA = os.path.expanduser("~/mnt/data/mimic_iii_ext_ppg/DESTINATION")
OUT = f"{H}/data/interim/ensemble_waves.csv"
plan = pd.read_csv(f"{H}/data/interim/extract_plan.csv", dtype={"subject": str})

done = set()
if os.path.exists(OUT) and os.path.getsize(OUT) > 10:
    done = set(pd.read_csv(OUT, usecols=["subject"], dtype={"subject": str}).subject.unique())
todo = [s for s in sorted(plan.subject.unique()) if s not in done]
print(f"대상 {plan.subject.nunique()} / 완료 {len(done)} / 남은 {len(todo)}", flush=True)
if not todo:
    print("ALLDONE", flush=True); sys.exit()

G = {k: v for k, v in plan.groupby("subject", sort=False).indices.items()}
os.chdir(DATA)
first = (not os.path.exists(OUT)) or os.path.getsize(OUT) <= 10
t0 = time.time(); npat = 0
GRID = np.linspace(0, 1, 100)
for s in todo:
    if time.time() - t0 > A.budget: break
    waves, ibis, rhys = [], [], []
    for i in G[s]:
        fp, rhy = plan.folder_path.iat[i], plan.rhythm.iat[i]
        try:
            rec = wfdb.rdrecord(fp)
            ix = rec.sig_name.index('PLETH')
            sig = rec.p_signal[:, ix]; fs = rec.fs
            x = bandpass(sig, fs)
            if x.std() < 1e-9: continue
            z0 = (x - x.mean()) / x.std()
            for on, sp, on2 in segment_beats(z0, fs):
                seg = x[on:on2]; rng = np.ptp(seg)
                if len(seg) < 8 or rng < 1e-9: continue
                w = np.interp(GRID, np.linspace(0, 1, len(seg)), (seg - seg.min()) / rng)
                waves.append(w); ibis.append(len(seg) / fs * 1000.0); rhys.append(rhy)
        except Exception:
            pass
    if len(waves) < A.min_beats: continue
    W = np.asarray(waves, dtype=np.float32); IB = np.asarray(ibis)
    sr = np.asarray([r == "SR" for r in rhys])
    rows = {"all": W.mean(0), "odd": W[1::2].mean(0), "even": W[0::2].mean(0),
            "sr": (W[sr].mean(0) if sr.sum() >= A.min_beats else np.full(100, np.nan, np.float32))}
    buf = []
    for k, v in rows.items():
        buf.append([s, k, float(np.median(IB)), int(len(W)), float(sr.mean())] + [round(float(x), 5) for x in v])
    df = pd.DataFrame(buf, columns=["subject","kind","med_ibi","n_beats","sr_frac"]+[f"v{i}" for i in range(100)])
    df.to_csv(OUT, mode="a", header=first, index=False); first = False
    npat += 1
el = max(time.time() - t0, 1)
print(f"환자 {npat} · {el:.0f}s ({npat/el*3600:.0f}/시간)", flush=True)
