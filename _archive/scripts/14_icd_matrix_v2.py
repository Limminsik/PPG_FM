"""v2 코호트(6,113명)의 ICD 매트릭스 재구성 — metadata.csv 청크 스캔."""
import os, ast, numpy as np, pandas as pd
from collections import defaultdict
H = os.path.expanduser("~/mnt/ppg_fm")
MD = os.path.expanduser("~/mnt/data/mimic_iii_ext_ppg/DESTINATION/metadata.csv")
P = pd.read_csv(f"{H}/data/interim/patient_features_v2.csv", usecols=["subject"], dtype={"subject": str})
keep = set(P.subject)
pat = defaultdict(set)
cols = ["subject_id", "icd10_truncated"]
for ch in pd.read_csv(MD, usecols=cols, dtype={"subject_id": str}, chunksize=500_000):
    ch = ch[ch.subject_id.isin(keep)]
    ch = ch[ch.icd10_truncated.notna()]
    for s, v in zip(ch.subject_id.values, ch.icd10_truncated.values):
        if s in pat and len(pat[s]) > 0:
            continue                       # 환자당 1회면 충분
        try:
            codes = ast.literal_eval(v) if isinstance(v, str) and v.startswith("[") else [v]
        except Exception:
            codes = [v]
        pat[s] |= {str(c).strip()[:3] for c in codes if str(c).strip()}
print("ICD 확보 환자", len(pat), flush=True)
allc = sorted({c for v in pat.values() for c in v})
rows = []
subs = sorted(keep)
for s in subs:
    v = pat.get(s, set())
    rows.append([1 if c in v else 0 for c in allc])
M = pd.DataFrame(rows, columns=allc, dtype=np.int8)
M.insert(0, "subject", subs)
n = M[allc].sum()
print("코드 총수", len(allc), "| ≥50명", int((n >= 50).sum()), "| ≥100명", int((n >= 100).sum()), flush=True)
M.to_csv(f"{H}/data/interim/patient_icd_matrix_v2.csv", index=False)
print("저장 완료", M.shape, flush=True)
