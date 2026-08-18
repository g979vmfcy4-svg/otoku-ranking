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
    '''    <a href="/earphones/most-reviewed/">レビュー件数順</a>\n</nav>''',
    '''    <a href="/earphones/most-reviewed/">レビュー件数順</a>\n    <a href="/earphones/methodology/">ランキングの決め方</a>\n</nav>''',
    "Methodologyナビ追加",
)

generate_path.write_text(text, encoding="utf-8")

methodology_path = Path("public/earphones/methodology/index.html")
methodology_path.parent.mkdir(parents=True, exist_ok=True)
methodology_path.write_text(
    '''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="google-site-verification" content="xebuT18VaLulU2FGAl1MrnJnOgS4b1ZjrZcFaV45KyQ">
<meta name="description" content="イヤホンランキングの決め方、楽天市場の商品データの取得方法、ベイズ補正、レビュー件数順、除外基準、更新方法を公開しています。">
<meta name="robots" content="index,follow">
<link rel="canonical" href="https://otoku-ranking.pages.dev/earphones/methodology/">
<title>ランキングの決め方｜イヤホン高評価ランキングの評価基準・データ取得方法</title>
<style>
* { box-sizing: border-box; }
body { margin:0; background:#f5f6f8; color:#222; font-family:-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif; }
header { background:#fff; padding:28px 16px; border-bottom:1px solid #ddd; }
header div, main, footer, .ranking-nav { max-width:760px; margin:auto; }
h1 { margin:0 0 10px; font-size:28px; }
header p { margin:0; color:#666; line-height:1.7; }
.ranking-nav { padding:14px 12px 0; display:flex; gap:8px; flex-wrap:wrap; }
.ranking-nav a { background:#fff; color:#333; text-decoration:none; border:1px solid #ddd; border-radius:8px; padding:8px 11px; font-size:13px; font-weight:bold; }
main { padding:18px 12px 32px; }
section { background:#fff; padding:20px; margin-bottom:14px; border-radius:14px; box-shadow:0 2px 8px rgba(0,0,0,.04); }
h2 { margin:0 0 12px; font-size:20px; }
h3 { margin:18px 0 8px; font-size:16px; }
p, li { line-height:1.8; font-size:14px; }
ul { padding-left:22px; }
.formula { background:#f5f6f8; border-radius:10px; padding:14px; overflow-wrap:anywhere; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:13px; line-height:1.7; }
.note { border-left:4px solid #444; padding-left:12px; color:#555; }
footer { padding:18px 14px 40px; color:#666; font-size:12px; line-height:1.7; }
@media(max-width:520px) { h1{font-size:24px;} section{padding:16px;} }
</style>
</head>
<body>
<header><div><h1>ランキングの決め方</h1><p>このサイトが、楽天市場のイヤホンをどのような条件で抽出し、どのように順位付けしているかを公開します。</p></div></header>
<nav class="ranking-nav" aria-label="イヤホンランキング">
<a href="/">高評価ランキング</a><a href="/earphones/under-5000/">5,000円以下</a><a href="/earphones/under-10000/">1万円以下</a><a href="/earphones/most-reviewed/">レビュー件数順</a><a href="/earphones/methodology/">ランキングの決め方</a>
</nav>
<main>
<section><h2>このサイトの基本方針</h2><p>当サイトは、実際に商品を試した主観的なレビューサイトではありません。楽天市場から取得できる商品データを使い、評価、レビュー件数、価格などの客観的な数値から、比較しやすいランキングを自動生成しています。</p><p>「音質が良い」「装着感が最高」といった、実機確認をしていない主観的な評価はランキング理由として使用しません。</p></section>
<section><h2>使用するデータ</h2><p>楽天市場の商品検索APIから取得した情報を利用しています。主に使用する項目は、商品名、価格、レビュー平均、レビュー件数、ジャンル、店舗名、商品画像、楽天アフィリエイトURLです。</p><p>データは原則として1日1回、自動更新します。価格や在庫は取得時点の情報であり、購入時には楽天市場の商品ページの最新情報をご確認ください。</p></section>
<section><h2>イヤホン本体だけを残すための条件</h2><p>「イヤホン」という検索語だけでは、ケース、変換アダプター、ストラップ、防災ラジオなどが混ざる場合があります。そのため、取得後に追加の判定を行います。</p><ul><li>楽天市場の「ヘッドホン・イヤホン」ジャンル（genreId 502835）であること</li><li>商品名に「イヤホン」「イヤフォン」「earphone」「earbud」などの表現があること</li><li>明らかなアクセサリー、変換アダプター、ラジオ、ケース単体などの除外語句に該当しないこと</li><li>レビューが10件以上あること</li><li>レビュー平均が0より大きく5以下であること</li><li>価格が0円より大きいこと</li><li>有効な楽天アフィリエイトURLが取得できていること</li></ul></section>
<section><h2>高評価ランキングの計算方法</h2><p>単純にレビュー平均だけで並べると、「★5.0・レビュー10件」の商品が「★4.8・レビュー5,000件」の商品より上になりやすくなります。そこで、レビュー件数による信頼度を反映するためにベイズ補正を使っています。</p><div class="formula">補正評価 = (レビュー件数 × 商品のレビュー平均 + 100 × 候補商品の平均評価) ÷ (レビュー件数 + 100)</div><p>レビュー件数が少ない商品ほど候補全体の平均評価に近づき、レビュー件数が十分に多い商品ほど実際のレビュー平均に近づきます。</p><p>高評価ランキング、5,000円以下ランキング、1万円以下ランキングはいずれも、この補正後の評価を高い順に並べています。</p></section>
<section><h2>価格帯ランキング</h2><h3>5,000円以下</h3><p>イヤホン本体として判定された候補のうち、API上の商品価格が5,000円以下のものだけを残し、その中でベイズ補正評価が高い順に並べます。</p><h3>1万円以下</h3><p>同様に、API上の商品価格が10,000円以下の候補だけを残して順位付けします。</p><p class="note">商品名に「クーポン適用で○○円」などの表記があっても、ランキングの価格条件はAPIから取得した商品価格を基準にしています。ポイント還元やクーポン適用後の実質価格とは一致しない場合があります。</p></section>
<section><h2>レビュー件数ランキング</h2><p>レビュー件数ランキングは、イヤホン本体として判定された候補をレビュー件数の多い順に並べます。このランキングではレビュー平均は表示しますが、順位計算には使用しません。</p></section>
<section><h2>自動更新とfail-safe</h2><p>ランキング生成はGitHub Actionsで自動実行しています。更新時には複数の検証を行い、異常がある場合は新しいページへ置き換えない設計にしています。</p><ul><li>正常な候補が10件未満なら更新を停止</li><li>価格帯ページに上限を超える商品が混ざっていないか確認</li><li>レビュー件数ランキングが降順になっているか確認</li><li>楽天アフィリエイトURLの形式を確認</li><li>生成HTMLに10件の商品カードが存在するか確認</li></ul></section>
<section><h2>ランキングの限界</h2><p>当サイトのランキングは楽天市場の商品を完全に網羅したものではありません。現在は楽天市場の商品検索APIから、検索条件に合う商品をレビュー件数の多い順で最大30件取得し、その候補群をさらに判定・順位付けしています。</p><p>そのため、「楽天市場に存在する全イヤホンの中で絶対に1位」という意味ではなく、当サイトが取得・検証できた候補群の中での順位です。</p><p>また、商品の性能、音質、装着感、耐久性などを当サイトが実機検証した結果ではありません。購入判断では、楽天市場の商品説明や個別レビューもあわせてご確認ください。</p></section>
<section><h2>広告・アフィリエイトについて</h2><p>当サイトは楽天アフィリエイトを利用しています。「楽天市場で見る」から商品を購入した場合、当サイトに成果報酬が発生することがあります。</p><p>アフィリエイト報酬の有無によって、個別商品のレビュー平均やレビュー件数などのデータを変更することはありません。</p></section>
</main>
<footer><p>当サイトは楽天アフィリエイトを利用しています。価格・在庫等は取得時点の情報です。</p><a href="https://developers.rakuten.com/" target="_blank" rel="noopener">Supported by Rakuten Developers</a></footer>
</body>
</html>
''',
    encoding="utf-8",
)

