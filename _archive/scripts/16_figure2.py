"""Figure 2 — PPG waveform features x ICD diagnosis codes (MIMIC-III-Ext-PPG).

Cell = covariate-adjusted standardised beta.  Non-significant (q>=0.05) cells are
left unpainted so the eye reads only what survived FDR control.
"""
import os, json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import Rectangle

H = os.path.expanduser("~/mnt/ppg_fm")
R = pd.read_csv(f"{H}/reports/phenome_wide_v2.csv")

MORPH = ["CT","LVET","CT_over_LVET","CT_over_IBI","LVET_over_IBI","dT",
         "W25","W50","W75","W50_over_IBI",
         "RI","notch_rel_height","IPA",
         "max_slope_norm","t_max_slope_rel",
         "b_over_a","c_over_a","d_over_a","e_over_a","aging_index"]
FAM = ([("Timing",f) for f in MORPH[:10]] + [("Amplitude ratio",f) for f in MORPH[10:13]] +
       [("Derivatives",f) for f in MORPH[13:20]] +
       [("Beat-to-beat IQR",f+"_iqr") for f in MORPH] +
       [("Detection rate",f) for f in ["cd_rate","ri_rate","lvet_rate"]])
FEATS = [f for _,f in FAM]

CHAP = {"A":"Infectious","B":"Infectious","C":"Neoplasm","D":"Blood/Neoplasm","E":"Endocrine",
        "F":"Mental","G":"Nervous","H":"Sensory","I":"Circulatory","J":"Respiratory","K":"Digestive",
        "L":"Skin","M":"Musculoskeletal","N":"Genitourinary","Q":"Congenital","R":"Symptoms",
        "S":"Injury","T":"Injury","V":"External","W":"External","X":"External","Y":"External",
        "Z":"Health status"}
ORDER = ["Circulatory","Respiratory","Endocrine","Genitourinary","Digestive","Blood/Neoplasm",
         "Infectious","Nervous","Mental","Symptoms","Musculoskeletal","Injury","Neoplasm",
         "Skin","Sensory","External","Health status","Congenital"]

B = R.pivot(index="feat", columns="icd10", values="beta").reindex(FEATS)
Q = R.pivot(index="feat", columns="icd10", values="q").reindex(FEATS)
sig = (Q < 0.05)
nsig_d = sig.sum(axis=0)                      # significant features per disease
nsig_f = sig.sum(axis=1)                      # significant diseases per feature

codes = list(B.columns)
meta = pd.DataFrame({"code": codes})
meta["chap"] = meta.code.str[0].map(CHAP).fillna("Other")
meta["nsig"] = meta.code.map(nsig_d)
meta["rank"] = meta.chap.map({c: i for i, c in enumerate(ORDER)}).fillna(99)
meta = meta.sort_values(["rank", "nsig"], ascending=[True, False]).reset_index(drop=True)
cols = meta.code.tolist()
B, Q, sig = B[cols], Q[cols], sig[cols]
nsig_d = nsig_d[cols]

Bm = np.ma.masked_where(~sig.values, B.values)
vmax = float(np.nanpercentile(np.abs(B.values[sig.values]), 99))
cmap = LinearSegmentedColormap.from_list("bwr2", ["#17607E", "#7FA9BC", "#E9EBEF", "#C98F98", "#9E3B4A"])
cmap.set_bad("#F7F8FA")
norm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)

nF, nD = len(FEATS), len(cols)
fig = plt.figure(figsize=(nD * 0.115 + 4.2, nF * 0.20 + 4.0), dpi=200)
gs = fig.add_gridspec(3, 3, height_ratios=[0.9, 0.34, nF * 0.20],
                      width_ratios=[nD * 0.115, 1.5, 0.34],
                      hspace=0.06, wspace=0.05, left=0.175, right=0.965, top=0.945, bottom=0.135)

# --- top bar: significant features per disease ---
axt = fig.add_subplot(gs[0, 0])
axt.bar(range(nD), nsig_d.values, width=0.78, color="#5E646F", linewidth=0)
axt.set_xlim(-0.5, nD - 0.5); axt.set_xticks([])
axt.set_ylabel("Sig.\nfeatures", fontsize=7.5, color="#191C22", labelpad=6)
axt.tick_params(axis="y", labelsize=7, colors="#5E646F", length=2)
for s in ("top", "right", "bottom"): axt.spines[s].set_visible(False)
axt.spines["left"].set_color("#D6D9DF")
axt.grid(axis="y", color="#EAECF0", lw=0.6); axt.set_axisbelow(True)

