# build_hub.py — PPG_FM 연구 허브 사이트 생성
# 원본: feature_atlas.html (진행현황 단일 문서) → docs/ 여러 페이지
import io, os, re, json, shutil

SRC = "feature_atlas.html"
OUT = "site/docs"
VER = "PPG_FM_v0.19_260909"
s = io.open(SRC, encoding="utf-8").read()

# ── 원본에서 조각 뽑기 ────────────────────────────────────────────
st0 = s.find("<style>"); st1 = s.find("</style>", st0)
base_css = s[st0+7:st1]
sc0 = s.find("<script>"); sc1 = s.find("</script>", sc0)
feat_js = s[sc0+8:sc1]
B = json.loads(re.search(r'const B = (\{.*?\});', feat_js, re.S).group(1))

def part(pid):
    i = s.find(f'id="{pid}"'); return s.rfind("<div", 0, i)
order = ["s1","s2","s3","s4","s5","s6"]
bnd = {p: part(p) for p in order}
foot = s.find("<footer")
P = {}
for k,p in enumerate(order):
    a = bnd[p]; b = bnd[order[k+1]] if k+1 < len(order) else foot
    P[p] = s[a:b].rstrip()+"\n"

# 5-6 정독 기록을 별도 페이지로
p5 = P["s5"]; i56 = p5.find("<section>\n    <h3>5-6.")
sec56 = p5[i56:p5.rfind("</div>")].rstrip()+"\n"
P["s5"] = p5[:i56].rstrip()+"\n\n</div>\n"

def strip_kicker(html, new_kicker, new_h2=None):
    html = re.sub(r'<p class="kicker">[^<]*</p>\n\s*', f'<p class="kicker">{new_kicker}</p>\n  ', html, count=1)
    if new_h2:
        html = re.sub(r'<h2>[^<]*</h2>', f'<h2>{new_h2}</h2>', html, count=1)
    return html

P["s56"] = ('<div class="part" id="s56">\n  <p class="kicker">작업실</p>\n'
            '  <h2>정독 기록</h2>\n'
            '  <p>선행 파운데이션 모델 논문을 한 편씩 원문으로 읽고 설계 논리를 남기는 자리다. '
            '왜 그 감독 신호를 골랐는가, 무엇을 근거로 그 선택이 옳다고 주장하는가, 결과가 그 주장을 실제로 뒷받침하는가.</p>\n'
            + sec56 + "</div>\n")
P["s1"] = strip_kicker(P["s1"], "작업실")
P["s2"] = strip_kicker(P["s2"], "연구")
P["s3"] = strip_kicker(P["s3"], "연구 · 자료")
P["s4"] = strip_kicker(P["s4"], "연구 · 1단계")
P["s5"] = strip_kicker(P["s5"], "연구 · 2단계")
P["s6"] = strip_kicker(P["s6"], "연구")

# 본문 안의 "Part n" 표기를 페이지 이름으로
PARTNAME = [("해당 Part에 있다","해당 페이지에 있다"),("Part 구분","페이지 구분"),
            ("Part 5-6","정독 기록"),("Part 5-","2단계 5-"),("Part 4-","1단계 4-"),("Part 3-","데이터 3-"),
            ("Part 1","진행 현황"),("Part 2","연구 개요"),("Part 3","데이터"),("Part 4","1단계"),
            ("Part 5","2단계"),("Part 6","참고문헌"),("문서 16","2단계 준비 문헌 조사")]
for _k in P:
    for a,c in PARTNAME: P[_k] = P[_k].replace(a,c)


# ── 절 제목에 고정 id를 주고, 본문의 절 참조를 링크로 ────────────
SECPAGE = {"1":"/log.html","2":"/research.html","3":"/data.html","4":"/stage1.html","5":"/stage2.html"}
def add_ids(html):
    html = re.sub(r'<h3>(\d+)-(\d+)\.', lambda m: f'<h3 id="s{m.group(1)}-{m.group(2)}">{m.group(1)}-{m.group(2)}.', html)
    html = re.sub(r'<span class="bn">([A-E])</span><h3>',
                  lambda m: f'<span class="bn">{m.group(1)}</span><h3 id="blk-{m.group(1).lower()}">', html)
    return html
