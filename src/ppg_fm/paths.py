"""프로젝트·데이터 경로 해석.

프로젝트 루트는 이 파일 위치에서 역산한다. 데이터 루트는 configs/paths.yaml의
data_root를 따르되, 그 경로가 없으면 프로젝트 루트 옆의 data 디렉터리를 쓴다
(윈도우 D:/data ↔ 리눅스 마운트 경로를 코드 수정 없이 오간다).
"""
from pathlib import Path
import os
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "paths.yaml"


def cfg() -> dict:
    with open(CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)


def data_root() -> Path:
    env = os.environ.get("PPG_FM_DATA_ROOT")
    if env:
        return Path(env)
    p = Path(cfg()["data_root"])
    if p.exists():
        return p
    alt = ROOT.parent / "data"
    if alt.exists():
        return alt
    raise FileNotFoundError(
        f"데이터 루트를 찾지 못했다: {p} 또는 {alt}. "
        "configs/paths.yaml의 data_root를 고치거나 PPG_FM_DATA_ROOT를 설정하라."
    )


def ext_ppg() -> Path:
    """MIMIC-III-Ext-PPG 배포 디렉터리."""
    return data_root() / "mimic_iii_ext_ppg" / "DESTINATION"


def metadata_csv() -> Path:
    return ext_ppg() / "metadata.csv"


def interim(name: str = "") -> Path:
    p = ROOT / "data" / "interim"
    p.mkdir(parents=True, exist_ok=True)
    return p / name if name else p


def reports(name: str = "") -> Path:
    p = ROOT / "reports"
    p.mkdir(parents=True, exist_ok=True)
    return p / name if name else p