# --- chapter band ---
axb = fig.add_subplot(gs[1, 0]); axb.set_xlim(-0.5, nD - 0.5); axb.set_ylim(0, 1); axb.axis("off")
tone = {c: v for c, v in zip(ORDER, ["#2C3E50","#3D5A6C","#4E7A63","#6B4E8C","#8A6A1C","#9E3B4A",
        "#5E646F","#3F5F8A","#7A5C8A","#6B7280","#4A6B57","#8C6B4A","#7A4A5C","#5C7A8A","#8A7A4A",
        "#6B6B6B","#4A5A7A","#7A7A5A"])}
i = 0
for ch, g in meta.groupby("rank", sort=True):
    name = g.chap.iloc[0]; n = len(g)
    axb.add_patch(Rectangle((i - 0.5, 0.12), n, 0.76, facecolor=tone.get(name, "#6B6B6B"), lw=0))
    if n >= 5:
        axb.text(i + n / 2 - 0.5, 0.5, name, ha="center", va="center", fontsize=6.6,
                 color="white", fontweight="600")
    i += n

# --- main heatmap ---
ax = fig.add_subplot(gs[2, 0])
ax.imshow(Bm, aspect="auto", cmap=cmap, norm=norm, interpolation="nearest")
ax.set_yticks(range(nF)); ax.set_yticklabels(FEATS, fontsize=6.4, color="#191C22", fontfamily="monospace")
ax.set_xticks(range(nD)); ax.set_xticklabels(cols, fontsize=5.0, rotation=90, color="#5E646F")
ax.tick_params(length=1.6, colors="#8C93A0")
for s in ax.spines.values(): s.set_color("#D6D9DF"); s.set_linewidth(0.7)
# feature-family separators + labels
i = 0; bounds = []
for fam in ["Timing","Amplitude ratio","Derivatives","Beat-to-beat IQR","Detection rate"]:
    n = sum(1 for f, _ in FAM if f == fam); bounds.append((fam, i, n)); i += n
for fam, s, n in bounds[1:]:
    ax.axhline(s - 0.5, color="#191C22", lw=0.9)
for fam, s, n in bounds:
    ax.text(-0.118, 1 - (s + n / 2) / nF, fam, transform=ax.transAxes, rotation=90,
            ha="center", va="center", fontsize=7.4, color="#191C22", fontweight="600")
i = 0
for _, g in meta.groupby("rank", sort=True):
    i += len(g)
    if i < nD: ax.axvline(i - 0.5, color="#FFFFFF", lw=0.8)

# --- right bar: significant diseases per feature ---
axr = fig.add_subplot(gs[2, 2])
axr.barh(range(nF), nsig_f.values, height=0.78, color="#5E646F", linewidth=0)
axr.set_ylim(nF - 0.5, -0.5); axr.set_yticks([])
axr.set_xlabel("Sig.\ndiseases", fontsize=7.5, color="#191C22")
axr.tick_params(axis="x", labelsize=7, colors="#5E646F", length=2)
for s in ("top", "right", "left"): axr.spines[s].set_visible(False)
axr.spines["bottom"].set_color("#D6D9DF")
axr.grid(axis="x", color="#EAECF0", lw=0.6); axr.set_axisbelow(True)

# --- colourbar ---
cax = fig.add_axes([0.79, 0.055, 0.155, 0.014])
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm); sm.set_array([])
cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
cb.set_label("Standardised β  (disease vs. rest, covariate-adjusted)", fontsize=7, color="#191C22", labelpad=4)
cb.ax.tick_params(labelsize=6.5, colors="#5E646F", length=2)
cb.outline.set_edgecolor("#D6D9DF"); cb.outline.set_linewidth(0.6)

fig.text(0.175, 0.062, "Unpainted cells: q ≥ 0.05 (Benjamini–Hochberg across all "
         f"{nF*nD:,} tests)", fontsize=7, color="#5E646F")
fig.text(0.175, 0.038, f"MIMIC-III-Ext-PPG · {nD} ICD-10 codes (≥100 patients) × {nF} PPG waveform "
         "features · n = 6,113 patients", fontsize=7, color="#5E646F")
fig.savefig(f"{H}/reports/figure2_phenome_wide.png", bbox_inches="tight", facecolor="white")
print("saved", nF, "x", nD, "| sig cells", int(sig.values.sum()), "| vmax", round(vmax,3))