def link_secrefs(html, here):
    def f(m):
        label, num = m.group(1), m.group(2)
        part = num.split("-")[0]
        page = "/reading.html" if num == "5-6" else SECPAGE.get(part)
        if not page: return m.group(0)
        href = ("" if page == here else "{{BASE}}"+page) + f"#s{num}"
        return f'<a class="xref" href="{href}">{label} {num}</a>'
    return re.sub(r'(진행 현황|연구 개요|데이터|1단계|2단계)\s(\d+-\d+)', f, html)
for _k in P:
    P[_k] = add_ids(P[_k])

# Figure 2: base64 → 파일 경로
P["s4"] = re.sub(r'<img([^>]*)src="data:image/png;base64,[^"]+"',
                 r'<img\1src="{{BASE}}/assets/figures/figure2_or.png"', P["s4"])

# 블록 헤더 오른쪽 라벨을 해당 페이지 링크로
BSPAGE = {"데이터":"/data.html","1단계":"/stage1.html","2단계":"/stage2.html"}
P["s1"] = re.sub(r'<span class="bs">(데이터|1단계|2단계)</span>',
                 lambda m: f'<span class="bs"><a href="{{{{BASE}}}}{BSPAGE[m.group(1)]}">{m.group(1)} →</a></span>',
                 P["s1"])

# 변경 이력: 최신 3건만 펼치고 나머지는 접는다
def fold_hist(html):
    h0 = html.find('<div class="hist">');
    if h0 < 0: return html
    h1 = html.find("\n    </div>\n  </section>", h0)
    inner = html[h0+len('<div class="hist">'):h1]
    ent = ["      <div><b>"+e for e in inner.split("      <div><b>") if e.strip()]
    new = NEW_HIST + "".join(ent[:2])
    rest = ent[2:]
    out = '<div class="hist">\n' + new
    if rest:
        out += ('\n    </div>\n    <details class="fold"><summary>이전 이력 %d건</summary><div class="hist">' % len(rest)
                + "".join(rest) + "\n    </div></details>")
    else:
        out += "\n    </div>"
    return html[:h0] + out + html[h1+len("\n    </div>"):]

NEW_HIST = """      <div><b>v0.19_260909</b><span><b>로컬 운영으로 전환 — 사이트를 순수 HTML로 바꿨다.</b>
      Jekyll 템플릿 문법을 걷어내고 각 페이지에 필요한 것을 모두 넣어,
      <code>docs/index.html</code>을 <b>더블클릭하면 브라우저에서 바로 열린다</b>(서버·빌드 불필요).
      링크는 전부 상대 경로라 나중에 GitHub Pages를 켜도 그대로 작동한다.
      저장소는 비공개로 돌리고, 사이트 공개는 논문이 나온 뒤에 결정한다.</span></div>
"""
P["s1"] = fold_hist(P["s1"])

# ── 히어로 파형 ──────────────────────────────────────────────────
def hero_wave(width=1200, height=150, cycles=7):
    sig = B["s"]; n = len(sig)
    pts = []
    total = n*cycles
    for c in range(cycles):
        for i in range(n):
            x = (c*n+i)/(total-1)*width
            y = height - 18 - sig[i]*(height-46)
            pts.append(f"{x:.1f},{y:.1f}")
    d = "M" + " L".join(pts)
    return (f'<svg class="wave" viewBox="0 0 {width} {height}" preserveAspectRatio="none" aria-hidden="true">'
            f'<defs><linearGradient id="wg" x1="0" x2="1"><stop offset="0" stop-color="var(--trace)" stop-opacity=".15"/>'
            f'<stop offset=".45" stop-color="var(--trace)" stop-opacity=".95"/>'
            f'<stop offset="1" stop-color="var(--trace)" stop-opacity=".15"/></linearGradient></defs>'
            f'<path d="{d}" fill="none" stroke="url(#wg)" stroke-width="2" stroke-linejoin="round"/></svg>')

# ── CSS ─────────────────────────────────────────────────────────
CHROME_CSS = io.open("site_chrome.css", encoding="utf-8").read()

