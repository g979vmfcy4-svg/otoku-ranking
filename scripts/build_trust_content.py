import html
import os
import re
from pathlib import Path


SITE = "https://otoku-ranking.pages.dev"
DEFAULT_CONTACT_URL = "https://github.com/g979vmfcy4-svg/otoku-ranking/issues"
OPERATOR_NAME = os.getenv("SITE_OPERATOR_NAME", "").strip() or "イヤホンランキング運営者"
CONTACT_URL = os.getenv("SITE_CONTACT_URL", "").strip() or DEFAULT_CONTACT_URL
GA_MEASUREMENT_ID = os.getenv("GA_MEASUREMENT_ID", "").strip()

if not CONTACT_URL.startswith("https://"):
    raise RuntimeError("SITE_CONTACT_URL は https:// で始まるURLを指定してください。")

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

RANKING_PAGES = [
    Path("public/index.html"),
    Path("public/earphones/under-5000/index.html"),
    Path("public/earphones/under-10000/index.html"),
    Path("public/earphones/wireless/index.html"),
    Path("public/earphones/wired/index.html"),
    Path("public/earphones/earcuff/index.html"),
    Path("public/earphones/most-reviewed/index.html"),
]

TRUST_STYLESHEET = '<link rel="stylesheet" href="/assets/trust-content.css">'
GUIDE_RE = re.compile(
    r'\s*<!-- decision-guide:start -->.*?<!-- decision-guide:end -->\s*',
    re.DOTALL,
)
OPERATOR_RE = re.compile(
    r'\s*<!-- operator-info:start -->.*?<!-- operator-info:end -->\s*',
    re.DOTALL,
)

BASE_NAV = '''<nav class="ranking-nav" aria-label="イヤホンランキング">
    <a href="/earphones/">ランキング一覧</a>
    <a href="/">総合</a>
    <a href="/earphones/under-5000/">5,000円以下</a>
    <a href="/earphones/under-10000/">5千〜1万円</a>
    <a href="/earphones/wireless/">ワイヤレス</a>
    <a href="/earphones/wired/">有線</a>
    <a href="/earphones/earcuff/">イヤーカフ</a>
    <a href="/earphones/most-reviewed/">レビュー件数順</a>
    <a href="/earphones/review-guide/">レビューの読み方</a>
    <a href="/earphones/methodology/">ランキング基準</a>
    <a href="/about/">このサイトについて</a>
</nav>'''

FOOTER = '''<footer>
    <p>当サイトは楽天アフィリエイトを利用しています。価格・在庫・レビュー件数などは取得時点の情報です。</p>
    <nav class="footer-links" aria-label="サイト情報">
        <a href="/about/">運営方針</a>
        <a href="/earphones/methodology/">ランキング基準</a>
        <a href="/earphones/review-guide/">レビューの読み方</a>
        <a href="/contact/">お問い合わせ</a>
        <a href="/privacy/">プライバシーポリシー</a>
        <a href="https://developers.rakuten.com/" target="_blank" rel="noopener">Supported by Rakuten Developers</a>
    </nav>
</footer>'''

STATIC_STYLE = '''<style>
*{box-sizing:border-box}body{margin:0;background:#f5f6f8;color:#222;font-family:-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif}header{background:#fff;padding:28px 16px;border-bottom:1px solid #ddd}header div,main,footer,.ranking-nav{max-width:760px;margin:auto}h1{margin:0 0 10px;font-size:28px}header p{margin:0;color:#666;line-height:1.7}.ranking-nav{padding:14px 12px 0;display:flex;gap:8px;flex-wrap:wrap}.ranking-nav a{background:#fff;color:#333;text-decoration:none;border:1px solid #ddd;border-radius:8px;padding:8px 11px;font-size:13px;font-weight:bold}main{padding:18px 12px 32px}section{background:#fff;padding:20px;margin-bottom:14px;border-radius:14px;box-shadow:0 2px 8px rgba(0,0,0,.04)}h2{margin:0 0 12px;font-size:20px}h3{margin:18px 0 8px;font-size:16px}p,li,dd,dt{line-height:1.8;font-size:14px}ul,ol{padding-left:22px}.note{border-left:4px solid #444;padding-left:12px;color:#555}.link{font-weight:bold}table{width:100%;border-collapse:collapse;margin:14px 0;font-size:13px}th,td{padding:10px;border:1px solid #ddd;text-align:left}th{background:#f7f8fa}footer{padding:18px 14px 40px;color:#666;font-size:12px;line-height:1.7}@media(max-width:520px){h1{font-size:24px}section{padding:16px}table{font-size:12px}}
</style>'''


