# otoku-ranking

楽天市場APIの商品データから、イヤホンの高評価・価格帯・種類別ランキングを毎日生成する静的サイトです。

## GitHub Actions設定

Repository secrets:

- `RAKUTEN_APPLICATION_ID`
- `RAKUTEN_ACCESS_KEY`
- `RAKUTEN_AFFILIATE_ID`

Repository variables（任意）:

- `GA_MEASUREMENT_ID`: GA4の測定ID（`G-`から始まる値）。未設定時はアクセス解析を読み込みません。
- `SITE_OPERATOR_NAME`: 「このサイトについて」に表示する運営者名。未設定時は「イヤホンランキング運営者」です。
- `SITE_CONTACT_URL`: 問い合わせ窓口のHTTPS URL。未設定時はGitHub Issuesを使用します。

ランキングページ、信頼性ページ、構造化データ、サイトマップ、アクセス解析コードは `.github/workflows/update.yml` の日次処理で再生成されます。
