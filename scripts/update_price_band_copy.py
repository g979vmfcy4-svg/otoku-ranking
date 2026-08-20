from pathlib import Path


TOP_PATH = Path("public/index.html")
METHODOLOGY_PATH = Path("public/earphones/methodology/index.html")
ABOUT_PATH = Path("public/about/index.html")


def replace_optional(text, old, new):
    if old in text:
        return text.replace(old, new)
    return text


top = TOP_PATH.read_text(encoding="utf-8")
top = replace_optional(
    top,
    '<span><strong>1万円以下</strong><small>予算内の上位を探す</small></span>',
    '<span><strong>5,001〜10,000円</strong><small>5千円超の価格帯から探す</small></span>',
)
if '<strong>5,001〜10,000円</strong>' not in top:
    raise RuntimeError("トップページの価格帯導線を更新できませんでした。")
TOP_PATH.write_text(top, encoding="utf-8")


methodology = METHODOLOGY_PATH.read_text(encoding="utf-8")
methodology = replace_optional(
    methodology,
    "高評価ランキング、5,000円以下ランキング、1万円以下ランキングはいずれも、この補正後の評価を高い順に並べています。",
    "高評価ランキング、5,000円以下ランキング、5,001〜10,000円ランキングはいずれも、この補正後の評価を高い順に並べています。",
)
methodology = replace_optional(
    methodology,
    '<h3>1万円以下</h3><p>同様に、API上の商品価格が10,000円以下の候補だけを残して順位付けします。</p>',
    '<h3>5,001〜10,000円</h3><p>楽天APIに最小価格5,001円・最大価格10,000円を指定して候補を取得し、その価格帯の中でベイズ補正評価が高い順に並べます。5,000円以下ランキングとは商品価格が重複しません。</p>',
)
methodology = replace_optional(
    methodology,
    "価格帯ページに上限を超える商品が混ざっていないか確認",
    "価格帯ページに指定範囲外の商品が混ざっていないか確認",
)
methodology = replace_optional(
    methodology,
    "現在は楽天市場の商品検索APIから、検索条件に合う商品をレビュー件数の多い順で最大30件取得し、その候補群をさらに判定・順位付けしています。",
    "総合ランキングとレビュー件数ランキングは、検索条件に合う商品をレビュー件数の多い順で最大30件取得して候補群を作ります。価格帯ランキングは、それぞれの価格条件を楽天APIに指定したうえで、その価格帯から最大30件を取得して判定・順位付けしています。",
)
if "5,001〜10,000円ランキング" not in methodology:
    raise RuntimeError("ランキング基準ページの価格帯説明を更新できませんでした。")
METHODOLOGY_PATH.write_text(methodology, encoding="utf-8")


about = ABOUT_PATH.read_text(encoding="utf-8")
about = replace_optional(
    about,
    "<li>1万円以下の高評価ランキング</li>",
    "<li>5,001〜10,000円の高評価ランキング</li>",
)
if "5,001〜10,000円の高評価ランキング" not in about:
    raise RuntimeError("Aboutページの価格帯説明を更新できませんでした。")
ABOUT_PATH.write_text(about, encoding="utf-8")

print("Price band copy update: OK")
