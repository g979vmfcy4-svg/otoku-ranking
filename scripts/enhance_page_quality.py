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


def display_name(raw_name):
    """楽天掲載名は保持したまま、画面表示用の短い商品名を作る。"""
    original = " ".join(raw_name.split())
    value = original

    promo_patterns = [
        r'^(?:楽天ランキング\d*位|楽天\d*位|迷ったらこれ[！!]?|20\d{2}年間MVP|総合ランキング\d*部門\d*位受賞)[\s・:：-]*',
        r'^[★☆]+[^★☆]{0,50}[★☆]+\s*',
        r'^＼[^／]{0,120}／\s*',
        r'^【[^】]{0,120}(?:OFF|クーポン|ポイント|楽天|P\d|エントリー|ランキング|セール|限定)[^】]*】\s*',
        r'^「[^」]{0,120}(?:OFF|クーポン|ポイント|楽天|実質|ランキング)[^」]*」\s*',
    ]

    changed = True
    while changed:
        changed = False
        for pattern in promo_patterns:
            cleaned = re.sub(pattern, "", value, count=1, flags=re.IGNORECASE)
            if cleaned != value:
                value = cleaned.strip()
                changed = True

    value = re.sub(r'^[★☆＼／!！\s]+', "", value).strip()

    # 商品種別を探すための文字列では、販促用の角括弧説明をいったん外す。
    parsed = re.sub(r'【[^】]{0,120}】', " ", value)
    parsed = " ".join(parsed.split())

    bluetooth_pattern = r'Bluetooth\s*(?:ver\.?\s*)?([4-6](?:\.\d+)?)'
    earphone_type = (
        r'(完全ワイヤレスイヤホン|ワイヤレスイヤホン|有線\s*イヤホン|'
        r'骨伝導イヤホン|ステレオイヤホン|イヤホン)'
    )

    # 型番が明確な代表的な書式は、型番まで残す。
    if re.search(r'パナソニック', parsed, re.IGNORECASE):
        model = re.search(r'\b(RP-[A-Z0-9-]+)\b', parsed, re.IGNORECASE)
        if model:
            return f"パナソニック {model.group(1).upper()} 有線イヤホン"

    anker = re.search(
        r'\b(Anker\s+Soundcore\s+[A-Za-z0-9-]+)',
        parsed,
        re.IGNORECASE,
    )
    if anker:
        return f"{anker.group(1)} ワイヤレスイヤホン"

    # 英字ブランド名・型番が商品種別の直前にある場合は、その部分を優先する。
    branded = re.match(
        rf'^([A-Za-z][A-Za-z0-9.+_-]*(?:\s+[A-Za-z0-9][A-Za-z0-9.+_-]*){{0,2}})'
        rf'(?:\s+公式)?\s+{earphone_type}',
        parsed,
        re.IGNORECASE,
    )
    if branded:
        prefix = " ".join(branded.group(1).split())
        kind = re.sub(r'\s+', "", branded.group(2))
        if kind == "完全ワイヤレスイヤホン":
            kind = "ワイヤレスイヤホン"
        result = f"{prefix} {kind}"
        bluetooth = re.search(bluetooth_pattern, value, re.IGNORECASE)
        if bluetooth:
            result += f" Bluetooth {bluetooth.group(1)}"
        return result

    # ブランドや型番が明確でない商品は、商品種別と高確度の仕様だけに絞る。
    category = re.search(earphone_type, parsed, re.IGNORECASE)
    if category:
        kind = re.sub(r'\s+', "", category.group(1))
        if kind == "完全ワイヤレスイヤホン":
            kind = "ワイヤレスイヤホン"

        prefix = parsed[: category.start()].strip(" ・/|｜-【】[]()（）")
        if any(
            token in prefix.lower()
            for token in ["off", "クーポン", "楽天", "ポイント", "ランキング", "実質"]
        ):
            prefix = ""

        result = f"{prefix} {kind}".strip()
        bluetooth = re.search(bluetooth_pattern, value, re.IGNORECASE)
        if bluetooth:
            result += f" Bluetooth {bluetooth.group(1)}"

        if not prefix:
            if re.search(r'\bANC\b', value, re.IGNORECASE):
                result += " ANC"
            elif "液晶" in value:
                result += " 液晶画面付き"
            elif "インナーイヤー" in value:
                result += " インナーイヤー"
            elif "耳掛け" in value:
                result += " 耳掛け"

        return shorten(" ".join(result.split()), 64)

    return shorten(original, 60)


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
    visible_name = display_name(item["name"])
    image_html = ""
    if item["image"]:
        image_html = (
            f'<img src="{item["image"]}" '
            f'alt="{escape_text(visible_name)}" loading="lazy">'
        )

    return f'''<article class="quick-card">
    <div class="quick-label">{escape_text(label)}</div>
    <div class="quick-image">{image_html}</div>
    <h3 title="{escape_text(item["name"])}">{escape_text(visible_name)}</h3>
    <div class="quick-stats">
        <span class="data-chip">★ {item["rating"]:.2f}</span>
        <span class="data-chip">{item["reviews"]:,}件</span>
    </div>
    <div class="quick-price">{item["price"]:,}円</div>
    <p class="quick-reason">{escape_text(reason)}</p>
    <a class="quick-button" href="{item["link"]}" target="_blank"
       rel="nofollow sponsored noopener">楽天市場で価格・詳細を見る</a>
</article>'''


