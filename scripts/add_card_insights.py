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


def signed_decimal(value):
    if abs(value) < 0.005:
        return "±0.00"
    sign = "+" if value > 0 else "−"
    return f"{sign}{abs(value):.2f}"


def signed_yen(value):
    rounded = round(value)
    if abs(rounded) < 100:
        return "ほぼ同水準"
    sign = "+" if rounded > 0 else "−"
    return f"{sign}{abs(rounded):,}円"


def metric(label, value):
    return (
        '<div class="insight-metric">'
        f'<span>{html.escape(label)}</span>'
        f'<strong>{html.escape(value)}</strong>'
        '</div>'
    )


def build_insight(card, cards, mode):
    ratings = [item["rating"] for item in cards]
    reviews = [item["reviews"] for item in cards]
    prices = [item["price"] for item in cards]
    average_rating = statistics.mean(ratings)
    median_price = statistics.median(prices)

    rating_rank = competition_rank(card["rating"], ratings)
    review_rank = competition_rank(card["reviews"], reviews)
    rating_delta = card["rating"] - average_rating
    price_delta = card["price"] - median_price

    if mode == "review_count":
        primary_label = "レビュー件数"
        primary_value = f"{card['rank']}位"
    else:
        primary_label = "補正評価"
        primary_value = f"{card['rank']}位"

    metrics = "".join([
        metric(primary_label, primary_value),
        metric("評価順位", f"{rating_rank}位"),
        metric("レビュー数", f"{review_rank}位"),
    ])
    detail = (
        f"★{card['rating']:.2f}（TOP10平均{signed_decimal(rating_delta)}）"
        f"・{card['reviews']:,}件"
        f"・{card['price']:,}円（価格中央値{signed_yen(price_delta)}）"
    )

    return (
        '<!-- rank-insight:start -->\n'
        '<div class="card-insight" aria-label="この商品の順位データ">\n'
        '  <div class="card-insight-label">順位の根拠</div>\n'
        f'  <div class="insight-metrics">{metrics}</div>\n'
        f'  <p class="insight-detail">{html.escape(detail)}</p>\n'
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
    if text.count('class="insight-metrics"') != 10:
        raise RuntimeError(f"順位指標の表示件数が不正です: {path}")
    if text.count(STYLESHEET) != 1:
        raise RuntimeError(f"順位説明CSSの読み込み件数が不正です: {path}")
    if mode == "bayesian" and text.count("補正評価") < 10:
        raise RuntimeError(f"補正評価の表示件数が不正です: {path}")
    if mode == "review_count" and text.count("レビュー件数") < 10:
        raise RuntimeError(f"レビュー件数の表示件数が不正です: {path}")

    path.write_text(text, encoding="utf-8")
    print(f"Ranking reasons: OK {path}")


for page, ranking_mode in PAGES.items():
    process(page, ranking_mode)
