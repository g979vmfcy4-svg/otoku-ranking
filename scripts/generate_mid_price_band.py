import os
import json
import html
import re
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright


SITE_URL = "https://otoku-ranking.pages.dev/"
API_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
SEARCH_KEYWORD = "イヤホン"
EARPHONE_GENRE_ID = 502835
MIN_REVIEW_COUNT = 10
RANKING_SIZE = 10
BAYES_PRIOR_WEIGHT = 100
MIN_PRICE = 5001
MAX_PRICE = 10000
TARGET_PATH = Path("public/earphones/under-10000/index.html")

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
    "minPrice": MIN_PRICE,
    "maxPrice": MAX_PRICE,
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
                return {ok: false, status: 0, error: String(error)};
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
        "5,001〜10,000円ランキングの楽天API取得に失敗しました: "
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


def rejection_reason(item):
    name = normalize_text(item.get("itemName", ""))
    if to_int(item.get("genreId")) != EARPHONE_GENRE_ID:
        return "genreId不一致"
    if not any(word in name for word in EARPHONE_WORDS):
        return "商品名にイヤホン表現なし"
    for word in HARD_EXCLUDE_WORDS:
        if word in name:
            return f"除外語句: {word}"
    if to_int(item.get("reviewCount")) < MIN_REVIEW_COUNT:
        return "レビュー件数不足"
    rating = to_float(item.get("reviewAverage"))
    if not 0 < rating <= 5:
        return "レビュー評価異常"
    price = to_int(item.get("itemPrice"))
    if not MIN_PRICE <= price <= MAX_PRICE:
        return "価格帯不一致"
    affiliate_url = str(item.get("affiliateUrl") or "")
    if (
        not affiliate_url.startswith("https://")
        or "hb.afl.rakuten.co.jp" not in affiliate_url
    ):
        return "アフィリエイトURL不正"
    return ""


filtered = []
excluded = []
for item in items:
    reason = rejection_reason(item)
    if reason:
        excluded.append((reason, str(item.get("itemName", "商品名なし"))))
        continue
    filtered.append(item)

if len(filtered) < RANKING_SIZE:
    for reason, name in excluded[:20]:
        print(f"- {reason} | {name[:100]}")
    raise RuntimeError(
        "5,001〜10,000円の正常なイヤホン候補が10件未満のため更新を中止します。"
        f" 候補件数: {len(filtered)}"
    )

prior_rating = sum(
    to_float(item.get("reviewAverage")) for item in filtered
) / len(filtered)


def bayesian_score(item):
    rating = to_float(item.get("reviewAverage"))
    reviews = to_int(item.get("reviewCount"))
    return (
        reviews * rating + BAYES_PRIOR_WEIGHT * prior_rating
    ) / (reviews + BAYES_PRIOR_WEIGHT)


ranking_items = sorted(filtered, key=bayesian_score, reverse=True)[:RANKING_SIZE]

if any(
    not MIN_PRICE <= to_int(item.get("itemPrice")) <= MAX_PRICE
    for item in ranking_items
):
    raise RuntimeError("5,001〜10,000円ランキングに価格帯外の商品が含まれています。")


def build_cards(source_items):
    cards = []
    for rank, item in enumerate(source_items, 1):
        name = html.escape(str(item.get("itemName", "商品名なし")))
        shop = html.escape(str(item.get("shopName", "")))
        price = to_int(item.get("itemPrice"))
        rating = to_float(item.get("reviewAverage"))
        reviews = to_int(item.get("reviewCount"))
        image = html.escape(get_image_url(item), quote=True)
        link = html.escape(str(item.get("affiliateUrl") or ""), quote=True)
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


text = TARGET_PATH.read_text(encoding="utf-8")
card_matches = list(
    re.finditer(r'<article class="card">.*?</article>', text, re.DOTALL)
)
if len(card_matches) != RANKING_SIZE:
    raise RuntimeError(
        "5,001〜10,000円ページの元商品カードが10件ではありません。"
    )

updated_match = re.search(
    r'<strong>最終更新：</strong>\s*(.*?)<br>', text, re.DOTALL
)
updated_text = updated_match.group(1).strip() if updated_match else "毎日更新"

text = re.sub(
    r'<title>.*?</title>',
    '<title>5,001〜10,000円のイヤホン高評価ランキング｜楽天市場TOP10</title>',
    text,
    count=1,
    flags=re.DOTALL,
)
text = re.sub(
    r'<meta name="description" content="[^"]*">',
    '<meta name="description" content="楽天市場の5,001〜10,000円のイヤホンを、レビュー平均とレビュー件数の信頼度を補正して毎日比較。高評価TOP10を掲載しています。">',
    text,
    count=1,
)
text = re.sub(
    r'<h1>.*?</h1>',
    '<h1>5,001〜10,000円のイヤホン高評価ランキング</h1>',
    text,
    count=1,
    flags=re.DOTALL,
)
text = re.sub(
    r'(<header>\s*<div>\s*<h1>.*?</h1>\s*)<p>.*?</p>',
    r'\1<p>楽天市場の商品データから5,001〜10,000円のイヤホンだけを抽出し、毎日自動比較しています。</p>',
    text,
    count=1,
    flags=re.DOTALL,
)
text = re.sub(
    r'<div class="notice">.*?</div>',
    (
        '<div class="notice">\n'
        '        <span class="pr">広告・PR</span><br>\n'
        f'        <strong>最終更新：</strong> {updated_text}<br>\n'
        '        5,001〜10,000円かつレビュー10件以上の商品を対象に、候補商品の平均評価を基準にベイズ補正を行い、評価の高さとレビュー件数の信頼度を両方反映して順位を決定しています。\n'
        '    </div>'
    ),
    text,
    count=1,
    flags=re.DOTALL,
)

card_matches = list(
    re.finditer(r'<article class="card">.*?</article>', text, re.DOTALL)
)
text = (
    text[: card_matches[0].start()]
    + build_cards(ranking_items)
    + text[card_matches[-1].end() :]
)

if text.count('class="card"') != RANKING_SIZE:
    raise RuntimeError("5,001〜10,000円ページの生成後カード数が不正です。")
if text.count("hb.afl.rakuten.co.jp") < RANKING_SIZE:
    raise RuntimeError("5,001〜10,000円ページのアフィリエイトURL検証に失敗しました。")

temp_path = TARGET_PATH.with_suffix(".html.tmp")
temp_path.write_text(text, encoding="utf-8")
os.replace(temp_path, TARGET_PATH)

print("5,001〜10,000円ランキング生成成功")
print(f"API取得件数: {len(items)}")
print(f"有効候補件数: {len(filtered)}")
print(f"掲載件数: {len(ranking_items)}")
print(f"ベイズ事前平均: {prior_rating:.4f}")
print("価格帯検証: OK")
