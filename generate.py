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

# 楽天市場
# 「ヘッドホン・イヤホン」ジャンル
EARPHONE_GENRE_ID = 502835

MIN_REVIEW_COUNT = 10
RANKING_SIZE = 10
BAYES_PRIOR_WEIGHT = 100


GOOGLE_SITE_VERIFICATION = (
    "xebuT18VaLulU2FGAl1MrnJnOgS4b1ZjrZcFaV45KyQ"
)


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


for name, value in {
    "RAKUTEN_APPLICATION_ID": APPLICATION_ID,
    "RAKUTEN_ACCESS_KEY": ACCESS_KEY,
    "RAKUTEN_AFFILIATE_ID": AFFILIATE_ID,
}.items():

    if not value:

        raise RuntimeError(
            f"{name} が設定されていません。"
        )


# =========================================================
# APIパラメータ
# =========================================================

params = {

    "applicationId":
        APPLICATION_ID,

    "accessKey":
        ACCESS_KEY,

    "affiliateId":
        AFFILIATE_ID,

    "format":
        "json",

    "formatVersion":
        2,

    "keyword":
        SEARCH_KEYWORD,

    # イヤホン系ジャンルに限定
    "genreId":
        EARPHONE_GENRE_ID,

    # 絞り込み検索
    "field":
        1,

    "hits":
        30,

    "imageFlag":
        1,

    "hasReviewFlag":
        1,

    "availability":
        1,

    "sort":
        "-reviewCount",
}


api_url = (
    API_URL
    + "?"
    + urllib.parse.urlencode(
        params
    )
)


