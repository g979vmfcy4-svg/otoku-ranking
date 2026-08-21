from pathlib import Path
import html
import re


PAGES = [
    Path("public/index.html"),
    Path("public/earphones/index.html"),
    Path("public/earphones/under-5000/index.html"),
    Path("public/earphones/under-10000/index.html"),
    Path("public/earphones/wireless/index.html"),
    Path("public/earphones/wired/index.html"),
    Path("public/earphones/earcuff/index.html"),
    Path("public/earphones/most-reviewed/index.html"),
    Path("public/earphones/methodology/index.html"),
    Path("public/about/index.html"),
]

DESIGN_STYLESHEET = '<link rel="stylesheet" href="/assets/design-polish.css">'
META_BLOCK_RE = re.compile(
    r'<!-- search-meta:start -->.*?<!-- search-meta:end -->',
    re.DOTALL,
)
LD_JSON_RE = re.compile(
    r'<script type="application/ld\+json">.*?</script>',
    re.DOTALL,
)
ROBOTS_META_RE = re.compile(
    r'<meta name="robots" content="([^"]*)">',
    re.IGNORECASE,
)
RAKUTEN_IMAGE_RE = re.compile(
    r'<img\b[^>]*src="https://thumbnail\.image\.rakuten\.co\.jp[^>]*>',
    re.IGNORECASE,
)
SKIP_LINK_RE = re.compile(
    r'\s*<a class="skip-link" href="#main-content">.*?</a>\s*',
    re.DOTALL,
)


def extract(pattern, text, label):
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        raise RuntimeError(f"{label} を取得できません")
    return html.unescape(match.group(1)).strip()


def build_meta_block(title, description, canonical, has_rakuten_images):
    preconnect = ""
    if has_rakuten_images:
        preconnect = '<link rel="preconnect" href="https://thumbnail.image.rakuten.co.jp" crossorigin>\n'

    return f'''<!-- search-meta:start -->
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta name="theme-color" content="#bf0000">
<meta property="og:type" content="website">
<meta property="og:site_name" content="イヤホンランキング">
<meta property="og:title" content="{html.escape(title, quote=True)}">
<meta property="og:description" content="{html.escape(description, quote=True)}">
<meta property="og:url" content="{html.escape(canonical, quote=True)}">
<meta name="twitter:card" content="summary">
{preconnect}<!-- search-meta:end -->'''


def enrich_website_structured_data(text):
    replacement = '''<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "イヤホンランキング",
  "alternateName": "otoku-ranking.pages.dev",
  "url": "https://otoku-ranking.pages.dev/"
}
</script>'''

    replaced = False

    def repl(match):
        nonlocal replaced
        block = match.group(0)
        if '"@type": "WebSite"' in block:
            replaced = True
            return replacement
        return block

    text = LD_JSON_RE.sub(repl, text)
    if not replaced:
        text = text.replace("</head>", replacement + "\n</head>", 1)
    return text


def enable_large_image_preview(text, path):
    match = ROBOTS_META_RE.search(text)
    if not match:
        raise RuntimeError(f"robots meta がありません: {path}")

    directives = [part.strip() for part in match.group(1).split(",") if part.strip()]
    directives = [
        directive
        for directive in directives
        if not directive.lower().startswith("max-image-preview:")
    ]
    directives.append("max-image-preview:large")
    replacement = f'<meta name="robots" content="{",".join(directives)}">'
    return text[:match.start()] + replacement + text[match.end():]


def add_dimensions(tag):
    if ' width="' not in tag:
        tag = tag[:-1] + ' width="128"' + tag[-1]
    if ' height="' not in tag:
        tag = tag[:-1] + ' height="128"' + tag[-1]
    return tag


def optimize_images(text):
    text = RAKUTEN_IMAGE_RE.sub(lambda m: add_dimensions(m.group(0)), text)
    match = RAKUTEN_IMAGE_RE.search(text)
    if not match:
        return text

    first = match.group(0)
    optimized = first
    if 'loading="lazy"' in optimized:
        optimized = optimized.replace('loading="lazy"', 'loading="eager" fetchpriority="high"', 1)
    elif 'loading="eager"' not in optimized:
        optimized = optimized[:-1] + ' loading="eager" fetchpriority="high">'
    elif 'fetchpriority=' not in optimized:
        optimized = optimized[:-1] + ' fetchpriority="high">'

    return text[:match.start()] + optimized + text[match.end():]


def add_design_accessibility(text, path):
    text = text.replace(DESIGN_STYLESHEET + "\n", "")
    text = text.replace(DESIGN_STYLESHEET, "")
    if "</head>" not in text:
        raise RuntimeError(f"</head> がありません: {path}")
    text = text.replace("</head>", DESIGN_STYLESHEET + "\n</head>", 1)

    text = SKIP_LINK_RE.sub("\n", text)
    main_match = re.search(r'<main\b([^>]*)>', text)
    if not main_match:
        raise RuntimeError(f"main 要素がありません: {path}")
    main_tag = main_match.group(0)
    if 'id="main-content"' not in main_tag:
        new_main = main_tag[:-1] + ' id="main-content">'
        text = text[:main_match.start()] + new_main + text[main_match.end():]

    body_match = re.search(r'<body\b[^>]*>', text)
    if not body_match:
        raise RuntimeError(f"body 要素がありません: {path}")
    skip_link = '<a class="skip-link" href="#main-content">本文へ移動</a>'
    text = text[:body_match.end()] + "\n" + skip_link + text[body_match.end():]
    return text


for path in PAGES:
    if not path.exists():
        raise RuntimeError(f"検索メタデータ対象ページがありません: {path}")

    text = path.read_text(encoding="utf-8")
    title = extract(r'<title>(.*?)</title>', text, f"title: {path}")
    description = extract(
        r'<meta name="description" content="([^"]*)">',
        text,
        f"description: {path}",
    )
    canonical = extract(
        r'<link rel="canonical" href="([^"]+)">',
        text,
        f"canonical: {path}",
    )

    text = META_BLOCK_RE.sub("", text)
    block = build_meta_block(
        title,
        description,
        canonical,
        "thumbnail.image.rakuten.co.jp" in text,
    )
    text = text.replace("</head>", block + "\n</head>", 1)

    if path == Path("public/index.html"):
        text = enrich_website_structured_data(text)

    text = enable_large_image_preview(text, path)
    text = optimize_images(text)
    text = add_design_accessibility(text, path)

    if text.count('rel="icon" href="/favicon.svg"') != 1:
        raise RuntimeError(f"favicon設定が不正です: {path}")
    if text.count('property="og:title"') != 1:
        raise RuntimeError(f"OGタイトル設定が不正です: {path}")
    if text.count("max-image-preview:large") != 1:
        raise RuntimeError(f"画像プレビュー設定が不正です: {path}")
    if text.count(DESIGN_STYLESHEET) != 1:
        raise RuntimeError(f"デザインCSS設定が不正です: {path}")
    if text.count('class="skip-link" href="#main-content"') != 1:
        raise RuntimeError(f"スキップリンク設定が不正です: {path}")
    if text.count('id="main-content"') != 1:
        raise RuntimeError(f"本文アンカー設定が不正です: {path}")

    path.write_text(text, encoding="utf-8")

print("Search metadata / favicon / image performance / UX polish: OK")
