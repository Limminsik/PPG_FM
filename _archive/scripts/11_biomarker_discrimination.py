"""바이오마커 관점 평가: 파형이 질환을 얼마나 판별하는가.

베이스라인(인구통계) 대비 PPG 파형의 증분 판별력을 본다. (문서 0 §6 필수 통제 2)
공변량은 '제거 대상'이 아니라 '넘어야 할 기준선'으로 쓴다.
"""
import os, json
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score

H = os.path.expanduser("~/mnt/ppg_fm")
OUT = f"{H}/reports/biomarker_auc.csv"
P = pd.read_csv(f"{H}/data/interim/patient_features_all.csv", dtype={"subject": str})
M = pd.read_csv(f"{H}/data/interim/patient_icd_matrix.csv", dtype={"subject": str})
if "subject" not in M.columns:
    M.insert(0, "subject", P.subject.values)
D = P.merge(M, on="subject")
EN = json.load(open(f"{H}/data/interim/icd_en.json"))

MORPH = ["CT","LVET","CT_over_LVET","CT_over_IBI","LVET_over_IBI","dT","W25","W50","W75",
         "W50_over_IBI","RI","notch_rel_height","IPA","max_slope_norm","t_max_slope_rel",
         "b_over_a","c_over_a","d_over_a","e_over_a","aging_index"]
CVF  = [f + "_cv" for f in MORPH]
RATE = ["cd_rate","ri_rate","lvet_rate"]
D["age2"] = D.age ** 2
DEMO = ["age","age2","male","HR","n_codes"]

SETS = {
    "demo":       DEMO,
    "wave":       MORPH,
    "summary":    CVF + RATE,
    "ppg":        MORPH + CVF + RATE,
    "demo_ppg":   DEMO + MORPH + CVF + RATE,
}
CODES = [c for c in M.columns if c != "subject" and D[c].sum() >= 100]

done = set()
if os.path.exists(OUT):
    done = set(pd.read_csv(OUT).icd10)
print(f"질환 {len(CODES)} / 완료 {len(done)}", flush=True)

def auc_cv(X, y, seed=0):
    pipe = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                         LogisticRegression(C=0.1, max_iter=2000))
    skf = StratifiedKFold(5, shuffle=True, random_state=seed)
    pr = np.zeros(len(y))
    for tr, te in skf.split(X, y):
        pipe.fit(X[tr], y[tr])
        pr[te] = pipe.predict_proba(X[te])[:, 1]
    return roc_auc_score(y, pr)

first = not os.path.exists(OUT)
rows = []
for k, code in enumerate(CODES, 1):
    if code in done: continue
    y = D[code].astype(int).values
    r = {"icd10": code, "en": EN.get(code), "n_case": int(y.sum())}
    for name, cols in SETS.items():
        r[f"auc_{name}"] = auc_cv(D[cols].values.astype(float), y)
    r["d_auc"] = r["auc_demo_ppg"] - r["auc_demo"]
    rows.append(r)
    if len(rows) >= 8:
        pd.DataFrame(rows).to_csv(OUT, mode="a", header=first, index=False)
        first = False; rows = []
        print(f"  {k}/{len(CODES)}", flush=True)
if rows:
    pd.DataFrame(rows).to_csv(OUT, mode="a", header=first, index=False)
print("완료", flush=True)
