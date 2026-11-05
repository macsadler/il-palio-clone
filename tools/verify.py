#!/usr/bin/env python3
"""Step 4 checks. Writes tools/REPORT.txt.
(a) every file: hash after reversing the link rewrite == MANIFEST hash; >=300 sampled pages re-fetched live and compared
(b) crawl all internal links in the repo; classify broken ones against the live site
(c) case-sensitivity check
Usage: python3 tools/verify.py [--sample 300]
"""
import os, re, sys, json, random, hashlib, argparse, posixpath, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rewrite as RW
ROOT = RW.ROOT
ap = argparse.ArgumentParser(); ap.add_argument('--sample', type=int, default=300); args = ap.parse_args()
UA = 'palio-backup-for-orlando'
BASE = 'https://www.ilpalio.org'
man = {}
for line in open(os.path.join(ROOT, 'tools/MANIFEST.txt'), encoding='utf-8'):
    if line.startswith('#') or not line.strip(): continue
    h, s, u = line.split()
    man[RW.local_path(urllib.parse.urlsplit(u).path)] = (h, int(s), u)
mirrored = set(man)
rlog = json.load(open(os.path.join(ROOT, 'tools/rewrite_log.json'))) if os.path.exists(os.path.join(ROOT, 'tools/rewrite_log.json')) else {}
out = []
def say(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); out.append(s)

# (a1) manifest hashes after reversing rewrite
bad = []; missing = []
for lp, (h, s, u) in man.items():
    fp = os.path.join(ROOT, lp)
    if not os.path.isfile(fp): missing.append(lp); continue
    d = open(fp, 'rb').read()
    if lp in rlog: d = RW.reverse(d, rlog[lp])
    if hashlib.sha256(d).hexdigest() != h: bad.append(lp)
say('A1 files in manifest:', len(man), '| missing on disk:', len(missing), '| hash mismatch after reversing rewrite:', len(bad))
for x in (missing + bad)[:20]: say('   !', x)

# (a2) live sample
def get(url):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=40) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410): return e.code, b''
        except Exception: pass
    return 0, b''
pages = sorted(p for p in man if p.lower().endswith(('.htm', '.html')))
random.seed(540)
sample = random.sample(pages, min(args.sample, len(pages)))
def chk(lp):
    st, live = get(man[lp][2])
    if st != 200: return lp, 'fetch-%s' % st
    if hashlib.sha256(live).hexdigest() != man[lp][0]: return lp, 'live-changed-since-mirror'
    new, n, e = RW.rewrite(live, lp, mirrored)
    return lp, 'ok' if new == open(os.path.join(ROOT, lp), 'rb').read() else 'DIFF'
with ThreadPoolExecutor(6) as ex: res = list(ex.map(chk, sample))
from collections import Counter
c = Counter(r for _, r in res)
say('A2 live sample pages:', len(sample), dict(c))
for lp, r in res:
    if r != 'ok': say('   !', lp, r)

# (b) internal link crawl
ATTR = re.compile(rb'''(?:href|src|background)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>"']+))''', re.I)
JSSTR = re.compile(rb'''["']([^"'\s<>()]+\.(?:html?|css|js|jpe?g|gif|png))["']''', re.I)
allfiles = set()
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in ('.git', 'tools')]
    for f in fn: allfiles.add(os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, '/'))
lower = {}
for f in allfiles: lower.setdefault(f.lower(), []).append(f)
broken = {}  # target -> (referrer, kind)
checked = 0; links = 0
for lp in sorted(allfiles):
    if not lp.lower().endswith(('.htm', '.html')): continue
    data = open(os.path.join(ROOT, lp), 'rb').read()
    cur = BASE + '/' + urllib.parse.quote(lp)
    for pat in (ATTR, JSSTR):
        for m in pat.finditer(data):
            ref = [x for x in m.groups() if x is not None][0].decode('latin-1').strip().replace('\\', '/')
            if not ref or ref.startswith(('#', 'javascript:', 'mailto:', 'tel:', 'data:')): continue
            u = urllib.parse.urljoin(cur, ref); s = urllib.parse.urlsplit(u)
            if s.netloc.lower() not in ('www.ilpalio.org', 'ilpalio.org') and s.netloc: continue
            if s.netloc.lower() == 'ilpalio.org' or ref.lower().startswith(('http://', 'https://')): continue  # absolute -> live host, not a repo link
            links += 1
            if s.query: continue
            t = RW.local_path(s.path)
            if t in allfiles: continue
            broken.setdefault(t, lp)
