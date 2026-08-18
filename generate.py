import os
import json
import html
import urllib.parse
from datetime import datetime, timezone, timedelta
from string import Template

from playwright.sync_api import sync_playwright


SITE_URL = "https://otoku-ranking.pages.dev/"
API_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
SEARCH_KEYWORD = "イヤホン"
EARPHONE_GENRE_ID = 502835

MIN_REVIEW_COUNT = 10
RANKING_SIZE = 10
BAYES_PRIOR_WEIGHT = 100
UNDER_5000_MAX_PRICE = 5000
UNDER_10000_MAX_PRICE = 10000

GOOGLE_SITE_VERIFICATION = "xebuT18VaLulU2FGAl1MrnJnOgS4b1ZjrZcFaV45KyQ"

APPLICATION_ID = os.getenv("RAKUTEN_APPLICATION_ID", "").strip()
ACCESS_KEY = os.getenv("RAKUTEN_ACCESS_KEY", "").strip()
AFFILIATE_ID = os.getenv("RAKUTEN_AFFILIATE_ID", "").strip()

for name, value in {
    "RAKUTEN_APPLICATION_ID": APPLICATION_ID,
    "RAKUTEN_ACCESS_KEY": ACCESS_KEY,
    "RAKUTEN_AFFILIATE_ID": AFFILIATE_ID,
}.items():
    if not value:
        raise RuntimeError(f"{name} が設定されていません。")


# =========================================================
# 楽天API取得
# =========================================================

params = {
    "applicationId": APPLICATION_ID,
    "accessKey": ACCESS_KEY,
    "affiliateId": AFFILIATE_ID,
    "format": "json",
    "formatVersion": 2,
    "keyword": SEARCH_KEYWORD,
    "genreId": EARPHONE_GENRE_ID,
    "field": 1,
    "hits": 30,
    "imageFlag": 1,
    "hasReviewFlag": 1,
    "availability": 1,
    "sort": "-reviewCount",
}

api_url = API_URL + "?" + urllib.parse.urlencode(params)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(locale="ja-JP")
    page.set_default_timeout(15000)

    site_response = page.goto(
        SITE_URL,
        wait_until="domcontentloaded",
        timeout=15000,
    )

    if site_response is None or site_response.status >= 400:
        browser.close()
        raise RuntimeError("公開サイトを正常に開けませんでした。")

    result = page.evaluate(
        """
        async (url) => {
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), 12000);

            try {
                const response = await fetch(url, {
                    method: "GET",
                    cache: "no-store",
                    credentials: "omit",
                    signal: controller.signal
                });

                return {
                    ok: true,
                    status: response.status,
                    text: await response.text()
                };
            } catch (error) {
                return {
                    ok: false,
                    status: 0,
                    error: String(error)
                };
            } finally {
                clearTimeout(timer);
            }
        }
        """,
        api_url,
    )

    browser.close()

if not result.get("ok"):
    raise RuntimeError(
        "楽天APIへのアクセスに失敗しました: "
        + str(result.get("error", "不明なエラー"))
    )

if int(result.get("status", 0)) != 200:
    raise RuntimeError(
        f"楽天API HTTP {result.get('status')}\n"
        + result.get("text", "")[:1500]
    )

try:
    data = json.loads(result["text"])
except json.JSONDecodeError as error:
    raise RuntimeError("楽天APIのJSON解析に失敗しました。") from error

raw_items = data.get("items") or data.get("Items") or []
if not isinstance(raw_items, list):
    raise RuntimeError("楽天APIの商品一覧形式が想定外です。")

items = []
for entry in raw_items:
    if not isinstance(entry, dict):
        continue
    if isinstance(entry.get("Item"), dict):
        items.append(entry["Item"])
    elif isinstance(entry.get("item"), dict):
        items.append(entry["item"])
    else:
        items.append(entry)

if len(items) < RANKING_SIZE:
    raise RuntimeError(
        "楽天APIから取得できた商品が少なすぎます。"
        f"取得件数: {len(items)}"
    )


# =========================================================
# 共通関数
# =========================================================

def to_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def to_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def get_image_url(item):
    images = item.get("mediumImageUrls", [])
    if not images:
        return ""

    first = images[0]
    if isinstance(first, str):
        return first
    if isinstance(first, dict):
        return first.get("imageUrl", "")
    return ""


def normalize_text(value):
    return str(value or "").lower().replace("　", " ")


