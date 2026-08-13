import os
import json
import html
import math
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta


# =========================================================
# 1. GitHub Secretsから楽天の認証情報を取得
# =========================================================

APPLICATION_ID = os.getenv("RAKUTEN_APPLICATION_ID", "").strip()
ACCESS_KEY = os.getenv("RAKUTEN_ACCESS_KEY", "").strip()
AFFILIATE_ID = os.getenv("RAKUTEN_AFFILIATE_ID", "").strip()

if not APPLICATION_ID:
    raise RuntimeError("RAKUTEN_APPLICATION_ID が設定されていません。")

if not ACCESS_KEY:
    raise RuntimeError("RAKUTEN_ACCESS_KEY が設定されていません。")

if not AFFILIATE_ID:
    raise RuntimeError("RAKUTEN_AFFILIATE_ID が設定されていません。")


# =========================================================
# 2. 楽天市場商品検索API
# =========================================================

API_URL = (
    "https://openapi.rakuten.co.jp/"
    "ichibams/api/IchibaItem/Search/20260701"
)

SEARCH_KEYWORD = "イヤホン"


# =========================================================
# 3. APIに渡す条件
# =========================================================

params = {
    "applicationId": APPLICATION_ID,
    "accessKey": ACCESS_KEY,
    "affiliateId": AFFILIATE_ID,
    "format": "json",
    "formatVersion": 2,
    "keyword": SEARCH_KEYWORD,
    "hits": 30,
    "imageFlag": 1,
    "hasReviewFlag": 1,
    "availability": 1,
    "sort": "-reviewCount",
}

url = API_URL + "?" + urllib.parse.urlencode(params)


# =========================================================
# 4. 楽天APIから商品データを取得
# =========================================================

try:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "otoku-ranking/1.0"
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        response_text = response.read().decode("utf-8")
        data = json.loads(response_text)

except urllib.error.HTTPError as e:
    error_body = e.read().decode("utf-8", errors="replace")
    raise RuntimeError(
        f"楽天APIでHTTPエラーが発生しました。\n"
        f"HTTP Status: {e.code}\n"
        f"Response: {error_body}"
    )

except urllib.error.URLError as e:
    raise RuntimeError(
        f"楽天APIへの接続に失敗しました。\n"
        f"{e}"
    )

except json.JSONDecodeError as e:
    raise RuntimeError(
        f"楽天APIのJSON解析に失敗しました。\n"
        f"{e}"
    )


# =========================================================
# 5. 商品一覧を取得
# =========================================================

items = data.get("items", [])

if not items:
    raise RuntimeError(
        "楽天APIから商品が1件も取得できませんでした。"
    )


# =========================================================
# 6. 数値変換用
# =========================================================

def to_int(value):
    try:
        return int(value or 0)
    except (ValueError, TypeError):
        return 0


def to_float(value):
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0.0


# =========================================================
# 7. 商品画像を取得
# =========================================================

def get_image_url(item):
    images = item.get("mediumImageUrls", [])

    if not images:
        return ""

    first = images[0]

    # formatVersion=2では通常こちら
    if isinstance(first, str):
        return first

    # 念のため旧形式にも対応
    if isinstance(first, dict):
        return first.get("imageUrl", "")

    return ""


# =========================================================
# 8. 商品を絞り込み
# =========================================================

filtered_items = []

for item in items:
    review_count = to_int(item.get("reviewCount"))
    review_average = to_float(item.get("reviewAverage"))
    price = to_int(item.get("itemPrice"))

    # レビューが少なすぎる商品を除外
    if review_count < 10:
        continue

    if review_average <= 0:
        continue

    if price <= 0:
        continue

    filtered_items.append(item)


if not filtered_items:
    raise RuntimeError(
        "ランキング条件を満たす商品がありませんでした。"
    )


