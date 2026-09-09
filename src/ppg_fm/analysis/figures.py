"""Figure 2 — 진단코드 × 파형 특징.

행은 파형 특징 43개를 계열별로 묶고, 열은 ICD-10 코드를 장(chapter)별로 묶어
장 안에서는 유의 특징 수 내림차순으로 놓는다. 셀 색은 log2 오즈비이며,
Bonferroni를 통과하지 못한 셀은 칠하지 않는다.

부가 패널
    상단 막대  질환별 유의 특징 수 — 어느 질환이 파형에 넓게 나타나는가
    우측 막대  특징별 유의 질환 수 — 어느 특징이 여러 질환에 걸쳐 움직이는가
    상단 색띠  ICD 장. 순환계부터 배치한다
"""
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import Rectangle

from .. import paths
from ..features import PATIENT_FAMILY
from .logistic import bonferroni

CHAPTER = {"A": "Infectious", "B": "Infectious", "C": "Neoplasm", "D": "Blood/Neoplasm",
           "E": "Endocrine", "F": "Mental", "G": "Nervous", "H": "Sensory",
           "I": "Circulatory", "J": "Respiratory", "K": "Digestive", "L": "Skin",
           "M": "Musculoskeletal", "N": "Genitourinary", "Q": "Congenital",
           "R": "Symptoms", "S": "Injury", "T": "Injury",
           "V": "External", "W": "External", "X": "External", "Y": "External",
           "Z": "Health status"}
CHAPTER_ORDER = ["Circulatory", "Respiratory", "Endocrine", "Genitourinary", "Digestive",
                 "Blood/Neoplasm", "Infectious", "Nervous", "Mental", "Symptoms",
                 "Musculoskeletal", "Injury", "Neoplasm", "Skin", "Sensory",
                 "External", "Health status", "Congenital"]
CHAPTER_TONE = ["#2C3E50", "#3D5A6C", "#4E7A63", "#6B4E8C", "#8A6A1C", "#9E3B4A",
                "#5E646F", "#3F5F8A", "#7A5C8A", "#6B7280", "#4A6B57", "#8C6B4A",
                "#7A4A5C", "#5C7A8A", "#8A7A4A", "#6B6B6B", "#4A5A7A", "#7A7A5A"]

FEATS = [f for _, fs in PATIENT_FAMILY for f in fs]

# 색 스케일 — 모든 Figure 2 판이 같은 값을 쓴다. log2 오즈비 ±1 = 오즈비 0.5~2.0.
# 유의 셀 |log2 OR|의 99 백분위수가 1.005여서 이 값을 반올림해 고정했다.
# 이 범위를 벗어나는 셀(855개 중 9개)은 양 끝 색으로 눌린다.
VMAX = 1.0


def _or_ticks(vmax=VMAX):
    """색막대 눈금 — log2 값과 오즈비를 함께 적는다."""
    t = [v for v in (-1.0, -0.5, 0.0, 0.5, 1.0) if abs(v) <= vmax + 1e-9]
    return t, [f"{v:+.1f}\n({2 ** v:.2f})".replace("+0.0", " 0.0") for v in t]


