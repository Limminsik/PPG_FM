# docs/ — PPG_FM 연구 허브

GitHub Pages 소스. 저장소 설정에서 **Pages → Source: Deploy from a branch → `main` / `/docs`**.

## 구조

**연구** — 바깥에 보여주는 면
| 파일 | 내용 |
|---|---|
| `index.html` | 홈 — 연구 질문, 규모, 1단계 대표 결과, 최근 갱신 |
| `research.html` | 연구 개요 — 두 단계 구조와 관계 |
| `stage1.html` | 1단계 — 파형 특징 23 → 43, 질환 연관, Figure 2 여섯 판 |
| `stage2.html` | 2단계 — 사전학습 자원, 선행 모델 지형 |
| `data.html` | 데이터 — 보유 자료, 코호트 정의, Table 1 |
| `references.html` | 참고문헌 |

**작업실** — 진행 관리
| 파일 | 내용 |
|---|---|
| `log.html` | 진행 현황 A–E · 작업 규칙 · 코드 구조 · 변경 이력 |
| `reading.html` | 선행 논문 정독 기록 |

## 고치는 법
- 버전: `_config.yml`의 `version` 한 곳. `log.html` 변경 이력에 한 줄 추가.
- 메뉴: `_data/nav.yml` (그룹 · 순서 · 라벨). 페이지 하단 이전/다음은 각 파일 front matter.
- 그림: 노트북을 다시 돌린 뒤 `reports/`에서 `docs/assets/figures/`로 복사.
- 새 페이지: `.md`로 써도 된다 — front matter에 `layout: default`, `title`, `section`.
