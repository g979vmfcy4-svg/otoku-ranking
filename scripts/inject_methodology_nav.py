from pathlib import Path


PAGES = [
    Path("public/index.html"),
    Path("public/earphones/under-5000/index.html"),
    Path("public/earphones/under-10000/index.html"),
    Path("public/earphones/most-reviewed/index.html"),
    Path("public/earphones/methodology/index.html"),
    Path("public/about/index.html"),
]

METHODOLOGY_LINK = '    <a href="/earphones/methodology/">ランキングの決め方</a>\n'
ABOUT_LINK = '    <a href="/about/">このサイトについて</a>\n'

for path in PAGES:
    text = path.read_text(encoding="utf-8")

    if '/earphones/methodology/' not in text:
        marker = '    <a href="/earphones/most-reviewed/">レビュー件数順</a>\n'
        if marker not in text:
            raise RuntimeError(
                f"Methodologyナビの挿入箇所が見つかりません: {path}"
            )
        text = text.replace(
            marker,
            marker + METHODOLOGY_LINK,
            1,
        )

    if '/about/' not in text:
        if METHODOLOGY_LINK not in text:
            compact_marker = '<a href="/earphones/methodology/">ランキングの決め方</a>'
            if compact_marker not in text:
                raise RuntimeError(
                    f"Aboutナビの挿入箇所が見つかりません: {path}"
                )
            text = text.replace(
                compact_marker,
                compact_marker + '<a href="/about/">このサイトについて</a>',
                1,
            )
        else:
            text = text.replace(
                METHODOLOGY_LINK,
                METHODOLOGY_LINK + ABOUT_LINK,
                1,
            )

    path.write_text(text, encoding="utf-8")

print("Methodology/About navigation injection: OK")