def figure2(R: pd.DataFrame, out: Path = None, dpi: int = 200,
            alpha: float = 0.05) -> Path:
    """오즈비 결과표 → Figure 2 PNG."""
    out = out or paths.reports("02_logistic/02_association_figure2/figure2_or.png")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    bonf = bonferroni(len(R), alpha)

    E = R.pivot(index="feat", columns="icd10", values="logOR").reindex(FEATS)
    P = R.pivot(index="feat", columns="icd10", values="p").reindex(FEATS)
    sig = P < bonf
    n_by_code = sig.sum(axis=0)          # 질환별 유의 특징 수
    n_by_feat = sig.sum(axis=1)          # 특징별 유의 질환 수

    meta = pd.DataFrame({"code": list(E.columns)})
    meta["chap"] = meta.code.str[0].map(CHAPTER).fillna("Other")
    meta["nsig"] = meta.code.map(n_by_code)
    meta["rank"] = meta.chap.map({c: i for i, c in enumerate(CHAPTER_ORDER)}).fillna(99)
    meta = meta.sort_values(["rank", "nsig"], ascending=[True, False]).reset_index(drop=True)
    cols = meta.code.tolist()
    E, sig, n_by_code = E[cols], sig[cols], n_by_code[cols]

    V = np.ma.masked_where(~sig.values, E.values / np.log(2))     # log2 오즈비
    vmax = VMAX
    cmap = LinearSegmentedColormap.from_list(
        "or", ["#17607E", "#7FA9BC", "#E9EBEF", "#C98F98", "#9E3B4A"])
    cmap.set_bad("#F7F8FA")
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)

    nF, nD = len(FEATS), len(cols)
    fig = plt.figure(figsize=(nD * .115 + 4.2, nF * .20 + 4.0), dpi=dpi)
    gs = fig.add_gridspec(3, 3, height_ratios=[.9, .34, nF * .20],
                          width_ratios=[nD * .115, 1.5, .34],
                          hspace=.06, wspace=.05,
                          left=.175, right=.965, top=.915, bottom=.215)

    fig.text(.175, .955, "Figure 2 · PPG waveform features × ICD-10 diagnosis codes",
             fontsize=12, fontweight="bold", color="#191C22", ha="left")
    fig.text(.175, .938, "Unadjusted logistic regression · effect size = odds ratio per 1 SD · "
             "Bonferroni-corrected", fontsize=8.5, color="#5E646F", ha="left")

    # 상단 막대 — 질환별 유의 특징 수
    axt = fig.add_subplot(gs[0, 0])
    axt.bar(range(nD), n_by_code.values, width=.78, color="#5E646F", linewidth=0)
    axt.set_xlim(-.5, nD - .5); axt.set_xticks([])
    axt.set_ylabel(f"Significant\nfeatures\n(of {nF})", fontsize=7.5, color="#191C22", labelpad=6)
    axt.tick_params(axis="y", labelsize=7, colors="#5E646F", length=2)
    for s in ("top", "right", "bottom"):
        axt.spines[s].set_visible(False)
    axt.spines["left"].set_color("#D6D9DF")
    axt.grid(axis="y", color="#EAECF0", lw=.6); axt.set_axisbelow(True)

    # ICD 장 색띠
    axb = fig.add_subplot(gs[1, 0])
    axb.set_xlim(-.5, nD - .5); axb.set_ylim(0, 1); axb.axis("off")
    tone = dict(zip(CHAPTER_ORDER, CHAPTER_TONE))
    i = 0
    for _, g in meta.groupby("rank", sort=True):
        name, n = g.chap.iloc[0], len(g)
        axb.add_patch(Rectangle((i - .5, .12), n, .76,
                                facecolor=tone.get(name, "#6B6B6B"), lw=0))
        if n >= 5:
            axb.text(i + n / 2 - .5, .5, name, ha="center", va="center",
                     fontsize=6.6, color="white", fontweight="600")
        i += n

    # 본체
    ax = fig.add_subplot(gs[2, 0])
    ax.imshow(V, aspect="auto", cmap=cmap, norm=norm, interpolation="nearest")
    ax.set_yticks(range(nF))
    ax.set_yticklabels(FEATS, fontsize=6.4, color="#191C22", fontfamily="monospace")
    ax.set_xticks(range(nD))
    ax.set_xticklabels(cols, fontsize=5.0, rotation=90, color="#5E646F")
    ax.tick_params(length=1.6, colors="#8C93A0")
    for s in ax.spines.values():
        s.set_color("#D6D9DF"); s.set_linewidth(.7)

    i = 0
    for fam, fs in PATIENT_FAMILY:
        n = len(fs)
        if i:
            ax.axhline(i - .5, color="#191C22", lw=.9)
        ax.text(-.118, 1 - (i + n / 2) / nF, fam, transform=ax.transAxes, rotation=90,
                ha="center", va="center", fontsize=7.4, color="#191C22", fontweight="600")
        i += n
    i = 0
    for _, g in meta.groupby("rank", sort=True):
        i += len(g)
        if i < nD:
            ax.axvline(i - .5, color="#FFFFFF", lw=.8)

    # 우측 막대 — 특징별 유의 질환 수
    axr = fig.add_subplot(gs[2, 2])
    axr.barh(range(nF), n_by_feat.reindex(FEATS).values, height=.78,
             color="#5E646F", linewidth=0)
    axr.set_ylim(nF - .5, -.5); axr.set_yticks([])
    axr.set_xlabel(f"Significant\ncodes (of {nD})", fontsize=7.5, color="#191C22")
    axr.tick_params(axis="x", labelsize=7, colors="#5E646F", length=2)
    for s in ("top", "right", "left"):
        axr.spines[s].set_visible(False)
    axr.spines["bottom"].set_color("#D6D9DF")
    axr.grid(axis="x", color="#EAECF0", lw=.6); axr.set_axisbelow(True)

    # 색막대
    cax = fig.add_axes([.755, .095, .19, .013])
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm); sm.set_array([])
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
    t, lab = _or_ticks()
    cb.set_ticks(t); cb.set_ticklabels(lab)
    cb.set_label("log$_2$ odds ratio per 1 SD  (odds ratio in parentheses) · unadjusted",
                 fontsize=7, color="#191C22", labelpad=4)
    cb.ax.tick_params(labelsize=6.5, colors="#5E646F", length=2)
    cb.outline.set_edgecolor("#D6D9DF"); cb.outline.set_linewidth(.6)

    n_sig = int(sig.values.sum())
    n_clip = int((np.abs(V.compressed()) > vmax).sum())
    lines = [
        ("Cell", "odds ratio for carrying that ICD-10 code per 1 SD increase of the feature "
                 "(logistic regression, one model per cell, no covariate adjustment). "
                 "Red = OR > 1, blue = OR < 1."),
        ("Colour scale", f"log$_2$ odds ratio, fixed at ±{vmax:.1f} "
                         f"(odds ratio {2 ** -vmax:.2f}–{2 ** vmax:.2f}) across every Figure 2 panel; "
                         f"{n_clip} cells beyond that range are drawn at the end colour."),
        ("Unpainted", f"p ≥ {bonf:.1e} (Bonferroni across all {nF * nD:,} tests). "
                      f"{n_sig:,} of {nF * nD:,} cells ({100 * n_sig / (nF * nD):.1f}%) are significant. "
                      "An unpainted cell is not evidence of no difference."),
        ("Axes", f"columns = {nD} ICD-10 3-character codes, grouped by chapter (colour band) and "
                 "ordered within a chapter by number of significant features; "
                 f"rows = {nF} patient-summary PPG features, grouped by family (labels at left)."),
        ("Bars", f"top = how many of the {nF} features are significant for that code; "
                 f"right = how many of the {nD} codes are significant for that feature."),
        ("Cohort", f"MIMIC-III-Ext-PPG · 6,113 patients · all rhythms · 10 segments per patient · "
                   f"2,361,435 beats · patient value = median across beats · "
                   f"{nD} ICD-10 codes with ≥100 patients × {nF} features."),
    ]
    y = .165
    for k, v in lines:
        fig.text(.175, y, k, fontsize=7, color="#191C22", fontweight="bold", ha="left")
        fig.text(.222, y, v, fontsize=7, color="#5E646F", ha="left")
        y -= .019
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return Path(out)


