from pathlib import Path
import json
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET


SITE_HOST = "otoku-ranking.pages.dev"
SITE_ORIGIN = f"https://{SITE_HOST}"
ENDPOINT = "https://api.indexnow.org/indexnow"
KEY_FILE = Path("public/fb6c0bc82a2306cdb2d15bc398deffe4.txt")
SITEMAP_FILE = Path("public/sitemap.xml")
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def load_key():
    key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not (8 <= len(key) <= 128):
        raise RuntimeError("IndexNow key length is invalid")
    return key


def load_dynamic_urls():
    root = ET.parse(SITEMAP_FILE).getroot()
    urls = []
    for entry in root.findall("sm:url", SITEMAP_NS):
        loc = entry.findtext("sm:loc", default="", namespaces=SITEMAP_NS).strip()
        lastmod = entry.findtext("sm:lastmod", default="", namespaces=SITEMAP_NS).strip()
        if loc and lastmod and loc.startswith(SITE_ORIGIN + "/"):
            urls.append(loc)
    if not urls:
        raise RuntimeError("No dynamic URLs with lastmod were found in sitemap.xml")
    return urls


def submit():
    key = load_key()
    urls = load_dynamic_urls()
    payload = {
        "host": SITE_HOST,
        "key": key,
        "keyLocation": f"{SITE_ORIGIN}/{KEY_FILE.name}",
        "urlList": urls,
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"IndexNow submission failed: HTTP {status}: {body}") from exc

    if status not in (200, 202):
        raise RuntimeError(f"Unexpected IndexNow response: HTTP {status}")

    print(f"IndexNow accepted {len(urls)} updated URLs (HTTP {status})")


if __name__ == "__main__":
    submit()
