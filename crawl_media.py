#!/usr/bin/env python3
"""
crawl_media.py — download every distinct question image into <repo>/media/.

Paths come from clean/media-manifest.json (URL -> {"file", "count"}). When two CDN
URLs share a basename but are different images, the manifest gives both a
sha1-prefixed name so they cannot overwrite each other.

Resumable: files already present with nonzero size are skipped.
--prune: delete files under media/ that the manifest does not reference.
"""
import argparse
import json
import os
import time
import urllib.parse
import urllib.request

REPO = os.path.expanduser(os.environ.get("JIAKAO_REPO", "~/jiakao/repo"))
MANIFEST = os.path.join(REPO, "clean", "media-manifest.json")
MEDIA = os.path.join(REPO, "media")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"


def legacy_relpath(url):
    base = os.path.basename(urllib.parse.urlparse(url).path) or "x"
    return f"media/{base[0].lower()}/{base}"


def entry_relpath(url, val):
    if isinstance(val, dict) and val.get("file"):
        return val["file"]
    return legacy_relpath(url)


def prune(expected):
    removed = 0
    for root, _, files in os.walk(MEDIA):
        for f in files:
            p = os.path.normpath(os.path.join(root, f))
            if p not in expected:
                os.remove(p)
                removed += 1
    for root, dirs, files in os.walk(MEDIA, topdown=False):
        if not dirs and not files and os.path.normpath(root) != os.path.normpath(MEDIA):
            os.rmdir(root)
    print(f"pruned {removed} files not referenced by the manifest")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prune", action="store_true")
    args = ap.parse_args()

    manifest = json.load(open(MANIFEST))
    items = [(u, entry_relpath(u, v)) for u, v in manifest.items()]
    print(f"{len(items)} distinct media files")
    ok = err = skip = 0
    for i, (url, rel) in enumerate(items):
        path = os.path.join(REPO, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
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
            print(f"[{i + 1}/{len(items)}] ok={ok} skip={skip} err={err}", flush=True)
    print(f"DONE ok={ok} skip={skip} err={err}")
    if args.prune:
        prune({os.path.normpath(os.path.join(REPO, rel)) for _, rel in items})


if __name__ == "__main__":
    main()
