"""질환 라벨 — ICD-10 3자리 환자×코드 이진 행렬.

metadata.csv의 icd10_truncated는 세그먼트마다 반복되므로 환자당 한 번만 읽는다.
"""
from pathlib import Path
import ast
from collections import defaultdict

import numpy as np
import pandas as pd

from .. import paths


def build(patients_path: Path = None, meta_csv: Path = None,
          out: Path = None, chunksize: int = 500_000) -> Path:
    patients_path = patients_path or paths.interim("patient_features_v2.csv")
    meta_csv = meta_csv or paths.metadata_csv()
    out = out or paths.interim("patient_icd_matrix_v2.csv")

    keep = set(pd.read_csv(patients_path, usecols=["subject"],
                           dtype={"subject": str}).subject)
    pat = defaultdict(set)
    for ch in pd.read_csv(meta_csv, usecols=["subject_id", "icd10_truncated"],
                          dtype={"subject_id": str}, chunksize=chunksize):
        ch = ch[ch.subject_id.isin(keep) & ch.icd10_truncated.notna()]
        for s, v in zip(ch.subject_id.values, ch.icd10_truncated.values):
            if pat[s]:
                continue                       # 환자당 1회면 충분
            try:
                codes = ast.literal_eval(v) if isinstance(v, str) and v.startswith("[") else [v]
            except Exception:
                codes = [v]
            pat[s] |= {str(c).strip()[:3] for c in codes if str(c).strip()}

    subs = sorted(keep)
    allc = sorted({c for v in pat.values() for c in v})
    M = pd.DataFrame([[1 if c in pat.get(s, set()) else 0 for c in allc] for s in subs],
                     columns=allc, dtype=np.int8)
    M.insert(0, "subject", subs)
    M.to_csv(out, index=False)
    return out


def code_counts(matrix_path: Path = None) -> pd.Series:
    matrix_path = matrix_path or paths.interim("patient_icd_matrix_v2.csv")
    M = pd.read_csv(matrix_path, dtype={"subject": str})
    return M.drop(columns="subject").sum().sort_values(ascending=False)
