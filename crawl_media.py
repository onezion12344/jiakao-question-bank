#!/usr/bin/env python3
"""
crawl_media.py — download all distinct question images referenced by the bank
into repo/media/ (sharded a/b/c directories by first char of filename key).
Resumable: skips files already present with nonzero size.
"""
import json
import os
import time
import urllib.parse
import urllib.request

REPO = os.path.expanduser(os.environ.get("JIAKAO_REPO", "~/jiakao/repo"))
MANIFEST = os.path.join(REPO, "clean", "media-manifest.json")
MEDIA = os.path.join(REPO, "media")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"


def shard_for(url):
    key = os.path.basename(urllib.parse.urlparse(url).path) or "x"
    return key[0].lower()


def main():
    manifest = json.load(open(MANIFEST))
    urls = sorted(manifest.keys())
    print(f"{len(urls)} distinct media files")
    ok = err = skip = 0
    for i, url in enumerate(urls):
        d = os.path.join(MEDIA, shard_for(url))
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, os.path.basename(urllib.parse.urlparse(url).path))
        if os.path.exists(path) and os.path.getsize(path) > 0:
            skip += 1
            continue
        for attempt in range(3):
            try:
                r = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.jiakaobaodian.com/"})
                with urllib.request.urlopen(r, timeout=30) as resp:
                    blob = resp.read()
                tmp = path + ".part"
                open(tmp, "wb").write(blob)
                os.replace(tmp, path)
                ok += 1
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 2:
                    err += 1
                    print(f"ERR {url}: {e}", flush=True)
                time.sleep(1.0 * (attempt + 1))
        if (i + 1) % 200 == 0:
            print(f"[{i + 1}/{len(urls)}] ok={ok} skip={skip} err={err}", flush=True)
    print(f"DONE ok={ok} skip={skip} err={err}")


if __name__ == "__main__":
    main()