EARPHONE_WORDS = (
    "イヤホン",
    "イヤフォン",
    "earphone",
    "earphones",
    "earbud",
    "earbuds",
)

HARD_EXCLUDE_WORDS = (
    "イヤホンジャックストラップ",
    "イヤホンジャック用ストラップ",
    "イヤホンジャックアクセサリー",
    "イヤホンジャックピアス",
    "ジャックピアス",
    "防災ラジオ",
    "ポータブルラジオ",
    "ラジオ付きライト",
    "イヤホン変換アダプタ",
    "イヤホン変換アダプター",
    "オーディオ変換アダプタ",
    "オーディオ変換アダプター",
    "イヤホン変換ケーブル",
    "イヤホン延長ケーブル",
    "イヤホン分配ケーブル",
    "イヤホンスプリッター",
    "イヤホン収納ケースのみ",
    "イヤホンケースのみ",
    "充電ケースのみ",
    "交換用充電ケース",
)


def get_rejection_reason(item):
    name = normalize_text(item.get("itemName", ""))
    genre_id = to_int(item.get("genreId"))

    if genre_id != EARPHONE_GENRE_ID:
        return f"genreId不一致({genre_id})"

    if not any(word in name for word in EARPHONE_WORDS):
        return "商品名にイヤホン表現なし"

    for word in HARD_EXCLUDE_WORDS:
        if word in name:
            return f"除外語句: {word}"

    reviews = to_int(item.get("reviewCount"))
    if reviews < MIN_REVIEW_COUNT:
        return "レビュー件数不足"

    rating = to_float(item.get("reviewAverage"))
    if not 0 < rating <= 5:
        return "レビュー評価異常"

    price = to_int(item.get("itemPrice"))
    if price <= 0:
        return "価格異常"

    affiliate_url = str(item.get("affiliateUrl") or "")
    if (
        not affiliate_url.startswith("https://")
        or "hb.afl.rakuten.co.jp" not in affiliate_url
    ):
        return "アフィリエイトURL不正"

    return ""


def bayesian_score(item, prior_rating):
    rating = to_float(item.get("reviewAverage"))
    reviews = to_int(item.get("reviewCount"))
    return (
        reviews * rating
        + BAYES_PRIOR_WEIGHT * prior_rating
    ) / (reviews + BAYES_PRIOR_WEIGHT)


def rank_by_bayesian(source_items):
    if len(source_items) < RANKING_SIZE:
        raise RuntimeError(
            "ランキング候補が10件未満のため更新を中止します。"
            f" 候補件数: {len(source_items)}"
        )

    prior_rating = sum(
        to_float(item.get("reviewAverage"))
        for item in source_items
    ) / len(source_items)

    ranked = sorted(
        source_items,
        key=lambda item: bayesian_score(item, prior_rating),
        reverse=True,
    )

    return ranked[:RANKING_SIZE], prior_rating


def rank_by_review_count(source_items):
    if len(source_items) < RANKING_SIZE:
        raise RuntimeError(
            "レビュー件数ランキング候補が10件未満のため更新を中止します。"
            f" 候補件数: {len(source_items)}"
        )

    ranked = sorted(
        source_items,
        key=lambda item: to_int(item.get("reviewCount")),
        reverse=True,
    )[:RANKING_SIZE]

    counts = [
        to_int(item.get("reviewCount"))
        for item in ranked
    ]

    if any(
        current < following
        for current, following in zip(counts, counts[1:])
    ):
        raise RuntimeError(
            "レビュー件数ランキングの並び順が不正です。"
        )

    return ranked, counts


def build_cards(ranking_items):
    cards = []

    for rank, item in enumerate(ranking_items, 1):
        name = html.escape(str(item.get("itemName", "商品名なし")))
        shop = html.escape(str(item.get("shopName", "")))
        price = to_int(item.get("itemPrice"))
        rating = to_float(item.get("reviewAverage"))
        reviews = to_int(item.get("reviewCount"))
        image = html.escape(get_image_url(item), quote=True)
        affiliate_url = str(item.get("affiliateUrl") or "")

        if (
            not affiliate_url.startswith("https://")
            or "hb.afl.rakuten.co.jp" not in affiliate_url
        ):
            raise RuntimeError(
                "アフィリエイトURLが不正です。"
                f"順位{rank}の商品を確認してください。"
            )

        link = html.escape(affiliate_url, quote=True)
        img = (
            f'<img src="{image}" alt="{name}" loading="lazy">'
            if image
            else ""
        )

        cards.append(
            f"""
            <article class="card">
                <div class="rank">{rank}</div>
                <div class="photo">{img}</div>
                <div class="info">
                    <h2>{name}</h2>
                    <div class="shop">{shop}</div>
                    <div class="rating">
                        ★ {rating:.2f}
                        <span>({reviews:,}件)</span>
                    </div>
                    <div class="price">{price:,}円</div>
                    <a
                        class="button"
                        href="{link}"
                        target="_blank"
                        rel="nofollow sponsored noopener"
                    >楽天市場で見る</a>
                </div>
            </article>
            """
        )

    return "".join(cards)