def apply_display_names(text, label):
    """ランキングカードの見出しだけを短縮し、元の商品名はtitle属性に保持する。"""
    changed = 0

    def replace_card(match):
        nonlocal changed
        body = match.group("body")
        heading = re.search(r'<h2>(.*?)</h2>', body, re.DOTALL)
        if not heading:
            raise RuntimeError(f"商品名見出しが見つかりません: {label}")

        raw_name = text_value(heading.group(1))
        visible_name = display_name(raw_name)
        replacement = (
            f'<h2 title="{escape_text(raw_name)}">'
            f'{escape_text(visible_name)}</h2>'
        )
        body = re.sub(
            r'<h2>.*?</h2>',
            replacement,
            body,
            count=1,
            flags=re.DOTALL,
        )
        changed += 1
        return '<article class="card">' + body + '</article>'

    updated = CARD_PATTERN.sub(replace_card, text)
    if changed != 10:
        raise RuntimeError(f"表示名を変更した商品カードが10件ではありません: {label} 件数={changed}")
    return updated


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
        <a class="jump-link" href="#ranking">総合ランキングを見る →</a>
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

ranking_head = '''<div class="ranking-list-head" id="ranking">
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

# 総合ランキングの長い楽天掲載名を、表示上だけ読みやすくする。
top_text = apply_display_names(top_text, "総合ランキング")

# ランキング本体やアフィリエイト導線を壊していないか最終確認する。
if top_text.count('class="card"') != 10:
    raise RuntimeError("V3化後の総合ランキング商品カードが10件ではありません。")
if top_text.count('class="quick-card"') != 3:
    raise RuntimeError("迷ったらこの3台が3件ではありません。")
if top_text.count('class="purpose-icon"') != 3:
    raise RuntimeError("目的別導線が3件ではありません。")
if 'class="compare-section"' in top_text or '<table class="compare-table">' in top_text:
    raise RuntimeError("不要な一覧比較が残っています。")
if 'class="guide-grid"' in top_text:
    raise RuntimeError("旧『このランキングの見方』が残っています。")
if top_text.count("hb.afl.rakuten.co.jp") < 10:
    raise RuntimeError("楽天アフィリエイトURLの確認に失敗しました。")

top_path.write_text(top_text, encoding="utf-8")

# 価格帯・レビュー件数順ページも、同じ表示名ルールを適用する。
for path in RANKING_PATHS[1:]:
    text = path.read_text(encoding="utf-8")
    text = apply_display_names(text, str(path))
    path.write_text(text, encoding="utf-8")

print("Purchase-first ranking page + clean product names optimization: OK")
