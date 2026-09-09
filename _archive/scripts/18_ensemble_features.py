"""앙상블 파형에서 43개 중 형태 특징 계산.

100점 시간정규화 파형을 환자의 중앙 IBI에 맞춰 원래 표본화 격자로 되돌린 뒤
기존 beat_features 를 그대로 적용한다.
"""
import os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from ppg_fm.morph.features import beat_features, FEATURE_NAMES
from scipy.signal import find_peaks

H = os.path.expanduser("~/mnt/ppg_fm")
FS = 125.0
E = pd.read_csv(f"{H}/data/interim/ensemble_waves.csv", dtype={"subject": str})
V = [f"v{i}" for i in range(100)]

def feats_from_wave(w, med_ibi):
    n = max(16, int(round(med_ibi * FS / 1000.0)))
    x = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, 100), w)
    pk, _ = find_peaks(x, prominence=0.2)
    sp = int(pk[0]) if len(pk) else int(np.argmax(x))
    if not (0 < sp < n - 1): return None
    return beat_features(x, FS, 0, sp, n)

out = []
for kind in ["all", "sr", "odd", "even"]:
    sub = E[E.kind == kind]
    for r in sub.itertuples(index=False):
        w = np.array([getattr(r, v) for v in V], dtype=float)
        if np.isnan(w).any(): continue
        f = feats_from_wave(w, r.med_ibi)
        if f is None: continue
        f = {k: f[k] for k in FEATURE_NAMES}
        f.update(subject=r.subject, kind=kind, HR=60000.0 / r.med_ibi,
                 n_beats=r.n_beats, sr_frac=r.sr_frac)
        out.append(f)
F = pd.DataFrame(out)
F.to_csv(f"{H}/data/interim/ensemble_features.csv", index=False)
print("환자×종류", F.shape)
for k in ["all", "sr", "odd", "even"]:
    g = F[F.kind == k]
    print(f"  {k:5s} {len(g):5d}명 · notch검출 {g.LVET.notna().mean():.3f} · c/d검출 {g.d_over_a.notna().mean():.3f} · RI검출 {g.RI.notna().mean():.3f}")