# ── 레이아웃 ─────────────────────────────────────────────────────
LAYOUT = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ page.title }} · {{ site.title }}</title>
<meta name="description" content="{{ site.description }}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gothic+A1:wght@400;600;700&family=IBM+Plex+Sans+KR:wght@400;500&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="{{ '/assets/style.css' | relative_url }}">
</head>
<body>
<aside class="sb">
  <a class="brand" href="{{ '/' | relative_url }}">
    <div class="t">{{ site.title }}</div>
    <div class="d">{{ site.tagline }}</div>
    <span class="ver">{{ site.version }}</span>
  </a>
  {% for g in site.data.nav %}<div class="grp">
    <h6>{{ g.group }}</h6>
    <nav>{% for n in g.items %}<a class="{% if page.url == n.url %}on{% endif %}" href="{{ n.url | relative_url }}"><span class="k">{{ n.k }}</span>{{ n.label }}</a>
    {% endfor %}</nav>
  </div>
  {% endfor %}
  <div class="ptoc" id="toc"></div>
  <div class="foot">
    <button class="theme" id="themeBtn" type="button" aria-label="밝게/어둡게 전환">◐ 화면</button><br>
    {% if site.repo_url %}<a href="{{ site.repo_url }}">GitHub 저장소</a><br>{% endif %}
    src/ppg_fm · 01_dataset · 02_logistic<br>
    reports/&lt;단계&gt;/&lt;노트북&gt;/manifest.json
  </div>
</aside>
<main class="main"><div class="in">
{% if page.url != "/" %}<p class="crumb"><a href="{{ '/' | relative_url }}">PPG_FM</a> / {{ page.section }} / {{ page.title }}</p>{% endif %}
{{ content }}
{% if page.prev_url %}<div class="pn">
  <div><a class="prev" href="{{ page.prev_url | relative_url }}"><span class="k">← 이전</span><span class="t">{{ page.prev_label }}</span></a></div>
  <div>{% if page.next_url %}<a class="next" href="{{ page.next_url | relative_url }}"><span class="k">다음 →</span><span class="t">{{ page.next_label }}</span></a>{% endif %}</div>
</div>{% endif %}
<footer>
  <span class="mono">{{ site.version }}</span> · 저장소의 <code>docs/</code>에서 GitHub Pages가 만든다<br>
  예시 박동: MIMIC-III-Ext-PPG, 125 Hz, N=120 · 검출률·분포 통계는 코호트 전체 박동 기준
</footer>
</div></main>
{% if page.scripts %}{% for sc in page.scripts %}<script src="{{ sc | relative_url }}"></script>{% endfor %}{% endif %}
<script>
(function(){
  var toc=document.getElementById('toc'); if(!toc) return;
  var hs=document.querySelectorAll('.main h2, .main .part > h3, .main section > h3, .main .blk-h h3, .main .fam-head h3');
  if(hs.length<2) return;
  var html='<h6>이 페이지</h6>', n=0;
  hs.forEach(function(h){
    if(!h.id) h.id='sec-'+(++n);
    var t=h.textContent.replace(/\s+/g,' ').trim();
    if(t.length>34) t=t.slice(0,32)+'…';
    html+='<a class="'+(h.tagName==='H2'?'h2':'h3')+'" href="#'+h.id+'">'+t+'</a>';
  });
  toc.innerHTML=html;
})();
(function(){
  var K='ppgfm-theme', r=document.documentElement, b=document.getElementById('themeBtn');
  try{ var v=localStorage.getItem(K); if(v) r.setAttribute('data-theme', v); }catch(e){}
  if(!b) return;
  b.addEventListener('click', function(){
    var cur=r.getAttribute('data-theme');
    if(!cur) cur = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    var nx = cur==='dark' ? 'light' : 'dark';
    r.setAttribute('data-theme', nx);
    try{ localStorage.setItem(K, nx); }catch(e){}
  });
})();
</script>
</body>
</html>
"""

NAV = [
 ("연구", [("1","홈","/"),("2","연구 개요","/research.html"),("3","1단계 — 파형 특징과 질환 연관","/stage1.html"),
          ("4","2단계 — 파운데이션 모델","/stage2.html"),("5","데이터","/data.html"),("6","참고문헌","/references.html")]),
 ("작업실", [("7","진행 현황","/log.html"),("8","정독 기록","/reading.html")]),
]
FLAT = [(k,l,u,g) for g,items in NAV for k,l,u in items]

# ── 홈 ──────────────────────────────────────────────────────────
HOME = """<div class="hero">
  <p class="eyebrow">가천대학교 DAC 연구실 · 연구 진행 중</p>
  <h1>PPG 파형에서 질환을 읽는다</h1>
  <p class="lede">손끝에서 재는 맥파 하나에 어떤 질환의 흔적이 남는가.
  먼저 사람이 정의한 계산식으로 파형 특징을 뽑아 질환과의 연관을 넓게 훑고,
  그 위에서 파형을 스스로 학습하는 파운데이션 모델을 설계한다.</p>
  <div class="cta">
    <a class="pri" href="{{BASE}}/research.html">연구 개요</a>
    <a href="{{BASE}}/stage1.html">1단계 결과 보기</a>
    <a href="{{BASE}}/log.html">진행 현황</a>
  </div>
  __WAVE__
