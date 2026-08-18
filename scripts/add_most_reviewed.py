from pathlib import Path


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: 置換対象が1件ではありません。件数={count}")
    return text.replace(old, new, 1)


generate_path = Path("generate.py")
text = generate_path.read_text(encoding="utf-8")

text = replace_once(
    text,
    '''under_10000_ranking_items, under_10000_prior_rating = rank_items(
    under_10000_filtered
)


# =========================================================
# HTML生成
''',
    '''under_10000_ranking_items, under_10000_prior_rating = rank_items(
    under_10000_filtered
)

most_reviewed_ranking_items = sorted(
    filtered,
    key=lambda item: to_int(item.get("reviewCount")),
    reverse=True,
)[:RANKING_SIZE]

if len(most_reviewed_ranking_items) != RANKING_SIZE:
    raise RuntimeError(
        "レビュー件数ランキング10件を生成できなかったため"
        "更新を中止します。"
    )


# =========================================================
# HTML生成
''',
    "レビュー件数ランキング追加",
)

text = replace_once(
    text,
    '''    <a href="/earphones/under-10000/">1万円以下</a>
</nav>''',
    '''    <a href="/earphones/under-10000/">1万円以下</a>
    <a href="/earphones/most-reviewed/">レビュー件数順</a>
</nav>''',
    "レビュー件数ランキングのナビ追加",
)

text = replace_once(
    text,
    '''under_10000_page_html = build_page(
    title=(
        "1万円以下のイヤホン高評価ランキング｜"
        "楽天レビューを毎日自動比較"
    ),
    meta_description=(
        "楽天市場の1万円以下のイヤホンを、レビュー評価とレビュー件数の"
        "信頼度をもとに毎日自動比較する高評価ランキングです。"
    ),
    canonical_url=(
        "https://otoku-ranking.pages.dev/earphones/under-10000/"
    ),
    h1="1万円以下 イヤホン高評価ランキング",
    header_description=(
        "楽天市場の商品データから1万円以下のイヤホンだけを抽出し、"
        "毎日自動比較しています。"
    ),
    ranking_description=(
        "1万円以下かつレビュー10件以上の商品を対象に、候補商品の"
        "平均評価を基準にベイズ補正を行い、評価の高さとレビュー件数の"
        "信頼度を両方反映して順位を決定しています。"
    ),
    ranking_items=under_10000_ranking_items,
)

if any(
''',
    '''under_10000_page_html = build_page(
    title=(
        "1万円以下のイヤホン高評価ランキング｜"
        "楽天レビューを毎日自動比較"
    ),
    meta_description=(
        "楽天市場の1万円以下のイヤホンを、レビュー評価とレビュー件数の"
        "信頼度をもとに毎日自動比較する高評価ランキングです。"
    ),
    canonical_url=(
        "https://otoku-ranking.pages.dev/earphones/under-10000/"
    ),
    h1="1万円以下 イヤホン高評価ランキング",
    header_description=(
        "楽天市場の商品データから1万円以下のイヤホンだけを抽出し、"
        "毎日自動比較しています。"
    ),
    ranking_description=(
        "1万円以下かつレビュー10件以上の商品を対象に、候補商品の"
        "平均評価を基準にベイズ補正を行い、評価の高さとレビュー件数の"
        "信頼度を両方反映して順位を決定しています。"
    ),
    ranking_items=under_10000_ranking_items,
)

most_reviewed_page_html = build_page(
    title=(
        "レビューが多いイヤホンランキング｜"
        "楽天レビュー件数を毎日比較"
    ),
    meta_description=(
        "楽天市場のイヤホンをレビュー件数が多い順に毎日自動比較。"
        "レビュー10件以上のイヤホン本体だけを対象にTOP10を掲載します。"
    ),
    canonical_url=(
        "https://otoku-ranking.pages.dev/earphones/most-reviewed/"
    ),
    h1="レビュー件数が多い イヤホンランキング",
    header_description=(
        "楽天市場の商品データからイヤホン本体だけを抽出し、"
        "レビュー件数が多い順に毎日ランキングしています。"
    ),
    ranking_description=(
        "レビュー10件以上のイヤホンを対象に、楽天の商品データの"
        "レビュー件数が多い順で掲載しています。評価点は表示しますが、"
        "このランキングの順位計算には使用していません。"
    ),
    ranking_items=most_reviewed_ranking_items,
)

most_reviewed_counts = [
    to_int(item.get("reviewCount"))
    for item in most_reviewed_ranking_items
]

if any(
    current < following
    for current, following in zip(
        most_reviewed_counts,
        most_reviewed_counts[1:],
    )
):
    raise RuntimeError(
        "レビュー件数ランキングの並び順が不正です。"
    )

if any(
''',
    "レビュー件数ページ追加",
)

text = replace_once(
    text,
    '''    (
        "public/earphones/under-10000/index.html",
        under_10000_page_html,
    ),
]''',
    '''    (
        "public/earphones/under-10000/index.html",
        under_10000_page_html,
    ),
    (
        "public/earphones/most-reviewed/index.html",
        most_reviewed_page_html,
    ),
]''',
    "レビュー件数ページ保存追加",
)

text = replace_once(
    text,
    '''print(f"1万円以下掲載件数: {len(under_10000_ranking_items)}")
print(f"1万円以下ベイズ事前平均: {under_10000_prior_rating:.4f}")
print(f"ベイズ事前レビュー数: {BAYES_PRIOR_WEIGHT}")''',
    '''print(f"1万円以下掲載件数: {len(under_10000_ranking_items)}")
print(f"1万円以下ベイズ事前平均: {under_10000_prior_rating:.4f}")
print(f"レビュー件数順掲載件数: {len(most_reviewed_ranking_items)}")
print(f"レビュー件数最多: {most_reviewed_counts[0]:,}件")
print(f"ベイズ事前レビュー数: {BAYES_PRIOR_WEIGHT}")''',
    "レビュー件数ログ追加",
)

text = replace_once(
    text,
    'print("総合・5,000円以下・1万円以下ランキングを更新しました。")',
    'print("総合・5,000円以下・1万円以下・レビュー件数順ランキングを更新しました。")',
    "完了ログ更新",
)

generate_path.write_text(text, encoding="utf-8")

workflow_path = Path(".github/workflows/update.yml")
workflow = workflow_path.read_text(encoding="utf-8")
workflow = replace_once(
    workflow,
    "git add public/index.html public/earphones/under-5000/index.html public/earphones/under-10000/index.html",
    "git add public/index.html public/earphones/under-5000/index.html public/earphones/under-10000/index.html public/earphones/most-reviewed/index.html",
    "GitHub Actionsのコミット対象追加",
)
workflow_path.write_text(workflow, encoding="utf-8")

print("most-reviewed patch applied")
