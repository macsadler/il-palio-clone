#!/bin/bash
# fetch 200 missing pages -> manifest -> rewrite -> counts -> commit+push; repeat until none left
cd "$(dirname "$0")/.."
while true; do
  LIMIT=200 python3 -u tools/fetch_missing.py > /tmp/fm_run.log 2>&1
  python3 tools/add_manifest.py >/dev/null && python3 tools/rewrite.py >/dev/null
  H=$(find . -not -path './.git/*' -not -path './tools/*' \( -name '*.htm' -o -name '*.html' \) | wc -l)
  M=$(grep MISSING_LEFT /tmp/fm_run.log | awk '{print $2}')
  D=$(grep -c . tools/dead_links.txt)
  sed -i '/^=== PROGRESS/,$d' tools/REPORT.txt
  printf '=== PROGRESS (updated %s UTC) ===\nHTML pages mirrored: %s\nLinked page targets still missing (fetchable): %s\nLinked pages 404 on Orlando'"'"'s own site (broken on original): %s\nBroken by us (page targets that exist live but are not yet copied): %s\n(The "STATUS AT TIME LIMIT" text above is from the earlier pass; these numbers are current.)\n' "$(date -u +%F\ %T)" "$H" "$M" "$D" "$M" >> tools/REPORT.txt
  git add -A; git commit -qm "Mirror batch: $H html pages, $M targets missing"; git push -q origin main 2>&1 | tail -1
  echo "$H html, $M missing" >> /tmp/claude-0/loop.log
  [ "$M" = "0" ] && break
  grep -q '^saved 0 ' /tmp/fm_run.log && break
done
echo DONE >> /tmp/claude-0/loop.log