</div>

<div class="part">
  <p class="kicker">연구 질문</p>
  <h2>무엇을 묻는가</h2>
  <p>PPG는 값싸고 어디에나 있지만, 임상에서는 심박수와 산소포화도를 넘어 잘 쓰이지 않는다.
  파형의 <strong>모양</strong> 자체에 얼마나 많은 임상 정보가 들어 있는지가 아직 정리되어 있지 않기 때문이다.
  이 연구는 그 질문을 두 번, 서로 다른 방법으로 묻는다.</p>
  <div class="grid3">
    <div class="card"><span class="q">질문 1</span><h3>계산식으로 어디까지 보이는가</h3>
      <p>박동 하나에서 시간·비율·미분으로 정의한 특징 23개를 재고 환자 단위 43개로 요약해,
      ICD-10 진단코드 171개 전부와의 연관을 같은 절차로 훑는다.</p></div>
    <div class="card"><span class="q">질문 2</span><h3>모델이 스스로 배우면 무엇이 달라지는가</h3>
      <p>라벨 없이 대규모 PPG로 표현을 학습한 뒤 같은 질환을 본다.
      1단계에서 유의했던 파형·혈역학적 특징을 그 설계의 기반으로 삼는다.</p></div>
    <div class="card"><span class="q">전제</span><h3>스케일에 흔들리지 않는 특징만</h3>
      <p>절대 진폭·기기·접촉압에 좌우되는 값은 처음부터 제외했다.
      남긴 것은 파형의 시간 구조와 비율, 그리고 형태를 못 뽑은 경우까지 담은 검출률이다.</p></div>
  </div>
</div>

<div class="part">
  <p class="kicker">규모</p>
  <h2>지금 이 연구가 딛고 선 숫자</h2>
  <div class="tiles">
    <div class="tile"><div class="v">6,114</div><div class="l">환자 · 고품질 SQI 통과 전원, 배제 조건 없음</div></div>
    <div class="tile"><div class="v">59,113</div><div class="l">30초 세그먼트 · 환자당 균등 간격 10개</div></div>
    <div class="tile"><div class="v">2,361,453</div><div class="l">박동 · 특징 계산의 단위</div></div>
    <div class="tile"><div class="v">23 → 43</div><div class="l">파형 특징 · 박동 단위 → 환자 요약</div></div>
    <div class="tile"><div class="v">171</div><div class="l">ICD-10 코드 · 환자 100명 이상</div></div>
    <div class="tile"><div class="v">193만 h</div><div class="l">2단계 사전학습에 쓸 수 있는 PPG</div></div>
  </div>
  <div class="steps">
    <a class="step" href="{{BASE}}/stage1.html"><span class="n">1단계</span>
      <div class="t">계산식 파형 특징과 질환 연관</div>
      <div class="s">탐색적 지형 훑기로 정리를 마쳤다 — 특징 정의 · 코호트 · Figure 2 여섯 판</div>
      <div class="bar"><i style="width:100%"></i></div></a>
    <a class="step" href="{{BASE}}/stage2.html"><span class="n">2단계</span>
      <div class="t">파운데이션 모델 — 준비 중</div>
      <div class="s">선행 논문 8편 정독 중(6편 완료) · 설계는 정독을 마친 뒤 잡는다</div>
      <div class="bar"><i class="wip" style="width:75%"></i></div></a>
  </div>
