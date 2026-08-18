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
    "UNDER_5000_MAX_PRICE = 5000\n",
    "UNDER_5000_MAX_PRICE = 5000\nUNDER_10000_MAX_PRICE = 10000\n",
    "1万円上限定数",
)

text = replace_once(
    text,
    "under_5000_ranking_items, under_5000_prior_rating = rank_items(\n"
    "    under_5000_filtered\n"
    ")\n\n\n"
    "# =========================================================\n"
    "# HTML生成\n",
    "under_5000_ranking_items, under_5000_prior_rating = rank_items(\n"
    "    under_5000_filtered\n"
    ")\n\n"
    "under_10000_filtered = [\n"
    "    item\n"
    "    for item in filtered\n"
    "    if to_int(item.get(\"itemPrice\")) <= UNDER_10000_MAX_PRICE\n"
    "]\n\n"
    "if len(under_10000_filtered) < RANKING_SIZE:\n"
    "    raise RuntimeError(\n"
    "        \"1万円以下の正常なイヤホン候補が10件未満のため\"\n"
    "        \"更新を中止します。\"\n"
    "        f\" 候補件数: {len(under_10000_filtered)}\"\n"
    "    )\n\n"
    "under_10000_ranking_items, under_10000_prior_rating = rank_items(\n"
    "    under_10000_filtered\n"
    ")\n\n\n"
    "# =========================================================\n"
    "# HTML生成\n",
    "1万円以下ランキング生成",
)

text = replace_once(
    text,
    '    <a href="/earphones/under-5000/">5,000円以下</a>\n',
    '    <a href="/earphones/under-5000/">5,000円以下</a>\n'
    '    <a href="/earphones/under-10000/">1万円以下</a>\n',
    "ナビ追加",
)

text = replace_once(
    text,
    "under_5000_page_html = build_page(\n",
    "under_5000_page_html = build_page(\n",
    "5千円ページ位置確認",
)

anchor = (
    "if any(\n"
    "    to_int(item.get(\"itemPrice\")) > UNDER_5000_MAX_PRICE\n"
    "    for item in under_5000_ranking_items\n"
    "):\n"
    "    raise RuntimeError(\n"
    "        \"5,000円以下ランキングに5,000円超の商品が含まれています。\"\n"
    "    )\n\n\n"
    "# =========================================================\n"
    "# 保存\n"
)

insert = (
    "under_10000_page_html = build_page(\n"
    "    title=(\n"
    "        \"1万円以下のイヤホン高評価ランキング｜\"\n"
    "        \"楽天レビューを毎日自動比較\"\n"
    "    ),\n"
    "    meta_description=(\n"
    "        \"楽天市場の1万円以下のイヤホンを、レビュー評価とレビュー件数の\"\n"
    "        \"信頼度をもとに毎日自動比較する高評価ランキングです。\"\n"
    "    ),\n"
    "    canonical_url=(\n"
    "        \"https://otoku-ranking.pages.dev/earphones/under-10000/\"\n"
    "    ),\n"
    "    h1=\"1万円以下 イヤホン高評価ランキング\",\n"
    "    header_description=(\n"
    "        \"楽天市場の商品データから1万円以下のイヤホンだけを抽出し、\"\n"
    "        \"毎日自動比較しています。\"\n"
    "    ),\n"
    "    ranking_description=(\n"
    "        \"1万円以下かつレビュー10件以上の商品を対象に、候補商品の\"\n"
    "        \"平均評価を基準にベイズ補正を行い、評価の高さとレビュー件数の\"\n"
    "        \"信頼度を両方反映して順位を決定しています。\"\n"
    "    ),\n"
    "    ranking_items=under_10000_ranking_items,\n"
    ")\n\n"
    "if any(\n"
    "    to_int(item.get(\"itemPrice\")) > UNDER_5000_MAX_PRICE\n"
    "    for item in under_5000_ranking_items\n"
    "):\n"
    "    raise RuntimeError(\n"
    "        \"5,000円以下ランキングに5,000円超の商品が含まれています。\"\n"
    "    )\n\n"
    "if any(\n"
    "    to_int(item.get(\"itemPrice\")) > UNDER_10000_MAX_PRICE\n"
    "    for item in under_10000_ranking_items\n"
    "):\n"
    "    raise RuntimeError(\n"
    "        \"1万円以下ランキングに1万円超の商品が含まれています。\"\n"
    "    )\n\n\n"
    "# =========================================================\n"
    "# 保存\n"
)

text = replace_once(text, anchor, insert, "1万円ページ追加")

text = replace_once(
    text,
    "    (\n"
    "        \"public/earphones/under-5000/index.html\",\n"
    "        under_5000_page_html,\n"
    "    ),\n"
    "]\n",
    "    (\n"
    "        \"public/earphones/under-5000/index.html\",\n"
    "        under_5000_page_html,\n"
    "    ),\n"
    "    (\n"
    "        \"public/earphones/under-10000/index.html\",\n"
    "        under_10000_page_html,\n"
    "    ),\n"
    "]\n",
    "保存対象追加",
)

text = replace_once(
    text,
    "print(f\"5,000円以下ベイズ事前平均: {under_5000_prior_rating:.4f}\")\n"
    "print(f\"ベイズ事前レビュー数: {BAYES_PRIOR_WEIGHT}\")\n",
    "print(f\"5,000円以下ベイズ事前平均: {under_5000_prior_rating:.4f}\")\n"
    "print(f\"1万円以下候補件数: {len(under_10000_filtered)}\")\n"
    "print(f\"1万円以下掲載件数: {len(under_10000_ranking_items)}\")\n"
    "print(f\"1万円以下ベイズ事前平均: {under_10000_prior_rating:.4f}\")\n"
    "print(f\"ベイズ事前レビュー数: {BAYES_PRIOR_WEIGHT}\")\n",
    "ログ追加",
)

text = replace_once(
    text,
    'print("public/index.html と 5,000円以下ランキングを更新しました。")\n',
    'print("総合・5,000円以下・1万円以下ランキングを更新しました。")\n',
    "完了ログ更新",
)

generate_path.write_text(text, encoding="utf-8")

workflow_path = Path(".github/workflows/update.yml")
workflow = workflow_path.read_text(encoding="utf-8")
workflow = replace_once(
    workflow,
    "          git add public/index.html public/earphones/under-5000/index.html\n",
    "          git add public/index.html public/earphones/under-5000/index.html public/earphones/under-10000/index.html\n",
    "Actions保存対象追加",
)
workflow_path.write_text(workflow, encoding="utf-8")

print("under-10000 patch applied")
