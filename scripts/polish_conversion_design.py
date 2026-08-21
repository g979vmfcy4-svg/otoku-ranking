from pathlib import Path
import html
import re


PAGES = [
    Path("public/index.html"),
    Path("public/earphones/index.html"),
    Path("public/earphones/under-5000/index.html"),
    Path("public/earphones/under-10000/index.html"),
    Path("public/earphones/wireless/index.html"),
    Path("public/earphones/wired/index.html"),
    Path("public/earphones/earcuff/index.html"),
    Path("public/earphones/most-reviewed/index.html"),
    Path("public/earphones/methodology/index.html"),
    Path("public/earphones/review-guide/index.html"),
    Path("public/about/index.html"),
    Path("public/contact/index.html"),
    Path("public/privacy/index.html"),
]

RANKING_MODES = {
    Path("public/index.html"): "bayesian",
    Path("public/earphones/under-5000/index.html"): "bayesian",
    Path("public/earphones/under-10000/index.html"): "bayesian",
    Path("public/earphones/wireless/index.html"): "bayesian",
    Path("public/earphones/wired/index.html"): "bayesian",
    Path("public/earphones/earcuff/index.html"): "bayesian",
    Path("public/earphones/most-reviewed/index.html"): "review_count",
}

TOP_PATH = Path("public/index.html")
STYLESHEET = '<link rel="stylesheet" href="/assets/conversion-polish.css">'
NAV_RE = re.compile(
    r'<nav class="ranking-nav(?: ranking-nav-polished)?" aria-label="イヤホンランキング">.*?</nav>',
    re.DOTALL,
)
TRUST_RE = re.compile(
    r'\s*<!-- ranking-trust:start -->.*?<!-- ranking-trust:end -->\s*',
    re.DOTALL,
)
NEW_METRIC_RE = re.compile(
    r'<div class="insight-metric" data-rank="(\d+)">\s*'
    r'<div class="metric-head"><span>([^<]+)</span><strong>\d+位</strong></div>\s*'
    r'<span class="metric-track" aria-hidden="true"><span class="metric-fill" style="width:\d+%"></span></span>\s*'
    r'</div>',
    re.DOTALL,
)
BASE_METRIC_RE = re.compile(
    r'<div class="insight-metric"><span>([^<]+)</span><strong>(\d+)位</strong></div>'
)
REVIEW_DUPLICATE_RE = re.compile(
    r'<div class="insight-metric"><span>レビュー数</span><strong>\d+位</strong></div>'
)

NAV_HTML = '''<nav class="ranking-nav ranking-nav-polished" aria-label="イヤホンランキング">
    <a class="nav-primary" href="/earphones/">一覧</a>
    <a class="nav-primary" href="/">総合</a>
    <details class="nav-group">
        <summary>価格</summary>
        <div class="nav-group-menu">
            <a href="/earphones/under-5000/">5,000円以下</a>
            <a href="/earphones/under-10000/">5,001〜10,000円</a>
        </div>
    </details>
    <details class="nav-group">
        <summary>種類</summary>
        <div class="nav-group-menu">
            <a href="/earphones/wireless/">ワイヤレス</a>
            <a href="/earphones/wired/">有線</a>
            <a href="/earphones/earcuff/">イヤーカフ</a>
        </div>
    </details>
    <a class="nav-primary" href="/earphones/most-reviewed/">レビュー</a>
    <details class="nav-group nav-group-secondary">
        <summary>基準・運営</summary>
        <div class="nav-group-menu">
            <a href="/earphones/review-guide/">レビューの読み方</a>
            <a href="/earphones/methodology/">ランキング基準</a>
            <a href="/about/">このサイトについて</a>
            <a href="/contact/">お問い合わせ</a>
            <a href="/privacy/">プライバシー</a>
        </div>
    </details>
</nav>'''

HERO_HTML = '''<header class="data-hero">
    <div class="hero-shell">
        <span class="hero-eyebrow">楽天市場イヤホンのデータ比較</span>
        <h1>楽天市場 イヤホン高評価ランキング</h1>
        <p class="hero-lead">楽天イヤホンを、レビューの「星」だけで選ばない。</p>
        <p class="hero-sub">レビュー評価 × レビュー件数を補正し、購入候補を客観データで毎日比較します。</p>
        <div class="hero-proof" aria-label="ランキングの特徴">
            <span>毎日自動更新</span>
            <span>レビュー10件以上</span>
            <span>候補最大30商品</span>
            <span>実機レビューではありません</span>
        </div>
    </div>
</header>'''


def visible_text(fragment):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", fragment)).split())


def add_stylesheet(text, path):
    text = text.replace(STYLESHEET + "\n", "").replace(STYLESHEET, "")
    if "</head>" not in text:
        raise RuntimeError(f"</head> がありません: {path}")
    return text.replace("</head>", STYLESHEET + "\n</head>", 1)


def polish_navigation(text, path):
    text, count = NAV_RE.subn(NAV_HTML, text, count=1)
    if count != 1:
        raise RuntimeError(f"ナビゲーションを置換できません: {path}")
    return text


