import os
import json
import html
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

APPLICATION_ID = os.environ["RAKUTEN_APPLICATION_ID"]
ACCESS_KEY = os.environ["RAKUTEN_ACCESS_KEY"]
AFFILIATE_ID = os.environ["RAKUTEN_AFFILIATE_ID"]

API_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"

params = {
    "applicationId": APPLICATION_ID,
    "affiliateId": AFFILIATE_ID,
    "format": "json",
    "formatVersion": 2,
    "keyword": "イヤホン",
    "hits": 30,
    "imageFlag": 1,
    "hasReviewFlag": 1,
    "sort": "-reviewCount",
}

url = API_URL + "?" + urllib.parse.urlencode(params)

request = urllib.request.Request(
    url,
    headers={
        "accessKey": ACCESS_KEY,
        "User-Agent": "otoku-ranking/1.0",
    },
)

with urllib.request.urlopen(request, timeout=30) as response:
    data = json.loads(response.read().decode("utf-8"))

items = data.get("items", [])

# レビュー件数が少なすぎる商品を除外
items = [
    item for item in items
    if int(item.get("reviewCount", 0) or 0) >= 10
]

# 評価を重視しつつ、同点ならレビュー件数が多い順
items.sort(
    key=lambda x: (
        float(x.get("reviewAverage", 0) or 0),
        int(x.get("reviewCount", 0) or 0),
    ),
    reverse=True,
)

items = items[:10]

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

cards = []

for rank, item in enumerate(items, start=1):
    name = html.escape(str(item.get("itemName", "商品名なし")))
    price = int(item.get("itemPrice", 0) or 0)
    rating = float(item.get("reviewAverage", 0) or 0)
    review_count = int(item.get("reviewCount", 0) or 0)

    affiliate_url = item.get("affiliateUrl") or item.get("itemUrl", "")
    affiliate_url = html.escape(affiliate_url, quote=True)

    image_url = html.escape(get_image_url(item), quote=True)

    image_html = ""
    if image_url:
        image_html = f"""
        <img
            src="{image_url}"
            alt="{name}"
            loading="lazy"
        >
        """

    cards.append(
        f"""
        <article class="card">
            <div class="rank">{rank}</div>

            <div class="image">
                {image_html}
            </div>

            <div class="content">
                <h2>{name}</h2>

                <div class="rating">
                    ★ {rating:.2f}
                    <span>（レビュー {review_count:,}件）</span>
                </div>

                <div class="price">
                    {price:,}円
                </div>

                <a
                    class="button"
                    href="{affiliate_url}"
                    target="_blank"
                    rel="nofollow sponsored noopener"
                >
                    楽天市場で見る
                </a>
            </div>
        </article>
        """
    )

jst = timezone(timedelta(hours=9))
updated = datetime.now(jst).strftime("%Y年%m月%d日 %H:%M")

page = f"""<!DOCTYPE html>
<html lang="ja">

<head>
<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>イヤホン高評価ランキング | お得商品ランキング</title>

<meta
    name="description"
    content="楽天市場の商品データをもとに、イヤホンをレビュー評価とレビュー件数から比較したランキングです。"
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
    background: white;
    border-bottom: 1px solid #e5e5e5;
    padding: 28px 18px;
}}

header div {{
    max-width: 760px;
    margin: auto;
}}

h1 {{
    margin: 0 0 10px;
    font-size: 28px;
}}

.subtitle {{
    margin: 0;
    color: #666;
    line-height: 1.6;
}}

main {{
    max-width: 760px;
    margin: 24px auto;
    padding: 0 14px;
}}

.notice {{
    background: white;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 18px;
    font-size: 14px;
    line-height: 1.7;
    color: #555;
}}

.card {{
    position: relative;
    display: flex;
    gap: 16px;
    background: white;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,.05);
}}

.rank {{
    position: absolute;
    top: -8px;
    left: -6px;
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: #222;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
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
    font-size: 16px;
    line-height: 1.5;
    margin: 0 0 10px;
}}

.rating {{
    font-weight: bold;
    margin-bottom: 8px;
}}

.rating span {{
    font-weight: normal;
    color: #777;
    font-size: 13px;
}}

.price {{
    font-size: 22px;
    font-weight: bold;
    margin-bottom: 14px;
}}

.button {{
    display: inline-block;
    background: #bf0000;
    color: white;
    text-decoration: none;
    border-radius: 8px;
    padding: 11px 18px;
    font-weight: bold;
}}

footer {{
    max-width: 760px;
    margin: 30px auto;
    padding: 20px 16px 50px;
    color: #666;
    font-size: 13px;
    line-height: 1.7;
}}

@media (max-width: 600px) {{

    .card {{
        gap: 12px;
        padding: 16px 12px;
    }}

    .image {{
        width: 100px;
        min-width: 100px;
    }}

    .image img {{
        width: 100px;
        height: 100px;
    }}

    .content h2 {{
        font-size: 14px;
    }}

    .price {{
        font-size: 19px;
    }}

}}

</style>
</head>

<body>

<header>
<div>

<h1>イヤホン 高評価ランキング</h1>

<p class="subtitle">
楽天市場の商品データから、
レビュー評価とレビュー件数をもとに自動更新しています。
</p>

</div>
</header>

<main>

<div class="notice">
<strong>更新日時：</strong>{updated}<br>
レビュー10件以上の商品を対象に、
レビュー評価が高い順で掲載しています。
</div>

{''.join(cards)}

</main>

<footer>

<p>
当サイトは楽天アフィリエイトを利用しています。
掲載価格・在庫等は取得時点の情報です。
購入前に楽天市場の商品ページで最新情報をご確認ください。
</p>

<!-- Rakuten Web Services Attribution Snippet FROM HERE -->
<a href="https://developers.rakuten.com/" target="_blank">Supported by Rakuten Developers</a>
<!-- Rakuten Web Services Attribution Snippet TO HERE -->

</footer>

</body>
</html>
"""

os.makedirs("public", exist_ok=True)

with open(
    "public/index.html",
    "w",
    encoding="utf-8",
) as f:
    f.write(page)

print(f"{len(items)}件の商品で public/index.html を更新しました。")
