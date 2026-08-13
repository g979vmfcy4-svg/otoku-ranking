import os
import json
import html
import math
import urllib.parse
from datetime import datetime, timezone, timedelta

from playwright.sync_api import sync_playwright, Error as PlaywrightError


SITE_URL = "https://otoku-ranking.pages.dev/"
API_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
SEARCH_KEYWORD = "イヤホン"


APPLICATION_ID = os.getenv(
    "RAKUTEN_APPLICATION_ID",
    ""
).strip()

ACCESS_KEY = os.getenv(
    "RAKUTEN_ACCESS_KEY",
    ""
).strip()

AFFILIATE_ID = os.getenv(
    "RAKUTEN_AFFILIATE_ID",
    ""
).strip()


required = {
    "RAKUTEN_APPLICATION_ID": APPLICATION_ID,
    "RAKUTEN_ACCESS_KEY": ACCESS_KEY,
    "RAKUTEN_AFFILIATE_ID": AFFILIATE_ID,
}

missing = [
    name
    for name, value in required.items()
    if not value
]

if missing:
    raise RuntimeError(
        "GitHub Secrets が不足しています: "
        + ", ".join(missing)
    )


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


api_url = (
    API_URL
    + "?"
    + urllib.parse.urlencode(params)
)


# =========================================================
# 楽天APIへアクセス
# =========================================================

try:

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            locale="ja-JP"
        )

        page = context.new_page()


        # まず許可されたサイトを開く
        site_response = page.goto(
            SITE_URL,
            wait_until="domcontentloaded",
            timeout=30000,
        )


        if site_response is None:

            raise RuntimeError(
                "公開サイトを開けませんでした。"
            )


        if site_response.status >= 400:

            raise RuntimeError(
                "公開サイトのHTTPステータスが異常です: "
                f"{site_response.status}"
            )


        # -------------------------------------------------
        # 実際に楽天APIへ送られるOrigin / Refererをログ表示
        # -------------------------------------------------

        def log_api_request(request):

            if request.url.startswith(
                API_URL
            ):

                headers = request.all_headers()

                print(
                    "API request Origin:",
                    headers.get(
                        "origin",
                        "(none)"
                    )
                )

                print(
                    "API request Referer:",
                    headers.get(
                        "referer",
                        "(none)"
                    )
                )


        page.on(
            "request",
            log_api_request
        )


        # -------------------------------------------------
        # ページ内JavaScriptのfetch()から楽天APIを呼ぶ
        # -------------------------------------------------

        with page.expect_response(
            lambda response:
                response.url.startswith(
                    API_URL
                ),
            timeout=30000,
        ) as response_info:

            page.evaluate(
                """
                url => {

                    fetch(
                        url,
                        {
                            method: "GET",
                            credentials: "omit",
                            cache: "no-store"
                        }
                    ).catch(
                        () => {}
                    );

                }
                """,
                api_url,
            )


        api_response = (
            response_info.value
        )

        status = (
            api_response.status
        )

        response_text = (
            api_response.text()
        )


        browser.close()


except PlaywrightError as e:

    raise RuntimeError(
        "Chromiumでのアクセス中に"
        "エラーが発生しました。\n"
        f"{e}"
    )


# =========================================================
# HTTPエラー
# =========================================================

if status != 200:

    raise RuntimeError(
        "楽天APIでHTTPエラーが発生しました。\n"
        f"HTTP Status: {status}\n"
        f"Response: {response_text[:2000]}"
    )


# =========================================================
# JSON解析
# =========================================================

try:

    data = json.loads(
        response_text
    )

except json.JSONDecodeError as e:

    raise RuntimeError(
        "楽天APIのJSON解析に失敗しました。\n"
        f"{e}"
    )


raw_items = (
    data.get("items")
    or data.get("Items")
    or []
)


items = []


for entry in raw_items:

    if not isinstance(
        entry,
        dict
    ):
        continue


    if isinstance(
        entry.get("Item"),
        dict
    ):

        items.append(
            entry["Item"]
        )


    elif isinstance(
        entry.get("item"),
        dict
    ):

        items.append(
            entry["item"]
        )


    else:

        items.append(
            entry
        )


if not items:

    raise RuntimeError(
        "楽天APIから商品が1件も"
        "取得できませんでした。"
    )


# =========================================================
# 型変換
# =========================================================

