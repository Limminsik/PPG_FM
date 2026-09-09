"""Figure 2 산출 — 확정 사양: 환자 요약 = 박동별 중앙값, 효과 크기 = 오즈비, 로지스틱.

공변량 조정 없음(무보정). 다중검정은 선행 연구 관례를 따라 Bonferroni.
"""
import os, json, warnings
import numpy as np, pandas as pd, statsmodels.api as sm
warnings.filterwarnings('ignore')
H = os.path.expanduser("~/mnt/ppg_fm")
MORPH = ["CT","LVET","CT_over_LVET","CT_over_IBI","LVET_over_IBI","dT","W25","W50","W75",
         "W50_over_IBI","RI","notch_rel_height","IPA","max_slope_norm","t_max_slope_rel",
         "b_over_a","c_over_a","d_over_a","e_over_a","aging_index"]
IQR  = [f + "_iqr" for f in MORPH]
RATE = ["cd_rate","ri_rate","lvet_rate"]
FEATS = MORPH + IQR + RATE

P = pd.read_csv(f"{H}/data/interim/patient_features_v2.csv", dtype={"subject":str}).set_index("subject")
M = pd.read_csv(f"{H}/data/interim/patient_icd_matrix_v2.csv", dtype={"subject":str})
raw = [c for c in M.columns if c != "subject"]
M = M.rename(columns={c: "icd_" + c for c in raw}).set_index("subject")
ICD = ["icd_" + c for c in raw]
idx = P.index.intersection(M.index)
P, M = P.loc[idx], M.loc[idx]
codes = [c for c in ICD if M[c].sum() >= 100]
Z = P[FEATS].apply(lambda s: (s - s.mean()) / s.std())
Z = Z.fillna(Z.median())
print(f"환자 {len(P)} · 질환 {len(codes)} · 특징 {len(FEATS)} = {len(codes)*len(FEATS):,} 검정", flush=True)

rows = []
for f in FEATS:
    z = Z[f].values
    X = sm.add_constant(z.reshape(-1, 1), has_constant="add")     # 공변량 없음
    for c in codes:
        d = M[c].astype(float).values
        try:
            r = sm.Logit(d, X).fit(disp=0)
            rows.append((c[4:], f, float(r.params[1]), float(r.pvalues[1]), int(d.sum())))
        except Exception:
            pass
R = pd.DataFrame(rows, columns=["icd10","feat","logOR","p","n_case"])
R["OR"] = np.exp(R.logOR)
bonf = 0.05 / len(R)
R["sig"] = R.p < bonf
en = json.load(open(f"{H}/data/interim/icd_en.json")); R["en"] = R.icd10.map(en)
R.to_csv(f"{H}/reports/figure2_or.csv", index=False)
print(f"Bonferroni 임계 {bonf:.2e} · 유의 {int(R.sig.sum()):,} / {len(R):,} ({R.sig.mean()*100:.1f}%)", flush=True)
print(f"유의 질환 {R[R.sig].icd10.nunique()} · 유의 특징 {R[R.sig].feat.nunique()}", flush=True)
t = R[R.sig].assign(a=lambda d: (np.log(d.OR)).abs()).nlargest(8, "a")
for _, r in t.iterrows():
    print(f"  {r.icd10} × {r.feat:22s} OR {r.OR:.3f}  p {r.p:.1e}  n {r.n_case}", flush=True)
