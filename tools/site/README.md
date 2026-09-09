# tools/site — 사이트 생성기 (보관용)

`docs/`의 정적 HTML을 처음 만든 스크립트다. **앞으로는 `docs/`를 직접 고치므로 이 스크립트를 다시 돌릴 필요는 없다.**
구조를 통째로 다시 짜야 할 때만 참고한다.

| 파일 | 내용 |
|---|---|
| `build_hub.py` | 진행현황 단일 문서(`feature_atlas.html`)를 8개 페이지로 나누고 정적 HTML을 만든다 |
| `site_chrome.css` | 사이트 디자인 시스템(팔레트·타이포·컴포넌트). `docs/assets/style.css`의 뒷부분이 이 파일이다 |

주의: `build_hub.py`를 다시 돌리면 `docs/`가 통째로 덮어써진다. 그 사이 `docs/`에 직접 넣은 수정은 사라진다.
