"""파형 특징 추출 — 계획표의 세그먼트를 읽어 박동 단위 특징을 뽑는다.

증분 저장·재개. 이미 처리한 환자는 출력 파일에서 읽어 건너뛴다.
"""
from pathlib import Path
import os
import time
import warnings

import pandas as pd
import wfdb

from .. import paths
from ..morph.features import extract as extract_beats

warnings.filterwarnings("ignore")


def _done(out: Path) -> set:
    if out.exists() and out.stat().st_size > 10:
        return set(pd.read_csv(out, usecols=["subject"],
                               dtype={"subject": str}).subject.unique())
    return set()


def run(budget_sec: int = 100_000, min_beats: int = 10,
        plan_path: Path = None, out: Path = None) -> dict:
    """계획표를 따라 박동 특징을 추출한다. budget_sec만큼 돌고 멈춘다(재개 가능).

    min_beats는 고정 길이(30초) 창에 대한 조건이므로 **서맥 환자를 체계적으로 배제한다.**
    세그먼트가 하나뿐인 환자에서 20박동을 요구하면 HR 40 bpm 미만이 전부 탈락한다.
    실제로 HR 43 bpm인 환자 하나가 18박동으로 탈락했다. 기준을 10으로 낮춰
    (세그먼트 1개 기준 HR 20 bpm) 리듬·심박수에 중립이 되게 한다.
    박동 수는 n_beats로 남으므로 필요하면 사후 민감도 분석에서 다룬다.
    """
    plan_path = plan_path or paths.interim("extract_plan.csv")
    out = out or paths.interim("beat_features_v2.csv")
    plan = pd.read_csv(plan_path, dtype={"subject": str})
    done = _done(out)
    todo = [s for s in sorted(plan.subject.unique()) if s not in done]
    if not todo:
        return {"status": "done", "patients": len(done), "remaining": 0}

    groups = dict(plan.groupby("subject", sort=False).indices)
    cwd = os.getcwd()
    os.chdir(paths.ext_ppg())
    first = not (out.exists() and out.stat().st_size > 10)
    t0, n_seg, n_pat = time.time(), 0, 0
    try:
        for s in todo:
            if time.time() - t0 > budget_sec:
                break
            ss = plan.iloc[groups[s]]
            rows = []
            for fp, rhy, hab in zip(ss.folder_path, ss.rhythm, ss.has_abp):
                try:
                    rec = wfdb.rdrecord(fp)
                    i = rec.sig_name.index("PLETH")
                    for f in extract_beats(rec.p_signal[:, i], rec.fs)[0]:
                        f["rhythm"] = rhy
                        f["has_abp"] = bool(hab)
                        rows.append(f)
                    n_seg += 1
                except Exception:
                    pass
            if len(rows) < min_beats:
                continue
            df = pd.DataFrame(rows)
            df.insert(0, "subject", s)
            df.to_csv(out, mode="a", header=first, index=False)
            first, n_pat = False, n_pat + 1
    finally:
        os.chdir(cwd)
    elapsed = max(time.time() - t0, 1)
    return {"status": "partial", "patients_this_run": n_pat, "segments": n_seg,
            "elapsed_sec": round(elapsed), "remaining": len(todo) - n_pat}
