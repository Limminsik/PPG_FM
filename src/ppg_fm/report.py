"""노트북별 산출물 관리.

노트북 하나가 만드는 표·그림은 그 노트북 이름의 폴더 아래에만 쌓인다.

    reports/
      01_dataset/02_cohort_definition/
        sqi_distribution.csv
        cohort_flow.csv
        manifest.json          ← 무엇을 언제 어떤 환경에서 만들었는가

사용법

    from ppg_fm.report import Report
    rep = Report("01_dataset/02_cohort_definition")
    rep.table(dist, "sqi_distribution.csv")
    rep.figure(fig, "cohort_flow.png")
    rep.done()
"""
from pathlib import Path
from datetime import datetime
import json
import platform
import sys

import pandas as pd

from . import paths

_PKGS = ["numpy", "pandas", "scipy", "statsmodels", "matplotlib", "wfdb", "pyarrow"]


def _versions() -> dict:
    import importlib
    out = {"python": sys.version.split()[0], "platform": platform.platform()}
    for m in _PKGS:
        try:
            out[m] = importlib.import_module(m).__version__
        except Exception:
            pass
    return out


class Report:
    """한 노트북의 산출물 폴더."""

    def __init__(self, name: str, root: Path = None):
        self.name = name.strip("/")
        self.dir = (root or paths.reports()) / self.name
        self.dir.mkdir(parents=True, exist_ok=True)
        self.started = datetime.now()
        self.items = []

    # ── 경로 ────────────────────────────────────────────────
    def path(self, filename: str) -> Path:
        return self.dir / filename

    def exists(self, filename: str) -> bool:
        return self.path(filename).exists()

    # ── 저장 ────────────────────────────────────────────────
    def table(self, df: pd.DataFrame, filename: str, note: str = "") -> Path:
        p = self.path(filename)
        if filename.endswith(".parquet"):
            df.to_parquet(p, index=False)
        else:
            df.to_csv(p, index=False, encoding="utf-8-sig")
        self._log(filename, note, rows=len(df), cols=df.shape[1])
        return p

    def figure(self, fig, filename: str, note: str = "", dpi: int = 170) -> Path:
        p = self.path(filename)
        fig.savefig(p, dpi=dpi, bbox_inches="tight")
        self._log(filename, note)
        return p

    def text(self, s: str, filename: str, note: str = "") -> Path:
        p = self.path(filename)
        p.write_text(s, encoding="utf-8")
        self._log(filename, note)
        return p

    def adopt(self, src: Path, note: str = "") -> Path:
        """다른 곳에서 만들어진 파일을 이 노트북의 산출물로 등록한다."""
        src = Path(src)
        self._log(src.name, note)
        return src

    # ── 기록 ────────────────────────────────────────────────
    def _log(self, filename: str, note: str, **extra):
        p = self.path(filename)
        rec = {"file": filename, "note": note,
               "bytes": p.stat().st_size if p.exists() else None,
               "saved_at": datetime.now().isoformat(timespec="seconds")}
        rec.update({k: v for k, v in extra.items() if v is not None})
        self.items = [i for i in self.items if i["file"] != filename] + [rec]

    def done(self, note: str = "") -> Path:
        """manifest.json을 갱신한다. 노트북 끝에서 한 번 부른다."""
        mf = self.path("manifest.json")
        prev = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else {}
        files = {i["file"]: i for i in prev.get("files", [])}
        files.update({i["file"]: i for i in self.items})
        doc = {"notebook": self.name, "note": note or prev.get("note", ""),
               "last_run": datetime.now().isoformat(timespec="seconds"),
               "elapsed_sec": round((datetime.now() - self.started).total_seconds(), 1),
               "environment": _versions(),
               "files": sorted(files.values(), key=lambda d: d["file"])}
        mf.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        return mf

    def summary(self) -> pd.DataFrame:
        mf = self.path("manifest.json")
        if not mf.exists():
            return pd.DataFrame(columns=["file", "note", "bytes", "saved_at"])
        return pd.DataFrame(json.loads(mf.read_text(encoding="utf-8"))["files"])

    def __repr__(self):
        return f"Report({self.name!r} → {self.dir})"


def index(root: Path = None) -> pd.DataFrame:
    """모든 노트북의 산출물을 한 표로. 지금 무엇이 있는지 확인할 때."""
    root = root or paths.reports()
    rows = []
    for mf in sorted(root.rglob("manifest.json")):
        doc = json.loads(mf.read_text(encoding="utf-8"))
        for f in doc["files"]:
            rows.append({"notebook": doc["notebook"], "file": f["file"],
                         "rows": f.get("rows"), "bytes": f.get("bytes"),
                         "note": f.get("note", ""), "saved_at": f.get("saved_at")})
    return pd.DataFrame(rows)
