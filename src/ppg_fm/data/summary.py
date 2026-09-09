"""환자 요약 — 박동 분포를 환자값 43개로 압축.

중앙값 20 + 박동간 IQR 20(원단위) + 검출률 3.
요약 방식은 네 가지(중앙값·분위수·앙상블·대표 박동)를 실측 비교해 중앙값으로 확정했다.
IQR을 중앙값으로 나누지 않는 이유는 부호가 바뀌는 특징에서 분모가 0에 가까워지면
값이 발산하기 때문이다.
"""
from pathlib import Path
import pandas as pd

from .. import paths
from ..features import MORPH


def build(beats_path: Path = None, index_path: Path = None,
          out: Path = None) -> Path:
    beats_path = beats_path or paths.interim("beat_features_v2.csv")
    index_path = index_path or paths.interim("seg_index.parquet")
    out = out or paths.interim("patient_features_v2.csv")

    use = ["subject", "IBI", "rhythm", "has_abp"] + MORPH
    dtype = {c: "float32" for c in MORPH + ["IBI"]}
    dtype["subject"] = str
    B = pd.read_csv(beats_path, usecols=use, dtype=dtype)

    g = B.groupby("subject", sort=True)
    med = g[MORPH].median()
    iqr = g[MORPH].quantile(.75) - g[MORPH].quantile(.25)
    iqr.columns = [c + "_iqr" for c in MORPH]

    P = med.join(iqr)
    P["HR"] = 60000.0 / g.IBI.median()
    P["n_beats"] = g.size()
    P["cd_rate"] = g.d_over_a.apply(lambda s: s.notna().mean())
    P["ri_rate"] = g.RI.apply(lambda s: s.notna().mean())
    P["lvet_rate"] = g.LVET.apply(lambda s: s.notna().mean())
    P["abp_frac"] = g.has_abp.mean()
    P["sr_frac"] = g.rhythm.apply(lambda s: (s == "SR").mean())
    P["af_frac"] = g.rhythm.apply(lambda s: s.isin(["AF", "AFLT"]).mean())
    P["pace_frac"] = g.rhythm.apply(lambda s: s.str.contains("PACE", na=False).mean())
    P["rhythm_mode"] = g.rhythm.agg(lambda s: s.mode().iat[0] if len(s.mode()) else "NA")
    P = P.reset_index()

    d = pd.read_parquet(index_path, columns=["subject", "age", "gender"])
    d["subject"] = d.subject.astype(str)
    P = P.merge(d.groupby("subject").first().reset_index(), on="subject", how="left")
    P["male"] = (P.gender.astype(str).str.upper().str[0] == "M").astype(int)
    P.to_csv(out, index=False)
    return out
