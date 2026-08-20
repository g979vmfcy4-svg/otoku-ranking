import html as html_lib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


SITE = "https://otoku-ranking.pages.dev"
SEO_STYLESHEET = '<link rel="stylesheet" href="/assets/seo-expansion.css">'
SITE_STYLESHEET = '<link rel="stylesheet" href="/assets/site-v2.css">'

PAGE_INFO = {
    Path("public/earphones/index.html"): ("イヤホンランキング", "/earphones/"),
    Path("public/earphones/under-5000/index.html"): ("5,000円以下", "/earphones/under-5000/"),
    Path("public/earphones/under-10000/index.html"): ("5,001〜10,000円", "/earphones/under-10000/"),
    Path("public/earphones/wireless/index.html"): ("ワイヤレスイヤホン", "/earphones/wireless/"),
    Path("public/earphones/wired/index.html"): ("有線イヤホン", "/earphones/wired/"),
    Path("public/earphones/earcuff/index.html"): ("イヤーカフ型イヤホン", "/earphones/earcuff/"),
    Path("public/earphones/most-reviewed/index.html"): ("レビュー件数順", "/earphones/most-reviewed/"),
    Path("public/earphones/methodology/index.html"): ("ランキング基準", "/earphones/methodology/"),
    Path("public/about/index.html"): ("このサイトについて", "/about/"),
}

RANKING_PATHS = [
    Path("public/earphones/under-5000/index.html"),
    Path("public/earphones/under-10000/index.html"),
    Path("public/earphones/wireless/index.html"),
    Path("public/earphones/wired/index.html"),
    Path("public/earphones/earcuff/index.html"),
    Path("public/earphones/most-reviewed/index.html"),
]

CATEGORY_PATHS = [
    Path("public/earphones/wireless/index.html"),
    Path("public/earphones/wired/index.html"),
    Path("public/earphones/earcuff/index.html"),
]

RELATED = [
    ("ランキング一覧", "/earphones/"),
    ("総合ランキング", "/"),
    ("5,000円以下", "/earphones/under-5000/"),
    ("5,001〜10,000円", "/earphones/under-10000/"),
    ("ワイヤレス", "/earphones/wireless/"),
    ("有線", "/earphones/wired/"),
    ("イヤーカフ", "/earphones/earcuff/"),
    ("レビュー件数順", "/earphones/most-reviewed/"),
]


def text_value(fragment):
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return " ".join(html_lib.unescape(fragment).split())


def escape(value):
    return html_lib.escape(str(value), quote=True)


