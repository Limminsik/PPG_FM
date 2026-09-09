"""환경 점검: 파이썬/GPU/패키지/데이터 경로."""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ppg_fm.config import load  # noqa: E402


def main():
    print(f"Python {sys.version.split()[0]}  ({sys.executable})")
    if sys.version_info < (3, 10):
        print("  ! 주의: pyPPG 등 일부 패키지가 3.10+ 를 요구할 수 있음")

    print("\n[패키지]")
    for m in ["numpy", "pandas", "scipy", "wfdb", "vitaldb", "torch",
              "pyPPG", "neurokit2", "sklearn", "matplotlib"]:
        try:
            mod = importlib.import_module(m)
            print(f"  OK   {m:12s} {getattr(mod, '__version__', '')}")
        except Exception as e:
            print(f"  MISS {m:12s} ({type(e).__name__})")

    print("\n[GPU]")
    try:
        import torch
        print(f"  cuda available : {torch.cuda.is_available()}")
        print(f"  torch version  : {torch.__version__}")
        if torch.cuda.is_available():
            print(f"  device         : {torch.cuda.get_device_name(0)}")
            print(f"  capability     : {torch.cuda.get_device_capability(0)}")
            free, total = torch.cuda.mem_get_info()
            print(f"  memory         : {total/1e9:.1f} GB")
    except Exception as e:
        print(f"  torch 확인 실패: {e}")

    print("\n[데이터 경로]")
    cfg = load()
    for name, d in cfg["datasets"].items():
        p = Path(d["root"])
        mark = "OK  " if p.exists() else "MISS"
        print(f"  {mark} {name:20s} {p}")


if __name__ == "__main__":
    main()
