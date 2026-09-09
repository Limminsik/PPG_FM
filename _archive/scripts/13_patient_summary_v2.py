"""환자 요약 v2 — IQR 원단위 변동성 + 리듬 구성 + ABP 비율."""
import os, numpy as np, pandas as pd
H = os.path.expanduser("~/mnt/ppg_fm")
MORPH = ["CT","LVET","CT_over_LVET","CT_over_IBI","LVET_over_IBI","dT","W25","W50","W75",
         "W50_over_IBI","RI","notch_rel_height","IPA","max_slope_norm","t_max_slope_rel",
         "b_over_a","c_over_a","d_over_a","e_over_a","aging_index"]
use = ["subject","IBI","rhythm","has_abp"] + MORPH
dt = {c: "float32" for c in MORPH + ["IBI"]}; dt["subject"] = str
B = pd.read_csv(f"{H}/data/interim/beat_features_v2.csv", usecols=use, dtype=dt)
print("박동", len(B), "환자", B.subject.nunique(), flush=True)
g = B.groupby("subject", sort=True)
med = g[MORPH].median()
q1, q3 = g[MORPH].quantile(.25), g[MORPH].quantile(.75)
iqr = (q3 - q1); iqr.columns = [c + "_iqr" for c in MORPH]
P = med.join(iqr)
P["HR"] = 60000.0 / g.IBI.median()
P["n_beats"] = g.size()
P["cd_rate"]   = g.d_over_a.apply(lambda s: s.notna().mean())
P["ri_rate"]   = g.RI.apply(lambda s: s.notna().mean())
P["lvet_rate"] = g.LVET.apply(lambda s: s.notna().mean())
P["abp_frac"]  = g.has_abp.mean()
P["sr_frac"]   = g.rhythm.apply(lambda s: (s == "SR").mean())
P["af_frac"]   = g.rhythm.apply(lambda s: s.isin(["AF","AFLT"]).mean())
P["pace_frac"] = g.rhythm.apply(lambda s: s.str.contains("PACE", na=False).mean())
P["rhythm_mode"] = g.rhythm.agg(lambda s: s.mode().iat[0] if len(s.mode()) else "NA")
P = P.reset_index()
# 인구통계·ICD 는 seg_index 에서
d = pd.read_parquet(f"{H}/data/interim/seg_index.parquet", columns=["subject","age","gender"])
d["subject"] = d.subject.astype(str)
demo = d.groupby("subject").first().reset_index()
P = P.merge(demo, on="subject", how="left")
P["male"] = (P.gender.astype(str).str.upper().str[0] == "M").astype(int)
P.to_csv(f"{H}/data/interim/patient_features_v2.csv", index=False)
print("환자 요약", P.shape, flush=True)
print(P[["cd_rate","ri_rate","lvet_rate","sr_frac","af_frac","abp_frac","n_beats"]].describe().round(3).to_string())
