from pathlib import Path
import html
import json
import os
import re
import time
import urllib.parse

from playwright.sync_api import sync_playwright


SITE_URL = "https://otoku-ranking.pages.dev/"
API_URL = "https://openapi.rakuten.co.jp/ichibaranking/api/IchibaItem/Ranking/20220601"
EARPHONE_GENRE_ID = 502835
TOP_PATH = Path("public/index.html")
METHODOLOGY_PATH = Path("public/earphones/methodology/index.html")
STYLESHEET = '<link rel="stylesheet" href="/assets/sales-comparison.css">'
SECTION_RE = re.compile(
    r'\s*<!-- sales-compare:start -->.*?<!-- sales-compare:end -->\s*',
    re.DOTALL,
)
METHOD_RE = re.compile(
    r'\s*<!-- sales-method:start -->.*?<!-- sales-method:end -->\s*',
    re.DOTALL,
)
CARD_RE = re.compile(r'<article class="card">(?P<body>.*?)</article>', re.DOTALL)
SUMMARY_RE = re.compile(
    r'<section class="quality-section ranking-data-summary"[^>]*>.*?</section>',
    re.DOTALL,
)

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


def compact_name(value, limit=52):
    value = " ".join(str(value or "").split())
    previous = None
    while value != previous:
        previous = value
        value = re.sub(r'^＼[^／]{0,120}／\s*', "", value)
        value = re.sub(
            r'^【[^】]{0,120}(?:OFF|クーポン|ポイント|楽天|ランキング|限定|セール)[^】]*】\s*',
            "",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(
            r'^(?:楽天ランキング\d*位|楽天\d*位)[\s・:：-]*',
            "",
            value,
            flags=re.IGNORECASE,
        )
    value = value.strip(" ・|｜-＼／")
    if len(value) > limit:
        value = value[: limit - 1].rstrip() + "…"
    return value or "商品名なし"


def is_earphone_item(item):
    name = str(item.get("itemName") or "").lower().replace("　", " ")
    earphone_terms = (
        "イヤホン",
        "イヤフォン",
        "earphone",
        "earphones",
        "earbud",
        "earbuds",
        "airpods",
        "freebuds",
        "galaxy buds",
        "pixel buds",
    )
    headphone_terms = (
        "ヘッドホン",
        "ヘッドフォン",
        "headphone",
        "headphones",
    )
    if any(term in name for term in earphone_terms):
        return True
    if any(term in name for term in headphone_terms):
        return False
    return False


def item_code_from_affiliate(href):
    try:
        parsed = urllib.parse.urlparse(html.unescape(href))
        query = urllib.parse.parse_qs(parsed.query)
        pc_url = (query.get("pc") or [""])[0]
        item = urllib.parse.urlparse(pc_url)
        parts = [part for part in item.path.split("/") if part]
        if item.netloc == "item.rakuten.co.jp" and len(parts) >= 2:
            return f"{parts[0]}:{parts[1]}"
    except (TypeError, ValueError):
        return ""
    return ""


def current_high_rating_ranks(text):
    result = {}
    for match in CARD_RE.finditer(text):
        body = match.group("body")
        rank_match = re.search(r'<div class="rank">\s*(\d+)\s*</div>', body)
        link_match = re.search(r'class="button"\s+href="([^"]+)"', body, re.DOTALL)
        if not rank_match or not link_match:
            continue
        rank = int(rank_match.group(1))
        if not 1 <= rank <= 10:
            continue
        code = item_code_from_affiliate(link_match.group(1))
        if code:
            result[code] = rank
    if len(result) < 8:
        raise RuntimeError(f"高評価TOP10の商品コード取得が不足しています: {len(result)}")
    return result


def normalize_items(data):
    raw_items = data.get("items") or data.get("Items") or []
    if not isinstance(raw_items, list):
        raise RuntimeError("楽天ランキングAPIの商品一覧形式が想定外です。")
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


def build_api_url():
    params = {
        "applicationId": APPLICATION_ID,
        "accessKey": ACCESS_KEY,
        "affiliateId": AFFILIATE_ID,
        "format": "json",
        "formatVersion": 2,
        "genreId": EARPHONE_GENRE_ID,
        "period": "realtime",
        "page": 1,
    }
    return API_URL + "?" + urllib.parse.urlencode(params)


def fetch_ranking(page):
    url = build_api_url()
    last_error = ""
    for attempt in range(1, 4):
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
            url,
        )
        if result.get("ok") and int(result.get("status", 0)) == 200:
            try:
                data = json.loads(result["text"])
                return data, normalize_items(data)
            except json.JSONDecodeError as error:
                raise RuntimeError("楽天ランキングAPIのJSON解析に失敗しました。") from error

        last_error = (
            f"attempt={attempt} status={result.get('status')} "
            f"error={result.get('error', '')} body={result.get('text', '')[:500]}"
        )
        if attempt < 3:
            time.sleep(attempt * 5)

    raise RuntimeError("楽天ランキングAPI取得に失敗しました: " + last_error)


