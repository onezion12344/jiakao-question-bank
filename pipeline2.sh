#!/bin/bash
# pipeline2.sh — after round1 crawl+repair: run round2 (zigezheng), repair again, rebuild repo, media.
set -x
cd ~/jiakao

# wait for pipeline1 to fully finish (it ends after media download)
while ps aux | grep -q "[p]ipeline.sh"; do sleep 30; done
echo "=== pipeline1 done, starting round2 ==="

python3 crawl_jiakao_round2.py

# repair pass for round2 sets
python3 - <<'EOF'
import glob, json, os
for f in sorted(glob.glob("data/ids-*.json")):
    name = os.path.basename(f)[len("ids-"):-5]
    ids = set(json.load(open(f)))
    fq = f"data/questions-{name}.json"
    rows = json.load(open(fq)) if os.path.exists(fq) else []
    have = {q.get("questionId") or q.get("id") for q in rows}
    missing = sorted(ids - have)
    json.dump(missing, open(f"data/missing-{name}.json", "w"))
    print(name, "missing", len(missing))
EOF
python3 repair_missing.py
python3 repair_missing.py

# rebuild repo with all sets
python3 build_repo.py
cp -f crawl_jiakao.py crawl_jiakao_round2.py build_repo.py repair_missing.py crawl_media.py pipeline2.sh repo/ 2>/dev/null

# media download for any new images (resumable)
python3 crawl_media.py >> media.log 2>&1

echo "=== PIPELINE2 COMPLETE ==="