</div>

<div class="part">
  <p class="kicker">1단계 결과</p>
  <h2>파형 특징 43개 × 진단코드 171개</h2>
  <p>셀 하나가 로지스틱 회귀 하나다 — 그 특징이 1 표준편차 높을 때 그 코드를 갖고 있을 오즈비.
  7,353번의 검정에 Bonferroni 기준을 대면 852개(11.6%)가 남는다.</p>
  <div class="showcase">
    <div class="pic"><a href="{{BASE}}/stage1.html"><img src="{{BASE}}/assets/figures/figure2_compact.png" alt="Figure 2 — 진단코드 × 파형 특징 오즈비"></a></div>
    <div class="body">
      <h3>읽어낸 것</h3>
      <ul class="plain">
        <li><b>신호는 심혈관에 갇혀 있지 않다</b> — 171개 코드 중 105개에서 유의 셀이 나왔고, 특징은 43개 전부가 어딘가에서 유의했다.</li>
        <li><b>넓게 퍼진 질환</b>은 심부전(I50) · 심방세동(I48) · 쇼크(R57) · 만성신질환(N18) · 만성허혈성심질환(I25) 순이다.</li>
        <li><b>넓게 움직인 특징</b>은 상승기 최대 기울기(<code>max_slope_norm</code>) 46개 질환, 2차 미분 b/a 41개, 박출 시간 비율 38개다.</li>
        <li><b>공변량은 보정하지 않았다</b> — 효과가 가장 큰 셀에는 외상·출혈이 올라오는데, 이 환자군은 더 젊고 심박이 빠르다. 두 층위를 구분해 읽는다.</li>
      </ul>
    </div>
  </div>
</div>

<div class="part">
  <p class="kicker">작업실</p>
  <h2>최근 갱신</h2>
  <div class="feed">__FEED__</div>
  <p style="margin-top:14px"><a href="{{BASE}}/log.html">진행 현황 전체 보기 →</a></p>
