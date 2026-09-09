"""경로/설정 로더 (Python 3.9 호환)."""
from pathlib import Path
from typing import Optional
import yaml

ROOT = Path(__file__).resolve().parents[2]


def load(cfg_name: str = "paths.yaml") -> dict:
    with open(ROOT / "configs" / cfg_name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def ds(name: str, cfg: Optional[dict] = None) -> dict:
    cfg = cfg or load()
    return cfg["datasets"][name]


def out_dir(kind: str = "reports") -> Path:
    p = ROOT / load()["out"][kind]
    p.mkdir(parents=True, exist_ok=True)
    return p
