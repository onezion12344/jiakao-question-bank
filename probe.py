#!/usr/bin/env python3
"""
probe.py — fail fast if the Chinese endpoints are unreachable from the runner
or start rejecting the _r signature. Runs before the ~40 min crawl.
"""
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def gen_r():
    i = str(abs(int(time.time() * 1000 * random.random() * 10000)))
    return "1" + i + str(sum(int(c) for c in i) + len(i)).zfill(3)


def probe(name, url, params):
    params = dict(params, _r=gen_r())
    full = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full, headers={
        "User-Agent": UA, "Referer": "https://www.jiakaobaodian.com/"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            code = resp.status
    except Exception as e:  # noqa: BLE001
        print(f"FAIL {name}: {e}")
        return False
    dt = time.time() - t0
    try:
        d = json.loads(body.decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001
        print(f"FAIL {name}: HTTP {code}, non-JSON body {body[:120]!r} ({dt:.1f}s)")
        return False
    ok = code == 200 and d.get("success") is not False and d.get("data") is not None
    n = len(d.get("data") or []) if isinstance(d.get("data"), list) else "obj"
    print(f"{'OK  ' if ok else 'FAIL'} {name}: HTTP {code} in {dt:.1f}s, items={n}, "
          f"errorCode={d.get('errorCode')}")
    return ok


def media_probe():
    """Fetch the first real image from the manifest — a 403 on the CDN root is normal,
    a 403 on an object means the runner's IP is being blocked."""
    path = os.path.join(os.environ.get("JIAKAO_REPO", "."), "clean", "media-manifest.json")
    url = None
    if os.path.exists(path):
        keys = sorted(json.load(open(path)))
        if keys:
            url = keys[0]
    if not url:
        print("WARN no media-manifest.json — skipping image check")
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Referer": "https://www.jiakaobaodian.com/"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            blob = resp.read(2048)
            print(f"OK   media object: HTTP {resp.status}, {len(blob)} bytes, "
                  f"{resp.headers.get('Content-Type')}")
            return len(blob) > 0
    except Exception as e:  # noqa: BLE001
        print(f"FAIL media object: {e}")
        return False


def main():
    checks = [
        ("api2 list-by-tag", "https://api2.jiakaobaodian.com/api/open/question/list-by-tag.htm",
         {"cityCode": "511300", "course": "kemu1", "tagId": 1, "carType": "car"}),
        ("tiku list-chapter", "https://jk-tiku.kakamobi.cn/api/web/practise/list-chapter.htm",
         {"carType": "car", "course": "kemu1", "cityCode": "110000"}),
    ]
    results = [probe(*c) for c in checks]
    results.append(media_probe())
    if not all(results):
        print("PROBE FAILED — GitHub runner cannot reach the API. Do not crawl.")
        sys.exit(1)
    print("PROBE OK")


if __name__ == "__main__":
    main()