# ─────────────────────────────────────────────────────────────
# Figure 2 변형 — 같은 자료를 다르게 자른 판
# ─────────────────────────────────────────────────────────────

def _prep(R, alpha=0.05):
    bonf = bonferroni(len(R), alpha)
    E = R.pivot(index="feat", columns="icd10", values="logOR").reindex(FEATS)
    P = R.pivot(index="feat", columns="icd10", values="p").reindex(FEATS)
    name = R.drop_duplicates("icd10").set_index("icd10").get("en", pd.Series(dtype=str))
    return E, P, P < bonf, bonf, name


def _cmap():
    c = LinearSegmentedColormap.from_list(
        "or", ["#17607E", "#7FA9BC", "#E9EBEF", "#C98F98", "#9E3B4A"])
    c.set_bad("#F7F8FA")
    return c


def _label(code, name):
    t = name.get(code) if hasattr(name, "get") else None
    return f"{code}  {t}" if isinstance(t, str) and t else code


def _heat(ax, V, rows, cols, name, vmax, fontsize=7.5):
    im = ax.imshow(V, aspect="auto", cmap=_cmap(),
                   norm=TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax), interpolation="nearest")
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([_label(c, name) for c in cols], fontsize=fontsize,
                       rotation=90, color="#191C22")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(rows, fontsize=fontsize, color="#191C22", fontfamily="monospace")
    ax.tick_params(length=1.6, colors="#8C93A0")
    for s in ax.spines.values():
        s.set_color("#D6D9DF"); s.set_linewidth(.7)
    return im


