from pathlib import Path


RANKING_PAGES = [
    Path("public/index.html"),
    Path("public/earphones/under-5000/index.html"),
    Path("public/earphones/under-10000/index.html"),
    Path("public/earphones/most-reviewed/index.html"),
]

NEEDLE = '''    <a href="/earphones/most-reviewed/">レビュー件数順</a>\n</nav>'''
REPLACEMENT = '''    <a href="/earphones/most-reviewed/">レビュー件数順</a>\n    <a href="/earphones/methodology/">ランキングの決め方</a>\n</nav>'''

for path in RANKING_PAGES:
    text = path.read_text(encoding="utf-8")

    if '/earphones/methodology/' in text:
        continue

    count = text.count(NEEDLE)
    if count != 1:
        raise RuntimeError(
            f"Methodologyナビの挿入箇所が想定外です: {path} 件数={count}"
        )

    path.write_text(
        text.replace(NEEDLE, REPLACEMENT, 1),
        encoding="utf-8",
    )

print("Methodology navigation injection: OK")
