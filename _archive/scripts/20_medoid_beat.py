"""대표 박동(medoid) 추출 — 환자의 중앙 특징 벡터에 가장 가까운 '실제' 박동 하나.

앙상블과 달리 합성 파형이 아니라 실제로 존재한 박동이므로
반사파 봉우리 같은 위치가 흔들리는 특징이 살아남는다.
"""
import os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings('ignore')
H = os.path.expanduser("~/mnt/ppg_fm")
MORPH = ["CT","LVET","CT_over_LVET","CT_over_IBI","LVET_over_IBI","dT","W25","W50","W75",
         "W50_over_IBI","RI","notch_rel_height","IPA","max_slope_norm","t_max_slope_rel",
         "b_over_a","c_over_a","d_over_a","e_over_a","aging_index"]
B = pd.read_csv(f"{H}/data/interim/beat_features_v2.csv", usecols=["subject"]+MORPH,
                dtype={**{f:"float32" for f in MORPH}, "subject":str})
B["_i"] = B.groupby("subject").cumcount()

Z = B[MORPH].astype("float32")
mu, sd = Z.mean(), Z.std().replace(0, 1)
Z = (Z - mu) / sd
Z["subject"] = B.subject.values; Z["_i"] = B._i.values
miss = Z[MORPH].isna().mean(axis=1).values

def medoid(idx_mask, tag):
    sub = Z[idx_mask]
    med = sub.groupby("subject")[MORPH].transform("median")
    dist = (sub[MORPH] - med).abs().mean(axis=1, skipna=True).values
    score = np.where(np.isnan(dist), 9e9, dist) + 0.5 * miss[idx_mask.values]
    tmp = pd.DataFrame({"subject": sub.subject.values, "_i": sub._i.values, "s": score})
    pick = tmp.loc[tmp.groupby("subject").s.idxmin(), ["subject", "_i"]]
    out = B.merge(pick, on=["subject", "_i"], how="inner").set_index("subject")[MORPH]
    print(f"  {tag}: {len(out)}명", flush=True)
    return out

all_m = pd.Series(True, index=Z.index)
M_all = medoid(all_m, "전체")
M_odd = medoid(Z._i % 2 == 1, "홀")
M_even = medoid(Z._i % 2 == 0, "짝")
M_all.to_csv(f"{H}/data/interim/medoid_all.csv")
M_odd.to_csv(f"{H}/data/interim/medoid_odd.csv")
M_even.to_csv(f"{H}/data/interim/medoid_even.csv")
print("검출률:", {f: round(float(M_all[f].notna().mean()), 3) for f in ["RI","dT","d_over_a","LVET"]})