def polish_hero(text):
    updated, count = re.subn(
        r'<header(?:\s+class="[^"]*")?>.*?</header>',
        HERO_HTML,
        text,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError("トップのファーストビューを置換できません。")
    return updated


def quick_label(match):
    content = match.group(1)
    small = re.search(r'<small>(.*?)</small>', content, re.DOTALL)
    original = visible_text(small.group(1) if small else content)
    for prefix in ("評価の安定性で選ぶ", "価格を抑えて選ぶ", "購入実績で選ぶ"):
        while original.startswith(prefix):
            original = original[len(prefix):].strip()
    if "総合" in original:
        intent = "評価の安定性で選ぶ"
    elif "5,000円以下" in original:
        intent = "価格を抑えて選ぶ"
    elif "レビュー件数" in original:
        intent = "購入実績で選ぶ"
    else:
        return match.group(0)
    return (
        '<div class="quick-label">'
        f'<span>{intent}</span><small>{html.escape(original)}</small>'
        '</div>'
    )


def polish_quick_picks(text):
    text = re.sub(
        r'<div class="quick-label">(.*?)</div>',
        quick_label,
        text,
        count=3,
        flags=re.DOTALL,
    )
    replacements = {
        "評価とレビュー件数を総合して上位になった候補です。":
            "レビュー件数を考慮した補正評価で最上位の候補です。",
        "5,000円以下で評価とレビュー実績を重視した候補です。":
            "5,000円以下で、評価の安定性を重視した候補です。",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(
        r'<p class="quick-reason">レビュー([0-9,]+)件。購入実績の多さを重視した候補です。</p>',
        r'<p class="quick-reason">レビュー\1件。購入実績を重視する人向けの候補です。</p>',
        text,
        count=1,
    )
    return text


def trust_block(mode):
    method = "レビュー件数を考慮して補正" if mode == "bayesian" else "レビュー件数が多い順"
    return f'''<!-- ranking-trust:start -->
<div class="ranking-trust-strip" aria-label="ランキング条件">
    <span><small>更新</small><strong>毎日</strong></span>
    <span><small>候補</small><strong>最大30商品</strong></span>
    <span><small>最低レビュー</small><strong>10件</strong></span>
    <span><small>順位基準</small><strong>{method}</strong></span>
    <a href="/earphones/methodology/">算出方法を見る →</a>
</div>
<!-- ranking-trust:end -->'''


def add_trust_strip(text, path, mode):
    text = TRUST_RE.sub("\n", text)
    marker = '<article class="card">'
    pos = text.find(marker)
    if pos < 0:
        raise RuntimeError(f"ランキング商品カードがありません: {path}")
    block = trust_block(mode)
    text = text[:pos] + block + "\n" + text[pos:]
    if text.count('<!-- ranking-trust:start -->') != 1:
        raise RuntimeError(f"ランキング条件表示が不正です: {path}")
    return text


def normalize_metrics(text):
    def to_base(match):
        rank = match.group(1)
        label = match.group(2)
        return f'<div class="insight-metric"><span>{label}</span><strong>{rank}位</strong></div>'
    return NEW_METRIC_RE.sub(to_base, text)


def add_metric_bars(text, path, mode):
    text = normalize_metrics(text)
    expected = 30
    if mode == "review_count":
        text, removed = REVIEW_DUPLICATE_RE.subn("", text)
        if removed not in (0, 10):
            raise RuntimeError(f"レビュー件数順の重複指標数が不正です: {path} removed={removed}")
        expected = 20

    count = 0

    def replace(match):
        nonlocal count
        label = match.group(1)
        rank = int(match.group(2))
        if not 1 <= rank <= 10:
            raise RuntimeError(f"順位バーの値が不正です: {path} rank={rank}")
        fill = 110 - rank * 10
        count += 1
        return (
            f'<div class="insight-metric" data-rank="{rank}">'
            f'<div class="metric-head"><span>{label}</span><strong>{rank}位</strong></div>'
            f'<span class="metric-track" aria-hidden="true"><span class="metric-fill" style="width:{fill}%"></span></span>'
            '</div>'
        )

    text = BASE_METRIC_RE.sub(replace, text)
    if count != expected:
        raise RuntimeError(f"順位バーの件数が不正です: {path} count={count} expected={expected}")
    return text


for path in PAGES:
    if not path.exists():
        raise RuntimeError(f"デザイン対象ページがありません: {path}")
    text = path.read_text(encoding="utf-8")
    text = add_stylesheet(text, path)
    text = polish_navigation(text, path)

    if path == TOP_PATH:
        text = polish_hero(text)
        text = polish_quick_picks(text)

    if path in RANKING_MODES:
        mode = RANKING_MODES[path]
        text = add_metric_bars(text, path, mode)
        text = add_trust_strip(text, path, mode)

    path.write_text(text, encoding="utf-8")

print("Conversion-focused hero / cards / data visualization / navigation: OK")
