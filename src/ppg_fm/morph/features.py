"""PPG 박동 단위 형태학 특징 추출.

설계 원칙 (문서 0 §4):
  PPG는 절대 스케일을 잃고, 타이밍과 정규화된 형태를 보존한다.
  -> 모든 특징은 **스케일 불변**(시간, 비율, 정규화 진폭)으로만 정의한다.
     절대 진폭은 접촉압·피부색·기기에 좌우되므로 특징으로 쓰지 않는다.

특징 계열
  timing   : CT, LVET(notch까지), CT/LVET(=AT/ET 대응), dT, 폭(25/50/75%)
  ratio    : RI(반사지수), IPA(면적비), notch 상대높이
  deriv1   : 최대 상승기울기(정규화), 상승기울기 시점비
  deriv2   : APG a~e파 -> b/a, c/a, d/a, e/a, aging index
  quality  : notch 검출 여부 (질병에 의한 소실 vs 잡음 — 문서 7 §4-2)

참조: Elgendi 2012, Takazawa 1998, Charlton PPG chapter, pyPPG(Physiol Meas 2024)
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt, find_peaks, savgol_filter

_trapz = getattr(np, "trapezoid", None) or np.trapz   # numpy 1.x / 2.x 호환

FEATURE_NAMES = [
    # --- timing (ms 또는 무차원) ---
    "IBI", "CT", "LVET", "CT_over_LVET", "CT_over_IBI", "LVET_over_IBI", "dT",
    "W25", "W50", "W75", "W50_over_IBI",
    # --- 정규화 진폭비 ---
    "RI", "notch_rel_height", "IPA",
    # --- 1차 미분 ---
    "max_slope_norm", "t_max_slope_rel",
    # --- 2차 미분 (APG) ---
    "b_over_a", "c_over_a", "d_over_a", "e_over_a", "aging_index",
    # --- 품질/검출 ---
    "notch_found", "apg_found",
]


def bandpass(x, fs, lo=0.5, hi=8.0, order=4):
    b, a = butter(order, [lo / (fs / 2), hi / (fs / 2)], btype="band")
    return filtfilt(b, a, np.nan_to_num(x))


def segment_beats(x, fs, prominence=0.4, min_bpm=33, max_bpm=150):
    """정규화 신호에서 onset-to-onset 박동 경계를 찾는다.

    Returns: list of (onset, peak, next_onset)
    """
    pk, _ = find_peaks(x, distance=int(60 / max_bpm * fs), prominence=prominence)
    out = []
    for i in range(len(pk) - 1):
        p0, p1 = pk[i], pk[i + 1]
        lo = max(0, p0 - int(0.45 * fs))
        on = lo + int(np.argmin(x[lo:p0])) if p0 > lo else p0
        n2 = max(0, p1 - int(0.45 * fs))
        on2 = n2 + int(np.argmin(x[n2:p1])) if p1 > n2 else p1
        if on2 <= on:
            continue
        dur = (on2 - on) / fs
        if not (60 / max_bpm <= dur <= 60 / min_bpm):
            continue
        out.append((on, p0, on2))
    return out


def _apg_waves(d2, sp_idx, n):
    """2차 미분에서 a,b,c,d,e 파. 실제 국소극값만 인정한다.

    c(국소최대)·d(국소최소)는 동맥이 경직되면 생리적으로 융합되어 사라진다
    (문서 7 §4-2). 그 경우 억지로 값을 만들지 않고 None 을 돌려주며,
    '검출 실패' 자체가 정보가 된다.
    """
    hi = max(sp_idx, 2)
    if hi <= 1:
        return None
    a = int(np.argmax(d2[:hi]))
    if a + 2 >= n:
        return None
    # b: a 이후 국소최소 (수축기 전반부)
    win_hi = min(n, a + 1 + max(3, int(0.6 * n)))
    if win_hi - (a + 1) < 2:
        return None
    b = a + 1 + int(np.argmin(d2[a + 1:win_hi]))
    if b + 2 >= n:
        return None
    # e: b 이후 가장 큰 국소최대 (이완기 초반 = dicrotic notch 대응)
    tail = d2[b + 1:n]
    pk, _ = find_peaks(tail)
    if len(pk) == 0:
        return None
    e = b + 1 + int(pk[np.argmax(tail[pk])])
    out = dict(a=a, b=b, c=None, d=None, e=e)
    # c, d: b 와 e 사이의 실제 국소극값 쌍 (c=최대가 d=최소보다 앞)
    lo, hi2 = b + 1, e
    if hi2 - lo >= 4:
        mid = d2[lo:hi2]
        cmax, _ = find_peaks(mid)
        dmin, _ = find_peaks(-mid)
        if len(cmax) and len(dmin):
            c_i = lo + int(cmax[np.argmax(mid[cmax])])
            after = [i for i in dmin if lo + i > c_i]
            if after:
                d_i = lo + int(min(after, key=lambda i: mid[i]))
                out["c"], out["d"] = c_i, d_i
    return out


def beat_features(x, fs, on, sp, on2):
    """한 박동의 형태학 특징. x는 대역통과된 원신호(정규화 전)."""
    seg = x[on:on2].astype(float)
    n = len(seg)
    rng = np.ptp(seg)
    if n < 8 or rng < 1e-9:
        return None
    s = (seg - seg.min()) / rng            # 진폭 정규화 [0,1]
    sp_i = sp - on                          # 수축기 피크 인덱스
    if not (0 < sp_i < n - 1):
        return None
    ms = 1000.0 / fs
    f = {k: np.nan for k in FEATURE_NAMES}
    f["IBI"] = n * ms
    f["CT"] = sp_i * ms
    f["CT_over_IBI"] = sp_i / n

    # --- 폭 (수축기 피크 기준 상대 높이) ---
    for lvl, key in [(0.25, "W25"), (0.50, "W50"), (0.75, "W75")]:
        idx = np.where(s >= lvl * s[sp_i])[0]
        f[key] = (idx[-1] - idx[0]) * ms if len(idx) >= 2 else np.nan
    f["W50_over_IBI"] = f["W50"] / f["IBI"] if f["IBI"] else np.nan

    # --- 미분 ---
    w = max(5, int(0.03 * fs) | 1)          # 홀수 윈도우
    if n > w + 2:
        d1 = savgol_filter(s, w, 3, deriv=1)
        d2 = savgol_filter(s, w, 3, deriv=2)
    else:
        d1 = np.gradient(s); d2 = np.gradient(d1)
    k = int(np.argmax(d1[:max(sp_i, 2)]))
    f["max_slope_norm"] = float(d1[k] * fs)   # 정규화진폭/초
    f["t_max_slope_rel"] = k / n

    # --- dicrotic notch: 2차 미분 e파 우선, 실패 시 1차 미분 fallback ---
    apg = _apg_waves(d2, sp_i, n)
    notch = None
    if apg and apg["e"] is not None and apg["e"] > sp_i:
        notch = apg["e"]
    else:
        tail = d1[sp_i:]
        pk, _ = find_peaks(tail)
        if len(pk):
            notch = sp_i + int(pk[0])
    f["notch_found"] = 1.0 if (apg and apg.get("e") is not None and apg["e"] > sp_i) else 0.0

    if notch is not None and sp_i < notch < n - 1:
        f["LVET"] = notch * ms
        f["CT_over_LVET"] = sp_i / notch          # <-- AT/ET 대응 지표
        f["LVET_over_IBI"] = notch / n
        f["notch_rel_height"] = float(s[notch] / (s[sp_i] + 1e-9))
        a1, a2 = _trapz(s[:notch]), _trapz(s[notch:])
        f["IPA"] = float(a2 / (a1 + 1e-9))
        # 이완기 피크(반사파) -> RI
        tail = s[notch:]
        pk, _ = find_peaks(tail)
        if len(pk):
            dp = notch + int(pk[np.argmax(tail[pk])])
            f["RI"] = float(s[dp] / (s[sp_i] + 1e-9))
            f["dT"] = (dp - sp_i) * ms

    # --- APG 비율 ---
    if apg and apg["a"] is not None and abs(d2[apg["a"]]) > 1e-12:
        A = d2[apg["a"]]
        f["apg_found"] = 1.0
        f["b_over_a"] = float(d2[apg["b"]] / A)
        for key, w_ in [("c_over_a", "c"), ("d_over_a", "d"), ("e_over_a", "e")]:
            if apg.get(w_) is not None:
                f[key] = float(d2[apg[w_]] / A)
        if all(apg.get(w_) is not None for w_ in "bcde"):
            f["aging_index"] = float(
                (d2[apg["b"]] - d2[apg["c"]] - d2[apg["d"]] - d2[apg["e"]]) / A)
    else:
        f["apg_found"] = 0.0
    return f


def extract(sig, fs, prominence=0.4):
    """신호 하나 -> (박동별 특징 리스트, 정규화 파형 배열[100포인트])."""
    x = bandpass(sig, fs)
    if x.std() < 1e-9:
        return [], np.empty((0, 100))
    z = (x - x.mean()) / x.std()
    feats, waves = [], []
    for on, sp, on2 in segment_beats(z, fs, prominence):
        f = beat_features(x, fs, on, sp, on2)
        if f is None:
            continue
        feats.append(f)
        seg = x[on:on2]; rng = np.ptp(seg)
        waves.append(np.interp(np.linspace(0, 1, 100),
                               np.linspace(0, 1, len(seg)), (seg - seg.min()) / rng))
    return feats, (np.array(waves) if waves else np.empty((0, 100)))