def _family_lines(ax, rows):
    i = 0
    for fam, fs in PATIENT_FAMILY:
        n = sum(1 for f in fs if f in rows)
        if n == 0:
            continue
        if i:
            ax.axhline(i - .5, color="#191C22", lw=.9)
        ax.annotate(fam, xy=(0, 1 - (i + n / 2) / len(rows)), xycoords="axes fraction",
                    xytext=(-108, 0), textcoords="offset points", rotation=90,
                    ha="center", va="center", fontsize=7.6, color="#191C22",
                    fontweight="bold")
        i += n


def figure2_compact(R, min_sig: int = 5, out: Path = None, dpi: int = 200) -> Path:
    """실제로 신호가 있는 것만 — 유의 특징 min_sig개 이상인 질환, 유의 질환이 있는 특징."""
    out = out or paths.reports("02_logistic/02_association_figure2/figure2_compact.png")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    E, P, sig, bonf, name = _prep(R)

    by_code = sig.sum(axis=0)
    cols = [c for c in E.columns if by_code[c] >= min_sig]
    meta = pd.DataFrame({"code": cols})
    meta["chap"] = meta.code.str[0].map(CHAPTER).fillna("Other")
    meta["rank"] = meta.chap.map({c: i for i, c in enumerate(CHAPTER_ORDER)}).fillna(99)
    meta["nsig"] = meta.code.map(by_code)
    meta = meta.sort_values(["rank", "nsig"], ascending=[True, False])
    cols = meta.code.tolist()

    rows = [f for f in FEATS if sig.loc[f, cols].sum() > 0]
    V = np.ma.masked_where(~sig.loc[rows, cols].values, E.loc[rows, cols].values / np.log(2))
    vmax = VMAX

    fig, ax = plt.subplots(figsize=(len(cols) * .30 + 4.5, len(rows) * .26 + 4.2), dpi=dpi)
    im = _heat(ax, V, rows, cols, name, vmax)
    _family_lines(ax, rows)
    i = 0
    for _, g in meta.groupby("rank", sort=True):
        i += len(g)
        if i < len(cols):
            ax.axvline(i - .5, color="#FFFFFF", lw=1.2)
    cb = fig.colorbar(im, ax=ax, fraction=.018, pad=.012)
    t, lab = _or_ticks()
    cb.set_ticks(t); cb.set_ticklabels(lab)
    cb.set_label("log$_2$ odds ratio per 1 SD\n(odds ratio in parentheses)", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    ax.set_xlabel("ICD-10 code  (grouped by chapter)", fontsize=9, labelpad=6)
    ax.set_ylabel("PPG waveform feature (patient summary)", fontsize=9, labelpad=6)
    ax.set_title(f"Figure 2 (compact) · codes with ≥{min_sig} significant features — "
                 f"{len(cols)} of {E.shape[1]} codes × {len(rows)} of {len(FEATS)} features\n"
                 f"Cell = odds ratio per 1 SD · unadjusted logistic · unpainted = "
                 f"p ≥ {bonf:.1e} (Bonferroni, {len(R):,} tests) · scale fixed at OR "
                 f"{2 ** -vmax:.2f}–{2 ** vmax:.2f}",
                 fontsize=9.5, pad=12)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return Path(out)


def figure2_chapter(R, chapter: str = "Circulatory", min_sig: int = 1,
                    out: Path = None, dpi: int = 200) -> Path:
    """한 ICD 장만 확대 — 순환계처럼 관심 계통을 자세히 본다."""
    out = out or paths.reports(
        f"02_logistic/02_association_figure2/figure2_{chapter.lower().replace('/', '_')}.png")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    E, P, sig, bonf, name = _prep(R)

    by_code = sig.sum(axis=0)
    cols = [c for c in E.columns
            if CHAPTER.get(c[0], "Other") == chapter and by_code[c] >= min_sig]
    cols = sorted(cols, key=lambda c: -by_code[c])
    rows = FEATS
    V = np.ma.masked_where(~sig.loc[rows, cols].values, E.loc[rows, cols].values / np.log(2))
    vmax = VMAX

    fig, ax = plt.subplots(figsize=(len(cols) * .34 + 4.5, len(rows) * .24 + 4.5), dpi=dpi)
    im = _heat(ax, V, rows, cols, name, vmax)
    _family_lines(ax, rows)
    cb = fig.colorbar(im, ax=ax, fraction=.02, pad=.012)
    t, lab = _or_ticks()
    cb.set_ticks(t); cb.set_ticklabels(lab)
    cb.set_label("log$_2$ odds ratio per 1 SD\n(odds ratio in parentheses)", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    ax.set_xlabel("ICD-10 code  (ordered by number of significant features)",
                  fontsize=9, labelpad=6)
    ax.set_ylabel("PPG waveform feature (patient summary)", fontsize=9, labelpad=6)
    ax.set_title(f"Figure 2 ({chapter}) — {len(cols)} ICD-10 codes × {len(rows)} features\n"
                 f"Cell = odds ratio per 1 SD · unadjusted logistic · unpainted = "
                 f"p ≥ {bonf:.1e} (Bonferroni, {len(R):,} tests) · scale fixed at OR "
                 f"{2 ** -vmax:.2f}–{2 ** vmax:.2f}",
                 fontsize=9.5, pad=12)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return Path(out)


def figure2_panels(R, chapters=None, min_sig: int = 2,
                   out: Path = None, dpi: int = 190) -> Path:
    """장별 소패널 — 계통마다 어떤 특징이 움직이는지 나란히 놓고 본다."""
    out = out or paths.reports("02_logistic/02_association_figure2/figure2_panels.png")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    E, P, sig, bonf, name = _prep(R)
    by_code = sig.sum(axis=0)
    chapters = chapters or ["Circulatory", "Respiratory", "Genitourinary",
                            "Endocrine", "Digestive", "Symptoms"]

    groups = []
    for ch in chapters:
        cs = [c for c in E.columns
              if CHAPTER.get(c[0], "Other") == ch and by_code[c] >= min_sig]
        if cs:
            groups.append((ch, sorted(cs, key=lambda c: -by_code[c])))
    widths = [len(cs) for _, cs in groups]
    vmax = VMAX

    fig = plt.figure(figsize=(sum(widths) * .26 + 4.0, len(FEATS) * .21 + 3.4), dpi=dpi)
    gs = fig.add_gridspec(1, len(groups), width_ratios=widths, wspace=.06,
                          left=.14, right=.965, top=.88, bottom=.20)
    tone = dict(zip(CHAPTER_ORDER, CHAPTER_TONE))
    for k, (ch, cs) in enumerate(groups):
        ax = fig.add_subplot(gs[0, k])
        V = np.ma.masked_where(~sig.loc[FEATS, cs].values,
                               E.loc[FEATS, cs].values / np.log(2))
        im = ax.imshow(V, aspect="auto", cmap=_cmap(),
                       norm=TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax), interpolation="nearest")
        ax.set_xticks(range(len(cs)))
        ax.set_xticklabels(cs, fontsize=6.2, rotation=90, color="#5E646F")
        ax.set_yticks(range(len(FEATS)))
        ax.set_yticklabels(FEATS if k == 0 else [], fontsize=6.4,
                           color="#191C22", fontfamily="monospace")
        ax.tick_params(length=1.6, colors="#8C93A0")
        for s in ax.spines.values():
            s.set_color("#D6D9DF"); s.set_linewidth(.7)
        i = 0
        for _, fs in PATIENT_FAMILY:
            i += len(fs)
            if i < len(FEATS):
                ax.axhline(i - .5, color="#191C22", lw=.8)
        ax.set_title(ch, fontsize=8.5, color="white", fontweight="bold", pad=6,
                     backgroundcolor=tone.get(ch, "#6B6B6B"))
    cax = fig.add_axes([.40, .055, .22, .014])
    cb = fig.colorbar(im, cax=cax, orientation="horizontal")
    t, lab = _or_ticks()
    cb.set_ticks(t); cb.set_ticklabels([l.replace("\n", " ") for l in lab])
    cb.set_label("log$_2$ odds ratio per 1 SD  (odds ratio in parentheses)", fontsize=7.5)
    cb.ax.tick_params(labelsize=6.5)
    fig.suptitle(f"Figure 2 by ICD chapter · codes with ≥{min_sig} significant features\n"
                 f"Cell = odds ratio per 1 SD · unadjusted logistic · unpainted = "
                 f"p ≥ {bonf:.1e} (Bonferroni, {len(R):,} tests) · "
                 f"scale fixed at OR {2 ** -vmax:.2f}–{2 ** vmax:.2f} · rows grouped by feature family",
                 fontsize=9.5, y=.975)
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return Path(out)


def figure2_top_cells(R, n: int = 40, out: Path = None, dpi: int = 200) -> Path:
    """효과가 큰 셀만 — 오즈비와 신뢰구간을 값으로 읽는 판."""
    out = out or paths.reports("02_logistic/02_association_figure2/figure2_top_cells.png")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    bonf = bonferroni(len(R))
    S = R[R.p < bonf].copy()
    S["abs"] = S.logOR.abs()
    S = S.nlargest(n, "abs").sort_values("logOR")
    lab = [f"{r.icd10} {r.en if isinstance(r.en, str) else ''} × {r.feat}"
           for r in S.itertuples()]
    col = ["#9E3B4A" if v > 0 else "#17607E" for v in S.logOR]
    size = 26 + 120 * (-np.log10(S.p) / -np.log10(S.p).max())

    fig, ax = plt.subplots(figsize=(9.2, n * .24 + 1.8), dpi=dpi)
    ax.axvline(1, color="#8C93A0", lw=.8)
    ax.hlines(range(n), 1, S.OR, color="#D6D9DF", lw=1.1)
    ax.scatter(S.OR, range(n), s=size, c=col, zorder=3, edgecolor="white", linewidth=.6)
    ax.set_yticks(range(n)); ax.set_yticklabels(lab, fontsize=7.4)
    ax.set_xscale("log")
    ax.set_xlabel("odds ratio per 1 SD increase of the feature  (log scale, 1.0 = no association)",
                  fontsize=9)
    ax.grid(axis="x", color="#EAECF0", lw=.7); ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#D6D9DF")
    ax.set_title(f"Top {n} cells by effect size · Bonferroni p < {bonf:.1e} · unadjusted\n"
                 "dot size = $-$log$_{10}$ p · red OR > 1 · blue OR < 1",
                 fontsize=9.5, pad=10)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return Path(out)


def figure2_feature_breadth(R, out: Path = None, dpi: int = 200) -> Path:
    """특징 쪽에서 본 판 — 어느 특징이 몇 개 질환에서, 어느 방향으로 움직이는가."""
    out = out or paths.reports("02_logistic/02_association_figure2/figure2_feature_breadth.png")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    bonf = bonferroni(len(R))
    S = R[R.p < bonf]
    pos = S[S.logOR > 0].groupby("feat").size().reindex(FEATS).fillna(0)
    neg = S[S.logOR < 0].groupby("feat").size().reindex(FEATS).fillna(0)

    fig, ax = plt.subplots(figsize=(8.4, len(FEATS) * .26 + 2.2), dpi=dpi)
    y = np.arange(len(FEATS))
    ax.barh(y, -neg.values, color="#17607E", height=.74, label="OR < 1")
    ax.barh(y, pos.values, color="#9E3B4A", height=.74, label="OR > 1")
    ax.axvline(0, color="#191C22", lw=.9)
    ax.set_yticks(y); ax.set_yticklabels(FEATS, fontsize=7.4, fontfamily="monospace")
    ax.set_ylim(len(FEATS) - .5, -.5)
    ax.set_xlabel("significant diseases", fontsize=9)
    ticks = ax.get_xticks()
    ax.set_xticks(ticks); ax.set_xticklabels([f"{abs(int(t))}" for t in ticks], fontsize=8)
    i = 0
    for fam, fs in PATIENT_FAMILY:
        if i:
            ax.axhline(i - .5, color="#D6D9DF", lw=.8)
        ax.text(ax.get_xlim()[0] * .96, i + len(fs) / 2 - .5, fam, ha="left", va="center",
                fontsize=7.6, color="#8C93A0", fontweight="bold")
        i += len(fs)
    ax.grid(axis="x", color="#EAECF0", lw=.7); ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#D6D9DF")
    ax.legend(fontsize=8, frameon=False, loc="upper right")
    ax.set_xlabel("number of ICD-10 codes reaching significance (of 172)", fontsize=9)
    ax.set_title("Figure 2 (feature view) — how many codes each feature reaches, by direction\n"
                 f"Red = OR > 1 (code more often seen when the feature is high) · "
                 f"blue = OR < 1 · Bonferroni p < {bonf:.1e}", fontsize=9.5, pad=10)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return Path(out)