def to_int(value):

    try:

        return int(
            value or 0
        )

    except (
        ValueError,
        TypeError
    ):

        return 0


def to_float(value):

    try:

        return float(
            value or 0
        )

    except (
        ValueError,
        TypeError
    ):

        return 0.0


# =========================================================
# 画像URL
# =========================================================

def get_image_url(item):

    images = item.get(
        "mediumImageUrls",
        []
    )


    if not images:

        return ""


    first = images[0]


    if isinstance(
        first,
        str
    ):

        return first


    if isinstance(
        first,
        dict
    ):

        return first.get(
            "imageUrl",
            ""
        )


    return ""


# =========================================================
# スコア
# =========================================================

def calculate_score(item):

    rating = to_float(
        item.get(
            "reviewAverage"
        )
    )

    reviews = to_int(
        item.get(
            "reviewCount"
        )
    )


    return (
        rating * 20
        +
        math.log10(
            reviews + 1
        ) * 8
    )


# =========================================================
# 商品絞り込み
# =========================================================

filtered = []


for item in items:

    review_count = to_int(
        item.get(
            "reviewCount"
        )
    )

    review_average = to_float(
        item.get(
            "reviewAverage"
        )
    )

    price = to_int(
        item.get(
            "itemPrice"
        )
    )


    if review_count < 10:

        continue


    if review_average <= 0:

        continue


    if price <= 0:

        continue


    filtered.append(
        item
    )


if not filtered:

    raise RuntimeError(
        "ランキング条件を満たす"
        "商品がありませんでした。"
    )


filtered.sort(
    key=calculate_score,
    reverse=True,
)


ranking_items = (
    filtered[:10]
)


# =========================================================
# 商品HTML
# =========================================================

cards = []


for rank, item in enumerate(
    ranking_items,
    1
):


    name = html.escape(
        str(
            item.get(
                "itemName",
                "商品名なし"
            )
        )
    )


    shop = html.escape(
        str(
            item.get(
                "shopName",
                ""
            )
        )
    )


    price = to_int(
        item.get(
            "itemPrice"
        )
    )


    rating = to_float(
        item.get(
            "reviewAverage"
        )
    )


    reviews = to_int(
        item.get(
            "reviewCount"
        )
    )


    score = calculate_score(
        item
    )


    image = html.escape(
        get_image_url(
            item
        ),
        quote=True,
    )


    link = (
        item.get(
            "affiliateUrl"
        )
        or
        item.get(
            "itemUrl"
        )
        or
        ""
    )


    link = html.escape(
        link,
        quote=True,
    )


    if image:

        image_html = (
            f'<img src="{image}" '
            f'alt="{name}" '
            f'loading="lazy">'
        )

    else:

        image_html = ""


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
      {name}
    </h2>

    <p class="shop">
      {shop}
    </p>

    <p class="rating">

      ★ {rating:.2f}

      <span>
        レビュー {reviews:,}件
      </span>

    </p>

    <p class="price">
      {price:,}円
    </p>

    <p class="score">
      ランキングスコア：
      {score:.1f}
    </p>

    <a
      class="button"
      href="{link}"
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
# 更新日時
# =========================================================

jst = timezone(
    timedelta(
        hours=9
    )
)


updated = datetime.now(
    jst
).strftime(
    "%Y年%m月%d日 %H:%M"
)


# =========================================================
# ページHTML
# =========================================================

