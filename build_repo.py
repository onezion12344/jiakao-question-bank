#!/usr/bin/env python3
"""
build_repo.py — transform raw crawled data into the clean GitHub-repo layout.

Input : ~/jiakao/data/questions-{carType}-{course}.json  (raw API rows)
Output: ~/jiakao/repo/
  clean/{carType}-{course}.ndjson   one question per line:
        {id, chapter, chapterTitle, type, question, options[], answer[], explain,
         conciseExplain, difficulty, wrongRate, media}
  clean/media-manifest.json         all distinct media URLs + counts
  index.json                        per-set stats
"""
import glob
import hashlib
import json
import os
import re
import time
import urllib.parse
from collections import Counter

DATA = os.path.expanduser(os.environ.get("JIAKAO_DATA", "~/jiakao/data"))
REPO = os.path.expanduser(os.environ.get("JIAKAO_REPO", "~/jiakao/repo"))
TODAY = os.environ.get("JIAKAO_DATE") or time.strftime("%Y-%m-%d", time.gmtime())
os.makedirs(os.path.join(REPO, "clean"), exist_ok=True)

COURSE_NAMES = {"kemu1": "科目一", "kemu3": "科目四", "zigezheng": "从业资格证"}
CAR_NAMES = {
    "car": "小车(C1/C2/C3)", "bus": "客车", "truck": "货车(A2/B2)",
    "moto": "摩托车", "keyun": "客运", "huoyun": "货运", "weixian": "危化品",
    "jiaolian": "教练员", "chuzu": "出租车",
}

ANSWER_BITS = [(16, "A"), (32, "B"), (64, "C"), (128, "D"), (256, "E"), (512, "F"), (1024, "G"), (2048, "H")]
OPT_KEYS = ["optionA", "optionB", "optionC", "optionD", "optionE", "optionF", "optionG", "optionH"]


def clean_html(s):
    if not s:
        return ""
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip()


def to_answer_letters(bits):
    return [letter for bit, letter in ANSWER_BITS if bits & bit]


def media_relpath(url, basename_counts):
    """Stable repo-relative path. CDN reuses filenames (image-24.jpg) across date
    directories for *different* images, so colliding basenames get a URL hash."""
    base = os.path.basename(urllib.parse.urlparse(url).path) or "x"
    if basename_counts[base] > 1:
        key = hashlib.sha1(url.encode()).hexdigest()[:10]
        return f"media/{key[0]}/{key}-{base}"
    return f"media/{base[0].lower()}/{base}"


def qid_key(r):
    try:
        return int(r.get("questionId") or r.get("id") or 0)
    except (TypeError, ValueError):
        return 0


def update_readme(index, total, media_files):
    """Rewrite the 题量 table + crawl date in README.md so they never go stale."""
    path = os.path.join(REPO, "README.md")
    if not os.path.exists(path):
        return
    text = open(path, encoding="utf-8").read()
    rows = "\n".join(
        "| {} | {} | {} |".format(s["carName"], s["courseName"], s["questions"])
        for s in index["sets"].values()
    )
    block = ("## 题量\n\n| 车型 | 科目 | 题量 |\n|---|---|---|\n" + rows +
             f"\n\n**合计 {total} 题**，{media_files:,} 张配图"
             f"（~100MB，`media/` 已本地化）。")
    new = re.sub(r"## 题量\n.*?(?=\n## )", block + "\n", text, count=1, flags=re.S)
    new = re.sub(r"数据于 \d{4}-\d{2}-\d{2}", f"数据于 {TODAY}", new)
    if new != text:
        open(path, "w", encoding="utf-8").write(new)
        print("README updated")


def main():
    index = {"source": "驾考宝典 (jiakaobaodian.com) via api2.jiakaobaodian.com",
             "crawled": TODAY, "sets": {}}
    media_counts = Counter()
    chapter_titles = {}

    # chapter titles from meta files
    for f in glob.glob(os.path.join(DATA, "meta-*.json")):
        for ch in json.load(open(f)).get("chapters", []):
            chapter_titles[(f.split("meta-")[1][:-5], ch["id"])] = ch.get("title", "")

    for fq in sorted(glob.glob(os.path.join(DATA, "questions-*.json"))):
        name = os.path.basename(fq)[len("questions-"):-5]
        car_type, course = name.rsplit("-", 1)
        rows = json.load(open(fq))
        rows.sort(key=qid_key)  # deterministic order -> real diffs between refreshes
        out = open(os.path.join(REPO, "clean", f"{name}.ndjson"), "w", encoding="utf-8")
        seen = set()
        stats = Counter()
        for r in rows:
            qid = r.get("questionId") or r.get("id")
            if qid in seen:
                continue
            seen.add(qid)
            options = [(k[-1], r[k]) for k in OPT_KEYS if r.get(k)]
            letters = to_answer_letters(r.get("answer") or 0)
            media = r.get("mediaContent") or ""
            if media:
                media_counts[media] += 1
            rec = {
                "id": qid,
                "carType": car_type,
                "course": course,
                "chapterId": r.get("chapterId"),
                "type": "判断题" if r.get("optionType") == 2 or len(options) == 2 else "单选题",
                "question": (r.get("question") or "").strip(),
                "options": [{"letter": l, "text": t} for l, t in options],
                "answer": letters,
                "explain": clean_html(r.get("explain") or ""),
                "conciseExplain": clean_html(r.get("conciseExplain") or ""),
                "difficulty": r.get("difficulty"),
                "wrongRate": r.get("wrongRate"),
                "media": media or None,
                "mediaType": ("image" if (r.get("mediaType") or 0) == 1 else
                              "video" if (r.get("mediaType") or 0) == 2 else None),
            }
            stats[rec["type"]] += 1
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        out.close()
        index["sets"][name] = {
            "carType": car_type, "carName": CAR_NAMES.get(car_type, car_type),
            "course": course, "courseName": COURSE_NAMES[course],
            "questions": len(seen), "types": dict(stats),
        }
        print(f"{name}: {len(seen)} questions ({dict(stats)})")

    basename_counts = Counter(os.path.basename(urllib.parse.urlparse(u).path) for u in media_counts)
    media_manifest = {u: {"file": media_relpath(u, basename_counts), "count": c}
                      for u, c in sorted(media_counts.items())}
    json.dump(media_manifest, open(os.path.join(REPO, "clean", "media-manifest.json"), "w"),
              ensure_ascii=False, indent=1)
    index["mediaImages"] = len(media_manifest)
    json.dump(index, open(os.path.join(REPO, "index.json"), "w"), ensure_ascii=False, indent=1)
    print(f"distinct media files: {len(media_manifest)}")
    total = sum(s["questions"] for s in index["sets"].values())
    print("total:", total)
    # count distinct local image files, not URLs: colliding CDN basenames were split
    update_readme(index, total, len({v["file"] for v in media_manifest.values()}))


if __name__ == "__main__":
    main()
