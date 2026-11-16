#!/usr/bin/env python3
"""
crawl_jiakao_round2.py — second pass for the 5 special carTypes whose course is
'zigezheng' (从业资格证: 客运/货运/危化品/教练员/出租车从业资格), plus kemu1/kemu3
re-check for those types in case some questions exist under those course names too.
Reuses crawl_jiakao.py via import.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crawl_jiakao import collect_ids, fetch_details, log, OUT, CARTYPES  # noqa: E402


def main():
    summary = {}
    targets = [("keyun", "zigezheng"), ("huoyun", "zigezheng"), ("weixian", "zigezheng"),
               ("jiaolian", "zigezheng"), ("chuzu", "zigezheng")]
    for car_type, course in targets:
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
            log(f"  no ids for {name}")
            continue
        json.dump(ids, open(f_ids, "w"))
        questions = fetch_details(ids)
        json.dump(questions, open(f_q, "w"), ensure_ascii=False)
        json.dump(meta, open(f_m, "w"), ensure_ascii=False)
        summary[name] = {"ids": len(ids), "fetched": len(questions)}
        log(f"  saved {len(questions)}/{len(ids)}")
    # also try zigezheng tags sweep (tagId may differ from kemu courses — handled inside collect_ids)
    log(f"DONE {json.dumps(summary, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
