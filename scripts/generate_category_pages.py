import html
import json
import os
import re
import statistics
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


SITE_URL = "https://otoku-ranking.pages.dev/"
API_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
EARPHONE_GENRE_ID = 502835
MIN_REVIEW_COUNT = 10
RANKING_SIZE = 10
BAYES_PRIOR_WEIGHT = 100
TEMPLATE_PATH = Path("public/earphones/under-5000/index.html")

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


CATEGORIES = [
    {
        "key": "wireless",
        "keyword": "ワイヤレス イヤホン",
        "path": Path("public/earphones/wireless/index.html"),
        "canonical": "https://otoku-ranking.pages.dev/earphones/wireless/",
        "title": "ワイヤレスイヤホン高評価ランキング｜楽天市場TOP10",
        "description": (
            "楽天市場のワイヤレスイヤホンを、レビュー平均とレビュー件数の"
            "信頼度を補正して毎日比較。高評価TOP10と価格・レビュー統計を掲載します。"
        ),
        "h1": "楽天市場 ワイヤレスイヤホン高評価ランキング",
        "header": (
            "楽天市場の商品データからワイヤレスイヤホンを抽出し、"
            "レビュー評価とレビュー件数をもとに毎日比較しています。"
        ),
        "notice": (
            "商品名からワイヤレス・完全ワイヤレス・Bluetooth対応と確認できる"
            "イヤホンを対象に、ベイズ補正後の評価が高い順で掲載しています。"
        ),
        "explanation_title": "ワイヤレスイヤホンの抽出条件",
        "explanation": (
            "楽天市場の商品検索APIで「ワイヤレス イヤホン」を検索し、"
            "イヤホン本体と判断できる商品だけを残します。商品名にワイヤレス、"
            "完全ワイヤレス、Bluetooth、ブルートゥースのいずれかが確認できることを"
            "追加条件とし、ケース単体や変換アダプターなどは除外します。"
        ),
    },
    {
        "key": "wired",
        "keyword": "有線 イヤホン",
        "path": Path("public/earphones/wired/index.html"),
        "canonical": "https://otoku-ranking.pages.dev/earphones/wired/",
        "title": "有線イヤホン高評価ランキング｜楽天市場TOP10",
        "description": (
            "楽天市場の有線イヤホンを、レビュー平均とレビュー件数の信頼度を"
            "補正して毎日比較。高評価TOP10と価格・レビュー統計を掲載します。"
        ),
        "h1": "楽天市場 有線イヤホン高評価ランキング",
        "header": (
            "楽天市場の商品データから有線イヤホンを抽出し、"
            "レビュー評価とレビュー件数をもとに毎日比較しています。"
        ),
        "notice": (
            "商品名から有線イヤホンと確認できる商品を対象に、"
            "ベイズ補正後の評価が高い順で掲載しています。"
        ),
        "explanation_title": "有線イヤホンの抽出条件",
        "explanation": (
            "楽天市場の商品検索APIで「有線 イヤホン」を検索し、商品名に「有線」が"
            "明記されたイヤホン本体を対象にします。ワイヤレス・Bluetoothを主用途と"
            "する商品や、ケース・変換アダプターなどの周辺機器は除外します。"
        ),
    },
    {
        "key": "earcuff",
        "keyword": "イヤーカフ イヤホン",
        "path": Path("public/earphones/earcuff/index.html"),
        "canonical": "https://otoku-ranking.pages.dev/earphones/earcuff/",
        "title": "イヤーカフ型イヤホン高評価ランキング｜楽天市場TOP10",
        "description": (
            "楽天市場のイヤーカフ型イヤホンを、レビュー平均とレビュー件数の"
            "信頼度を補正して毎日比較。高評価TOP10と価格・レビュー統計を掲載します。"
        ),
        "h1": "楽天市場 イヤーカフ型イヤホン高評価ランキング",
        "header": (
            "楽天市場の商品データからイヤーカフ型イヤホンを抽出し、"
            "レビュー評価とレビュー件数をもとに毎日比較しています。"
        ),
        "notice": (
            "商品名からイヤーカフ・耳挟み・クリップ式と確認できるイヤホンを対象に、"
            "ベイズ補正後の評価が高い順で掲載しています。"
        ),
        "explanation_title": "イヤーカフ型イヤホンの抽出条件",
        "explanation": (
            "楽天市場の商品検索APIで「イヤーカフ イヤホン」を検索し、商品名に"
            "イヤーカフ、耳挟み、耳はさみ、クリップ式などの表現が確認できる"
            "イヤホン本体を対象にします。交換部品やケースなどは除外します。"
        ),
    },
]


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
    "交換用イヤーピース",
    "イヤーピースのみ",
)


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


def normalize_text(value):
    return str(value or "").lower().replace("　", " ")


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


