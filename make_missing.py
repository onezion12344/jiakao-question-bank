#!/usr/bin/env python3
"""
make_missing.py — diff collected ids against fetched details and write data/missing-*.json
for repair_missing.py. Skips sets whose crawl never produced a questions file (failed run),
so a broken crawl cannot turn into thousands of single-question requests.
"""
import glob
import json
import os

DATA = os.path.expanduser(os.environ.get("JIAKAO_DATA", "~/jiakao/data"))


def main():
    total = 0
    for f in sorted(glob.glob(os.path.join(DATA, "ids-*.json"))):
        name = os.path.basename(f)[len("ids-"):-5]
        fq = os.path.join(DATA, f"questions-{name}.json")
        if not os.path.exists(fq):
            print(f"{name}: no questions file, skipped")
            continue
        ids = set(json.load(open(f)))
        rows = json.load(open(fq))
        have = {q.get("questionId") or q.get("id") for q in rows}
        missing = sorted(ids - have)
        json.dump(missing, open(os.path.join(DATA, f"missing-{name}.json"), "w"))
        total += len(missing)
        print(f"{name}: {len(ids)} ids, {len(have)} fetched, missing {len(missing)}")
    print(f"total missing: {total}")


if __name__ == "__main__":
    main()