# =========================================================
# 9. 独自スコア計算
#
# 評価だけではレビュー数10件の★5.0などが
# 上位になりすぎるため、レビュー数も加味します。
# =========================================================

def calculate_score(item):
    review_average = to_float(item.get("reviewAverage"))
    review_count = to_int(item.get("reviewCount"))

    return (
        review_average * 20
        + math.log10(review_count + 1) * 8
    )


filtered_items.sort(
    key=calculate_score,
    reverse=True
)

ranking_items = filtered_items[:10]


# =========================================================
# 10. 商品カードHTML生成
# =========================================================

cards = []

for rank, item in enumerate(ranking_items, start=1):

    item_name = html.escape(
        str(item.get("itemName", "商品名なし"))
    )

    shop_name = html.escape(
        str(item.get("shopName", ""))
    )

    price = to_int(item.get("itemPrice"))

    review_average = to_float(
        item.get("reviewAverage")
    )

    review_count = to_int(
        item.get("reviewCount")
    )

    image_url = get_image_url(item)

    affiliate_url = (
        item.get("affiliateUrl")
        or item.get("itemUrl")
        or ""
    )

    image_url = html.escape(
        image_url,
        quote=True
    )

    affiliate_url = html.escape(
        affiliate_url,
        quote=True
    )

    score = calculate_score(item)

    image_html = ""

    if image_url:
        image_html = f"""
        <img
            src="{image_url}"
            alt="{item_name}"
            loading="lazy"
        >
        """

    cards.append(
        f"""
        <article class="card">

            <div class="rank">
                {rank}
            </div>

            <div class="image">
                {image_html}
            </div>

            <div class="content">

                <h2>
                    {item_name}
                </h2>

                <p class="shop">
                    {shop_name}
                </p>

                <div class="rating">
                    ★ {review_average:.2f}
                    <span>
                        レビュー {review_count:,}件
                    </span>
                </div>

                <div class="price">
                    {price:,}円
                </div>

                <div class="score">
                    ランキングスコア：
                    {score:.1f}
                </div>

                <a
                    class="button"
                    href="{affiliate_url}"
                    target="_blank"
                    rel="nofollow sponsored noopener"
                >
                    楽天市場で商品を見る
                </a>

            </div>

        </article>
        """
    )


# =========================================================
# 11. 更新日時
# =========================================================

jst = timezone(
    timedelta(hours=9)
)

updated = datetime.now(jst).strftime(
    "%Y年%m月%d日 %H:%M"
)


# =========================================================
# 12. Webページ全体
# =========================================================

