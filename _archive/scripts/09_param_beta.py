"""대역통과 상한을 바꿔가며 질환 연관 계수(beta)가 유지되는지 검증."""
import os, sys, argparse, warnings
import numpy as np, pandas as pd, wfdb
warnings.filterwarnings("ignore")
from scipy.signal import butter, filtfilt, find_peaks, savgol_filter

HOME = os.path.expanduser("~/mnt/ppg_fm")
DATA = os.path.expanduser("~/mnt/data/mimic_iii_ext_ppg/DESTINATION")
OUT  = f"{HOME}/data/interim/param_beta_feats.csv"
CUTS = [8, 12, 20]

def beats(sig, fs, hi):
    b, a = butter(4, [0.5/(fs/2), hi/(fs/2)], btype="band")
    x = filtfilt(b, a, np.nan_to_num(sig))
    if x.std() < 1e-9: return []
    z = (x - x.mean()) / x.std()
    pk, _ = find_peaks(z, distance=int(.4*fs), prominence=.4)
    w = max(5, int(.03*fs) | 1); out = []
    for i in range(len(pk)-1):
        p0, p1 = pk[i], pk[i+1]
        lo = max(0, p0-int(.45*fs)); on = lo+int(np.argmin(z[lo:p0])) if p0 > lo else p0
        n2 = max(0, p1-int(.45*fs)); on2 = n2+int(np.argmin(z[n2:p1])) if p1 > n2 else p1
        seg = x[on:on2]
        if not (int(.4*fs) <= len(seg) <= int(1.8*fs)) or np.ptp(seg) < 1e-9: continue
        s = (seg-seg.min())/np.ptp(seg); n = len(s); sp = p0-on
        if not (0 < sp < n-1) or n <= w+2: continue
        d2 = savgol_filter(s, w, 3, deriv=2)
        A = int(np.argmax(d2[:max(sp, 2)]))
        if A+2 >= n: continue
        wh = min(n, A+1+max(3, int(.6*n)))
        if wh-(A+1) < 2: continue
        Bi = A+1+int(np.argmin(d2[A+1:wh]))
        if Bi+2 >= n: continue
        tail = d2[Bi+1:n]; p, _ = find_peaks(tail)
        if len(p) == 0: continue
        E = Bi+1+int(p[np.argmax(tail[p])])
        cd = False
        if E-Bi >= 6:
            mid = d2[Bi+1:E]; cm, _ = find_peaks(mid); dm, _ = find_peaks(-mid)
            if len(cm) and len(dm):
                ci = Bi+1+int(cm[np.argmax(mid[cm])])
                if [k for k in dm if Bi+1+k > ci]: cd = True
        out.append((cd, sp/fs*1000, E/fs*1000, float(d2[Bi]/(d2[A]+1e-12)), len(s)/fs*1000))
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=250)
    ap.add_argument("--seg", type=int, default=2); A = ap.parse_args()
    idx = pd.read_parquet(f"{HOME}/data/interim/seg_index.parquet")
    idx["subject"] = idx.subject.astype(str)
    h = idx[idx.hq & (idx.rhythm == "SR")]
    P = pd.read_csv(f"{HOME}/data/interim/patient_features_all.csv", dtype={"subject": str})
    subs = P.subject.tolist()
    done = set()
    if os.path.exists(OUT):
        done = set(pd.read_csv(OUT, usecols=["subject"], dtype={"subject": str}).subject)
    todo = [s for s in subs if s not in done][:A.n]
    print(f"대상 {len(subs)} / 완료 {len(done)} / 이번 {len(todo)}", flush=True)
    os.chdir(DATA); first = not os.path.exists(OUT)
    for k, s in enumerate(todo, 1):
        ss = h[h.subject == s]
        if not len(ss): continue
        sigs = []
        for fp in ss.sample(min(A.seg, len(ss)), random_state=1).folder_path:
            try:
                rec = wfdb.rdrecord(fp)
                sigs.append((rec.p_signal[:, rec.sig_name.index("PLETH")], rec.fs))
            except Exception: pass
        row = {"subject": s}
        ok = True
        for hi in CUTS:
            B = []
            for sig, fs in sigs: B += beats(sig, fs, hi)
            if len(B) < 20: ok = False; break
            D = pd.DataFrame(B, columns=["cd", "ct", "lvet", "ba", "ibi"])
            row[f"cd_{hi}"] = D.cd.mean()
            row[f"ctlvet_{hi}"] = (D.ct/D.lvet).median()
            row[f"ba_{hi}"] = D.ba.median()
            row[f"ct_{hi}"] = D.ct.median()
        if not ok: continue
        pd.DataFrame([row]).to_csv(OUT, mode="a", header=first, index=False); first = False
        if k % 60 == 0: print(f"  {k}/{len(todo)}", flush=True)
    print("완료", flush=True)

if __name__ == "__main__": main()
