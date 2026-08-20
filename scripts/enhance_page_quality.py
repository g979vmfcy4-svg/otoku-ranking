from pathlib import Path
import html as html_lib
import re


RANKING_PATHS = [
    Path("public/index.html"),
    Path("public/earphones/under-5000/index.html"),
    Path("public/earphones/under-10000/index.html"),
    Path("public/earphones/most-reviewed/index.html"),
]

STYLESHEET = '<link rel="stylesheet" href="/assets/site-v2.css">'
CARD_PATTERN = re.compile(
    r'<article class="card">(?P<body>.*?)</article>',
    re.DOTALL,
)


def replace_single(pattern, replacement, text, label):
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


def text_value(fragment):
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return " ".join(html_lib.unescape(fragment).split())


def shorten(value, limit=58):
    value = " ".join(value.split())
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def escape_text(value):
    return html_lib.escape(str(value), quote=True)


def parse_cards(text, label):
    parsed = []

    for match in CARD_PATTERN.finditer(text):
        body = match.group("body")
        rank_match = re.search(r'<div class="rank">(\d+)</div>', body)
        image_match = re.search(
            r'<img src="([^"]+)" alt="([^"]*)"',
            body,
            re.DOTALL,
        )
        name_match = re.search(r"<h2>(.*?)</h2>", body, re.DOTALL)
        shop_match = re.search(
            r'<div class="shop">(.*?)</div>',
            body,
            re.DOTALL,
        )
        rating_match = re.search(
            r"★\s*([0-9.]+)\s*<span>\(([0-9,]+)件\)</span>",
            body,
            re.DOTALL,
        )
        price_match = re.search(
            r'<div class="price">([0-9,]+)円</div>',
            body,
        )
        link_match = re.search(
            r'class="button"\s+href="([^"]+)"',
            body,
            re.DOTALL,
        )

        if not all([
            rank_match,
            name_match,
            shop_match,
            rating_match,
            price_match,
            link_match,
        ]):
            raise RuntimeError(f"商品カード解析に失敗しました: {label}")

        parsed.append({
            "rank": int(rank_match.group(1)),
            "image": image_match.group(1) if image_match else "",
            "name": text_value(name_match.group(1)),
            "shop": text_value(shop_match.group(1)),
            "rating": float(rating_match.group(1)),
            "reviews": int(rating_match.group(2).replace(",", "")),
            "price": int(price_match.group(1).replace(",", "")),
            "link": link_match.group(1),
        })

    if len(parsed) != 10:
        raise RuntimeError(
            f"商品カードが10件ではありません: {label} 件数={len(parsed)}"
        )

    return parsed


def choose_distinct(source, used_names):
    for item in source:
        if item["name"] not in used_names:
            used_names.add(item["name"])
            return item
    raise RuntimeError("迷ったらこの3台の候補を3商品に分けられませんでした。")


def build_quick_card(item, label, reason):
    image_html = ""
    if item["image"]:
        image_html = (
            f'<img src="{item["image"]}" '
            f'alt="{escape_text(shorten(item["name"], 80))}" loading="lazy">'
        )

    return f'''<article class="quick-card">
    <div class="quick-label">{escape_text(label)}</div>
    <div class="quick-image">{image_html}</div>
    <h3 title="{escape_text(item["name"])}">{escape_text(shorten(item["name"], 62))}</h3>
    <div class="quick-stats">
        <span class="data-chip">★ {item["rating"]:.2f}</span>
        <span class="data-chip">{item["reviews"]:,}件</span>
    </div>
    <div class="quick-price">{item["price"]:,}円</div>
    <p class="quick-reason">{escape_text(reason)}</p>
    <a class="quick-button" href="{item["link"]}" target="_blank"
       rel="nofollow sponsored noopener">楽天市場で価格・詳細を見る</a>
</article>'''


