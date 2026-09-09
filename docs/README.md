# docs/ — PPG_FM 연구 허브 (정적 HTML)

빌드도 서버도 필요 없다. **`docs/index.html`을 더블클릭**하면 브라우저에서 열린다.
링크가 모두 상대 경로라, 나중에 GitHub Pages(Settings → Pages → main / docs)를 켜면 같은 파일이 그대로 사이트가 된다.

## 구조

**연구**
| 파일 | 내용 |
|---|---|
| `index.html` | 홈 — 연구 질문, 규모, 1단계 대표 결과, 최근 갱신 |
| `research.html` | 연구 개요 — 두 단계의 관계 |
| `stage1.html` | 1단계 — 파형 특징 23 → 43, 질환 연관, Figure 2 여섯 판 |
| `stage2.html` | 2단계 — 사전학습 자원, 선행 모델 지형 |
| `data.html` | 데이터 — 보유 자료, 코호트 정의, Table 1 |
| `references.html` | 참고문헌 |

**작업실**
| 파일 | 내용 |
|---|---|
| `log.html` | 진행 현황 A–E · 작업 규칙 · 코드 구조 · 변경 이력 |
| `reading.html` | 선행 논문 정독 기록 |

## 고치는 법
- 내용은 각 `.html`을 직접 고친다. 절 제목의 `id`(`s4-11` 형태)는 링크가 걸려 있으니 바꾸지 않는다.
- 버전을 올릴 때는 각 페이지 사이드바·꼬리말의 `PPG_FM_v0.XX_YYMMDD`와 `log.html`의 변경 이력을 함께 고친다.
- 메뉴를 바꾸려면 8개 파일의 `<aside class="sb">` 안 목록을 같이 고친다.
- 그림은 노트북을 다시 돌린 뒤 `reports/`에서 `assets/figures/`로 복사한다.
- `<meta name="robots" content="noindex, nofollow">`가 들어 있어 검색엔진에 수집되지 않는다.
