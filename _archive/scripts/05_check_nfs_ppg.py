"""NFS(및 임의 수면 코호트) EDF에 PPG(Pleth) 채널이 있는지 확인.

문서 1 §6 미확인 항목. SHHS/WSC는 없음이 확인됐다.
"""
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ppg_fm.config import load  # noqa: E402

PPG_KEYS = ("PLETH", "PPG", "PLET", "PULSE")


def edf_channels(path):
    with open(path, "rb") as f:
        f.seek(252)
        ns = int(f.read(4).decode().strip())
        f.seek(256)
        labels = [f.read(16).decode("latin-1").strip() for _ in range(ns)]
        f.seek(256 + ns * (16 + 80 + 8 + 8 + 8 + 8 + 8 + 80))
        nsamp = [int(f.read(8).decode().strip()) for _ in range(ns)]
        f.seek(244)
        dur = float(f.read(8).decode().strip())
    return list(zip(labels, [n / dur for n in nsamp]))


def main():
    cfg = load()
    for name in ["nfs", "shhs", "wsc"]:
        root = cfg["datasets"].get(name, {}).get("root")
        if not root or not Path(root).exists():
            print(f"--- {name}: 경로 없음 ---")
            continue
        files = glob.glob(str(Path(root) / "**" / "*.edf"), recursive=True)
        print(f"--- {name}: EDF {len(files):,}개 ---")
        if not files:
            continue
        chans = edf_channels(files[0])
        has = [l for l, _ in chans if any(k in l.upper() for k in PPG_KEYS)]
        for l, r in chans:
            mark = " <== PPG?" if any(k in l.upper() for k in PPG_KEYS) else ""
            print(f"   {l:20s} {r:8.1f} Hz{mark}")
        print(f"   => PPG 채널: {has if has else '없음'}\n")


if __name__ == "__main__":
    main()