def shorten(value, limit=64):
    value = " ".join(value.split())
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def display_name(raw_name):
    """カテゴリページの商品名から販促文を落とし、元名はtitle属性に保持する。"""
    original = " ".join(raw_name.split())
    value = original

    patterns = [
        r'^(?:楽天ランキング\d*位|楽天\d*位|迷ったらこれ[！!]?|20\d{2}年間MVP)[\s・:：-]*',
        r'^＼[^／]{0,140}／\s*',
        r'^【[^】]{0,140}(?:OFF|クーポン|ポイント|楽天|P\d|セール|限定|ランキング)[^】]*】\s*',
        r'^「[^」]{0,140}(?:OFF|クーポン|ポイント|楽天|実質|ランキング)[^」]*」\s*',
    ]
    changed = True
    while changed:
        changed = False
        for pattern in patterns:
            cleaned = re.sub(pattern, "", value, count=1, flags=re.IGNORECASE)
            if cleaned != value:
                value = cleaned.strip()
                changed = True

    parsed = re.sub(r'【[^】]{0,140}】', " ", value)
    parsed = " ".join(parsed.split())

    known_patterns = [
        r'\b(Anker\s+Soundcore\s+[A-Za-z0-9-]+)',
        r'\b(SOUNDPEATS\s+[A-Za-z0-9-]+)',
        r'\b(HUAWEI\s+FreeBuds\s+[A-Za-z0-9-]+(?:\s+ANC)?)',
        r'\b(SONY\s+WF-[A-Za-z0-9-]+)',
    ]
    for pattern in known_patterns:
        match = re.search(pattern, parsed, re.IGNORECASE)
        if match:
            kind = "イヤーカフ型イヤホン" if "イヤーカフ" in parsed else "ワイヤレスイヤホン"
            return shorten(f"{match.group(1)} {kind}")

    panasonic = re.search(r'\b(RP-[A-Z0-9-]+)\b', parsed, re.IGNORECASE)
    if panasonic and re.search(r'パナソニック|Panasonic', parsed, re.IGNORECASE):
        return f"パナソニック {panasonic.group(1).upper()} 有線イヤホン"

    type_match = re.search(
        r'(イヤーカフ(?:型)?イヤホン|完全ワイヤレスイヤホン|ワイヤレスイヤホン|有線\s*イヤホン|ステレオイヤホン|イヤホン)',
        parsed,
        re.IGNORECASE,
    )
    if type_match:
        kind = re.sub(r'\s+', "", type_match.group(1))
        if kind == "完全ワイヤレスイヤホン":
            kind = "ワイヤレスイヤホン"
        prefix = parsed[: type_match.start()].strip(" ・/|｜-【】[]()（）")
        if len(prefix) > 28 or any(
            token in prefix.lower()
            for token in ("off", "クーポン", "楽天", "ポイント", "ランキング", "実質")
        ):
            prefix = ""
        result = f"{prefix} {kind}".strip()
        bluetooth = re.search(r'Bluetooth\s*(?:ver\.?\s*)?([4-6](?:\.\d+)?)', value, re.IGNORECASE)
        if bluetooth and "有線" not in kind:
            result += f" Bluetooth {bluetooth.group(1)}"
        return shorten(result)

    return shorten(original, 60)


def clean_category_product_names(path):
    text = path.read_text(encoding="utf-8")
    changed = 0

    def repl(match):
        nonlocal changed
        body = match.group(1)
        heading = re.search(r'<h2>(.*?)</h2>', body, re.DOTALL)
        if not heading:
            return match.group(0)
        raw = text_value(heading.group(1))
        visible = display_name(raw)
        body = re.sub(
            r'<h2>.*?</h2>',
            f'<h2 title="{escape(raw)}">{escape(visible)}</h2>',
            body,
            count=1,
            flags=re.DOTALL,
        )
        changed += 1
        return '<article class="card">' + body + '</article>'

    text = re.sub(
        r'<article class="card">(.*?)</article>',
        repl,
        text,
        flags=re.DOTALL,
    )
    if changed != 10:
        raise RuntimeError(f"カテゴリページの商品表示名変更が10件ではありません: {path} ({changed})")

    text = text.replace(">楽天市場で見る</a>", ">楽天市場で価格・詳細を見る</a>")
    if SITE_STYLESHEET not in text:
        text = text.replace("</head>", SITE_STYLESHEET + "\n</head>", 1)
    path.write_text(text, encoding="utf-8")


def breadcrumb_html(label, path_value):
    if path_value == "/earphones/":
        return (
            '<nav class="breadcrumbs" aria-label="パンくず">'
            '<a href="/">トップ</a><span>›</span>'
            f'<span aria-current="page">{escape(label)}</span></nav>'
        )

    if path_value == "/about/":
        return (
            '<nav class="breadcrumbs" aria-label="パンくず">'
            '<a href="/">トップ</a><span>›</span>'
            f'<span aria-current="page">{escape(label)}</span></nav>'
        )

    return (
        '<nav class="breadcrumbs" aria-label="パンくず">'
        '<a href="/">トップ</a><span>›</span>'
        '<a href="/earphones/">イヤホンランキング</a><span>›</span>'
        f'<span aria-current="page">{escape(label)}</span></nav>'
    )