# =========================================================
# 商品抽出・ランキング
# =========================================================

filtered = []
excluded_items = []

for item in items:
    reason = get_rejection_reason(item)
    if reason:
        excluded_items.append({
            "name": str(item.get("itemName", "商品名なし")),
            "reason": reason,
        })
        continue
    filtered.append(item)

if len(filtered) < RANKING_SIZE:
    for excluded in excluded_items[:20]:
        print(
            f"- {excluded['reason']} | "
            f"{excluded['name'][:100]}"
        )
    raise RuntimeError(
        "正常なイヤホン候補が10件未満のため更新を中止します。"
        f" 候補件数: {len(filtered)}"
    )

ranking_items, prior_rating = rank_by_bayesian(filtered)

under_5000_filtered = [
    item
    for item in filtered
    if to_int(item.get("itemPrice")) <= UNDER_5000_MAX_PRICE
]
under_5000_ranking_items, under_5000_prior_rating = rank_by_bayesian(
    under_5000_filtered
)

under_10000_filtered = [
    item
    for item in filtered
    if to_int(item.get("itemPrice")) <= UNDER_10000_MAX_PRICE
]
under_10000_ranking_items, under_10000_prior_rating = rank_by_bayesian(
    under_10000_filtered
)

most_reviewed_ranking_items, most_reviewed_counts = rank_by_review_count(
    filtered
)

if any(
    to_int(item.get("itemPrice")) > UNDER_5000_MAX_PRICE
    for item in under_5000_ranking_items
):
    raise RuntimeError(
        "5,000円以下ランキングに5,000円超の商品が含まれています。"
    )

if any(
    to_int(item.get("itemPrice")) > UNDER_10000_MAX_PRICE
    for item in under_10000_ranking_items
):
    raise RuntimeError(
        "1万円以下ランキングに1万円超の商品が含まれています。"
    )


# =========================================================
# HTML生成
# =========================================================

updated = datetime.now(
    timezone(timedelta(hours=9))
).strftime("%Y年%m月%d日 %H:%M")

PAGE_TEMPLATE = Template(
    """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="google-site-verification" content="$google_verification">
<meta name="description" content="$meta_description">
<meta name="robots" content="index,follow">
<link rel="canonical" href="$canonical_url">
<title>$page_title</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    background: #f5f6f8;
    color: #222;
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
}
header {
    background: #fff;
    padding: 24px 16px;
    border-bottom: 1px solid #ddd;
}
header div, main, footer, .ranking-nav {
    max-width: 760px;
    margin: auto;
}
h1 { margin: 0 0 8px; font-size: 26px; }
header p { margin: 0; color: #666; line-height: 1.6; }
.ranking-nav {
    padding: 14px 12px 0;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}
.ranking-nav a {
    background: #fff;
    color: #333;
    text-decoration: none;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 8px 11px;
    font-size: 13px;
    font-weight: bold;
}
main { padding: 18px 12px; }
.notice {
    background: #fff;
    padding: 14px;
    border-radius: 12px;
    margin-bottom: 18px;
    line-height: 1.7;
    font-size: 14px;
}
.pr {
    display: inline-block;
    background: #eee;
    border-radius: 5px;
    padding: 3px 7px;
    font-size: 12px;
    font-weight: bold;
}
.card {
    position: relative;
    display: flex;
    gap: 14px;
    background: #fff;
    padding: 16px;
    margin-bottom: 14px;
    border-radius: 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,.05);
}
.rank {
    position: absolute;
    top: -7px;
    left: -5px;
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: #222;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
}
.photo {
    width: 110px;
    min-width: 110px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.photo img { width: 110px; height: 110px; object-fit: contain; }
.info { flex: 1; }
h2 { font-size: 15px; line-height: 1.5; margin: 0 0 7px; }
.shop { font-size: 12px; color: #777; margin-bottom: 7px; }
.rating { font-weight: bold; margin-bottom: 7px; }
.rating span { font-size: 12px; color: #777; font-weight: normal; }
.price { font-size: 21px; font-weight: bold; margin-bottom: 12px; }
.button {
    display: inline-block;
    background: #bf0000;
    color: #fff;
    text-decoration: none;
    padding: 10px 14px;
    border-radius: 8px;
    font-weight: bold;
}
footer {
    padding: 18px 14px 40px;
    color: #666;
    font-size: 12px;
    line-height: 1.7;
}
@media(max-width: 520px) {
    .photo { width: 90px; min-width: 90px; }
    .photo img { width: 90px; height: 90px; }
    h2 { font-size: 13px; }
    .price { font-size: 18px; }
    .button { font-size: 13px; padding: 9px 11px; }
}
</style>
</head>
<body>
<header>
    <div>
        <h1>$h1</h1>
        <p>$header_description</p>
    </div>
</header>
<nav class="ranking-nav" aria-label="イヤホンランキング">
    <a href="/">高評価ランキング</a>
    <a href="/earphones/under-5000/">5,000円以下</a>
    <a href="/earphones/under-10000/">1万円以下</a>
    <a href="/earphones/most-reviewed/">レビュー件数順</a>
</nav>
<main>
    <div class="notice">
        <span class="pr">広告・PR</span><br>
        <strong>最終更新：</strong> $updated<br>
        $ranking_description
    </div>
    $cards
</main>
<footer>
    <p>
        当サイトは楽天アフィリエイトを利用しています。
        価格・在庫等は取得時点の情報です。
        購入前に楽天市場の商品ページで最新情報をご確認ください。
    </p>
    <a href="https://developers.rakuten.com/" target="_blank" rel="noopener">
        Supported by Rakuten Developers
    </a>
</footer>
</body>
</html>
"""
)