def escape(value):
    return html.escape(str(value), quote=True)


def add_stylesheet(text):
    text = text.replace(TRUST_STYLESHEET + "\n", "").replace(TRUST_STYLESHEET, "")
    if "</head>" not in text:
        raise RuntimeError("</head> が見つかりません。")
    return text.replace("</head>", TRUST_STYLESHEET + "\n</head>", 1)


def replace_footer(text, path):
    updated, count = re.subn(r"<footer>.*?</footer>", FOOTER, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"footerを更新できません: {path}")
    return updated


def build_static_page(*, title, description, canonical, h1, lead, body):
    return f'''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="google-site-verification" content="xebuT18VaLulU2FGAl1MrnJnOgS4b1ZjrZcFaV45KyQ">
<meta name="description" content="{escape(description)}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{escape(canonical)}">
<title>{escape(title)}</title>
{STATIC_STYLE}
<link rel="stylesheet" href="/assets/seo-expansion.css">
{TRUST_STYLESHEET}
</head>
<body>
<header><div><h1>{escape(h1)}</h1><p>{escape(lead)}</p></div></header>
{BASE_NAV}
<main>
{body}
</main>
{FOOTER}
</body>
</html>
'''


def build_review_guide():
    body = '''<section>
<h2>星の数だけでは判断しにくい理由</h2>
<p>レビュー平均は商品の評価を短時間で確認できる便利な数字ですが、件数が少ないほど、数件の高評価・低評価で平均が大きく動きます。平均点とレビュー件数を一緒に見ることで、評価の高さと安定性を分けて考えられます。</p>
<table><thead><tr><th>例</th><th>レビュー平均</th><th>レビュー件数</th><th>読み取り方</th></tr></thead><tbody><tr><td>A</td><td>★4.80</td><td>15件</td><td>高評価だが、今後平均が動く可能性が比較的大きい</td></tr><tr><td>B</td><td>★4.60</td><td>3,000件</td><td>Aより平均は低いが、多数の評価が蓄積している</td></tr></tbody></table>
<p class="note">どちらが必ず優れているという意味ではありません。平均点の高さを優先するか、評価の蓄積を優先するかで選択が変わります。</p>
</section>
<section>
<h2>当サイトがベイズ補正を使う理由</h2>
<p>当サイトでは、レビュー件数が少ない商品の平均点を候補全体の平均へ少し近づける「ベイズ補正」を使用しています。レビューが十分に多い商品は実際の平均点に近く、少ない商品ほど候補全体の平均の影響を受けます。</p>
<p>ただし、ベイズ補正は音質や耐久性を測定するものではありません。レビュー数字の見かけ上の不安定さを抑え、同じ候補群を比べやすくする処理です。</p>
<p><a class="link" href="/earphones/methodology/">実際の式と候補抽出条件を見る →</a></p>
</section>
<section>
<h2>購入前に確認したい4つの手順</h2>
<ol><li><strong>目的を決める：</strong>総合、価格、種類、レビュー件数のどの軸を優先するか決めます。</li><li><strong>順位差を過大評価しない：</strong>星の差が小さい商品は、価格やレビュー件数も一緒に比較します。</li><li><strong>低評価レビューも確認する：</strong>接続、装着感、初期不良など、自分が避けたい問題が繰り返し書かれていないか確認します。</li><li><strong>楽天市場で最終確認する：</strong>対応機器、付属品、保証、送料、クーポン、在庫は購入時点の商品ページで確認します。</li></ol>
</section>
<section>
<h2>このデータで分かること・分からないこと</h2>
<div class="guide-columns"><div><h3>分かること</h3><ul><li>取得時点の価格</li><li>レビュー平均と件数</li><li>同じ候補群内での相対的な順位</li><li>価格帯・種類別の比較</li></ul></div><div><h3>分からないこと</h3><ul><li>実際の音質や装着感</li><li>長期間使用した耐久性</li><li>レビュー内容が自分にも当てはまるか</li><li>商品名に書かれた機能の実性能</li></ul></div></div>
<p class="note">当サイトは候補を絞るためのデータ比較サイトです。最終的な購入判断を代行するものではありません。</p>
</section>
<section class="static-actions"><h2>ランキングから候補を探す</h2><p><a class="primary-link" href="/">総合ランキングを見る →</a> <a class="secondary-link" href="/earphones/">目的別ランキングを選ぶ →</a></p></section>'''
    return build_static_page(
        title="イヤホンレビューの星と件数の読み方｜ランキング活用ガイド",
        description="イヤホンのレビュー平均とレビュー件数の違い、ベイズ補正の役割、購入前に確認したいポイントを分かりやすく解説します。",
        canonical=SITE + "/earphones/review-guide/",
        h1="イヤホンレビューの星と件数の読み方",
        lead="レビュー平均だけで決めず、件数・価格・低評価の内容も組み合わせて候補を絞るためのガイドです。",
        body=body,
    )