def build_comparison_table(items):
    rows = []

    for item in items:
        rows.append(
            f'''<tr>
    <td class="compare-rank">{item["rank"]}</td>
    <td class="compare-product" title="{escape_text(item["name"])}">
        {escape_text(shorten(item["name"], 54))}
        <small>{escape_text(shorten(item["shop"], 30))}</small>
    </td>
    <td>★ {item["rating"]:.2f}</td>
    <td>{item["reviews"]:,}件</td>
    <td><strong>{item["price"]:,}円</strong></td>
    <td><a class="table-button" href="{item["link"]}" target="_blank"
           rel="nofollow sponsored noopener">詳細</a></td>
</tr>'''
        )

    return f'''<section class="quality-section compare-section" id="comparison">
    <div class="section-head">
        <div>
            <span class="section-kicker">一覧比較</span>
            <h2>高評価イヤホンTOP10を比較</h2>
            <p>評価・レビュー件数・価格をまとめて確認できます。</p>
        </div>
    </div>
    <div class="compare-wrap">
        <table class="compare-table">
            <thead>
                <tr>
                    <th>順位</th><th>商品</th><th>評価</th>
                    <th>レビュー</th><th>価格</th><th>楽天</th>
                </tr>
            </thead>
            <tbody>{"".join(rows)}</tbody>
        </table>
    </div>
</section>'''


# 毎日の生成後に、4ランキングへ共通デザインとCTA文言を適用する。
for path in RANKING_PATHS:
    text = path.read_text(encoding="utf-8")

    if STYLESHEET not in text:
        text = replace_single(
            r"</head>",
            STYLESHEET + "\n</head>",
            text,
            f"V2 stylesheet: {path}",
        )

    text = text.replace(
        ">楽天市場で見る</a>",
        ">楽天市場で価格・詳細を見る</a>",
    )
    path.write_text(text, encoding="utf-8")


# トップページは、説明より先に商品へ到達できる購入導線へ並べ替える。
top_path = Path("public/index.html")
under_5000_path = Path("public/earphones/under-5000/index.html")
most_reviewed_path = Path("public/earphones/most-reviewed/index.html")

top_text = top_path.read_text(encoding="utf-8")
top_items = parse_cards(top_text, "総合ランキング")
under_5000_items = parse_cards(
    under_5000_path.read_text(encoding="utf-8"),
    "5,000円以下ランキング",
)
most_reviewed_items = parse_cards(
    most_reviewed_path.read_text(encoding="utf-8"),
    "レビュー件数ランキング",
)

# ヘッダーは短い一言だけにし、説明バッジは置かない。
top_text = replace_single(
    r'(<header>\s*<div>\s*<h1>.*?</h1>\s*)<p>.*?</p>',
    r'\1<p>レビュー評価とレビュー件数から、楽天市場のイヤホンを毎日比較。</p>',
    top_text,
    "compact hero description",
)

notice_match = re.search(
    r'<div class="notice">(?P<body>.*?)</div>',
    top_text,
    re.DOTALL,
)
if not notice_match:
    raise RuntimeError("トップページの更新情報を取得できませんでした。")

notice_body = notice_match.group("body")
updated_match = re.search(
    r'<strong>最終更新：</strong>\s*(.*?)<br>',
    notice_body,
    re.DOTALL,
)
updated_text = text_value(updated_match.group(1)) if updated_match else "毎日更新"

ranking_explanation = re.sub(
    r'.*?<strong>最終更新：</strong>.*?<br>',
    "",
    notice_body,
    count=1,
    flags=re.DOTALL,
)
ranking_explanation = text_value(ranking_explanation)

used_names = set()
overall_pick = choose_distinct(top_items, used_names)
budget_pick = choose_distinct(under_5000_items, used_names)
reviewed_pick = choose_distinct(most_reviewed_items, used_names)

affiliate_disclosure = '''<div class="affiliate-disclosure">
    <span>広告</span>
    当サイトは楽天アフィリエイトを利用しています。
</div>'''

quick_html = f'''<section class="quality-section quick-section" id="quick-picks">
    <div class="section-head">
        <div>
            <span class="section-kicker">まずはここから</span>
            <h2>迷ったらこの3台</h2>
            <p>総合・予算・レビュー件数の3つの軸から、候補をすぐ選べます。</p>
        </div>
        <a class="jump-link" href="#comparison">TOP10を比較 →</a>
    </div>
    <div class="quick-grid">
        {build_quick_card(overall_pick, f"総合 {overall_pick['rank']}位", "評価とレビュー件数を総合して上位になった候補です。")}
        {build_quick_card(budget_pick, f"5,000円以下 {budget_pick['rank']}位", "5,000円以下で評価とレビュー実績を重視した候補です。")}
        {build_quick_card(reviewed_pick, f"レビュー件数 {reviewed_pick['rank']}位", f"レビュー{reviewed_pick['reviews']:,}件。購入実績の多さを重視した候補です。")}
    </div>
</section>'''

