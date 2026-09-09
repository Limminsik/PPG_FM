# docs/ — 진행 현황 홈페이지

GitHub Pages 소스. 저장소 설정에서 **Pages → Source: Deploy from a branch → `main` / `/docs`** 를 고르면 빌드된다.

| 파일 | 내용 |
|---|---|
| `index.html` | 진행 현황 A–E · 작업 규칙 · 코드 구조 · 변경 이력 · 연구 목적 |
| `data.html` | 데이터 현황 · 코호트 정의 · Table 1 |
| `stage1.html` | 1단계 — 파형 특징 23 → 43, 질환 연관, Figure 2 |
| `stage2.html` | 2단계 — 구조 · 사전학습 자원 · 선행 모델 지형 |
| `reading.html` | 선행 논문 정독 기록 |
| `references.html` | 참고문헌 |
| `assets/figures/` | 홈페이지용 그림 복사본. 원본은 `reports/`에서 노트북이 만든다 |

- 버전은 `_config.yml`의 `version`에 있다. 갱신할 때 올리고 `index.html`의 변경 이력에 한 줄 적는다.
- 새 페이지는 `.md`로 써도 된다(front matter에 `layout: default`, `title`). `_data/nav.yml`에 추가하면 상단 메뉴에 뜬다.
- 그림을 다시 만들면 `reports/`에서 `assets/figures/`로 복사한다.