def build_privacy_page():
    if GA_MEASUREMENT_ID:
        analytics_text = '''当サイトは、利用状況を把握して改善するためGoogle Analytics 4を利用します。Google AnalyticsはCookie等を利用して閲覧情報を収集する場合があります。収集された情報はGoogleのプライバシーポリシーに基づいて管理されます。<a href="https://policies.google.com/privacy?hl=ja" target="_blank" rel="noopener">Googleプライバシーポリシー</a>もご確認ください。'''
    else:
        analytics_text = "現在、Google Analyticsによるアクセス解析は無効です。有効化する場合は、このページの記載も同時に更新します。"

    body = f'''<section><h2>基本方針</h2><p>当サイトは、取得する情報をサイトの運営・改善に必要な範囲で扱い、目的外に利用しないよう努めます。</p></section>
<section><h2>アクセス解析</h2><p>{analytics_text}</p></section>
<section><h2>広告・外部サービス</h2><p>当サイトは楽天アフィリエイトを利用しています。商品リンクを選択すると楽天市場へ移動し、楽天側の規約・プライバシーポリシーに基づいて情報が扱われます。当サイトは、楽天市場で入力される購入情報や決済情報を取得しません。</p><p>商品画像・価格・レビュー情報などは楽天市場の商品APIから取得しています。</p></section>
<section><h2>免責事項</h2><p>掲載情報は取得時点のものです。正確性の確保に努めますが、価格、在庫、仕様、保証、配送条件などの最新情報は購入前に楽天市場の商品ページでご確認ください。</p></section>
<section><h2>お問い合わせ</h2><p>掲載内容や本方針に関するご連絡は、<a class="link" href="/contact/">お問い合わせページ</a>からお願いします。</p></section>'''
    return build_static_page(
        title="プライバシーポリシー｜イヤホンランキング",
        description="イヤホンランキングにおけるアクセス解析、広告、外部サービス、個人情報の取り扱い方針を説明します。",
        canonical=SITE + "/privacy/",
        h1="プライバシーポリシー",
        lead="当サイトが利用するアクセス解析・広告・外部サービスと、情報の取り扱い方針を説明します。",
        body=body,
    )


def build_contact_page():
    contact_label = "GitHub Issuesで問い合わせる" if CONTACT_URL == DEFAULT_CONTACT_URL else "お問い合わせ窓口を開く"
    body = f'''<section><h2>お問い合わせの対象</h2><ul><li>掲載内容の誤りやリンク切れ</li><li>ランキング条件・計算方法について</li><li>権利関係や掲載情報について</li><li>その他、サイト運営に関するご連絡</li></ul></section>
<section><h2>お問い合わせ窓口</h2><p>現在の無料運用では、公開リポジトリの問い合わせ窓口を利用しています。</p><p><a class="primary-link" href="{escape(CONTACT_URL)}" target="_blank" rel="noopener">{escape(contact_label)} →</a></p><p class="note">公開画面に氏名、住所、電話番号、注文番号などの個人情報を書き込まないでください。返信や対応をお約束するものではありません。</p></section>
<section><h2>運営者</h2><p>{escape(OPERATOR_NAME)}</p><p>ランキングの目的・編集方針は、<a class="link" href="/about/">このサイトについて</a>をご確認ください。</p></section>'''
    return build_static_page(
        title="お問い合わせ｜イヤホンランキング",
        description="イヤホンランキングの掲載内容、リンク、ランキング基準、権利関係などに関するお問い合わせ窓口です。",
        canonical=SITE + "/contact/",
        h1="お問い合わせ",
        lead="掲載内容の誤り、リンク切れ、ランキング基準などに関するご連絡を受け付けています。",
        body=body,
    )


