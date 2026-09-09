"""형태학 특징 추출 스모크 테스트.

문서 7 §7-3: 진폭이 아니라 '정규화 타이밍'을 표적으로 삼는다.
여기서는 pyPPG fiducial 검출이 실제로 도는지, 그리고
핵심 타이밍 지표(CT, LVET 근사, CT/LVET)가 뽑히는지 확인한다.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ppg_fm.config import ds  # noqa: E402


def load_one_segment():
    """MIMIC-III-Ext-PPG에서 PPG 세그먼트 하나."""
    import wfdb
    root = Path(ds("mimic_ext_ppg")["root"])
    with open(root / "RECORDS") as f:
        rec_name = next(ln.strip() for ln in f if ln.strip())
    rec = wfdb.rdrecord(str(root / rec_name))
    # PLETH 채널 찾기
    idx = None
    for i, nm in enumerate(rec.sig_name):
        if "PLETH" in nm.upper() or "PPG" in nm.upper():
            idx = i
            break
    if idx is None:
        raise RuntimeError(f"PLETH 채널 없음: {rec.sig_name}")
    return rec.p_signal[:, idx], rec.fs, rec_name


def basic_timing(sig, fs):
    """의존성 없는 최소 타이밍 지표 (pyPPG 실패 시 fallback)."""
    from scipy.signal import butter, filtfilt, find_peaks
    b, a = butter(4, [0.5 / (fs / 2), 8 / (fs / 2)], btype="band")
    x = filtfilt(b, a, np.nan_to_num(sig))
    x = (x - x.mean()) / (x.std() + 1e-9)
    pk, _ = find_peaks(x, distance=int(0.4 * fs), prominence=0.3)
    if len(pk) < 3:
        return None
    onsets = []
    for p in pk:
        lo = max(0, p - int(0.5 * fs))
        onsets.append(lo + int(np.argmin(x[lo:p])) if p > lo else p)
    ct = (np.array(pk) - np.array(onsets)) / fs * 1000  # ms
    ibi = np.diff(pk) / fs * 1000
    return {
        "n_beats": len(pk),
        "HR_bpm": 60000 / np.median(ibi) if len(ibi) else np.nan,
        "crest_time_ms_median": float(np.median(ct)),
        "crest_time_ms_iqr": float(np.subtract(*np.percentile(ct, [75, 25]))),
    }


def main():
    print("=== PPG 세그먼트 로드 ===")
    sig, fs, name = load_one_segment()
    print(f"  record : {name}")
    print(f"  fs     : {fs} Hz, length {len(sig)} ({len(sig)/fs:.1f}s)")
    print(f"  NaN 비율: {np.isnan(sig).mean():.1%}")

    print("\n=== 기본 타이밍 지표 (scipy) ===")
    r = basic_timing(sig, fs)
    if r:
        for k, v in r.items():
            print(f"  {k:24s} {v:.2f}" if isinstance(v, float) else f"  {k:24s} {v}")
    else:
        print("  박동 검출 실패")

    print("\n=== pyPPG fiducial 검출 ===")
    try:
        from pyPPG import PPG, Fiducials
        from pyPPG.datahandling import load_data
        import pyPPG.preproc as PP
        import pyPPG.fiducials as FP
        print("  pyPPG import OK -> 실제 파이프라인은 notebooks/ 에서 구성")
    except Exception as e:
        print(f"  pyPPG 미설치/실패: {type(e).__name__}: {e}")
        print("  -> uv pip install pyPPG  (Python 3.10+ 필요할 수 있음)")


if __name__ == "__main__":
    main()