def build_section(data, items, own_ranks):
    ranked = sorted(
        [item for item in items if to_int(item.get("rank")) > 0],
        key=lambda item: to_int(item.get("rank")),
    )
    earphone_items = [item for item in ranked if is_earphone_item(item)]
    top10 = earphone_items[:10]
    if len(top10) < 10:
        raise RuntimeError(
            f"楽天売れ筋からイヤホン該当商品を10件抽出できません: {len(top10)}"
        )

    overlaps = 0
    low_review_count = 0
    rows = []
    for item in top10:
        sales_rank = to_int(item.get("rank"))
        item_code = str(item.get("itemCode") or "")
        reviews = to_int(item.get("reviewCount"))
        own_rank = own_ranks.get(item_code)
        if own_rank:
            overlaps += 1
            own_label = f'<strong class="compare-hit">{own_rank}位</strong>'
        elif reviews < 10:
            low_review_count += 1
            own_label = '<span class="compare-out">対象外（10件未満）</span>'
        else:
            own_label = '<span class="compare-out">TOP10圏外</span>'

        name = html.escape(compact_name(item.get("itemName", "")))
        full_name = html.escape(str(item.get("itemName", "")), quote=True)
        rating = to_float(item.get("reviewAverage"))
        price = to_int(item.get("itemPrice"))
        affiliate_url = str(item.get("affiliateUrl") or "")
        if affiliate_url.startswith("https://") and "hb.afl.rakuten.co.jp" in affiliate_url:
            product = (
                f'<a href="{html.escape(affiliate_url, quote=True)}" target="_blank" '
                f'rel="nofollow sponsored noopener" title="{full_name}">{name}</a>'
            )
        else:
            product = f'<span title="{full_name}">{name}</span>'

        rows.append(
            '<div class="compare-row" role="row">'
            f'<div role="cell" data-label="楽天ジャンル順位"><strong>{sales_rank}位</strong></div>'
            f'<div role="cell" data-label="商品">{product}<small>{price:,}円</small></div>'
            f'<div role="cell" data-label="レビュー">★ {rating:.2f}<small>{reviews:,}件</small></div>'
            f'<div role="cell" data-label="高評価順位">{own_label}</div>'
            '</div>'
        )

    updated = html.escape(str(data.get("lastBuildDate") or "取得時点のリアルタイム順位"))
    return f'''<!-- sales-compare:start -->
<section class="sales-compare-section" aria-label="楽天売れ筋と高評価ランキングの比較">
  <div class="sales-compare-head">
    <span class="section-kicker">もう1つの見方</span>
    <h2>楽天売れ筋と高評価TOP10を比較</h2>
    <p>「よく売れている商品」と「レビュー件数を考慮して評価が安定している商品」は同じとは限りません。今回、両方のTOP10に入った商品は<strong>{overlaps}商品</strong>でした。</p>
  </div>
  <div class="sales-compare-glance" aria-label="比較結果の概要">
    <div><span>比較した売れ筋</span><strong>10商品</strong></div>
    <div><span>両方TOP10</span><strong>{overlaps}商品</strong></div>
    <div><span>レビュー10件未満</span><strong>{low_review_count}商品</strong></div>
  </div>
  <details class="sales-compare-details">
    <summary>売れ筋10商品の比較表を見る</summary>
    <div class="compare-table" role="table" aria-label="楽天ジャンル順位と高評価順位の比較">
      <div class="compare-header" role="row">
        <div role="columnheader">楽天ジャンル順位</div><div role="columnheader">商品</div><div role="columnheader">レビュー</div><div role="columnheader">高評価順位</div>
      </div>
      {''.join(rows)}
    </div>
    <p class="compare-note">楽天側は「ヘッドホン・イヤホン」ジャンルのランキングAPIによるリアルタイム順位（{updated}）から、商品名でイヤホンと確認できる商品を抽出しています。元の楽天ジャンル順位は変更していません。当サイト高評価はレビュー10件以上を対象にレビュー件数を考慮して補正した総合TOP10です。音質・装着感などの実機評価ではありません。</p>
  </details>
</section>
<!-- sales-compare:end -->'''


