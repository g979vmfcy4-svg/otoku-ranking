from pathlib import Path
import re


PAGE_SETTINGS = {
    Path("public/index.html"): {
        "title": "イヤホン高評価ランキング｜楽天市場レビューTOP10を毎日比較",
        "description": (
            "楽天市場のイヤホンを、レビュー平均とレビュー件数をベイズ補正して"
            "毎日比較。高評価イヤホンTOP10を掲載しています。"
        ),
        "h1": "楽天市場 イヤホン高評価ランキング",
    },
    Path("public/earphones/index.html"): {
        "title": "イヤホンランキング一覧｜価格・種類・レビューで楽天市場を比較",
        "description": (
            "楽天市場のイヤホンを、総合・価格帯・ワイヤレス・有線・イヤーカフ・"
            "レビュー件数など複数の軸から比較できるランキング一覧です。"
        ),
        "h1": "楽天市場 イヤホンランキング一覧",
    },
    Path("public/earphones/under-5000/index.html"): {
        "title": "5,000円以下のイヤホン高評価ランキング｜楽天市場TOP10",
        "description": (
            "楽天市場の5,000円以下のイヤホンを、レビュー平均とレビュー件数の"
            "信頼度を補正して毎日比較。高評価TOP10を掲載しています。"
        ),
        "h1": "5,000円以下のイヤホン高評価ランキング",
    },
    Path("public/earphones/under-10000/index.html"): {
        "title": "5,001〜10,000円のイヤホン高評価ランキング｜楽天市場TOP10",
        "description": (
            "楽天市場の5,001〜10,000円のイヤホンを、レビュー平均とレビュー件数の"
            "信頼度を補正して毎日比較。高評価TOP10を掲載しています。"
        ),
        "h1": "5,001〜10,000円のイヤホン高評価ランキング",
    },
    Path("public/earphones/wireless/index.html"): {
        "title": "ワイヤレスイヤホン高評価ランキング｜楽天市場TOP10",
        "description": (
            "楽天市場のワイヤレスイヤホンをレビュー平均とレビュー件数の信頼度を"
            "補正して毎日比較。高評価TOP10と独自集計データを掲載しています。"
        ),
        "h1": "楽天市場 ワイヤレスイヤホン高評価ランキング",
    },
    Path("public/earphones/wired/index.html"): {
        "title": "有線イヤホン高評価ランキング｜楽天市場TOP10",
        "description": (
            "楽天市場の有線イヤホンをレビュー平均とレビュー件数の信頼度を補正して"
            "毎日比較。高評価TOP10と独自集計データを掲載しています。"
        ),
        "h1": "楽天市場 有線イヤホン高評価ランキング",
    },
    Path("public/earphones/earcuff/index.html"): {
        "title": "イヤーカフ型イヤホン高評価ランキング｜楽天市場TOP10",
        "description": (
            "楽天市場のイヤーカフ型イヤホンをレビュー平均とレビュー件数の信頼度を"
            "補正して毎日比較。高評価TOP10と独自集計データを掲載しています。"
        ),
        "h1": "楽天市場 イヤーカフ型イヤホン高評価ランキング",
    },
    Path("public/earphones/most-reviewed/index.html"): {
        "title": "レビュー件数が多いイヤホンランキング｜楽天市場TOP10",
        "description": (
            "楽天市場のイヤホンをレビュー件数が多い順に毎日比較。"
            "イヤホン本体だけを対象にレビュー件数TOP10を掲載しています。"
        ),
        "h1": "レビュー件数が多いイヤホンランキング",
    },
    Path("public/earphones/methodology/index.html"): {
        "title": "イヤホンランキングの決め方｜評価基準・ベイズ補正・除外条件",
        "description": (
            "楽天市場のイヤホンランキングで使う評価基準、ベイズ補正、価格帯・"
            "種類別ランキング、レビュー件数順、商品除外条件、更新方法を公開しています。"
        ),
        "h1": "イヤホンランキングの決め方",
    },
    Path("public/about/index.html"): {
        "title": "このサイトについて｜楽天市場イヤホンランキング",
        "description": (
            "楽天市場のイヤホンを客観的な商品データで比較する当サイトの目的、"
            "ランキング方針、更新方法、広告・アフィリエイトについて説明します。"
        ),
        "h1": "このイヤホンランキングサイトについて",
    },
}

NAV_HTML = """<nav class="ranking-nav" aria-label="イヤホンランキング">
    <a href="/earphones/">ランキング一覧</a>
    <a href="/">総合</a>
    <a href="/earphones/under-5000/">5,000円以下</a>
    <a href="/earphones/under-10000/">5千〜1万円</a>
    <a href="/earphones/wireless/">ワイヤレス</a>
    <a href="/earphones/wired/">有線</a>
    <a href="/earphones/earcuff/">イヤーカフ</a>
    <a href="/earphones/most-reviewed/">レビュー件数順</a>
    <a href="/earphones/methodology/">ランキング基準</a>
    <a href="/about/">このサイトについて</a>
</nav>"""

WEBSITE_STRUCTURED_DATA = """<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "イヤホンランキング",
  "url": "https://otoku-ranking.pages.dev/"
}
</script>"""


def replace_single(pattern, replacement, text, label):
    updated, count = re.subn(
        pattern,
        replacement,
        text,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError(f"{label} の置換件数が想定外です: {count}")
    return updated


for path, settings in PAGE_SETTINGS.items():
    if not path.exists():
        raise RuntimeError(f"SEO対象ページが見つかりません: {path}")

    text = path.read_text(encoding="utf-8")

    text = replace_single(
        r"<title>.*?</title>",
        f"<title>{settings['title']}</title>",
        text,
        f"title: {path}",
    )
    text = replace_single(
        r'<meta name="description" content="[^"]*">',
        f'<meta name="description" content="{settings["description"]}">',
        text,
        f"description: {path}",
    )
    text = replace_single(
        r"<h1>.*?</h1>",
        f"<h1>{settings['h1']}</h1>",
        text,
        f"h1: {path}",
    )
    text = replace_single(
        r'<nav class="ranking-nav" aria-label="イヤホンランキング">.*?</nav>',
        NAV_HTML,
        text,
        f"navigation: {path}",
    )

    if path == Path("public/index.html"):
        if '"@type": "WebSite"' not in text:
            text = replace_single(
                r"</head>",
                WEBSITE_STRUCTURED_DATA + "\n</head>",
                text,
                "WebSite structured data",
            )

    path.write_text(text, encoding="utf-8")

print("SEO title/description/H1/navigation optimization: OK")
