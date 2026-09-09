"""추출 계획표 1회 생성 — 환자당 N세그먼트를 등간격으로 고른 작은 CSV."""
import numpy as np, pandas as pd, gc, sys
N = int(sys.argv[1]) if len(sys.argv) > 1 else 10
H = "/sessions/rcw-01p75qppzlc1iwmpuvmxtmpo/mnt/ppg_fm"
d = pd.read_parquet(f"{H}/data/interim/seg_index.parquet",
                    columns=["folder_path", "subject", "rhythm", "has_abp", "hq"])
d = d[d.hq].drop(columns="hq")
d["subject"] = d.subject.astype(str)
gc.collect()
print("hq 세그먼트", len(d), "환자", d.subject.nunique(), flush=True)
idx = d.groupby("subject", sort=False).indices      # 정렬 복사 없음
pick = []
for s, ii in idx.items():
    ii = np.sort(ii)                                 # 원본 순서 = 대략 시간 순
    k = min(N, len(ii))
    pick.append(ii[np.unique(np.linspace(0, len(ii) - 1, k).round().astype(int))])
sel = np.concatenate(pick)
plan = d.iloc[sel].copy()
plan.to_csv(f"{H}/data/interim/extract_plan.csv", index=False)
print("계획 세그먼트", len(plan), "환자", plan.subject.nunique(), flush=True)
