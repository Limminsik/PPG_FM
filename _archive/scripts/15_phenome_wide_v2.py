"""W1 질환 WIDE v2 — 6,113명 · 전 리듬 · IQR 변동성 · 172코드(≥100명)."""
import os, json, numpy as np, pandas as pd, statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
H = os.path.expanduser("~/mnt/ppg_fm")
P = pd.read_csv(f"{H}/data/interim/patient_features_v2.csv", dtype={"subject": str})
M = pd.read_csv(f"{H}/data/interim/patient_icd_matrix_v2.csv", dtype={"subject": str})
ICD = [c for c in M.columns if c != "subject"]
M = M.rename(columns={c: "icd_" + c for c in ICD})       # 특징명(W50 등)과 충돌 방지
ICD = ["icd_" + c for c in ICD]
D = P.merge(M, on="subject")
MORPH = ["CT","LVET","CT_over_LVET","CT_over_IBI","LVET_over_IBI","dT","W25","W50","W75",
         "W50_over_IBI","RI","notch_rel_height","IPA","max_slope_norm","t_max_slope_rel",
         "b_over_a","c_over_a","d_over_a","e_over_a","aging_index"]
IQR  = [f + "_iqr" for f in MORPH]
RATE = ["cd_rate","ri_rate","lvet_rate"]
FEATS = MORPH + IQR + RATE
CLS = {**{f:"파형" for f in MORPH}, **{f:"변동성" for f in IQR}, **{f:"검출률" for f in RATE}}
codes = [c for c in ICD if D[c].sum() >= 100]
D["age2"] = D.age ** 2
D["n_codes"] = D[ICD].sum(axis=1)
COV = ["age","age2","male","HR","n_codes"]
D = D.dropna(subset=COV)
print(f"환자 {len(D)} · 질환 {len(codes)} · 특징 {len(FEATS)} = {len(codes)*len(FEATS)} 검정", flush=True)
Z = D[FEATS].apply(lambda s: (s - s.mean()) / s.std())
X0 = D[COV].astype(float).values
rows = []
for code in codes:
    d = D[code].astype(float).values
    for f in FEATS:
        y = Z[f].values; m = ~np.isnan(y)
        X = sm.add_constant(np.column_stack([d[m], X0[m]]), has_constant="add")
        try:
            r = sm.OLS(y[m], X).fit()
            rows.append((code[4:], f, CLS[f], r.params[1], r.pvalues[1], int(d[m].sum())))
        except Exception:
            pass
R = pd.DataFrame(rows, columns=["icd10","feat","class","beta","p","n_case"])
R["q"] = multipletests(R.p.values, method="fdr_bh")[1]
en = json.load(open(f"{H}/data/interim/icd_en.json")); R["en"] = R.icd10.map(en)
R.to_csv(f"{H}/reports/phenome_wide_v2.csv", index=False)
sig = R[R.q < 0.05]
print(f"유의 {len(sig)} / {len(R)} ({len(sig)/len(R)*100:.1f}%) · 질환 {sig.icd10.nunique()}", flush=True)
print(sig.groupby("class").size().to_string(), flush=True)
