from pathlib import Path
import html
import re
import statistics


PAGES = {
    Path("public/index.html"): "bayesian",
    Path("public/earphones/under-5000/index.html"): "bayesian",
    Path("public/earphones/under-10000/index.html"): "bayesian",
    Path("public/earphones/wireless/index.html"): "bayesian",
    Path("public/earphones/wired/index.html"): "bayesian",
    Path("public/earphones/earcuff/index.html"): "bayesian",
    Path("public/earphones/most-reviewed/index.html"): "review_count",
}

STYLESHEET = '<link rel="stylesheet" href="/assets/data-insights.css">'
CARD_RE = re.compile(r'<article class="card">(?P<body>.*?)</article>', re.DOTALL)
OLD_INSIGHT_RE = re.compile(
    r'\s*<!-- rank-insight:start -->.*?<!-- rank-insight:end -->\s*',
    re.DOTALL,
)


def parse_number(pattern, body, label):
    match = re.search(pattern, body, re.DOTALL)
    if not match:
        raise RuntimeError(f"{label}を取得できません")
    return match


def parse_cards(text, path):
    cards = []
    for match in CARD_RE.finditer(text):
        body = OLD_INSIGHT_RE.sub("\n", match.group("body"))
        rank_match = parse_number(r'<div class="rank">\s*(\d+)\s*</div>', body, f"順位: {path}")
        rating_match = parse_number(
            r'★\s*([0-9.]+)\s*<span>\(([0-9,]+)件\)</span>',
            body,
            f"評価/レビュー: {path}",
        )
        price_match = parse_number(
            r'<div class="price">\s*([0-9,]+)円\s*</div>',
            body,
            f"価格: {path}",
        )
        cards.append({
            "rank": int(rank_match.group(1)),
            "rating": float(rating_match.group(1)),
            "reviews": int(rating_match.group(2).replace(",", "")),
            "price": int(price_match.group(1).replace(",", "")),
            "body": body,
        })

    if len(cards) != 10:
        raise RuntimeError(f"ランキングカードが10件ではありません: {path} ({len(cards)})")
    if sorted(card["rank"] for card in cards) != list(range(1, 11)):
        raise RuntimeError(f"ランキング順位が1〜10ではありません: {path}")
    return cards


def competition_rank(value, values):
    return 1 + sum(other > value for other in values)


def rating_context(rating, average):
    diff = rating - average
    if abs(diff) < 0.005:
        return f"表示評価★{rating:.2f}はTOP10平均と同水準"
    direction = "高い" if diff > 0 else "低い"
    return f"表示評価★{rating:.2f}はTOP10平均より{abs(diff):.2f}{direction}"


def price_context(price, median):
    if median <= 0:
        return "価格中央値との比較対象外"
    pct = (price - median) / median * 100
    if abs(pct) < 3:
        return f"価格{price:,}円はTOP10中央値とほぼ同水準"
    direction = "安い" if pct < 0 else "高い"
    return f"価格{price:,}円はTOP10中央値より{abs(pct):.0f}%{direction}"


def build_insight(card, cards, mode):
    ratings = [item["rating"] for item in cards]
    reviews = [item["reviews"] for item in cards]
    prices = [item["price"] for item in cards]
    average_rating = statistics.mean(ratings)
    median_price = statistics.median(prices)

    rating_rank = competition_rank(card["rating"], ratings)
    review_rank = competition_rank(card["reviews"], reviews)
    rating_text = rating_context(card["rating"], average_rating)
    price_text = price_context(card["price"], median_price)

    if mode == "review_count":
        sentence = (
            f"レビュー{card['reviews']:,}件でTOP10内{review_rank}位。"
            f"このページはレビュー件数順のため、この件数が順位の基準です。"
            f"{rating_text}（評価順位はTOP10内{rating_rank}位）。{price_text}。"
        )
    else:
        sentence = (
            f"レビュー件数を考慮した補正後評価で{card['rank']}位。"
            f"{rating_text}（評価順位はTOP10内{rating_rank}位）、"
            f"レビュー件数は{card['reviews']:,}件でTOP10内{review_rank}位。"
            f"{price_text}。"
        )

    return (
        '<!-- rank-insight:start -->\n'
        '<div class="card-insight" aria-label="この商品の順位データ">\n'
        '  <div class="card-insight-label">データで見る</div>\n'
        f'  <p>{html.escape(sentence)}</p>\n'
        '</div>\n'
        '<!-- rank-insight:end -->'
    )


def insert_insight(body, insight, path):
    updated, count = re.subn(
        r'(\s*<a\s+class="button")',
        "\n" + insight + r'\1',
        body,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError(f"商品カードへ順位説明を挿入できません: {path}")
    return updated


def process(path, mode):
    if not path.exists():
        raise RuntimeError(f"対象ページがありません: {path}")

    text = path.read_text(encoding="utf-8")
    text = OLD_INSIGHT_RE.sub("\n", text)
    if STYLESHEET not in text:
        text = text.replace("</head>", STYLESHEET + "\n</head>", 1)

    cards = parse_cards(text, path)
    by_rank = {card["rank"]: card for card in cards}

    def replace_card(match):
        body = OLD_INSIGHT_RE.sub("\n", match.group("body"))
        rank_match = re.search(r'<div class="rank">\s*(\d+)\s*</div>', body)
        if not rank_match:
            raise RuntimeError(f"カード順位を再取得できません: {path}")
        rank = int(rank_match.group(1))
        card = by_rank.get(rank)
        if not card:
            raise RuntimeError(f"順位データがありません: {path} rank={rank}")
        insight = build_insight(card, cards, mode)
        return '<article class="card">' + insert_insight(body, insight, path) + '</article>'

    text = CARD_RE.sub(replace_card, text)

    if text.count('<!-- rank-insight:start -->') != 10:
        raise RuntimeError(f"順位説明が10件ではありません: {path}")
    if text.count(STYLESHEET) != 1:
        raise RuntimeError(f"順位説明CSSの読み込み件数が不正です: {path}")
    if mode == "bayesian" and text.count("補正後評価で") != 10:
        raise RuntimeError(f"補正後評価の説明件数が不正です: {path}")
    if mode == "review_count" and text.count("このページはレビュー件数順") != 10:
        raise RuntimeError(f"レビュー件数順の説明件数が不正です: {path}")

    path.write_text(text, encoding="utf-8")
    print(f"Ranking reasons: OK {path}")


for page, ranking_mode in PAGES.items():
    process(page, ranking_mode)
