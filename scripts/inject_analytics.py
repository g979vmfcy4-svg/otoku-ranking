import json
import os
import re
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
    Path("public/earphones/review-guide/index.html"),
    Path("public/about/index.html"),
    Path("public/contact/index.html"),
    Path("public/privacy/index.html"),
]

SCRIPT_TAG = '<script defer src="/assets/analytics.js"></script>'
ANALYTICS_PATH = Path("public/assets/analytics.js")
GA_MEASUREMENT_ID = os.getenv("GA_MEASUREMENT_ID", "").strip()

if GA_MEASUREMENT_ID and not re.fullmatch(r"G-[A-Z0-9]+", GA_MEASUREMENT_ID, re.IGNORECASE):
    raise RuntimeError("GA_MEASUREMENT_ID の形式が不正です。G- から始まる測定IDを指定してください。")

analytics = ANALYTICS_PATH.read_text(encoding="utf-8")
analytics, count = re.subn(
    r'const GA_MEASUREMENT_ID = .*?;',
    f'const GA_MEASUREMENT_ID = {json.dumps(GA_MEASUREMENT_ID)};',
    analytics,
    count=1,
)
if count != 1:
    raise RuntimeError("analytics.js のGA測定ID設定箇所が見つかりません。")
ANALYTICS_PATH.write_text(analytics, encoding="utf-8")

for path in PAGES:
    text = path.read_text(encoding="utf-8")

    if SCRIPT_TAG not in text:
        if "</body>" not in text:
            raise RuntimeError(f"</body> が見つかりません: {path}")
        text = text.replace("</body>", SCRIPT_TAG + "\n</body>", 1)

    if text.count(SCRIPT_TAG) != 1:
        raise RuntimeError(f"analytics.js の読み込み数が想定外です: {path}")

    path.write_text(text, encoding="utf-8")

status = "enabled" if GA_MEASUREMENT_ID else "disabled (GA_MEASUREMENT_ID is not set)"
print(f"Analytics script injection: OK / {status}")