</div>
"""

def feed_items(html, k=4):
    h0 = html.find('<div class="hist">')
    inner = html[h0:h0+9000]
    out = []
    for m in re.finditer(r'<div><b>([^<]+)</b><span>(.*?)</span></div>', inner, re.S):
        ver, body = m.group(1), re.sub(r'<[^>]+>','',m.group(2))
        body = re.sub(r'\s+',' ',body).strip()
        if len(body) > 130: body = body[:128]+'…'
        out.append(f'<a href="{{{{BASE}}}}/log.html#s1-3"><span class="v">{ver}</span><span class="t">{body}</span></a>')
        if len(out) >= k: break
    return "\n".join(out)

# ── 쓰기 ────────────────────────────────────────────────────────
if os.path.isdir(OUT): shutil.rmtree(OUT)
for d in ["_layouts","_data","assets/figures"]: os.makedirs(f"{OUT}/{d}", exist_ok=True)

io.open(f"{OUT}/assets/style.css","w",encoding="utf-8").write(base_css.strip()+"\n"+CHROME_CSS)
io.open(f"{OUT}/assets/feature_cards.js","w",encoding="utf-8").write(feat_js.strip()+"\n")
io.open(f"{OUT}/_layouts/default.html","w",encoding="utf-8").write(LAYOUT)

nav_yml = ""
for g, items in NAV:
    nav_yml += f"- group: {g}\n  items:\n"
    for k,l,u in items:
        nav_yml += f"    - {{k: '{k}', label: '{l}', url: '{u}'}}\n"
io.open(f"{OUT}/_data/nav.yml","w",encoding="utf-8").write(nav_yml)

io.open(f"{OUT}/_config.yml","w",encoding="utf-8").write(f"""title: PPG_FM
tagline: PPG 파형 특징과 질환 연관 · 파운데이션 모델
description: 손끝 맥파(PPG)의 파형 특징으로 질환 연관을 훑고, 그 위에서 파운데이션 모델을 설계하는 연구
baseurl: "/PPG_FM"     # 프로젝트 페이지 경로. 사용자 페이지로 옮기면 ""
url: "https://limminsik.github.io"
version: {VER}
repo_url: "https://github.com/Limminsik/PPG_FM"
lang: ko
markdown: kramdown
exclude: [README.md]
""")

PAGEMAP = {"/":"HOME","/research.html":"s2","/stage1.html":"s4","/stage2.html":"s5",
           "/data.html":"s3","/references.html":"s6","/log.html":"s1","/reading.html":"s56"}

def links(html, here):
    def f(m):
        t = m.group(1)
        page = {"s1":"/log.html","s2":"/research.html","s3":"/data.html","s4":"/stage1.html",
                "s5":"/stage2.html","s56":"/reading.html"}.get(t)
        if t.startswith("ref-"): page = "/references.html"
        if not page: return m.group(0)
        return f'href="{"" if page==here else "{{BASE}}"+page}#{t}"'
    return re.sub(r'href="#([^"]+)"', f, html)

GAL = """
  <section>
    <h3>Figure 2 변형 — 같은 자료를 다르게 자른 판</h3>
    <p>여섯 판 모두 색 스케일을 오즈비 0.50~2.00으로 고정했다. 파일은 <code>reports/02_logistic/02_association_figure2/</code>에서 생성된다.</p>
    <div class="gal">
      <figure><a href="{{BASE}}/assets/figures/figure2_compact.png"><img src="{{BASE}}/assets/figures/figure2_compact.png" alt="compact"></a><figcaption>compact — 유의 특징 ≥5인 54코드, 질환명 표기</figcaption></figure>
      <figure><a href="{{BASE}}/assets/figures/figure2_circulatory.png"><img src="{{BASE}}/assets/figures/figure2_circulatory.png" alt="circulatory"></a><figcaption>순환계 27코드 확대</figcaption></figure>
      <figure><a href="{{BASE}}/assets/figures/figure2_panels.png"><img src="{{BASE}}/assets/figures/figure2_panels.png" alt="panels"></a><figcaption>ICD 장별 소패널 6개</figcaption></figure>
      <figure><a href="{{BASE}}/assets/figures/figure2_top_cells.png"><img src="{{BASE}}/assets/figures/figure2_top_cells.png" alt="top cells"></a><figcaption>효과 상위 40셀을 오즈비 축에</figcaption></figure>
      <figure><a href="{{BASE}}/assets/figures/figure2_feature_breadth.png"><img src="{{BASE}}/assets/figures/figure2_feature_breadth.png" alt="feature breadth"></a><figcaption>특징별 유의 질환 수, 방향 구분</figcaption></figure>
    </div>
  </section>
