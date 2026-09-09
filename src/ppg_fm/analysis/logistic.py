"""질환 연관 — 로지스틱 회귀, 효과 크기는 특징 1 표준편차당 오즈비.

    logit P(D_p = 1) = b0 + b * z(X_p)

D_p = 해당 ICD 코드 보유 여부, X_p = 환자 요약 특징, exp(b) = 오즈비.
공변량은 넣지 않는다 — 파형 특징 자체와 질환의 연관을 보는 것이 목적이다.
대조군은 해당 코드가 없는 나머지 전원.
다중검정은 선행 연구(ECG PheWAS · npj Digital Medicine · dicrotic notch) 관례를
따라 Bonferroni를 쓴다.
"""
from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .. import paths
from ..features import PATIENT

warnings.filterwarnings("ignore")


# ICD-10 3자리 코드가 아닌 토큰 — 임상 실체가 아니므로 분석에서 제외한다.
# 'NoD'는 ICD-9 → ICD-10 매핑이 되지 않은 항목이며, 실제 진단 코드와 같은 환자 목록에
# 섞여 들어온다. phenome-wide 그림의 한 행으로 둘 근거가 없다.
NON_CLINICAL = {"NoD"}


def load_cohort(min_cases: int = 100):
    """환자 요약표와 ICD 행렬을 붙이고, 사례 수 기준을 넘는 코드만 남긴다."""
    P = (pd.read_csv(paths.interim("patient_features_v2.csv"), dtype={"subject": str})
         .set_index("subject"))
    M = pd.read_csv(paths.interim("patient_icd_matrix_v2.csv"), dtype={"subject": str})
    raw = [c for c in M.columns if c != "subject"]
    # ICD 코드와 특징 이름이 충돌할 수 있어 접두사를 붙인다 (예: W50)
    M = M.rename(columns={c: "icd_" + c for c in raw}).set_index("subject")
    idx = P.index.intersection(M.index)
    P, M = P.loc[idx], M.loc[idx]
    codes = [c for c in M.columns
             if M[c].sum() >= min_cases and c[4:] not in NON_CLINICAL]
    return P, M, codes


def standardize(P: pd.DataFrame, feats=None) -> pd.DataFrame:
    feats = feats or PATIENT
    Z = P[feats].apply(lambda s: (s - s.mean()) / s.std())
    return Z.fillna(Z.median())


def run(min_cases: int = 100, feats=None, out: Path = None) -> pd.DataFrame:
    feats = feats or PATIENT
    out = out or paths.reports("02_logistic/02_association_figure2/figure2_or.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    P, M, codes = load_cohort(min_cases)
    Z = standardize(P, feats)

    rows = []
    for f in feats:
        X = sm.add_constant(Z[f].values.reshape(-1, 1), has_constant="add")
        for c in codes:
            y = M[c].astype(float).values
            try:
                r = sm.Logit(y, X).fit(disp=0)
                rows.append((c[4:], f, float(r.params[1]), float(r.pvalues[1]), int(y.sum())))
            except Exception:
                pass

    R = pd.DataFrame(rows, columns=["icd10", "feat", "logOR", "p", "n_case"])
    R["OR"] = np.exp(R.logOR)
    R["sig"] = R.p < bonferroni(len(R))
    en_path = paths.interim("icd_en.json")
    if en_path.exists():
        R["en"] = R.icd10.map(json.load(open(en_path, encoding="utf-8")))
    R.to_csv(out, index=False)
    return R


def bonferroni(n_tests: int, alpha: float = 0.05) -> float:
    return alpha / n_tests


def summarize(R: pd.DataFrame) -> dict:
    b = bonferroni(len(R))
    S = R[R.p < b]
    return {"검정 수": len(R), "Bonferroni 임계": b,
            "유의 셀": len(S), "유의율(%)": round(100 * len(S) / len(R), 1),
            "유의 질환": S.icd10.nunique(), "유의 특징": S.feat.nunique()}


def top_cells(R: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    S = R[R.p < bonferroni(len(R))].copy()
    S["abs_logOR"] = S.logOR.abs()
    cols = [c for c in ["icd10", "en", "feat", "OR", "p", "n_case"] if c in S.columns]
    return S.nlargest(n, "abs_logOR")[cols].reset_index(drop=True)


def breadth(R: pd.DataFrame, n: int = 12) -> pd.DataFrame:
    """질환별 유의 특징 수 — 어느 질환이 파형에 넓게 나타나는가."""
    S = R[R.p < bonferroni(len(R))]
    d = S.groupby("icd10").size().sort_values(ascending=False).head(n).rename("n_sig_feat")
    d = d.reset_index()
    if "en" in R.columns:
        d = d.merge(R.drop_duplicates("icd10")[["icd10", "en"]], on="icd10", how="left")
    return d