# =========================================================
# 楽天API取得
# =========================================================

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True
    )

    page = browser.new_page(
        locale="ja-JP"
    )

    page.set_default_timeout(
        15000
    )


    site_response = page.goto(
        SITE_URL,
        wait_until="domcontentloaded",
        timeout=15000,
    )


    if (
        site_response is None
        or site_response.status >= 400
    ):

        browser.close()

        raise RuntimeError(
            "公開サイトを正常に開けませんでした。"
        )


    result = page.evaluate(
        """
        async (url) => {

            const controller =
                new AbortController();

            const timer =
                setTimeout(
                    () => controller.abort(),
                    12000
                );

            try {

                const response =
                    await fetch(
                        url,
                        {
                            method: "GET",
                            cache: "no-store",
                            credentials: "omit",
                            signal: controller.signal
                        }
                    );

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


# =========================================================
# APIレスポンス検証
# =========================================================

if not result.get(
    "ok"
):

    raise RuntimeError(
        "楽天APIへのアクセスに失敗しました: "
        + str(
            result.get(
                "error",
                "不明なエラー"
            )
        )
    )


if int(
    result.get(
        "status",
        0
    )
) != 200:

    raise RuntimeError(
        f"楽天API HTTP {result.get('status')}\n"
        + result.get(
            "text",
            ""
        )[:1500]
    )


try:

    data = json.loads(
        result["text"]
    )

except json.JSONDecodeError as error:

    raise RuntimeError(
        "楽天APIのJSON解析に失敗しました。"
    ) from error


raw_items = (
    data.get("items")
    or data.get("Items")
    or []
)


if not isinstance(
    raw_items,
    list
):

    raise RuntimeError(
        "楽天APIの商品一覧形式が想定外です。"
    )


# =========================================================
# 商品一覧取り出し
# =========================================================

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


# API自体がおかしい場合は公開しない
if len(
    items
) < RANKING_SIZE:

    raise RuntimeError(
        "楽天APIから取得できた商品が少なすぎます。"
        f"取得件数: {len(items)}"
    )


# =========================================================
# 数値変換
# =========================================================

def to_int(
    value
):

    try:

        return int(
            value or 0
        )

    except (
        TypeError,
        ValueError
    ):

        return 0


def to_float(
    value
):

    try:

        return float(
            value or 0
        )

    except (
        TypeError,
        ValueError
    ):

        return 0.0


# =========================================================
# 画像URL
# =========================================================

def get_image_url(
    item
):

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
# 商品名正規化
# =========================================================

def normalize_text(
    value
):

    return (
        str(
            value or ""
        )
        .lower()
        .replace(
            "　",
            " "
        )
    )


# =========================================================
# イヤホン判定
# =========================================================

EARPHONE_WORDS = (

    "イヤホン",

    "イヤフォン",

    "earphone",

    "earphones",

    "earbud",

    "earbuds",

)


# 明らかに
# 「イヤホン本体ではない」
# 商品だけを除外する。
#
# 「イヤホンジャック」単体は
# 有線イヤホン本体にも使われるため
# 除外しない。

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


def get_rejection_reason(
    item
):

    name = normalize_text(
        item.get(
            "itemName",
            ""
        )
    )


    genre_id = to_int(
        item.get(
            "genreId"
        )
    )


    # -----------------------------
    # ジャンル確認
    # -----------------------------

    if genre_id != EARPHONE_GENRE_ID:

        return (
            f"genreId不一致({genre_id})"
        )


    # -----------------------------
    # 商品名にイヤホン表現があるか
    # -----------------------------

    if not any(
        word in name
        for word in EARPHONE_WORDS
    ):

        return (
            "商品名にイヤホン表現なし"
        )


    # -----------------------------
    # 明らかな非イヤホン商品
    # -----------------------------

    for word in HARD_EXCLUDE_WORDS:

        if word in name:

            return (
                f"除外語句: {word}"
            )


    # -----------------------------
    # レビュー件数
    # -----------------------------

    reviews = to_int(
        item.get(
            "reviewCount"
        )
    )


    if reviews < MIN_REVIEW_COUNT:

        return (
            "レビュー件数不足"
        )


    # -----------------------------
    # レビュー評価
    # -----------------------------

    rating = to_float(
        item.get(
            "reviewAverage"
        )
    )


    if not (
        0 < rating <= 5
    ):

        return (
            "レビュー評価異常"
        )


    # -----------------------------
    # 価格
    # -----------------------------

    price = to_int(
        item.get(
            "itemPrice"
        )
    )


    if price <= 0:

        return (
            "価格異常"
        )


    # -----------------------------
    # アフィリエイトURL
    # -----------------------------

    affiliate_url = str(
        item.get(
            "affiliateUrl"
        )
        or ""
    )


    if (
        not affiliate_url.startswith(
            "https://"
        )
        or
        "hb.afl.rakuten.co.jp"
        not in affiliate_url
    ):

        return (
            "アフィリエイトURL不正"
        )


    return ""


# =========================================================
# ベイズ補正ランキングスコア
# =========================================================

def score(
    item,
    prior_rating,
):

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
        reviews * rating
        +
        BAYES_PRIOR_WEIGHT * prior_rating
    ) / (
        reviews
        +
        BAYES_PRIOR_WEIGHT
    )


# =========================================================
# 商品絞り込み
# =========================================================

filtered = []

excluded_items = []


for item in items:

    reason = get_rejection_reason(
        item
    )


    if reason:

        excluded_items.append(
            {
                "name":
                    str(
                        item.get(
                            "itemName",
                            "商品名なし"
                        )
                    ),

                "reason":
                    reason,
            }
        )

        continue


    filtered.append(
        item
    )


# =========================================================
# fail-safe
#
# 正常なイヤホンが10件揃わなければ
# public/index.htmlを変更しない
# =========================================================

if len(
    filtered
) < RANKING_SIZE:

    print(
        "除外された商品:"
    )


    for excluded in excluded_items[
        :20
    ]:

        print(
            f"- "
            f"{excluded['reason']}"
            f" | "
            f"{excluded['name'][:100]}"
        )


    raise RuntimeError(
        "正常なイヤホン候補が10件未満のため"
        "更新を中止します。"
        f" 候補件数: {len(filtered)}"
    )


# =========================================================
# ベイズ補正用の基準評価
#
# 候補商品の平均レビュー評価を基準にして、
# レビュー件数が少ない商品の高評価を過大評価しにくくする。
# =========================================================

prior_rating = (
    sum(
        to_float(
            item.get(
                "reviewAverage"
            )
        )
        for item in filtered
    )
    / len(filtered)
)


# =========================================================
# ランキング作成
# =========================================================

filtered.sort(
    key=lambda item: score(
        item,
        prior_rating,
    ),
    reverse=True,
)


ranking_items = (
    filtered[
        :RANKING_SIZE
    ]
)


if len(
    ranking_items
) != RANKING_SIZE:

    raise RuntimeError(
        "ランキング10件を生成できなかったため"
        "更新を中止します。"
    )


# =========================================================
# 商品カード生成
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


    image = html.escape(
        get_image_url(
            item
        ),
        quote=True,
    )


    affiliate_url = str(
        item.get(
            "affiliateUrl"
        )
        or ""
    )


    # アフィリエイトリンクを
    # 実際にクリックせず
    # URL形式のみ検証

    if (
        not affiliate_url.startswith(
            "https://"
        )
        or
        "hb.afl.rakuten.co.jp"
        not in affiliate_url
    ):

        raise RuntimeError(
            "アフィリエイトURLが不正です。"
            f"順位{rank}の商品を確認してください。"
        )


    link = html.escape(
        affiliate_url,
        quote=True,
    )


    if image:

        img = (
            f'<img src="{image}" '
            f'alt="{name}" '
            f'loading="lazy">'
        )

    else:

        img = ""


    cards.append(
        f"""
        <article class="card">

            <div class="rank">
                {rank}
            </div>

            <div class="photo">
                {img}
            </div>

            <div class="info">

                <h2>
                    {name}
                </h2>

                <div class="shop">
                    {shop}
                </div>

                <div class="rating">

                    ★ {rating:.2f}

                    <span>
                        ({reviews:,}件)
                    </span>

                </div>

                <div class="price">
                    {price:,}円
                </div>

                <a
                    class="button"
                    href="{link}"
                    target="_blank"
                    rel="nofollow sponsored noopener"
                >
                    楽天市場で見る
                </a>

            </div>

        </article>
        """
    )


# =========================================================
# 更新日時
# =========================================================

updated = datetime.now(
    timezone(
        timedelta(
            hours=9
        )
    )
).strftime(
    "%Y年%m月%d日 %H:%M"
)


# =========================================================
# HTML
# =========================================================

page_template = Template(
"""<!doctype html>

<html lang="ja">

<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<meta
    name="google-site-verification"
    content="$google_verification"
>

<meta
    name="description"
    content="楽天市場のイヤホンを、レビュー評価とレビュー件数をもとに毎日自動比較する高評価ランキングです。"
>

<meta
    name="robots"
    content="index,follow"
>

<link
    rel="canonical"
    href="https://otoku-ranking.pages.dev/"
>

<title>
イヤホン高評価ランキング｜楽天レビューを毎日自動比較
</title>


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
        #ffffff;

    padding:
        24px 16px;

    border-bottom:
        1px solid #dddddd;

}


