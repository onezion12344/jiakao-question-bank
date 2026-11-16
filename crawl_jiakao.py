#!/usr/bin/env python3
"""
crawl_jiakao.py — full extraction of the 驾考宝典 (jiakaobaodian.com) question bank.

API map (reverse-engineered 2026-11-16, all endpoints live-verified):
  _r signature  : "1" + str(abs(int(time_ms * random * 10000))) + zfill(3)(digitsum+len)
  chapter tree  : GET https://jk-tiku.kakamobi.cn/api/web/practise/list-chapter.htm
                  params: carType, course, cityCode  -> [{id, chapter, count, title, ...}]
  chapter ids   : GET https://jk-tiku.kakamobi.cn/api/web/practise/chapter.htm
                  params: carType, course, chapterId, cityCode -> {.., questionList: [id..<=100]}
  tag id lists  : GET https://api2.jiakaobaodian.com/api/open/question/list-by-tag.htm
                  params: _r, cityCode, course, tagId, carType -> [id...]  (FULL list, uncapped)
  batch details : POST https://api2.jiakaobaodian.com/api/open/question/question-list.htm?_r=...
                  form: questionIds=id,id,...   (~905 verified in one shot)
  answer bitmask: 16=A 32=B 64=C 128=D (multi-select sums bits)
"""
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request

OUT = os.path.expanduser(os.environ.get("JIAKAO_DATA", "~/jiakao/data"))
os.makedirs(OUT, exist_ok=True)

API2 = "https://api2.jiakaobaodian.com/api/open"
TIKU = "https://jk-tiku.kakamobi.cn/api/web"
CITY = "110000"  # Beijing — includes local question sets in chapter trees

CARTYPES = ["car", "bus", "truck", "moto", "keyun", "huoyun", "weixian", "jiaolian", "chuzu"]
COURSES = ["kemu1", "kemu3"]  # kemu3 internally = 科目四 (安全文明常识)
TAG_SWEEP_MAX = 60

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def gen_r() -> str:
    """Reproduces the JS: i=abs(parseInt(Date.now()*random*1e4)); checksum=digitsum+len zfill(3)."""
    i = str(abs(int(time.time() * 1000 * random.random() * 10000)))
    t = sum(int(c) for c in i) + len(i)
    return "1" + i + str(t).zfill(3)


def _req(url: str, params: dict, method: str = "GET", tries: int = 4) -> dict:
    qs = urllib.parse.urlencode(params)
    if method == "GET":
        full = f"{url}?{qs}"
        data = None
    else:
        full = url
        data = qs.encode()
    last_err = None
    for k in range(tries):
        try:
            r = urllib.request.Request(full, data=data, method=method)
            r.add_header("User-Agent", UA)
            r.add_header("Referer", "https://www.jiakaobaodian.com/")
            if method == "POST":
                r.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
            with urllib.request.urlopen(r, timeout=60) as resp:
                body = resp.read().decode("utf-8", "replace")
            d = json.loads(body)
            if d.get("success") is False:
                raise RuntimeError(f"api error {d.get('errorCode')}: {d.get('message')}")
            return d
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.5 * (k + 1))
    raise RuntimeError(f"FAILED {method} {url} {last_err}")


def get(url, **params):
    params.setdefault("_r", gen_r())
    return _req(url, params, "GET")


def post(url, **params):
    params.setdefault("_r", gen_r())
    return _req(url, params, "POST")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def collect_ids(car_type: str, course: str) -> tuple[list, dict]:
    """Union of chapter ids + full tag id lists. Returns (sorted ids, meta)."""
    ids = set()
    meta = {"chapters": [], "tags": {}}

    try:
        chapters = get(f"{TIKU}/practise/list-chapter.htm", carType=car_type,
                       course=course, cityCode=CITY).get("data") or []
    except RuntimeError as e:
        log(f"  list-chapter failed: {e}")
        chapters = []
    for ch in chapters:
        meta["chapters"].append({k: ch.get(k) for k in ("id", "chapter", "count", "title")})
        time.sleep(0.35)
        try:
            d = get(f"{TIKU}/practise/chapter.htm", carType=car_type, course=course,
                    chapterId=ch["id"], cityCode=CITY).get("data") or {}
            ids.update(d.get("questionList") or [])
        except RuntimeError as e:
            log(f"  chapter {ch['id']} failed: {e}")
    log(f"  chapters: {len(chapters)}, ids so far: {len(ids)}")

    for tag in range(0, TAG_SWEEP_MAX + 1):
        time.sleep(0.35)
        try:
            got = get(f"{API2}/question/list-by-tag.htm", cityCode="511300", course=course,
                      tagId=tag, carType=car_type).get("data") or []
        except RuntimeError as e:
            log(f"  tag {tag} failed: {e}")
            continue
        if got:
            meta["tags"][str(tag)] = len(got)
            ids.update(got)
    log(f"  tags hit: {meta['tags']}, total unique ids: {len(ids)}")
    return sorted(ids), meta


def fetch_details(ids: list, batch: int = 400) -> list:
    out = []
    for i in range(0, len(ids), batch):
        chunk = ids[i:i + batch]
        time.sleep(0.5)
        d = post(f"{API2}/question/question-list.htm", questionIds=",".join(map(str, chunk)))
        rows = d.get("data") or []
        out.extend(rows)
        log(f"  details {i + len(chunk)}/{len(ids)} (+{len(rows)})")
    return out


def main():
    summary = {}
    for car_type in CARTYPES:
        for course in COURSES:
            name = f"{car_type}-{course}"
            f_ids = os.path.join(OUT, f"ids-{name}.json")
            f_q = os.path.join(OUT, f"questions-{name}.json")
            f_m = os.path.join(OUT, f"meta-{name}.json")
            if os.path.exists(f_q):
                log(f"skip {name} (done)")
                continue
            log(f"=== {name} ===")
            ids, meta = collect_ids(car_type, course)
            if not ids:
                log(f"  no ids for {name}, skipping")
                continue
            json.dump(ids, open(f_ids, "w"))
            questions = fetch_details(ids)
            json.dump(questions, open(f_q, "w"), ensure_ascii=False)
            json.dump(meta, open(f_m, "w"), ensure_ascii=False)
            ok = len(questions) == len(ids)
            summary[name] = {"ids": len(ids), "fetched": len(questions), "chapters": len(meta["chapters"])}
            log(f"  saved {len(questions)}/{len(ids)} {'OK' if ok else 'MISMATCH'}")
    json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), ensure_ascii=False, indent=1)
    log(f"DONE {json.dumps(summary, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