purpose_html = '''<section class="purpose-section" aria-label="目的別ランキング">
    <a href="/earphones/under-5000/">
        <span class="purpose-icon">¥</span>
        <span><strong>5,000円以下</strong><small>価格を抑えて探す</small></span>
        <b>→</b>
    </a>
    <a href="/earphones/under-10000/">
        <span class="purpose-icon">1万</span>
        <span><strong>1万円以下</strong><small>予算内の上位を探す</small></span>
        <b>→</b>
    </a>
    <a href="/earphones/most-reviewed/">
        <span class="purpose-icon">★</span>
        <span><strong>レビュー件数順</strong><small>購入実績から探す</small></span>
        <b>→</b>
    </a>
</section>'''

ranking_head = '''<div class="ranking-list-head">
    <span class="section-kicker">詳しく見る</span>
    <h2>総合ランキングTOP10</h2>
    <p>各商品の評価・レビュー件数・価格を確認して、気になる商品は楽天市場で最新情報を確認できます。</p>
</div>'''

top_sections = (
    affiliate_disclosure
    + "\n"
    + quick_html
    + "\n"
    + purpose_html
    + "\n"
    + build_comparison_table(top_items)
    + "\n"
    + ranking_head
)

top_text = replace_single(
    r'<div class="notice">.*?</div>',
    top_sections,
    top_text,
    "purchase-first top sections",
)

about_html = f'''<section class="quality-section about-ranking-section">
    <div class="section-head">
        <div>
            <span class="section-kicker">このサイトについて</span>
            <h2>このランキングについて</h2>
            <p>商品を見たあとで、必要な人だけ確認できるようランキングの考え方をまとめています。</p>
        </div>
    </div>
    <div class="about-ranking-grid">
        <div>
            <strong>データで比較</strong>
            <p>楽天市場のレビュー評価・レビュー件数・価格など、取得できる商品データをもとに順位を決めています。</p>
        </div>
        <div>
            <strong>毎日更新</strong>
            <p>最終更新：{escape_text(updated_text)}。価格やレビュー件数は取得時点の情報です。</p>
        </div>
        <div>
            <strong>実機レビューではありません</strong>
            <p>音質や装着感を実際に試した順位ではありません。購入前に楽天市場で仕様・販売条件をご確認ください。</p>
        </div>
    </div>
    <p class="ranking-note">{escape_text(ranking_explanation)}</p>
    <div class="about-ranking-links">
        <a href="/earphones/methodology/">ランキング基準を詳しく見る →</a>
        <a href="/about/">このサイトについて →</a>
    </div>
</section>'''

top_text = replace_single(
    r"</main>",
    about_html + "\n</main>",
    top_text,
    "bottom ranking explanation",
)


# ランキング本体やアフィリエイト導線を壊していないか最終確認する。
if top_text.count('class="card"') != 10:
    raise RuntimeError("V3化後の総合ランキング商品カードが10件ではありません。")
if top_text.count('class="quick-card"') != 3:
    raise RuntimeError("迷ったらこの3台が3件ではありません。")
if top_text.count("<tr>") != 11:
    raise RuntimeError("TOP10比較表の行数が想定外です。")
if top_text.count('class="purpose-icon"') != 3:
    raise RuntimeError("目的別導線が3件ではありません。")
if 'class="guide-grid"' in top_text:
    raise RuntimeError("旧『このランキングの見方』が残っています。")
if top_text.count("hb.afl.rakuten.co.jp") < 10:
    raise RuntimeError("楽天アフィリエイトURLの確認に失敗しました。")

top_path.write_text(top_text, encoding="utf-8")
print("Purchase-first ranking page V3 optimization: OK")