"""
p4 = P["s4"]; k = p4.rfind("</div>"); P["s4"] = p4[:k] + GAL + "</div>\n"

home = HOME.replace("__WAVE__", hero_wave()).replace("__FEED__", feed_items(P["s1"]))

TITLE = {u:(k,l,g) for k,l,u,g in FLAT}
def fname(u): return "index.html" if u == "/" else u.lstrip("/")

def render(i, kk, label, url, grp, body):
    navhtml = ""
    for g, items in NAV:
        navhtml += f'  <div class="grp">\n    <h6>{g}</h6>\n    <nav>\n'
        for k2,l2,u2 in items:
            on = ' class="on"' if u2 == url else ''
            navhtml += f'      <a{on} href="{fname(u2)}"><span class="k">{k2}</span>{l2}</a>\n'
        navhtml += "    </nav>\n  </div>\n"
    crumb = "" if url == "/" else f'<p class="crumb"><a href="index.html">PPG_FM</a> / {grp} / {label}</p>\n'
    pn = ""
    if i > 0:
        nx = (f'<a class="next" href="{fname(FLAT[i+1][2])}"><span class="k">다음 →</span>'
              f'<span class="t">{FLAT[i+1][1]}</span></a>') if i < len(FLAT)-1 else ""
        pn = ('<div class="pn">\n'
              f'  <div><a class="prev" href="{fname(FLAT[i-1][2])}"><span class="k">← 이전</span>'
              f'<span class="t">{FLAT[i-1][1]}</span></a></div>\n  <div>{nx}</div>\n</div>\n')
    scripts = '<script src="assets/feature_cards.js"></script>\n' if url == "/stage1.html" else ""
    body = body.replace("{{BASE}}/", "").replace("{{BASE}}", "")
    return PAGE_TPL.format(title=label, site=SITE, tagline=TAGLINE, ver=VER, desc=DESC,
                           nav=navhtml, crumb=crumb, content=body, pn=pn, scripts=scripts, repo=REPO)

SITE, TAGLINE = "PPG_FM", "PPG 파형 특징과 질환 연관 · 파운데이션 모델"
DESC = "손끝 맥파(PPG)의 파형 특징으로 질환 연관을 훑고, 그 위에서 파운데이션 모델을 설계하는 연구"
REPO = "https://github.com/Limminsik/PPG_FM"

PAGE_TPL = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{title} · {site}</title>
<meta name="description" content="{desc}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gothic+A1:wght@400;600;700&family=IBM+Plex+Sans+KR:wght@400;500&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<aside class="sb">
  <a class="brand" href="index.html">
    <div class="t">{site}</div>
    <div class="d">{tagline}</div>
    <span class="ver">{ver}</span>
  </a>
{nav}  <div class="ptoc" id="toc"></div>
  <div class="foot">
    <button class="theme" id="themeBtn" type="button" aria-label="밝게/어둡게 전환">◐ 화면</button><br>
    <a href="{repo}">GitHub 저장소</a><br>
    src/ppg_fm · 01_dataset · 02_logistic<br>
    reports/&lt;단계&gt;/&lt;노트북&gt;/manifest.json
  </div>
</aside>
<main class="main"><div class="in">
{crumb}{content}
{pn}<footer>
  <span class="mono">{ver}</span> · 이 문서는 <code>docs/</code>의 정적 HTML이다 — 파일을 열면 그대로 보인다<br>
  예시 박동: MIMIC-III-Ext-PPG, 125 Hz, N=120 · 검출률·분포 통계는 코호트 전체 박동 기준
</footer>
</div></main>
{scripts}<script>
(function(){{
  var toc=document.getElementById('toc'); if(!toc) return;
  var hs=document.querySelectorAll('.main h2, .main .part > h3, .main section > h3, .main .blk-h h3, .main .fam-head h3');
  if(hs.length<2) return;
  var html='<h6>이 페이지</h6>', n=0;
  hs.forEach(function(h){{
    if(!h.id) h.id='sec-'+(++n);
    var t=h.textContent.replace(/\\s+/g,' ').trim();
    if(t.length>34) t=t.slice(0,32)+'…';
    html+='<a class="'+(h.tagName==='H2'?'h2':'h3')+'" href="#'+h.id+'">'+t+'</a>';
  }});
  toc.innerHTML=html;
}})();
(function(){{
  var K='ppgfm-theme', r=document.documentElement, b=document.getElementById('themeBtn');
  try{{ var v=localStorage.getItem(K); if(v) r.setAttribute('data-theme', v); }}catch(e){{}}
  if(!b) return;
  b.addEventListener('click', function(){{
    var cur=r.getAttribute('data-theme');
    if(!cur) cur = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    var nx = cur==='dark' ? 'light' : 'dark';
    r.setAttribute('data-theme', nx);
    try{{ localStorage.setItem(K, nx); }}catch(e){{}}
  }});
}})();
</script>
</body>
</html>
"""

for i,(kk,label,url,grp) in enumerate(FLAT):
    raw = home if url == "/" else P[PAGEMAP[url]]
    body = link_secrefs(links(raw, url), url)
    io.open(f"{OUT}/{fname(url)}", "w", encoding="utf-8").write(render(i, kk, label, url, grp, body))

io.open(f"{OUT}/.nojekyll","w").write("")
io.open(f"{OUT}/README.md","w",encoding="utf-8").write("""# docs/ — PPG_FM 연구 허브 (정적 HTML)

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
""")
print("built (static)", VER)
for r,_,fs in os.walk(OUT):
    for f in sorted(fs): print(" ", os.path.join(r,f), os.path.getsize(os.path.join(r,f)))
