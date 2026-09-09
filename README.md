# [ppg_fm — PPG 파형 특징과 질환 연관 (1단계)](https://limminsik.github.io/PPG_FM/)

전체 연구는 두 단계다.

| 단계 | 특징을 어떻게 얻는가 | 상태 |
|---|---|---|
| **1단계** | 시간·비율·미분으로 정의한 계산식 파형 특징 | 진행 중 — 이 저장소 |
| 2단계 | 파운데이션 모델이 학습한 특징 | 예정 |

두 단계는 **같은 데이터·같은 평가 코호트·같은 분할**을 공유하고 특징을 얻는 방법만 바뀐다.
그래서 1단계의 결과가 2단계가 넘어야 할 값이 된다.

## 설계 제1원칙

> **PPG는 절대 스케일을 잃고, 타이밍과 정규화된 형태를 보존한다.**

| 막힌 것 (절대 스케일 필요) | 열린 것 (스케일 불변) |
|---|---|
| 절대 SBP/DBP · 절대 CO · 절대 SVR · 경직도지수(신장 필요) · PTT(ECG 필요) | LVET · CT · CT/LVET · W50 · RI · IPA · b/a · d/a · aging_index |

## 데이터

1단계는 **질환 라벨이 붙은 PPG**가 필요하고, 그 조건을 만족하는 것은 MIMIC-III-Ext-PPG 하나다.
2단계 사전학습에는 라벨이 필요 없으므로 보유한 PPG 전부를 쓴다.

| 데이터셋 | fs | 규모 | 라벨 | 1단계 | 2단계 |
|---|---:|---|---|:--:|:--:|
| MIMIC-III-Ext-PPG | 125 Hz | 6,189명 · 5.3만 시간 | ICD-10 1,092코드 · 리듬 16종 | ● | ● |
| MIMIC-III Waveform 원본 | 125 Hz | 39,320 레코드 · 228만 시간 | — | | ● |
| VitalDB | 500 Hz | 6,388 케이스 · 126 GB | 동맥압 동시기록 | | ● |
| MIMIC-IV Waveform | 125 Hz | 198명 · 8,969시간 | — | | ● |
| NFS | 256 Hz | 398파일 · 3,607시간 | 연령·성별·BMI·수면설문 | | ● |
| PPGArrhythmiaDetection | 100 Hz | 46,827 세그먼트 | 부정맥 6클래스 | | ● |
| WildPPG · WF-PPG | 100–128 Hz | 102명 | 부위 · 접촉압 | | ● |

Ext-PPG는 원본 waveform 레코드 10,623개에서 추출됐고 그중 8,424개가 원본 덤프에 있다.
나머지 45,413개(84.4% · 약 193만 시간)는 라벨 코호트와 무관하므로 사전학습–평가 분리에 누출이 없다.

## 1단계 코호트

```
① 전체              환자 6,189 · 세그먼트 6,399,754
② SQI [1,1,1]       세그먼트 5,401,385 · 환자 6,114
③ 세그먼트 표집       환자당 균등 간격 10개 → 59,113 · 리듬 제한 없음
④ 박동 추출          박동 2,361,435 · 박동이 없는 1명 탈락
⑤ 1단계 코호트       환자 6,113 · 환자당 박동 중앙값 395
```

SQI는 데이터셋이 제공하는 값이다. 30초를 10초씩 세 구간으로 나눠 Orphanidou 등(2015)
알고리즘으로 각 구간에 +1/0을 매긴 3원소 벡터 `vector_10s_pleth_sqi`이며, 세 구간이 모두
+1인 세그먼트만 쓴다. 이 지표가 보는 것은 박동 검출 가능성과 박동 간 일관성이지
미세 형태의 신뢰도가 아니다 — 그것은 별도 검출률로 다룬다.

## 특징

박동 단위 **23개** → 환자 단위 **43개**.

| 계열 | 개수 |
|---|---:|
| 타이밍 | 11 |
| 정규화 진폭비 | 3 |
| 1차 미분 | 2 |
| 2차 미분 (APG) | 5 |
| 검출 플래그 | 2 |
| **박동 단위 합** | **23** |
| 중앙값 | 20 |
| 박동간 IQR (원단위) | 20 |
| 검출률 | 3 |
| **환자 단위 합** | **43** |

환자 요약은 네 방식(중앙값 · 분위수 · 앙상블 · 대표 박동)을 재현성·검출률·질환 신호로
실측 비교해 **박동별 중앙값**으로 확정했다.

## 분석

```
logit P(D_p = 1) = b0 + b · z(X_p)      exp(b) = 특징 1 SD당 오즈비
```

- 분석 단위는 환자 (박동 단위 회귀는 의사반복으로 p값이 부풀어 오른다)
- 공변량 보정 없음 — 파형 특징 자체와 질환의 연관을 보는 것이 목적
- Firth 보정 불필요 (사례 최소 코드에서 계수 변화 0.0~2.8%, 사건당 변수 수 14)
- 다중검정은 선행 연구 관례를 따라 Bonferroni (7,396 검정 → p < 6.8e−6)

