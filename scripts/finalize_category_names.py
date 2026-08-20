import html
import re
from pathlib import Path


PAGES = {
    Path("public/earphones/wireless/index.html"): "wireless",
    Path("public/earphones/wired/index.html"): "wired",
    Path("public/earphones/earcuff/index.html"): "earcuff",
}

CARD_PATTERN = re.compile(r'<article class="card">(.*?)</article>', re.DOTALL)


def normalize(value):
    return " ".join(html.unescape(value).split())


def strip_promotions(value):
    patterns = [
        r'^[★☆\s]+',
        r'^(?:楽天ランキング\d*位|楽天\d*位|迷ったらこれ[！!]?|20\d{2}年間MVP)[★☆\s・:：-]*',
        r'^＼[^／]{0,160}／\s*',
        r'^【[^】]{0,160}(?:OFF|クーポン|ポイント|楽天|P\d|セール|限定|ランキング)[^】]*】\s*',
        r'^「[^」]{0,160}(?:OFF|クーポン|ポイント|楽天|実質|ランキング)[^」]*」\s*',
    ]
    changed = True
    while changed:
        changed = False
        for pattern in patterns:
            cleaned = re.sub(pattern, "", value, count=1, flags=re.IGNORECASE).strip()
            if cleaned != value:
                value = cleaned
                changed = True
    return value


def bluetooth_suffix(raw):
    match = re.search(
        r'Bluetooth\s*(?:ver\.?\s*)?([4-6](?:\.\d+)?)',
        raw,
        re.IGNORECASE,
    )
    return f" Bluetooth {match.group(1)}" if match else ""


def known_product(raw):
    patterns = [
        r'\b(Anker\s+Soundcore\s+[A-Za-z0-9-]+)',
        r'\b(SOUNDPEATS\s+[A-Za-z0-9-]+)',
        r'\b(HUAWEI\s+FreeBuds\s+[A-Za-z0-9-]+(?:\s+ANC)?)',
        r'\b(SONY\s+WF-[A-Za-z0-9-]+)',
        r'\b(YOBYBO\s+[A-Za-z0-9-]+)',
        r'\b(QCY\s+[A-Za-z0-9-]+)',
        r'(ラディウス\s+HP-[A-Za-z0-9-]+(?:\s+NEKO)?)',
        r'\b(Lazata\b)',
        r'\b(Ennice\b)',
        r'\b(Kinglucky\b)',
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            return " ".join(match.group(1).split())
    return ""


def better_name(raw, visible, category):
    raw = normalize(raw)
    visible = normalize(visible)
    cleaned = strip_promotions(raw)
    product = known_product(cleaned)
    bt = bluetooth_suffix(raw)

    if category == "earcuff":
        if "イヤーカフ" in visible and visible not in ("イヤーカフ", "イヤーカフ型イヤホン"):
            return visible
        if product:
            return f"{product} イヤーカフ型イヤホン"
        return f"イヤーカフ型イヤホン{bt}"

    if category == "wired":
        if "有線" in visible and visible != "有線イヤホン":
            return visible
        if product:
            return f"{product} 有線イヤホン"
        model = re.search(r'\b(RP-[A-Z0-9-]+)\b', raw, re.IGNORECASE)
        if model and re.search(r'パナソニック|Panasonic', raw, re.IGNORECASE):
            return f"パナソニック {model.group(1).upper()} 有線イヤホン"
        return "有線イヤホン"

    # wireless
    if visible not in ("イヤホン", "ワイヤレスイヤホン"):
        return visible
    if product:
        return f"{product} ワイヤレスイヤホン"
    return f"ワイヤレスイヤホン{bt}"


def update_page(path, category):
    text = path.read_text(encoding="utf-8")
    changed = 0

    def replace_card(match):
        nonlocal changed
        body = match.group(1)
        heading = re.search(
            r'<h2 title="([^"]*)">(.*?)</h2>',
            body,
            re.DOTALL,
        )
        if not heading:
            raise RuntimeError(f"title付き商品名が見つかりません: {path}")

        raw = heading.group(1)
        visible = re.sub(r"<[^>]+>", "", heading.group(2))
        improved = better_name(raw, visible, category)
        replacement = (
            f'<h2 title="{html.escape(normalize(raw), quote=True)}">'
            f'{html.escape(improved)}</h2>'
        )
        body = body[: heading.start()] + replacement + body[heading.end() :]
        changed += 1
        return '<article class="card">' + body + '</article>'

    text = CARD_PATTERN.sub(replace_card, text)
    if changed != 10:
        raise RuntimeError(f"商品名最終調整が10件ではありません: {path} ({changed})")

    # カテゴリページの表示名が極端に曖昧になっていないことを確認。
    headings = re.findall(r'<h2 title="[^"]*">(.*?)</h2>', text, re.DOTALL)
    if category == "wireless" and any(normalize(h) == "イヤホン" for h in headings):
        raise RuntimeError("ワイヤレスページに『イヤホン』だけの商品名が残っています。")
    if category == "wired" and any("有線" not in normalize(h) for h in headings):
        raise RuntimeError("有線ページの商品表示名に『有線』がない商品があります。")
    if category == "earcuff" and any("イヤーカフ" not in normalize(h) for h in headings):
        raise RuntimeError("イヤーカフページの商品表示名に『イヤーカフ』がない商品があります。")

    path.write_text(text, encoding="utf-8")


for page, category in PAGES.items():
    update_page(page, category)

print("Category product display-name finalization: OK")