def insert_section(text, section):
    text = SECTION_RE.sub("\n", text)
    if STYLESHEET not in text:
        text = text.replace("</head>", STYLESHEET + "\n</head>", 1)

    summary_match = SUMMARY_RE.search(text)
    if summary_match:
        insert_at = summary_match.end()
        text = text[:insert_at] + "\n" + section + text[insert_at:]
    else:
        marker = '<section class="quality-section about-ranking-section">'
        if marker not in text:
            raise RuntimeError("売れ筋比較の挿入位置が見つかりません。")
        text = text.replace(marker, section + "\n" + marker, 1)

    if text.count('<!-- sales-compare:start -->') != 1:
        raise RuntimeError("売れ筋比較セクションの件数が不正です。")
    if text.find('id="ranking"') > text.find('<!-- sales-compare:start -->'):
        raise RuntimeError("売れ筋比較が総合ランキングより前に配置されています。")
    return text


def methodology_block():
    return '''<!-- sales-method:start -->
<section><h2>楽天売れ筋との比較</h2><p>トップページでは、当サイトの高評価ランキングとは別に、楽天市場ランキングAPIのリアルタイム順位を取得して「売れ筋」と「高評価」の違いを比較します。</p><p>楽天側のgenreId 502835は「ヘッドホン・イヤホン」ジャンルのため、APIが返す元のジャンル順位は変更せず、商品名に「イヤホン」「イヤフォン」「earbud」「AirPods」「FreeBuds」などイヤホンと判断できる表現がある商品を上位順に10件抽出します。明確なヘッドホン商品は比較対象から除外します。</p><p>当サイト側の高評価TOP10とは楽天の商品コードで照合します。レビュー10件未満の商品は当サイト高評価ランキングの対象外として表示し、それ以外で一致しない商品は「TOP10圏外」と表示します。売れ筋順位そのものを当サイトの高評価順位計算には使用しません。</p></section>
<!-- sales-method:end -->'''


def update_methodology():
    if not METHODOLOGY_PATH.exists():
        raise RuntimeError("ランキング基準ページがありません。")
    text = METHODOLOGY_PATH.read_text(encoding="utf-8")
    text = METHOD_RE.sub("\n", text)
    marker = '<section><h2>自動更新とfail-safe</h2>'
    if marker not in text:
        raise RuntimeError("ランキング基準ページの挿入位置がありません。")
    text = text.replace(marker, methodology_block() + "\n" + marker, 1)
    METHODOLOGY_PATH.write_text(text, encoding="utf-8")


if not TOP_PATH.exists():
    raise RuntimeError("トップページがありません。")

page_text = TOP_PATH.read_text(encoding="utf-8")
own_ranks = current_high_rating_ranks(page_text)
update_methodology()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(locale="ja-JP")
    page.set_default_timeout(15000)
    site_response = page.goto(SITE_URL, wait_until="domcontentloaded", timeout=15000)
    if site_response is None or site_response.status >= 400:
        browser.close()
        raise RuntimeError("公開サイトを正常に開けませんでした。")
    ranking_data, ranking_items = fetch_ranking(page)
    browser.close()

section_html = build_section(ranking_data, ranking_items, own_ranks)
TOP_PATH.write_text(insert_section(page_text, section_html), encoding="utf-8")
print("Rakuten realtime sales vs high-rating comparison: OK")
