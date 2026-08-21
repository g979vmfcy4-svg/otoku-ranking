from pathlib import Path
import re
import statistics


TARGETS = {
    Path("public/index.html"): "総合ランキングTOP10",
    Path("public/earphones/under-5000/index.html"): "5,000円以下ランキングTOP10",
    Path("public/earphones/under-10000/index.html"): "5,001〜10,000円ランキングTOP10",
    Path("public/earphones/most-reviewed/index.html"): "レビュー件数ランキングTOP10",
}

STYLESHEET = '<link rel="stylesheet" href="/assets/seo-hardening.css">'
CARD_RE = re.compile(r'<article class="card">(?P<body>.*?)</article>', re.DOTALL)
SUMMARY_RE = re.compile(r'<section class="quality-section ranking-data-summary">.*?</section>', re.DOTALL)


def parse_number(value):
    return int(value.replace(",", ""))


def parse_cards(text, label):
    items = []
    matches = list(CARD_RE.finditer(text))
    if len(matches) != 10:
        raise RuntimeError(f"{label}: 商品カードが10件ではありません ({len(matches)})")

    for match in matches:
        body = match.group("body")
        rating_match = re.search(r"★\s*([0-9.]+)\s*<span>\(([0-9,]+)件\)</span>", body, re.DOTALL)
        price_match = re.search(r'<div class="price">([0-9,]+)円</div>', body)
        if not rating_match or not price_match:
            raise RuntimeError(f"{label}: 商品カードの数値解析に失敗しました")
        items.append({
            "rating": float(rating_match.group(1)),
            "reviews": parse_number(rating_match.group(2)),
            "price": parse_number(price_match.group(1)),
        })
    return items, matches


def build_summary(label, items):
    prices = [item["price"] for item in items]
    ratings = [item["rating"] for item in items]
    reviews = [item["reviews"] for item in items]

    average_price = round(statistics.mean(prices))
    median_price = round(statistics.median(prices))
    average_rating = statistics.mean(ratings)
    median_reviews = round(statistics.median(reviews))
    total_reviews = sum(reviews)

    return f'''<section class="quality-section ranking-data-summary" aria-label="TOP10データ概要">
    <div class="summary-head">
        <span class="section-kicker">独自集計</span>
        <h2>今回の{label}データ</h2>
        <p>現在掲載しているTOP10の商品価格・楽天レビューを集計した値です。価格やレビュー件数は取得時点の情報です。</p>
    </div>
    <div class="ranking-summary-grid">
        <div><span>TOP10平均価格</span><strong>{average_price:,}円</strong></div>
        <div><span>価格中央値</span><strong>{median_price:,}円</strong></div>
        <div><span>平均レビュー評価</span><strong>★ {average_rating:.2f}</strong></div>
        <div><span>レビュー中央値</span><strong>{median_reviews:,}件</strong></div>
        <div><span>TOP10レビュー合計</span><strong>{total_reviews:,}件</strong></div>
    </div>
</section>'''


for path, label in TARGETS.items():
    if not path.exists():
        raise RuntimeError(f"対象ページがありません: {path}")

    text = path.read_text(encoding="utf-8")
    text = SUMMARY_RE.sub("", text)
    items, matches = parse_cards(text, label)

    # 既存のランキング10商品を先に見せたまま、その直後に独自集計を置く。
    insert_at = matches[-1].end()
    summary = build_summary(label, items)
    text = text[:insert_at] + "\n" + summary + text[insert_at:]

    if STYLESHEET not in text:
        if "</head>" not in text:
            raise RuntimeError(f"</head> がありません: {path}")
        text = text.replace("</head>", STYLESHEET + "\n</head>", 1)

    if text.count('class="ranking-data-summary"') != 1:
        raise RuntimeError(f"独自集計セクションの数が不正です: {path}")

    path.write_text(text, encoding="utf-8")

print("Ranking TOP10 statistics: OK")