header div,
main,
footer {

    max-width:
        760px;

    margin:
        auto;

}


h1 {

    margin:
        0 0 8px;

    font-size:
        26px;

}


header p {

    margin:
        0;

    color:
        #666666;

    line-height:
        1.6;

}


main {

    padding:
        18px 12px;

}


.notice {

    background:
        #ffffff;

    padding:
        14px;

    border-radius:
        12px;

    margin-bottom:
        18px;

    line-height:
        1.7;

    font-size:
        14px;

}


.pr {

    display:
        inline-block;

    background:
        #eeeeee;

    border-radius:
        5px;

    padding:
        3px 7px;

    font-size:
        12px;

    font-weight:
        bold;

}


.card {

    position:
        relative;

    display:
        flex;

    gap:
        14px;

    background:
        #ffffff;

    padding:
        16px;

    margin-bottom:
        14px;

    border-radius:
        14px;

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
        -7px;

    left:
        -5px;

    width:
        34px;

    height:
        34px;

    border-radius:
        50%;

    background:
        #222222;

    color:
        #ffffff;

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    font-weight:
        bold;

}


.photo {

    width:
        110px;

    min-width:
        110px;

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

}


.photo img {

    width:
        110px;

    height:
        110px;

    object-fit:
        contain;

}


.info {

    flex:
        1;

}


h2 {

    font-size:
        15px;

    line-height:
        1.5;

    margin:
        0 0 7px;

}


.shop {

    font-size:
        12px;

    color:
        #777777;

    margin-bottom:
        7px;

}


.rating {

    font-weight:
        bold;

    margin-bottom:
        7px;

}


.rating span {

    font-size:
        12px;

    color:
        #777777;

    font-weight:
        normal;

}


