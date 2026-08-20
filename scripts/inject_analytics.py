from pathlib import Path


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

SCRIPT_TAG = '<script defer src="/assets/analytics.js"></script>'

for path in PAGES:
    text = path.read_text(encoding="utf-8")

    if SCRIPT_TAG not in text:
        if "</body>" not in text:
            raise RuntimeError(f"</body> が見つかりません: {path}")
        text = text.replace("</body>", SCRIPT_TAG + "\n</body>", 1)

    if text.count(SCRIPT_TAG) != 1:
        raise RuntimeError(f"analytics.js の読み込み数が想定外です: {path}")

    path.write_text(text, encoding="utf-8")

print("Analytics script injection: OK")