def category_matches(name, category_key):
    if category_key == "wireless":
        return any(
            word in name
            for word in ("ワイヤレス", "bluetooth", "ブルートゥース")
        )

    if category_key == "wired":
        if "有線" not in name:
            return False
        return not any(
            word in name
            for word in ("ワイヤレス", "bluetooth", "ブルートゥース")
        )

    if category_key == "earcuff":
        return any(
            word in name
            for word in ("イヤーカフ", "耳挟み", "耳はさみ", "耳ばさみ", "クリップ式")
        )

    raise RuntimeError(f"未知のカテゴリです: {category_key}")


def rejection_reason(item, category):
    name = normalize_text(item.get("itemName", ""))

    if to_int(item.get("genreId")) != EARPHONE_GENRE_ID:
        return "genreId不一致"

    if not any(word in name for word in EARPHONE_WORDS):
        return "商品名にイヤホン表現なし"

    for word in HARD_EXCLUDE_WORDS:
        if word in name:
            return f"除外語句: {word}"

    if not category_matches(name, category["key"]):
        return "カテゴリ条件不一致"

    reviews = to_int(item.get("reviewCount"))
    if reviews < MIN_REVIEW_COUNT:
        return "レビュー件数不足"

    rating = to_float(item.get("reviewAverage"))
    if not 0 < rating <= 5:
        return "レビュー評価異常"

    if to_int(item.get("itemPrice")) <= 0:
        return "価格異常"

    affiliate_url = str(item.get("affiliateUrl") or "")
    if (
        not affiliate_url.startswith("https://")
        or "hb.afl.rakuten.co.jp" not in affiliate_url
    ):
        return "アフィリエイトURL不正"

    return ""


def normalize_items(data):
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
    return items


def build_api_url(category):
    params = {
        "applicationId": APPLICATION_ID,
        "accessKey": ACCESS_KEY,
        "affiliateId": AFFILIATE_ID,
        "format": "json",
        "formatVersion": 2,
        "keyword": category["keyword"],
        "genreId": EARPHONE_GENRE_ID,
        "field": 1,
        "hits": 30,
        "imageFlag": 1,
        "hasReviewFlag": 1,
        "availability": 1,
        "sort": "-reviewCount",
    }
    return API_URL + "?" + urllib.parse.urlencode(params)


def fetch_api(page, category):
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
        build_api_url(category),
    )

    if not result.get("ok"):
        raise RuntimeError(
            f"{category['key']} の楽天API取得に失敗しました: "
            + str(result.get("error", "不明なエラー"))
        )

    if int(result.get("status", 0)) != 200:
        raise RuntimeError(
            f"楽天API HTTP {result.get('status')} ({category['key']})\n"
            + result.get("text", "")[:1500]
        )

    try:
        return normalize_items(json.loads(result["text"]))
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"楽天APIのJSON解析に失敗しました: {category['key']}"
        ) from error


def rank_items(items, category):
    filtered = []
    excluded = []

    for item in items:
        reason = rejection_reason(item, category)
        if reason:
            excluded.append((reason, str(item.get("itemName", "商品名なし"))))
            continue
        filtered.append(item)

    if len(filtered) < RANKING_SIZE:
        for reason, name in excluded[:20]:
            print(f"- {category['key']} | {reason} | {name[:100]}")
        raise RuntimeError(
            f"{category['key']} の正常な候補が10件未満です。"
            f" 候補件数: {len(filtered)}"
        )

    prior_rating = statistics.mean(
        to_float(item.get("reviewAverage")) for item in filtered
    )

    def score(item):
        rating = to_float(item.get("reviewAverage"))
        reviews = to_int(item.get("reviewCount"))
        return (
            reviews * rating + BAYES_PRIOR_WEIGHT * prior_rating
        ) / (reviews + BAYES_PRIOR_WEIGHT)

    ranking = sorted(filtered, key=score, reverse=True)[:RANKING_SIZE]
    return ranking, filtered, prior_rating


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


def build_stats(ranking_items, candidate_count):
    prices = [to_int(item.get("itemPrice")) for item in ranking_items]
    ratings = [to_float(item.get("reviewAverage")) for item in ranking_items]
    reviews = [to_int(item.get("reviewCount")) for item in ranking_items]

    return {
        "candidate_count": candidate_count,
        "average_price": round(statistics.mean(prices)),
        "median_price": round(statistics.median(prices)),
        "average_rating": statistics.mean(ratings),
        "median_reviews": round(statistics.median(reviews)),
        "max_reviews": max(reviews),
    }