def breadcrumb_json(label, path_value):
    items = [
        {"@type": "ListItem", "position": 1, "name": "トップ", "item": SITE + "/"}
    ]
    if path_value not in ("/earphones/", "/about/"):
        items.append(
            {
                "@type": "ListItem",
                "position": 2,
                "name": "イヤホンランキング",
                "item": SITE + "/earphones/",
            }
        )
        position = 3
    else:
        position = 2

    items.append(
        {
            "@type": "ListItem",
            "position": position,
            "name": label,
            "item": SITE + path_value,
        }
    )
    data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": items,
    }
    return '<script type="application/ld+json" data-seo="breadcrumb">\n' + json.dumps(
        data, ensure_ascii=False, indent=2
    ) + "\n</script>"


def add_breadcrumbs(path, label, path_value):
    text = path.read_text(encoding="utf-8")
    if SEO_STYLESHEET not in text:
        text = text.replace("</head>", SEO_STYLESHEET + "\n</head>", 1)

    if 'data-seo="breadcrumb"' not in text:
        text = text.replace(
            "</head>",
            breadcrumb_json(label, path_value) + "\n</head>",
            1,
        )

    if 'class="breadcrumbs"' not in text:
        text = text.replace(
            "<main>",
            "<main>\n" + breadcrumb_html(label, path_value),
            1,
        )

    path.write_text(text, encoding="utf-8")


