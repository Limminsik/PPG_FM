# ppg_fm 환경 설정 — 처음 한 번만 실행한다.
# 사용:  powershell -ExecutionPolicy Bypass -File .\setup.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[1/4] 가상환경 생성" -ForegroundColor Cyan
uv venv --python 3.9.21

Write-Host "[2/4] 패키지 설치" -ForegroundColor Cyan
.\.venv\Scripts\activate
uv pip install -e ".[dev]" statsmodels

Write-Host "[3/4] Jupyter 커널 등록" -ForegroundColor Cyan
python -m ipykernel install --user --name="ppg_fm" --display-name="Python 3.9.21 (ppg_fm)"

Write-Host "[4/4] 확인" -ForegroundColor Cyan
python -c "from ppg_fm import paths, features as F; print('데이터', paths.data_root()); print('특징', len(F.BEAT), '/', len(F.PATIENT))"

Write-Host ""
Write-Host "완료. jupyter lab 으로 01_dataset/01 부터 순서대로 실행한다." -ForegroundColor Green
Write-Host "GPU가 필요해지면(2단계):" -ForegroundColor DarkGray
Write-Host "  uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu129" -ForegroundColor DarkGray