.price {

    font-size:
        21px;

    font-weight:
        bold;

    margin-bottom:
        12px;

}


.button {

    display:
        inline-block;

    background:
        #bf0000;

    color:
        #ffffff;

    text-decoration:
        none;

    padding:
        10px 14px;

    border-radius:
        8px;

    font-weight:
        bold;

}


footer {

    padding:
        18px 14px 40px;

    color:
        #666666;

    font-size:
        12px;

    line-height:
        1.7;

}


@media(
    max-width: 520px
) {

    .photo {

        width:
            90px;

        min-width:
            90px;

    }


    .photo img {

        width:
            90px;

        height:
            90px;

    }


    h2 {

        font-size:
            13px;

    }


    .price {

        font-size:
            18px;

    }


    .button {

        font-size:
            13px;

        padding:
            9px 11px;

    }

}


</style>

</head>


<body>


<header>

    <div>

        <h1>
            イヤホン 高評価ランキング
        </h1>

        <p>

            楽天市場の商品データをもとに、
            レビュー評価とレビュー件数から
            毎日自動比較しています。

        </p>

    </div>

</header>


<main>


    <div class="notice">


        <span class="pr">
            広告・PR
        </span>


        <br>


        <strong>
            最終更新：
        </strong>


        $updated


        <br>


        レビュー10件以上の商品を対象に、
        候補商品の平均評価を基準にベイズ補正を行い、
        評価の高さとレビュー件数の信頼度を
        両方反映して順位を決定しています。


    </div>


    $cards


</main>


<footer>


    <p>

        当サイトは
        楽天アフィリエイトを
        利用しています。

        価格・在庫等は
        取得時点の情報です。

        購入前に
        楽天市場の商品ページで
        最新情報をご確認ください。

    </p>


    <a
        href="https://developers.rakuten.com/"
        target="_blank"
        rel="noopener"
    >

        Supported by Rakuten Developers

    </a>


</footer>


</body>


</html>
"""
)


page_html = page_template.substitute(

    google_verification=
        GOOGLE_SITE_VERIFICATION,

    updated=
        updated,

    cards=
        "".join(
            cards
        ),

)


# =========================================================
# 保存
#
# tempファイル
# ↓
# HTML検証
# ↓
# 正常な場合だけindex.htmlへ置換
# =========================================================

os.makedirs(
    "public",
    exist_ok=True
)


temp_path = (
    "public/index.html.tmp"
)

final_path = (
    "public/index.html"
)


with open(
    temp_path,
    "w",
    encoding="utf-8",
) as f:

    f.write(
        page_html
    )


# =========================================================
# HTML最終検証
# =========================================================

if (
    "<html" not in page_html
    or
    "</html>" not in page_html
    or
    page_html.count(
        'class="card"'
    ) != RANKING_SIZE
):

    if os.path.exists(
        temp_path
    ):

        os.remove(
            temp_path
        )


    raise RuntimeError(
        "生成HTMLの検証に失敗したため"
        "更新を中止します。"
    )


# 正常な場合だけ
# index.htmlを置き換える

os.replace(
    temp_path,
    final_path,
)


# =========================================================
# ログ
# =========================================================

print(
    "楽天ランキング生成成功"
)


print(
    f"API取得件数: "
    f"{len(items)}"
)


print(
    f"イヤホン候補件数: "
    f"{len(filtered)}"
)


print(
    f"除外件数: "
    f"{len(excluded_items)}"
)


if excluded_items:

    print(
        "除外商品の確認ログ:"
    )


    for excluded in excluded_items[
        :10
    ]:

        print(
            f"- "
            f"{excluded['reason']}"
            f" | "
            f"{excluded['name'][:100]}"
        )


print(
    f"掲載件数: "
    f"{len(ranking_items)}"
)


print(
    f"ベイズ事前平均: "
    f"{prior_rating:.4f}"
)


print(
    f"ベイズ事前レビュー数: "
    f"{BAYES_PRIOR_WEIGHT}"
)


print(
    "Bayesian ranking: OK"
)


print(
    "Genre validation: OK"
)


print(
    "Google Search Console verification tag: OK"
)


print(
    "Affiliate URL validation: OK"
)


print(
    "Fail-safe HTML validation: OK"
)


print(
    "public/index.html を更新しました。"
)