def add_type_links_to_top():
    path = Path("public/index.html")
    text = path.read_text(encoding="utf-8")
    if SEO_STYLESHEET not in text:
        text = text.replace("</head>", SEO_STYLESHEET + "\n</head>", 1)

    if 'class="type-ranking-section"' in text:
        path.write_text(text, encoding="utf-8")
        return

    section = '''<section class="type-ranking-section" aria-label="種類別イヤホンランキング">
    <div class="type-ranking-head">
        <div><span class="section-kicker">種類から探す</span><h2>イヤホンのタイプを選ぶ</h2></div>
    </div>
    <div class="type-ranking-grid">
        <a href="/earphones/wireless/"><strong>ワイヤレスイヤホン</strong><span>Bluetooth・完全ワイヤレスを比較</span><b>ランキングを見る →</b></a>
        <a href="/earphones/wired/"><strong>有線イヤホン</strong><span>有線タイプだけで高評価を比較</span><b>ランキングを見る →</b></a>
        <a href="/earphones/earcuff/"><strong>イヤーカフ型イヤホン</strong><span>耳を挟むタイプを独立して比較</span><b>ランキングを見る →</b></a>
    </div>
</section>'''

    pattern = r'(<section class="purpose-section".*?</section>)'
    updated, count = re.subn(pattern, r'\1\n' + section, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError("トップページへ種類別導線を追加できませんでした。")
    path.write_text(updated, encoding="utf-8")


def add_related_links(path, current_url):
    text = path.read_text(encoding="utf-8")
    if 'class="related-rankings"' in text:
        return

    links = []
    for label, url in RELATED:
        if url == current_url:
            continue
        links.append(f'<a href="{url}">{escape(label)}</a>')

    section = (
        '<section class="related-rankings">'
        '<h2>関連するイヤホンランキング</h2>'
        '<div class="related-links">' + "".join(links) + '</div>'
        '</section>'
    )
    text = text.replace("</main>", section + "\n</main>", 1)
    path.write_text(text, encoding="utf-8")


def update_explanatory_pages():
    methodology_path = Path("public/earphones/methodology/index.html")
    methodology = methodology_path.read_text(encoding="utf-8")
    if "<h2>種類別ランキング</h2>" not in methodology:
        section = '''<section><h2>種類別ランキング</h2><p>ワイヤレス・有線・イヤーカフ型は、総合ランキングの30候補を単純に振り分けるのではなく、種類ごとに楽天市場の商品検索APIへ別の検索条件を指定して最大30件を取得します。</p><ul><li>ワイヤレス：商品名にワイヤレス、完全ワイヤレス、Bluetooth、ブルートゥース等が確認できること</li><li>有線：商品名に「有線」が明記され、ワイヤレス・Bluetoothを主用途とする商品ではないこと</li><li>イヤーカフ型：商品名にイヤーカフ、耳挟み、耳はさみ、クリップ式等が確認できること</li></ul><p>各種類でイヤホン本体の判定、レビュー10件以上などの共通条件を適用した後、その候補群の平均評価を用いてベイズ補正しTOP10を決定します。</p></section>'''
        methodology = methodology.replace(
            "<section><h2>レビュー件数ランキング</h2>",
            section + "\n<section><h2>レビュー件数ランキング</h2>",
            1,
        )
        methodology_path.write_text(methodology, encoding="utf-8")

    about_path = Path("public/about/index.html")
    about = about_path.read_text(encoding="utf-8")
    marker = "<li>レビュー件数が多い順のランキング</li>"
    if "<li>ワイヤレスイヤホンの高評価ランキング</li>" not in about and marker in about:
        replacement = (
            "<li>ワイヤレスイヤホンの高評価ランキング</li>"
            "<li>有線イヤホンの高評価ランキング</li>"
            "<li>イヤーカフ型イヤホンの高評価ランキング</li>"
            + marker
        )
        about = about.replace(marker, replacement, 1)
        about_path.write_text(about, encoding="utf-8")


def write_sitemap():
    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")
    dynamic = [
        "/",
        "/earphones/under-5000/",
        "/earphones/under-10000/",
        "/earphones/wireless/",
        "/earphones/wired/",
        "/earphones/earcuff/",
        "/earphones/most-reviewed/",
    ]
    static = [
        "/earphones/",
        "/earphones/methodology/",
        "/about/",
    ]

    rows = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in dynamic:
        rows.extend([
            "  <url>",
            f"    <loc>{SITE}{url}</loc>",
            f"    <lastmod>{today}</lastmod>",
            "  </url>",
        ])
    for url in static:
        rows.extend([
            "  <url>",
            f"    <loc>{SITE}{url}</loc>",
            "  </url>",
        ])
    rows.append("</urlset>")
    Path("public/sitemap.xml").write_text("\n".join(rows) + "\n", encoding="utf-8")


# カテゴリページは既存の表示名処理の対象外なので、同水準まで整える。
for category_path in CATEGORY_PATHS:
    clean_category_product_names(category_path)

# パンくずとBreadcrumbListを全下層ページへ付与する。
for path, (label, url) in PAGE_INFO.items():
    if not path.exists():
        raise RuntimeError(f"SEO構造化対象ページがありません: {path}")
    add_breadcrumbs(path, label, url)

# トップには種類別の検索入口を追加する。
add_type_links_to_top()

# ランキングページ同士を文脈付き内部リンクで接続する。
for ranking_path in RANKING_PATHS:
    _, current_url = PAGE_INFO[ranking_path]
    add_related_links(ranking_path, current_url)

update_explanatory_pages()
write_sitemap()

# 最終検証
for path in CATEGORY_PATHS:
    text = path.read_text(encoding="utf-8")
    if text.count('class="card"') != 10:
        raise RuntimeError(f"カテゴリページのカード数が10件ではありません: {path}")
    if text.count("hb.afl.rakuten.co.jp") < 10:
        raise RuntimeError(f"カテゴリページの楽天リンクが不足しています: {path}")
    if 'class="category-data-section"' not in text:
        raise RuntimeError(f"カテゴリ独自統計がありません: {path}")

sitemap = Path("public/sitemap.xml").read_text(encoding="utf-8")
for _, url in PAGE_INFO.values():
    if SITE + url not in sitemap:
        raise RuntimeError(f"sitemapにURLがありません: {url}")
if SITE + "/" not in sitemap:
    raise RuntimeError("sitemapにトップページがありません。")

print("Breadcrumbs / category internal links / sitemap SEO: OK")
