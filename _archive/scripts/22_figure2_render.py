"""Figure 2 렌더 - 진단코드(x) x 파형특징(y), 값은 log2 오즈비."""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

R = pd.read_csv("reports/figure2_or.csv")
BONF = 0.05 / len(R)

# 유의 결과가 하나라도 있는 질환만
keep = R.groupby("icd10")["p"].min()
keep = keep[keep < BONF].index
S = R[R.icd10.isin(keep)].copy()

order = ["CT","LVET","DT","dT","t_max_slope","t_max_slope_rel","W50","W75",
         "t_a","t_b","t_d","RI","notch_rel_height","aug_index",
         "max_slope_norm","min_slope_norm",
         "b_over_a","c_over_a","d_over_a","e_over_a","aging_index"]
feats = [f for f in order if f in set(S.feat)] + sorted(set(S.feat) - set(order))

M = S.pivot(index="feat", columns="icd10", values="logOR").reindex(feats)
P = S.pivot(index="feat", columns="icd10", values="p").reindex(feats)
# 질환 정렬: ICD 장 순서
cols = sorted(M.columns)
M, P = M[cols], P[cols]

V = (M / np.log(2)).values          # log2 OR
Vm = np.where(P.values < BONF, V, np.nan)   # 유의한 셀만 색

fig, ax = plt.subplots(figsize=(max(14, len(cols)*0.19), len(feats)*0.30 + 2.4), dpi=170)
lim = np.nanpercentile(np.abs(Vm), 99)
im = ax.imshow(Vm, cmap="RdBu_r", norm=TwoSlopeNorm(0, -lim, lim),
               aspect="auto", interpolation="nearest")
ax.set_facecolor("#f4f4f2")
ax.set_yticks(range(len(feats))); ax.set_yticklabels(feats, fontsize=7.5)
ax.set_xticks(range(len(cols)));  ax.set_xticklabels(cols, fontsize=5.4, rotation=90)
ax.set_xlabel(f"ICD-10 diagnosis code (n={len(cols)} with >=1 significant cell)", fontsize=9)
ax.set_ylabel("PPG waveform feature (patient median)", fontsize=9)
for s in ax.spines.values(): s.set_linewidth(0.4); s.set_color("#999")
ax.tick_params(length=2, width=0.4)
cb = fig.colorbar(im, ax=ax, fraction=0.012, pad=0.008)
cb.set_label("log$_2$ odds ratio per 1 SD", fontsize=8); cb.ax.tick_params(labelsize=7)
ax.set_title(f"Unadjusted logistic OR  |  {len(R):,} tests  |  Bonferroni p < {BONF:.2e}  |  "
             f"{int((R.p<BONF).sum()):,} significant ({(R.p<BONF).mean()*100:.1f}%)",
             fontsize=9.5, pad=8)
fig.tight_layout()
fig.savefig("reports/figure2_or.png", bbox_inches="tight")
print("saved", M.shape)