def build_page(
    *,
    title,
    meta_description,
    canonical_url,
    h1,
    header_description,
    ranking_description,
    ranking_items,
):
    page_html = PAGE_TEMPLATE.substitute(
        google_verification=GOOGLE_SITE_VERIFICATION,
        page_title=title,
        meta_description=meta_description,
        canonical_url=canonical_url,
        h1=h1,
        header_description=header_description,
        ranking_description=ranking_description,
        updated=updated,
        cards=build_cards(ranking_items),
    )

    if (
        "<html" not in page_html
        or "</html>" not in page_html
        or page_html.count('class="card"') != RANKING_SIZE
    ):
        raise RuntimeError(
            f"生成HTMLの検証に失敗しました: {canonical_url}"
        )

    return page_html


page_html = build_page(
    title="イヤホン高評価ランキング｜楽天レビューを毎日自動比較",
    meta_description=(
        "楽天市場のイヤホンを、レビュー評価とレビュー件数をもとに"
        "毎日自動比較する高評価ランキングです。"
    ),
    canonical_url="https://otoku-ranking.pages.dev/",
    h1="イヤホン 高評価ランキング",
    header_description=(
        "楽天市場の商品データをもとに、レビュー評価とレビュー件数から"
        "毎日自動比較しています。"
    ),
    ranking_description=(
        "レビュー10件以上の商品を対象に、候補商品の平均評価を基準に"
        "ベイズ補正を行い、評価の高さとレビュー件数の信頼度を"
        "両方反映して順位を決定しています。"
    ),
    ranking_items=ranking_items,
)

under_5000_page_html = build_page(
    title=(
        "5000円以下のイヤホン高評価ランキング｜"
        "楽天レビューを毎日自動比較"
    ),
    meta_description=(
        "楽天市場の5,000円以下のイヤホンを、レビュー評価とレビュー件数の"
        "信頼度をもとに毎日自動比較する高評価ランキングです。"
    ),
    canonical_url=(
        "https://otoku-ranking.pages.dev/earphones/under-5000/"
    ),
    h1="5,000円以下 イヤホン高評価ランキング",
    header_description=(
        "楽天市場の商品データから5,000円以下のイヤホンだけを抽出し、"
        "毎日自動比較しています。"
    ),
    ranking_description=(
        "5,000円以下かつレビュー10件以上の商品を対象に、候補商品の"
        "平均評価を基準にベイズ補正を行い、評価の高さとレビュー件数の"
        "信頼度を両方反映して順位を決定しています。"
    ),
    ranking_items=under_5000_ranking_items,
)