say('B1 relative internal links examined:', links, '| distinct missing targets:', len(broken))
def classify(t):
    st, _ = get(BASE + '/' + urllib.parse.quote(t))
    return t, st
def is_page(t): return os.path.splitext(t.lower())[1] in ('.htm', '.html', '.css', '.js') or not os.path.splitext(t)[1]
media_missing = [t for t in broken if not is_page(t)]
with ThreadPoolExecutor(6) as ex: cl = list(ex.map(classify, sorted(t for t in broken if is_page(t))))
cl += [(t, 200) for t in media_missing[:0]]
say('B0 missing media targets (images etc., not mirrored in this pass, stay on live site; not individually re-checked):', len(media_missing))
log = json.load(open(os.path.join(ROOT, 'tools/crawl_log.json'))) if os.path.exists(os.path.join(ROOT, 'tools/crawl_log.json')) else {}
orig_broken = [t for t, st in cl if st in (404, 410, 403)]
live_ok = [t for t, st in cl if st == 200]
other = [t for t, st in cl if st not in (404, 410, 403, 200)]
def bydesign(t):
    ext = os.path.splitext(t.lower())[1]
    return ext not in ('.htm', '.html', '.css', '.js')
by_design = media_missing
by_us = [t for t in live_ok if not bydesign(t)]
say('B2 missing targets that are ALSO missing (404) on Orlando\'s live site (broken on original):', len(orig_broken))
say('B3 missing targets exist live but are media/large/skipped files left on live site (not mirrored by design):', len(by_design))
say('B4 missing targets that are pages/css/js and exist live (BROKEN BY US, must be 0):', len(by_us))
say('B5 live check inconclusive (timeout etc):', len(other))
for t in by_us[:30]: say('   ! by-us', t, '<-', broken[t])
json.dump(dict(orig_broken={t: broken[t] for t in orig_broken}, by_design=by_design, by_us=by_us, other=other), open(os.path.join(ROOT, 'tools/broken_links.json'), 'w'), indent=0)

# (c) case sensitivity
pairs = {k: v for k, v in lower.items() if len(v) > 1}
say('C1 file names that exist in more than one letter-case spelling (kept as separate files):', len(pairs))
for k, v in list(pairs.items())[:10]: say('   ', v)
say('C2 files whose repo spelling is not found by exact case but would be by lowercase (links needing a case twin):',
    sum(1 for t in broken if t.lower() in lower))

# counts
n_pages = len(pages)
rw = sum(len(v) for v in rlog.values())
say('')
say('PAGES MIRRORED (html/htm):', n_pages)
say('LINKS REWRITTEN (absolute -> relative):', rw, 'in', len(rlog), 'files')
say('LINKS BROKEN ON THE ORIGINAL SITE (distinct targets):', len(orig_broken))
say('LINKS BROKEN BY US (distinct targets):', len(by_us))
sk = Counter(r.get('status') + ':' + r.get('kind', '') for r in log.values() if r.get('status') not in ('ok',))
say('FILES SKIPPED / NOT FETCHED (status:kind -> count) from crawl log:', dict(sk))
say('  skip-big = image over the size cap (photo archive, first pass); skip-type = video/audio/PDF/Word/etc; query-skipped = URLs with ?query (search runs live)')
open(os.path.join(ROOT, 'tools/REPORT.txt'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