def add_decision_guide(text, path):
    text = GUIDE_RE.sub("\n", text)
    guide = '''<!-- decision-guide:start -->
<section class="decision-guide" aria-labelledby="decision-guide-title">
    <div><span class="section-kicker">順位を見る前に</span><h2 id="decision-guide-title">このランキングの使い方</h2></div>
    <div class="decision-guide-grid">
        <div><strong>1. 順位</strong><p>補正後の評価、またはレビュー件数の基準で候補を絞ります。</p></div>
        <div><strong>2. 数字</strong><p>星、レビュー件数、価格とTOP10内での位置を一緒に確認します。</p></div>
        <div><strong>3. 最終確認</strong><p>音質・装着感は未検証です。仕様や保証は楽天市場で確認します。</p></div>
    </div>
    <a class="decision-guide-link" href="/earphones/review-guide/">レビューの星と件数の読み方 →</a>
</section>
<!-- decision-guide:end -->'''
    marker = '<article class="card">'
    position = text.find(marker)
    if position < 0:
        raise RuntimeError(f"商品カードが見つかりません: {path}")
    text = text[:position] + guide + "\n" + text[position:]
    if text.count("<!-- decision-guide:start -->") != 1:
        raise RuntimeError(f"選び方ガイドの追加に失敗しました: {path}")
    return text


def add_operator_info(text):
    text = OPERATOR_RE.sub("\n", text)
    block = f'''<!-- operator-info:start -->
<section class="operator-info"><h2>運営情報</h2><dl><div><dt>運営者</dt><dd>{escape(OPERATOR_NAME)}</dd></div><div><dt>サイトの目的</dt><dd>楽天市場のイヤホン候補を、取得可能な客観データで比較しやすくすること</dd></div><div><dt>お問い合わせ</dt><dd><a class="link" href="/contact/">お問い合わせページ</a></dd></div><div><dt>情報の取り扱い</dt><dd><a class="link" href="/privacy/">プライバシーポリシー</a></dd></div></dl></section>
<!-- operator-info:end -->'''
    marker = "<section><h2>今後の方針</h2>"
    if marker not in text:
        raise RuntimeError("aboutページの挿入位置が見つかりません。")
    return text.replace(marker, block + "\n" + marker, 1)


def add_guide_to_hub(text):
    if 'href="/earphones/review-guide/" class="hub-method-link"' in text:
        return text
    marker = '<a href="/earphones/methodology/" class="hub-method-link">ランキング基準を詳しく見る →</a>'
    replacement = marker + '\n<a href="/earphones/review-guide/" class="hub-method-link">レビューの読み方を見る →</a>'
    if marker not in text:
        raise RuntimeError("ランキング一覧ページのガイド導線を追加できません。")
    return text.replace(marker, replacement, 1)


for path in PAGES:
    if not path.exists():
        raise RuntimeError(f"信頼性改善の対象ページがありません: {path}")
    text = path.read_text(encoding="utf-8")
    text = add_stylesheet(text)
    text = replace_footer(text, path)
    if path in RANKING_PAGES:
        text = add_decision_guide(text, path)
    if path == Path("public/about/index.html"):
        text = add_operator_info(text)
    if path == Path("public/earphones/index.html"):
        text = add_guide_to_hub(text)
    path.write_text(text, encoding="utf-8")

STATIC_PAGES = {
    Path("public/earphones/review-guide/index.html"): build_review_guide(),
    Path("public/privacy/index.html"): build_privacy_page(),
    Path("public/contact/index.html"): build_contact_page(),
}

for path, content in STATIC_PAGES.items():
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

print("Trust pages / buyer guidance / consistent footer: OK")
