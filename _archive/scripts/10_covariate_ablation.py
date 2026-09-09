"""공변량 보정의 필요성 검정 + 특징 계열별(파형 / 요약) 결과 분리."""
import os, json
import numpy as np, pandas as pd, statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

H = os.path.expanduser("~/mnt/ppg_fm")
P = pd.read_csv(f"{H}/data/interim/patient_features_all.csv", dtype={"subject": str})
M = pd.read_csv(f"{H}/data/interim/patient_icd_matrix.csv", dtype={"subject": str})
if "subject" not in M.columns:
    M.insert(0, "subject", P.subject.values)
P = P.merge(M, on="subject")
EN = json.load(open(f"{H}/data/interim/icd_en.json"))

MORPH = ["CT","LVET","CT_over_LVET","CT_over_IBI","LVET_over_IBI","dT","W25","W50","W75",
         "W50_over_IBI","RI","notch_rel_height","IPA","max_slope_norm","t_max_slope_rel",
         "b_over_a","c_over_a","d_over_a","e_over_a","aging_index"]
CV   = [f + "_cv" for f in MORPH]
RATE = ["cd_rate","ri_rate","lvet_rate"]
FEATS = MORPH + CV + RATE
CLASS = {**{f:"파형" for f in MORPH}, **{f:"변동성" for f in CV}, **{f:"검출률" for f in RATE}}

CODES = [c for c in M.columns if c != "subject" and P[c].sum() >= 100]
print(f"질환 {len(CODES)} · 특징 {len(FEATS)} · 환자 {len(P)}", flush=True)

MODELS = {
    "M0_무보정":      [],
    "M1_연령":        ["age","age2"],
    "M2_연령성별":     ["age","age2","male"],
    "M3_전체":        ["age","age2","male","HR","n_codes"],
}
P["age2"] = P.age ** 2

Z = P[FEATS].apply(lambda s: (s - s.mean()) / s.std())
rows = []
for name, cov in MODELS.items():
    X0 = P[cov].astype(float) if cov else None
    for code in CODES:
        d = P[code].astype(float).values
        for f in FEATS:
            y = Z[f].values
            m = ~np.isnan(y)
            X = np.column_stack([d[m]] + ([X0.values[m]] if cov else []))
            X = sm.add_constant(X, has_constant="add")
            try:
                r = sm.OLS(y[m], X).fit()
                rows.append((name, code, f, CLASS[f], r.params[1], r.pvalues[1], int(d[m].sum())))
            except Exception:
                pass
    print(f"  {name} 완료", flush=True)

R = pd.DataFrame(rows, columns=["model","icd10","feat","class","beta","p","n_case"])
R["q"] = np.nan
for name, g in R.groupby("model"):
    R.loc[g.index, "q"] = multipletests(g.p.values, method="fdr_bh")[1]
R["en"] = R.icd10.map(EN)
R.to_csv(f"{H}/reports/covariate_ablation.csv", index=False)
print("저장 완료", R.shape)