workflow_path = Path(".github/workflows/update.yml")
workflow_path.write_text(
    '''name: Update Rakuten Ranking

on:
  workflow_dispatch:

  schedule:
    - cron: "0 21 * * *"

  push:
    branches:
      - main
    paths:
      - "generate.py"
      - ".github/workflows/update.yml"

permissions:
  contents: write

jobs:
  update-ranking:
    runs-on: ubuntu-latest

    env:
      RAKUTEN_APPLICATION_ID: ${{ secrets.RAKUTEN_APPLICATION_ID }}
      RAKUTEN_ACCESS_KEY: ${{ secrets.RAKUTEN_ACCESS_KEY }}
      RAKUTEN_AFFILIATE_ID: ${{ secrets.RAKUTEN_AFFILIATE_ID }}

    steps:
      - name: Checkout repository
        uses: actions/checkout@v5

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.13"

      - name: Check Python syntax
        run: python -m py_compile generate.py

      - name: Install Playwright
        run: |
          python -m pip install --upgrade pip
          pip install playwright
          python -m playwright install --with-deps chromium

      - name: Generate ranking pages
        run: python generate.py

      - name: Commit updated pages
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add public/index.html public/earphones/under-5000/index.html public/earphones/under-10000/index.html public/earphones/most-reviewed/index.html public/earphones/methodology/index.html
          git diff --cached --quiet && exit 0
          git commit -m "Update ranking"
          git push
''',
    encoding="utf-8",
)

Path("scripts/add_methodology.py").unlink()
print("methodology page and navigation applied; workflow restored")