page = f"""<!DOCTYPE html>
<html lang="ja">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
イヤホン高評価ランキング | お得商品ランキング
</title>

<meta
    name="description"
    content="楽天市場の商品データをもとに、イヤホンをレビュー評価とレビュー件数から自動比較したランキングです。"
>

<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    background: #f5f6f8;
    color: #222;
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Helvetica Neue",
        Arial,
        sans-serif;
}}

header {{
    background: #ffffff;
    border-bottom: 1px solid #e5e5e5;
    padding: 28px 18px;
}}

.header-inner {{
    max-width: 760px;
    margin: auto;
}}

h1 {{
    margin: 0 0 12px;
    font-size: 28px;
}}

.subtitle {{
    margin: 0;
    color: #666;
    line-height: 1.7;
}}

main {{
    max-width: 760px;
    margin: 24px auto;
    padding: 0 14px;
}}

.notice {{
    background: #ffffff;
    padding: 16px;
    border-radius: 12px;
    margin-bottom: 20px;
    font-size: 14px;
    line-height: 1.7;
}}

.ad-label {{
    display: inline-block;
    font-size: 12px;
    font-weight: bold;
    background: #eeeeee;
    padding: 4px 8px;
    border-radius: 5px;
    margin-bottom: 8px;
}}

.card {{
    position: relative;
    display: flex;
    gap: 16px;
    background: #ffffff;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,.05);
}}

.rank {{
    position: absolute;
    top: -8px;
    left: -6px;
    width: 36px;
    height: 36px;
    background: #222;
    color: white;
    border-radius: 50%;
    display: flex;
    justify-content: center;
    align-items: center;
    font-weight: bold;
}}

.image {{
    width: 128px;
    min-width: 128px;
    min-height: 128px;
    display: flex;
    align-items: center;
    justify-content: center;
}}

.image img {{
    width: 128px;
    height: 128px;
    object-fit: contain;
}}

.content {{
    flex: 1;
}}

.content h2 {{
    margin: 0 0 8px;
    font-size: 16px;
    line-height: 1.5;
}}

.shop {{
    margin: 0 0 8px;
    font-size: 13px;
    color: #777;
}}

.rating {{
    font-weight: bold;
    margin-bottom: 8px;
}}

.rating span {{
    margin-left: 6px;
    font-weight: normal;
    font-size: 13px;
    color: #777;
}}

.price {{
    font-size: 23px;
    font-weight: bold;
    margin-bottom: 6px;
}}

.score {{
    font-size: 12px;
    color: #777;
    margin-bottom: 14px;
}}

.button {{
    display: inline-block;
    background: #bf0000;
    color: #ffffff;
    text-decoration: none;
    border-radius: 8px;
    padding: 12px 18px;
    font-weight: bold;
}}

footer {{
    max-width: 760px;
    margin: 30px auto;
    padding: 20px 16px 50px;
    color: #666;
    font-size: 13px;
    line-height: 1.8;
}}

@media (max-width: 600px) {{

    .card {{
        gap: 12px;
        padding: 16px 12px;
    }}

    .image {{
        width: 96px;
        min-width: 96px;
    }}

    .image img {{
        width: 96px;
        height: 96px;
    }}

    .content h2 {{
        font-size: 14px;
    }}

    .price {{
        font-size: 19px;
    }}

    .button {{
        padding: 10px 12px;
        font-size: 14px;
    }}

}}

</style>

</head>


<body>

<header>

<div class="header-inner">

<h1>
イヤホン 高評価ランキング
</h1>

<p class="subtitle">
楽天市場の商品データをもとに、
レビュー評価とレビュー件数から
自動でランキングを作成しています。
</p>

</div>

</header>


<main>

<div class="notice">

<div class="ad-label">
広告・PR
</div>

<br>

<strong>
最終更新：
</strong>

{updated}

<br>

レビュー10件以上の商品を対象に、
評価とレビュー件数を組み合わせた
独自スコアで順位を決定しています。

</div>


{''.join(cards)}


</main>


<footer>

<p>
当サイトは楽天アフィリエイトを利用しています。
掲載されている価格・在庫・レビュー情報などは
取得時点の情報です。
購入前に楽天市場の商品ページで
最新情報をご確認ください。
</p>

<!-- Rakuten Web Services Attribution Snippet FROM HERE -->
<a href="https://developers.rakuten.com/" target="_blank">Supported by Rakuten Developers</a>
<!-- Rakuten Web Services Attribution Snippet TO HERE -->

</footer>


</body>

</html>
"""


# =========================================================
# 13. public/index.htmlを書き換え
# =========================================================

os.makedirs(
    "public",
    exist_ok=True
)

output_file = "public/index.html"

with open(
    output_file,
    "w",
    encoding="utf-8"
) as f:
    f.write(page)


# =========================================================
# 14. GitHub Actionsのログに結果表示
# =========================================================

print(
    "====================================="
)

print(
    "楽天ランキング生成成功"
)

print(
    f"検索キーワード: {SEARCH_KEYWORD}"
)

print(
    f"取得商品数: {len(items)}"
)

print(
    f"条件通過商品数: {len(filtered_items)}"
)

print(
    f"ランキング掲載数: {len(ranking_items)}"
)

print(
    f"出力先: {output_file}"
)

print(
    "====================================="
)
