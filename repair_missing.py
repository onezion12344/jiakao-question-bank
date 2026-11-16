#!/usr/bin/env python3
"""
repair_missing.py — fetch questions the api2 batch endpoint returned empty for,
via the tiku host single-question endpoint (practise/view.htm), one by one.
Runs after crawl_jiakao.py; merges results into the same questions-*.json file.
"""
import glob
import json
import os
import time

DATA = os.path.expanduser(os.environ.get("JIAKAO_DATA", "~/jiakao/data"))
TIKU = "https://jk-tiku.kakamobi.cn/api/web"


def gen_r():
    import random
    i = str(abs(int(time.time() * 1000 * random.random() * 10000)))
    t = sum(int(c) for c in i) + len(i)
    return "1" + i + str(t).zfill(3)


def fetch_one(car_type, course, qid):
    import urllib.parse
    import urllib.request
    url = (f"{TIKU}/practise/view.htm?_r={gen_r()}&carType={car_type}&course={course}"
           f"&questionId={qid}&cityCode=110000")
    r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.jiakaobaodian.com/"})
    with urllib.request.urlopen(r, timeout=30) as resp:
        d = json.loads(resp.read().decode())
    return d.get("data") or None


def main():
    for f in sorted(glob.glob(os.path.join(DATA, "missing-*.json"))):
        name = os.path.basename(f)[len("missing-"):-5]
        car_type, course = name.rsplit("-", 1)
        missing = json.load(open(f))
        fq = os.path.join(DATA, f"questions-{name}.json")
        rows = json.load(open(fq)) if os.path.exists(fq) else []
        have = {q.get("questionId") or q.get("id") for q in rows}
        todo = [m for m in missing if m not in have]
        if not todo:
            continue
        print(f"{name}: repairing {len(todo)} questions")
        got = dead = 0
        for n, qid in enumerate(todo):
            time.sleep(0.15)
            try:
                d = fetch_one(car_type, course, qid)
            except Exception as e:  # noqa: BLE001
                d = None
                print(f"  ERR {qid}: {e}")
            if d and d.get("question"):
                d.setdefault("questionId", qid)
                rows.append(d)
                got += 1
            else:
                dead += 1
            if (n + 1) % 25 == 0:  # incremental save — never lose progress
                json.dump(rows, open(fq, "w"), ensure_ascii=False)
                print(f"  [{n + 1}/{len(todo)}] recovered={got} dead={dead}", flush=True)
        json.dump(rows, open(fq, "w"), ensure_ascii=False)
        json.dump([], open(f, "w"))  # mark repaired
        print(f"  recovered {got}, truly dead {dead}")


if __name__ == "__main__":
    main()