under_10000_page_html = build_page(
    title=(
        "1万円以下のイヤホン高評価ランキング｜"
        "楽天レビューを毎日自動比較"
    ),
    meta_description=(
        "楽天市場の1万円以下のイヤホンを、レビュー評価とレビュー件数の"
        "信頼度をもとに毎日自動比較する高評価ランキングです。"
    ),
    canonical_url=(
        "https://otoku-ranking.pages.dev/earphones/under-10000/"
    ),
    h1="1万円以下 イヤホン高評価ランキング",
    header_description=(
        "楽天市場の商品データから1万円以下のイヤホンだけを抽出し、"
        "毎日自動比較しています。"
    ),
    ranking_description=(
        "1万円以下かつレビュー10件以上の商品を対象に、候補商品の"
        "平均評価を基準にベイズ補正を行い、評価の高さとレビュー件数の"
        "信頼度を両方反映して順位を決定しています。"
    ),
    ranking_items=under_10000_ranking_items,
)

most_reviewed_page_html = build_page(
    title=(
        "レビューが多いイヤホンランキング｜"
        "楽天レビュー件数を毎日比較"
    ),
    meta_description=(
        "楽天市場のイヤホンをレビュー件数が多い順に毎日自動比較。"
        "イヤホン本体だけを対象にレビュー件数TOP10を掲載します。"
    ),
    canonical_url=(
        "https://otoku-ranking.pages.dev/earphones/most-reviewed/"
    ),
    h1="レビュー件数が多い イヤホンランキング",
    header_description=(
        "楽天市場の商品データからイヤホン本体だけを抽出し、"
        "レビュー件数が多い順に毎日ランキングしています。"
    ),
    ranking_description=(
        "レビュー10件以上のイヤホンを対象に、楽天の商品データの"
        "レビュー件数が多い順で掲載しています。評価点は表示しますが、"
        "このランキングの順位計算には使用していません。"
    ),
    ranking_items=most_reviewed_ranking_items,
)


# =========================================================
# 保存
# =========================================================

pages_to_write = [
    ("public/index.html", page_html),
    (
        "public/earphones/under-5000/index.html",
        under_5000_page_html,
    ),
    (
        "public/earphones/under-10000/index.html",
        under_10000_page_html,
    ),
    (
        "public/earphones/most-reviewed/index.html",
        most_reviewed_page_html,
    ),
]

# 全ページを検証してから一括で置換する。
for final_path, page_content in pages_to_write:
    if (
        "<html" not in page_content
        or "</html>" not in page_content
        or page_content.count('class="card"') != RANKING_SIZE
    ):
        raise RuntimeError(
            f"生成HTMLの最終検証に失敗しました: {final_path}"
        )

temp_files = []
for final_path, page_content in pages_to_write:
    directory = os.path.dirname(final_path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    temp_path = final_path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(page_content)
    temp_files.append((temp_path, final_path))

for temp_path, final_path in temp_files:
    os.replace(temp_path, final_path)


# =========================================================
# ログ
# =========================================================

print("楽天ランキング生成成功")
print(f"API取得件数: {len(items)}")
print(f"イヤホン候補件数: {len(filtered)}")
print(f"除外件数: {len(excluded_items)}")

if excluded_items:
    print("除外商品の確認ログ:")
    for excluded in excluded_items[:10]:
        print(
            f"- {excluded['reason']} | "
            f"{excluded['name'][:100]}"
        )

print(f"総合掲載件数: {len(ranking_items)}")
print(f"総合ベイズ事前平均: {prior_rating:.4f}")
print(f"5,000円以下候補件数: {len(under_5000_filtered)}")
print(f"5,000円以下掲載件数: {len(under_5000_ranking_items)}")
print(f"5,000円以下ベイズ事前平均: {under_5000_prior_rating:.4f}")
print(f"1万円以下候補件数: {len(under_10000_filtered)}")
print(f"1万円以下掲載件数: {len(under_10000_ranking_items)}")
print(f"1万円以下ベイズ事前平均: {under_10000_prior_rating:.4f}")
print(f"レビュー件数順掲載件数: {len(most_reviewed_ranking_items)}")
print(f"レビュー件数最多: {most_reviewed_counts[0]:,}件")
print(f"ベイズ事前レビュー数: {BAYES_PRIOR_WEIGHT}")
print("Genre validation: OK")
print("Affiliate URL validation: OK")
print("Fail-safe HTML validation: OK")
print("総合・5,000円以下・1万円以下・レビュー件数順ランキングを更新しました。")
