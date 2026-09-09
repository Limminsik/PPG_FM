"""코호트 정의 — 세그먼트 인덱스 생성, SQI 필터, 추출 계획표.

데이터 구조
    환자(subject_id) → 레코드(record_id) → 세그먼트(.hea/.dat, 30초·125Hz)
    세그먼트 한 개마다 metadata.csv에 한 행이 있고, 그 행에 품질 지표·리듬·
    인구통계·진단코드가 함께 들어 있다.

품질 지표(SQI)는 데이터셋이 제공하는 값이다. 30초를 10초씩 세 구간으로 나눠
각 구간에 Orphanidou 등(2015) 알고리즘으로 +1(통과) / 0(미통과)을 매기고,
3원소 벡터 vector_10s_pleth_sqi로 배포한다. 음수(계산 불가)는 배포 전 제외됐다.
여기서는 세 구간이 모두 +1인 세그먼트만 고품질로 본다.
"""
from pathlib import Path
import numpy as np
import pandas as pd

from .. import paths

HQ_VECTOR = "[1,1,1]"
META_COLS = ["folder_path", "subject_id", "record_id", "event_rhythm",
             "age", "gender", "vector_10s_pleth_sqi", "vector_10s_abp_sqi",
             "icd10_truncated", "strat_fold"]


def _norm(s: pd.Series) -> pd.Series:
    return s.fillna("").str.replace(" ", "", regex=False)


def sqi_distribution(meta_csv: Path = None, chunksize: int = 500_000) -> pd.DataFrame:
    """SQI 벡터별 세그먼트 수. 필터가 무엇을 남기고 무엇을 버리는지 확인용."""
    meta_csv = meta_csv or paths.metadata_csv()
    from collections import Counter
    c, n = Counter(), 0
    for ch in pd.read_csv(meta_csv, usecols=["vector_10s_pleth_sqi"],
                          dtype=str, chunksize=chunksize):
        c.update(_norm(ch["vector_10s_pleth_sqi"]))
        n += len(ch)
    d = (pd.DataFrame({"sqi": list(c), "n_segment": list(c.values())})
         .sort_values("n_segment", ascending=False).reset_index(drop=True))
    d["pct"] = (100 * d.n_segment / n).round(2)
    d["hq"] = d.sqi == HQ_VECTOR
    return d


def build_index(meta_csv: Path = None, out: Path = None,
                chunksize: int = 500_000) -> Path:
    """metadata.csv → 세그먼트 인덱스(parquet). hq 플래그를 여기서 붙인다."""
    meta_csv = meta_csv or paths.metadata_csv()
    out = out or paths.interim("seg_index.parquet")
    frames = []
    for ch in pd.read_csv(meta_csv, usecols=META_COLS, dtype=str, chunksize=chunksize):
        frames.append(pd.DataFrame({
            "folder_path": ch.folder_path,
            "subject": ch.subject_id,
            "record": ch.record_id,
            "rhythm": ch.event_rhythm,
            "age": pd.to_numeric(ch.age, errors="coerce"),
            "gender": ch.gender,
            "fold": ch.strat_fold,
            "hq": _norm(ch["vector_10s_pleth_sqi"]).eq(HQ_VECTOR),
            "has_abp": ~ch["vector_10s_abp_sqi"].fillna("nan").str.contains("nan"),
        }))
    idx = pd.concat(frames, ignore_index=True)
    idx.to_parquet(out, index=False)
    return out


def cohort_flow(index_path: Path = None) -> pd.DataFrame:
    """코호트가 확정되는 경로를 단계별 표로."""
    index_path = index_path or paths.interim("seg_index.parquet")
    d = pd.read_parquet(index_path, columns=["subject", "hq"])
    rows = [("① 전체", len(d), d.subject.nunique()),
            ("② SQI [1,1,1]", int(d.hq.sum()), d[d.hq].subject.nunique())]
    plan = paths.interim("extract_plan.csv")
    if plan.exists():
        p = pd.read_csv(plan, dtype={"subject": str})
        rows.append(("③ 세그먼트 표집", len(p), p.subject.nunique()))
    feat = paths.interim("patient_features_v2.csv")
    if feat.exists():
        f = pd.read_csv(feat, usecols=["subject", "n_beats"], dtype={"subject": str})
        rows.append(("④ 박동 추출", int(f.n_beats.sum()), len(f)))
    return pd.DataFrame(rows, columns=["단계", "세그먼트/박동", "환자"])


def build_plan(n_per_patient: int = 10, index_path: Path = None,
               out: Path = None) -> Path:
    """환자마다 기록 전체에서 균등 간격으로 N개 세그먼트를 고른다.

    리듬은 제한하지 않는다 — 정상동율동만 남기면 부정맥 환자가 통째로 빠진다.
    """
    index_path = index_path or paths.interim("seg_index.parquet")
    out = out or paths.interim("extract_plan.csv")
    d = pd.read_parquet(index_path, columns=["folder_path", "subject", "rhythm",
                                             "has_abp", "hq"])
    d = d[d.hq].drop(columns="hq")
    d["subject"] = d.subject.astype(str)
    pick = []
    for _, ii in d.groupby("subject", sort=False).indices.items():
        ii = np.sort(ii)                                # 원본 순서 ≈ 시간 순
        k = min(n_per_patient, len(ii))
        take = np.unique(np.linspace(0, len(ii) - 1, k).round().astype(int))
        pick.append(ii[take])
    d.iloc[np.concatenate(pick)].to_csv(out, index=False)
    return out
