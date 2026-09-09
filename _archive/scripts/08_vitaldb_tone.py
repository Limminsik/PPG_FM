"""VitalDB — PPG의 c-d파 검출률이 동맥압 기반 혈관 긴장도를 추적하는가.

기준(gold standard): 동맥압 이완기의 지수 감쇠 시상수 tau = R x C.
Windkessel 모형에서 tau 는 전신혈관저항과 직결되는 물리량이며,
혈관수축 -> tau 증가, 혈관확장 -> tau 감소.

설계: 환자 내(within-patient) 시간에 따른 공변동을 본다.
      수술 중에는 마취(혈관확장)와 승압제(수축)로 긴장도가 크게 변하므로
      한 환자 안에서 자연 실험이 성립한다.
"""
import os, sys, json, glob, warnings, argparse
import numpy as np, pandas as pd, vitaldb
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from ppg_fm.morph.features import extract, bandpass
from scipy.signal import find_peaks

FS = 500
WIN = 60          # 초 단위 창
HOME = os.path.expanduser("~/mnt/ppg_fm")
OUT = f"{HOME}/data/interim/vitaldb_tone.csv"


def art_tone(ar, fs=FS):
    """동맥압 창에서 tau(이완기 감쇠 시상수, ms) 와 보조 지표."""
    ar = ar[np.isfinite(ar)]
    if len(ar) < fs * 5:
        return None
    if not (30 < np.median(ar) < 140):        # 생리 범위 밖 = 아티팩트
        return None
    pk, _ = find_peaks(ar, distance=int(0.4 * fs), prominence=8)
    if len(pk) < 5:
        return None
    taus, notch_h, pps = [], [], []
    for i in range(len(pk) - 1):
        p0, p1 = pk[i], pk[i + 1]
        beat = ar[p0:p1]
        if len(beat) < int(0.35 * fs) or len(beat) > int(1.8 * fs):
            continue
        # dicrotic notch = 수축기 피크 이후 1차 미분의 첫 국소최대
        d1 = np.gradient(beat)
        cand, _ = find_peaks(d1[int(0.12 * fs):int(0.55 * fs)])
        if len(cand) == 0:
            continue
        nz = int(0.12 * fs) + int(cand[0])
        dia = beat[nz:]
        if len(dia) < int(0.15 * fs):
            continue
        # 이완기 지수 감쇠 적합: log(P - Pinf) ~ -t/tau
        pinf = min(beat.min() - 5.0, 0.0)
        y = dia - pinf
        if np.any(y <= 0):
            continue
        t = np.arange(len(dia)) / fs
        try:
            slope = np.polyfit(t, np.log(y), 1)[0]
        except Exception:
            continue
        if slope >= 0:
            continue
        tau = -1.0 / slope * 1000.0
        if not (100 < tau < 4000):
            continue
        taus.append(tau)
        notch_h.append((beat[nz] - beat.min()) / (np.ptp(beat) + 1e-9))
        pps.append(np.ptp(beat))
    if len(taus) < 4:
        return None
    return dict(tau=float(np.median(taus)),
                art_notch=float(np.median(notch_h)),
                pp=float(np.median(pps)),
                map_=float(np.median(ar)),
                n_art_beats=len(taus))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=40)
    ap.add_argument("--max-win", type=int, default=25, help="케이스당 최대 창 수")
    A = ap.parse_args()

    trk = json.load(open(f"{HOME}/data/interim/vitaldb_tracks_sample.json"))
    both = [f for f, ts in trk.items()
            if "SNUADC/PLETH" in ts and "SNUADC/ART" in ts]
    done = set()
    if os.path.exists(OUT):
        done = set(pd.read_csv(OUT, usecols=["case"]).case.astype(str))
    todo = [f for f in both if f.split(".")[0] not in done][:A.cases]
    print(f"PLETH+ART 케이스 {len(both)} / 완료 {len(done)} / 이번 {len(todo)}", flush=True)

    os.chdir(os.path.expanduser("~/mnt/data/VitalDB/vitaldb_dataset"))
    first = not os.path.exists(OUT)
    for f in todo:
        cid = f.split(".")[0]
        try:
            v = np.asarray(vitaldb.vital_recs(
                f, track_names=["SNUADC/PLETH", "SNUADC/ART"], interval=1 / FS), dtype=float)
        except Exception:
            continue
        pl, ar = v[:, 0], v[:, 1]
        n_win = len(pl) // (WIN * FS)
        step = max(1, n_win // A.max_win)
        rows = []
        for w in range(0, n_win, step):
            s = w * WIN * FS
            wp, wa = pl[s:s + WIN * FS], ar[s:s + WIN * FS]
            if np.isfinite(wp).mean() < .9 or np.isfinite(wa).mean() < .9:
                continue
            tone = art_tone(wa)
            if tone is None:
                continue
            F, _ = extract(np.nan_to_num(wp), FS)
            if len(F) < 25:
                continue
            d = pd.DataFrame(F)
            rows.append(dict(case=cid, t_min=s / FS / 60,
                             cd_rate=d.d_over_a.notna().mean(),
                             ri_rate=d.RI.notna().mean(),
                             CT_over_LVET=d.CT_over_LVET.median(),
                             notch_rel_height=d.notch_rel_height.median(),
                             IPA=d.IPA.median(),
                             e_over_a=d.e_over_a.median(),
                             b_over_a=d.b_over_a.median(),
                             HR=60000 / d.IBI.median(),
                             n_beats=len(d), **tone))
        if len(rows) >= 5:
            pd.DataFrame(rows).to_csv(OUT, mode="a", header=first, index=False)
            first = False
            print(f"  case {cid}: 창 {len(rows)}", flush=True)
    print("완료", flush=True)


if __name__ == "__main__":
    main()