def build_stats_html(category, stats):
    return f'''<section class="category-data-section" aria-label="ランキングデータ概要">
    <div class="category-data-head">
        <span class="section-kicker">独自集計</span>
        <h2>今回の{html.escape(category['h1'].replace('楽天市場 ', ''))}データ</h2>
        <p>楽天APIから最大30件を取得して条件判定し、TOP10の数値を集計しています。</p>
    </div>
    <div class="category-stats-grid">
        <div><span>有効候補</span><strong>{stats['candidate_count']}件</strong></div>
        <div><span>TOP10平均価格</span><strong>{stats['average_price']:,}円</strong></div>
        <div><span>TOP10価格中央値</span><strong>{stats['median_price']:,}円</strong></div>
        <div><span>TOP10平均評価</span><strong>★ {stats['average_rating']:.2f}</strong></div>
        <div><span>レビュー中央値</span><strong>{stats['median_reviews']:,}件</strong></div>
        <div><span>レビュー最多</span><strong>{stats['max_reviews']:,}件</strong></div>
    </div>
</section>'''


def replace_once(text, pattern, replacement, label):
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


def build_page(template, category, ranking_items, candidate_count, updated):
    text = template

    text = replace_once(
        text,
        r"<title>.*?</title>",
        f"<title>{category['title']}</title>",
        f"title {category['key']}",
    )
    text = replace_once(
        text,
        r'<meta name="description" content="[^"]*">',
        f'<meta name="description" content="{category["description"]}">',
        f"description {category['key']}",
    )
    text = replace_once(
        text,
        r'<link rel="canonical" href="[^"]+">',
        f'<link rel="canonical" href="{category["canonical"]}">',
        f"canonical {category['key']}",
    )
    text = replace_once(
        text,
        r"<h1>.*?</h1>",
        f"<h1>{category['h1']}</h1>",
        f"h1 {category['key']}",
    )
    text = replace_once(
        text,
        r'(<header>\s*<div>\s*<h1>.*?</h1>\s*)<p>.*?</p>',
        rf'\1<p>{category["header"]}</p>',
        f"header {category['key']}",
    )

    notice_html = f'''<div class="notice">
        <span class="pr">広告・PR</span><br>
        <strong>最終更新：</strong> {updated}<br>
        {category['notice']}
    </div>'''
    text = replace_once(
        text,
        r'<div class="notice">.*?</div>',
        notice_html,
        f"notice {category['key']}",
    )

    card_matches = list(
        re.finditer(r'<article class="card">.*?</article>', text, re.DOTALL)
    )
    if len(card_matches) != RANKING_SIZE:
        raise RuntimeError(
            f"テンプレートの商品カードが10件ではありません: {category['key']}"
        )

    text = (
        text[: card_matches[0].start()]
        + build_cards(ranking_items)
        + text[card_matches[-1].end() :]
    )

    stats_html = build_stats_html(
        category,
        build_stats(ranking_items, candidate_count),
    )
    text = text.replace(notice_html, notice_html + "\n" + stats_html, 1)

    explanation_html = f'''<section class="category-explanation-section">
    <h2>{html.escape(category['explanation_title'])}</h2>
    <p>{html.escape(category['explanation'])}</p>
    <p>順位はレビュー10件以上の商品を対象に、候補商品の平均評価を事前平均としてベイズ補正し、レビュー評価の高さとレビュー件数の信頼度を両方反映して決定します。</p>
</section>'''
    text = replace_once(
        text,
        r"</main>",
        explanation_html + "\n</main>",
        f"explanation {category['key']}",
    )

    if text.count('class="card"') != RANKING_SIZE:
        raise RuntimeError(f"生成後カード数が不正です: {category['key']}")
    if text.count("hb.afl.rakuten.co.jp") < RANKING_SIZE:
        raise RuntimeError(f"アフィリエイトURL検証に失敗しました: {category['key']}")
    if 'class="category-data-section"' not in text:
        raise RuntimeError(f"独自統計セクションがありません: {category['key']}")

    return text


def write_atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".html.tmp")
    temp_path.write_text(content, encoding="utf-8")
    os.replace(temp_path, path)


if not TEMPLATE_PATH.exists():
    raise RuntimeError("カテゴリページ生成用テンプレートが見つかりません。")

template = TEMPLATE_PATH.read_text(encoding="utf-8")
updated = datetime.now(
    timezone(timedelta(hours=9))
).strftime("%Y年%m月%d日 %H:%M")

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

    results = []
    for category in CATEGORIES:
        items = fetch_api(page, category)
        ranking, filtered, prior_rating = rank_items(items, category)
        page_html = build_page(
            template,
            category,
            ranking,
            len(filtered),
            updated,
        )
        results.append(
            (category, page_html, len(items), len(filtered), prior_rating)
        )

    browser.close()

# 3カテゴリすべての取得・検証が成功してから一括置換する。
for category, page_html, _, _, _ in results:
    write_atomic(category["path"], page_html)

for category, _, api_count, candidate_count, prior_rating in results:
    print(f"{category['key']} category ranking: OK")
    print(f"  API取得件数: {api_count}")
    print(f"  有効候補件数: {candidate_count}")
    print(f"  掲載件数: {RANKING_SIZE}")
    print(f"  ベイズ事前平均: {prior_rating:.4f}")

print("Wireless / wired / earcuff category pages generated: OK")
