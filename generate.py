import os
import urllib.parse
from playwright.sync_api import sync_playwright


SITE_URL = "https://otoku-ranking.pages.dev/"

API_URL = (
    "https://openapi.rakuten.co.jp/"
    "ichibams/api/IchibaItem/Search/20260701"
)


APPLICATION_ID = os.getenv(
    "RAKUTEN_APPLICATION_ID",
    ""
).strip()

ACCESS_KEY = os.getenv(
    "RAKUTEN_ACCESS_KEY",
    ""
).strip()

AFFILIATE_ID = os.getenv(
    "RAKUTEN_AFFILIATE_ID",
    ""
).strip()


if not APPLICATION_ID:
    raise RuntimeError(
        "RAKUTEN_APPLICATION_ID がありません"
    )

if not ACCESS_KEY:
    raise RuntimeError(
        "RAKUTEN_ACCESS_KEY がありません"
    )

if not AFFILIATE_ID:
    raise RuntimeError(
        "RAKUTEN_AFFILIATE_ID がありません"
    )


params = {
    "applicationId": APPLICATION_ID,
    "accessKey": ACCESS_KEY,
    "affiliateId": AFFILIATE_ID,
    "format": "json",
    "formatVersion": 2,
    "keyword": "イヤホン",
    "hits": 1,
}


api_url = (
    API_URL
    + "?"
    + urllib.parse.urlencode(params)
)


print("")
print("====================================")
print("楽天API 接続診断開始")
print("====================================")
print("")


with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True
    )

    context = browser.new_context(
        locale="ja-JP"
    )

    page = context.new_page()

    page.set_default_timeout(
        15000
    )


    # ---------------------------------
    # 実際のAPIリクエストを監視
    # ---------------------------------

    request_info = {
        "seen": False,
        "origin": "",
        "referer": "",
        "sec_fetch_site": "",
    }

    response_info = {
        "seen": False,
        "status": None,
    }


    def handle_request(request):

        if not request.url.startswith(
            API_URL
        ):
            return

        request_info["seen"] = True

        headers = request.all_headers()

        request_info["origin"] = (
            headers.get(
                "origin",
                "(なし)"
            )
        )

        request_info["referer"] = (
            headers.get(
                "referer",
                "(なし)"
            )
        )

        request_info["sec_fetch_site"] = (
            headers.get(
                "sec-fetch-site",
                "(なし)"
            )
        )


    def handle_response(response):

        if not response.url.startswith(
            API_URL
        ):
            return

        response_info["seen"] = True
        response_info["status"] = (
            response.status
        )


    page.on(
        "request",
        handle_request
    )

    page.on(
        "response",
        handle_response
    )


    # ---------------------------------
    # 1. 自分のサイトを開く
    # ---------------------------------

    print(
        "1. 公開サイトを開いています..."
    )

    site_response = page.goto(
        SITE_URL,
        wait_until="domcontentloaded",
        timeout=15000,
    )


    if site_response is None:

        print(
            "公開サイト: 応答なし"
        )

    else:

        print(
            "公開サイト HTTP:",
            site_response.status
        )


    # ---------------------------------
    # 2. ページ内fetchでAPIを呼ぶ
    #
    # 10秒で強制停止する
    # ---------------------------------

    print("")
    print(
        "2. 楽天APIを呼び出しています..."
    )


    fetch_result = page.evaluate(
        """
        async (url) => {

            const controller =
                new AbortController();

            const timer =
                setTimeout(
                    () => controller.abort(),
                    10000
                );

            try {

                const response =
                    await fetch(
                        url,
                        {
                            method: "GET",
                            cache: "no-store",
                            credentials: "omit",
                            signal: controller.signal
                        }
                    );

                return {
                    type: "response",
                    status: response.status
                };

            } catch (error) {

                return {
                    type: "error",
                    message: String(error)
                };

            } finally {

                clearTimeout(timer);

            }

        }
        """,
        api_url,
    )


    # ---------------------------------
    # 診断結果
    # ---------------------------------

    print("")
    print("====================================")
    print("診断結果")
    print("====================================")

    print(
        "APIリクエスト発生:",
        request_info["seen"]
    )

    print(
        "Origin:",
        request_info["origin"]
    )

    print(
        "Referer:",
        request_info["referer"]
    )

    print(
        "Sec-Fetch-Site:",
        request_info["sec_fetch_site"]
    )

    print(
        "APIレスポンス発生:",
        response_info["seen"]
    )

    print(
        "HTTP Status:",
        response_info["status"]
    )

    print(
        "ブラウザfetch結果:",
        fetch_result
    )

    print("====================================")
    print("診断終了")
    print("====================================")
    print("")

    browser.close()