page_html = """<!DOCTYPE html>

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
  content="楽天市場の商品データをもとにイヤホンを比較したランキングです。"
>

<style>

* {
  box-sizing: border-box;
}

body {

  margin: 0;

  background:
    #f5f6f8;

  color:
    #222;

  font-family:
    -apple-system,
    BlinkMacSystemFont,
    "Helvetica Neue",
    Arial,
    sans-serif;

}

header {

  background:
    #fff;

  border-bottom:
    1px solid #e5e5e5;

  padding:
    28px 18px;

}

.header-inner,
main,
footer {

  max-width:
    760px;

  margin-left:
    auto;

  margin-right:
    auto;

}

h1 {

  margin:
    0 0 12px;

  font-size:
    28px;

}

.subtitle {

  margin:
    0;

  color:
    #666;

  line-height:
    1.7;

}

main {

  margin-top:
    24px;

  padding:
    0 14px;

}

.notice {

  background:
    #fff;

  padding:
    16px;

  border-radius:
    12px;

  margin-bottom:
    20px;

  font-size:
    14px;

  line-height:
    1.7;

}

.ad-label {

  display:
    inline-block;

  font-size:
    12px;

  font-weight:
    bold;

  background:
    #eee;

  padding:
    4px 8px;

  border-radius:
    5px;

  margin-bottom:
    8px;

}

.card {

  position:
    relative;

  display:
    flex;

  gap:
    16px;

  background:
    #fff;

  border-radius:
    14px;

  padding:
    18px;

  margin-bottom:
    16px;

  box-shadow:
    0 2px 8px
    rgba(
      0,
      0,
      0,
      .05
    );

}

.rank {

  position:
    absolute;

  top:
    -8px;

  left:
    -6px;

  width:
    36px;

  height:
    36px;

  background:
    #222;

  color:
    #fff;

  border-radius:
    50%;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

  font-weight:
    bold;

}

.image {

  width:
    128px;

  min-width:
    128px;

  min-height:
    128px;

  display:
    flex;

  align-items:
    center;

  justify-content:
    center;

}

.image img {

  width:
    128px;

  height:
    128px;

  object-fit:
    contain;

}

.content {

  flex:
    1;

}

.content h2 {

  margin:
    0 0 8px;

  font-size:
    16px;

  line-height:
    1.5;

}

.shop {

  margin:
    0 0 8px;

  font-size:
    13px;

  color:
    #777;

}

.rating {

  font-weight:
    bold;

  margin:
    0 0 8px;

}

.rating span {

  font-weight:
    normal;

  font-size:
    13px;

  color:
    #777;

}

.price {

  font-size:
    23px;

  font-weight:
    bold;

  margin:
    0 0 6px;

}

.score {

  font-size:
    12px;

  color:
    #777;

  margin:
    0 0 14px;

}

.button {

  display:
    inline-block;

  background:
    #bf0000;

  color:
    #fff;

  text-decoration:
    none;

  border-radius:
    8px;

  padding:
    12px 18px;

  font-weight:
    bold;

}

footer {

  padding:
    20px 16px 50px;

  color:
    #666;

  font-size:
    13px;

  line-height:
    1.8;

}


@media (
  max-width: 600px
) {

  .card {

    gap:
      12px;

    padding:
      16px 12px;

  }

  .image {

    width:
      96px;

    min-width:
      96px;

  }

  .image img {

    width:
      96px;

    height:
      96px;

  }

  .content h2 {

    font-size:
      14px;

  }

  .price {

    font-size:
      19px;

  }

  .button {

    padding:
      10px 12px;

    font-size:
      14px;

  }

}

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

    __UPDATED__

    <br>

    レビュー10件以上の商品を対象に、
    評価とレビュー件数を組み合わせた
    独自スコアで順位を決定しています。

  </div>

  __CARDS__

</main>


<footer>

  <p>

    当サイトは楽天アフィリエイトを
    利用しています。

    掲載価格・販売状況は
    取得時点の情報であり、
    変更される場合があります。

    購入時は楽天市場の商品ページに
    表示される最新情報を
    ご確認ください。

  </p>


  <a
    href="https://developers.rakuten.com/"
    target="_blank"
  >

    Supported by Rakuten Developers

  </a>

</footer>


</body>

</html>
"""


page_html = (
    page_html
    .replace(
        "__UPDATED__",
        updated
    )
    .replace(
        "__CARDS__",
        "".join(
            cards
        )
    )
)


# =========================================================
# ファイル保存
# =========================================================

os.makedirs(
    "public",
    exist_ok=True
)


with open(
    "public/index.html",
    "w",
    encoding="utf-8"
) as f:

    f.write(
        page_html
    )


# =========================================================
# ログ
# =========================================================

print(
    "====================================="
)

print(
    "楽天ランキング生成成功"
)

print(
    "API request mode: "
    "fetch from allowed site"
)

print(
    f"検索キーワード: "
    f"{SEARCH_KEYWORD}"
)

print(
    f"取得商品数: "
    f"{len(items)}"
)

print(
    f"条件通過商品数: "
    f"{len(filtered)}"
)

print(
    f"ランキング掲載数: "
    f"{len(ranking_items)}"
)

print(
    "出力先: "
    "public/index.html"
)

print(
    "====================================="
)
