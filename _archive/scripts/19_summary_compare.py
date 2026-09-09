"""환자 요약 방식 3종 비교 — ① 중앙값 ② 박동별 분위수 ③ 앙상블 평균 박동.

세 지표로 잰다: 재현성(홀/짝 분할), 검출률, 질환 신호(로지스틱 오즈비).
"""
import os, warnings
import numpy as np, pandas as pd, statsmodels.api as sm
from scipy.stats import spearmanr
warnings.filterwarnings('ignore')
H = os.path.expanduser("~/mnt/ppg_fm")
MORPH = ["CT","LVET","CT_over_LVET","CT_over_IBI","LVET_over_IBI","dT","W25","W50","W75",
         "W50_over_IBI","RI","notch_rel_height","IPA","max_slope_norm","t_max_slope_rel",
         "b_over_a","c_over_a","d_over_a","e_over_a","aging_index"]

B = pd.read_csv(f"{H}/data/interim/beat_features_v2.csv",
                usecols=["subject","IBI"]+MORPH, dtype={**{f:"float32" for f in MORPH+["IBI"]},"subject":str})
B["_i"] = B.groupby("subject").cumcount()
E = pd.read_csv(f"{H}/data/interim/ensemble_features.csv", dtype={"subject":str})

def q(df, p):
    g = df.groupby("subject")[MORPH].quantile(p); g.columns = [f"{c}" for c in MORPH]; return g
sets = {}
sets["①중앙값"]      = {"main": q(B,.50), "odd": q(B[B._i%2==1],.50), "even": q(B[B._i%2==0],.50), "nf": 20}
qs = {}
for p,tag in [(.25,"p25"),(.50,"p50"),(.75,"p75")]:
    qs[tag] = (q(B,p), q(B[B._i%2==1],p), q(B[B._i%2==0],p))
sets["②분위수"] = {"main": pd.concat([qs[t][0].add_suffix(f"_{t}") for t in qs],axis=1),
                   "odd":  pd.concat([qs[t][1].add_suffix(f"_{t}") for t in qs],axis=1),
                   "even": pd.concat([qs[t][2].add_suffix(f"_{t}") for t in qs],axis=1), "nf": 60}
ee = lambda k: E[E.kind==k].set_index("subject")[MORPH]
sets["③앙상블"] = {"main": ee("all"), "odd": ee("odd"), "even": ee("even"), "nf": 20}

P = pd.read_csv(f"{H}/data/interim/patient_features_v2.csv", dtype={"subject":str}).set_index("subject")
M = pd.read_csv(f"{H}/data/interim/patient_icd_matrix_v2.csv", dtype={"subject":str})
raw = [c for c in M.columns if c!="subject"]; M = M.rename(columns={c:"icd_"+c for c in raw}).set_index("subject")
ICD = ["icd_"+c for c in raw]
codes = [c for c in ICD if M[c].sum()>=100]
print(f"질환 {len(codes)}개\n")

print(f"{'방식':10s} {'특징수':>5s} {'재현성 중앙값':>12s} {'재현성 최저':>10s} {'검출률 중앙값':>12s} {'유의셀':>7s} {'유의율':>7s} {'|logOR| 중앙':>12s}")
res={}
for name, S in sets.items():
    cols = list(S["main"].columns)
    rs=[]
    for c in cols:
        a,b = S["odd"][c], S["even"][c]
        m = a.notna() & b.notna()
        if m.sum()>200: rs.append(spearmanr(a[m],b[m])[0])
    det = [S["main"][c].notna().mean() for c in cols]
    idx = S["main"].index.intersection(P.index).intersection(M.index)
    X = P.loc[idx,["age","male","HR"]].copy(); X["age2"]=X.age**2
    X["n_codes"]=M.loc[idx,ICD].sum(axis=1)
    ok = X.notna().all(axis=1); idx = idx[ok]; X = X.loc[idx,["age","age2","male","HR","n_codes"]].astype(float).values
    F = S["main"].loc[idx]
    ntest = len(cols)*len(codes); bonf = 0.05/ntest
    sig=0; ors=[]
    for c in cols:
        y = F[c].values.astype(float)
        y = np.where(np.isnan(y), np.nanmedian(y), y)
        z = (y-y.mean())/ (y.std() if y.std()>0 else 1)
        Z = sm.add_constant(np.column_stack([z,X]), has_constant="add")
        for cd in codes:
            d = M.loc[idx,cd].astype(float).values
            try:
                r = sm.Logit(d,Z).fit(disp=0)
                if r.pvalues[1] < bonf: sig+=1; ors.append(abs(r.params[1]))
            except Exception: pass
    res[name]=(np.median(rs), min(rs), np.median(det), sig, sig/ntest*100, np.median(ors) if ors else np.nan, ntest)
    r=res[name]
    print(f"{name:10s} {len(cols):5d} {r[0]:12.3f} {r[1]:10.3f} {r[2]:12.3f} {r[3]:7d} {r[4]:6.1f}% {r[5]:12.3f}")
pd.DataFrame(res, index=["재현성중앙","재현성최저","검출률","유의셀","유의율","logOR중앙","검정수"]).T.to_csv(f"{H}/reports/summary_method_compare.csv")