## 구성

```
01_dataset/                     데이터·코호트·라벨 정의
  01_data_inventory.ipynb         보유 PPG 현황, 단계별 사용 계획
  02_cohort_definition.ipynb      데이터 구조 · SQI · 코호트 확정 경로
  03_labels_icd.ipynb             ICD-10 라벨 지형, 분석 대상 코드 확정
  04_waveform_features.ipynb      박동 특징 23개 추출 → 환자 요약 43개
02_logistic/                    질환 연관 분석
  01_summary_method.ipynb         환자 요약 방식 네 가지 실측 비교
  02_association_figure2.ipynb    로지스틱 · 오즈비 · Figure 2
src/ppg_fm/
  paths.py                        프로젝트·데이터 경로 해석
  features.py                     특징 이름 정의 (23 / 43)
  morph/features.py               박동 단위 특징 추출기
  data/cohort.py                  세그먼트 인덱스 · SQI 필터 · 추출 계획
  data/extract.py                 박동 특징 추출 (증분 저장 · 재개)
  data/summary.py                 환자 요약 (중앙값 · IQR · 검출률)
  data/labels.py                  ICD 환자×코드 행렬
  analysis/logistic.py            로지스틱 회귀 · 오즈비 · Bonferroni
  analysis/figures.py             Figure 2 렌더
  report.py                       노트북별 산출물 관리 (manifest)
setup.ps1                       환경 설정 (처음 한 번)
configs/paths.yaml              데이터 루트
data/interim/                   중간 산출물
reports/<단계>/<노트북>/        노트북별 산출물 + manifest.json
_archive/                       이전 구조 (참고용, 실행 경로 아님)
```

## 환경 설정

처음 한 번만.

```powershell
cd C:\dev\ppg_fm
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

setup.ps1이 하는 일 — `uv venv --python 3.9.21` → `uv pip install -e ".[dev]" statsmodels`
→ Jupyter 커널 `ppg_fm` 등록 → 데이터 경로와 특징 개수 확인.
GPU는 2단계에서 필요해지면 `uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu129`.

수동으로 하려면:

```powershell
uv venv --python 3.9.21
.venv\Scripts\activate
uv pip install -e ".[dev]" statsmodels
python -m ipykernel install --user --name="ppg_fm" --display-name="Python 3.9.21 (ppg_fm)"
```

## 실행 순서

```powershell
jupyter lab
# 01_dataset/01 → 02 → 03 → 04 → 02_logistic/01 → 02
```

노트북은 산출물이 이미 있으면 다시 계산하지 않는다. 처음부터 돌리려면 `data/interim/`의
해당 파일을 지운 뒤 실행한다. 박동 추출은 전 코호트 기준 수십 분 걸린다.

## 산출물 관리

노트북 하나가 만드는 표·그림은 **그 노트북 이름의 폴더 아래에만** 쌓인다.

```
reports/
  01_dataset/
    01_data_inventory/      dataset_plan.csv
    02_cohort_definition/   sqi_distribution.csv · cohort_flow.csv
    03_labels_icd/          icd_code_counts.csv · analysis_codes.csv · icd_case_count_hist.png
    04_waveform_features/   beat_detection_rate.csv · patient_feature_summary.csv
                            reliability_projection.csv
  02_logistic/
    01_summary_method/      summary_method_compare.csv · split_half_reliability.csv
    02_association_figure2/ figure2_or.csv · figure2_or.png · figure2_summary.csv
                            significant_cells.csv · significant_breadth.csv
                            covariate_ablation.csv
  _legacy/                  이전 구조의 산출물 (참고용)
```

각 폴더에 `manifest.json`이 함께 남아 **무엇을 언제 어떤 환경에서 만들었는지**를 기록한다 —
파일명·메모·행 수·크기·저장 시각, 그리고 Python과 주요 패키지 버전.

노트북 안에서는 이렇게 쓴다.

```python
from ppg_fm.report import Report
rep = Report("01_dataset/02_cohort_definition")

rep.table(dist, "sqi_distribution.csv", "SQI 벡터별 세그먼트 수")
rep.figure(fig, "cohort_flow.png", "코호트 확정 경로")
rep.done("데이터 구조 · SQI 필터 · 코호트 확정 경로")   # manifest 갱신
```

지금 무엇이 있는지 한 표로 보려면:

```python
from ppg_fm.report import index
index()
```

git은 `manifest.json`만 추적하고 데이터 파일은 무시한다 — 결과의 **목록과 이력**은 남고
용량은 저장소에 들어가지 않는다.

## 방법론 통제

1. **환자 단위 분할** — 윈도우 랜덤 분할 금지 (성능이 크게 부풀어 오른다)
2. **베이스라인 3종** — 상수/중앙값, 인구통계 단독, HR/HRV 단독
3. **피험자 신원 프로브** — 임베딩의 subject ID 예측력으로 지름길을 정량화 (2단계)
4. **상용기기 출력을 라벨로 쓰지 않는다**
5. **절흔 소실을 저품질로 처리하지 않는다** — 병든 환자를 배제하게 된다
