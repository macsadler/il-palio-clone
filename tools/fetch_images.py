#!/usr/bin/env python3
"""Fetch small images (<= MAXKB, default 250) that mirrored pages reference and that are not yet in the repo.
Appends MANIFEST rows (raw bytes as fetched). Commits+pushes every BATCH files if COMMIT=1.
"""
import os, re, sys, hashlib, subprocess, urllib.parse, urllib.request, urllib.error, time, json
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
BASE = 'https://www.ilpalio.org'
MAXB = int(os.environ.get('MAXKB', '250')) * 1024
BATCH = int(os.environ.get('BATCH', '200'))
MAXREPO = int(os.environ.get('MAXMB', '650')) * 1024 * 1024
IMG = ('.jpg', '.jpeg', '.gif', '.png', '.ico', '.svg', '.webp', '.bmp')
ATTR = re.compile(rb'''(?:src|background|href)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>"']+))''', re.I)
CSSURL = re.compile(rb'''url\(\s*["']?([^)"']+)["']?\s*\)''', re.I)
JSSTR = re.compile(rb'''["']([^"'\s<>()]+\.(?:jpe?g|gif|png|ico|bmp))["']''', re.I)
SKIPF = os.path.join(ROOT, 'tools', 'skipped_images.txt')
skipped = set(open(SKIPF).read().split('\n')) - {''} if os.path.exists(SKIPF) else set()
have = set(); total = 0
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d != '.git']
    for f in fn:
        p = os.path.join(dp, f); have.add(os.path.relpath(p, ROOT).replace(os.sep, '/')); total += os.path.getsize(p)
targets = {}
for lp in sorted(have):
    if not lp.lower().endswith(('.htm', '.html', '.css')) or lp.startswith('tools/'): continue
    data = open(os.path.join(ROOT, lp), 'rb').read()
    cur = BASE + '/' + urllib.parse.quote(lp)
    for pat in (ATTR, CSSURL, JSSTR):
        for m in pat.finditer(data):
            ref = [x for x in m.groups() if x is not None][0].decode('latin-1').strip().replace('\\', '/')
            if not ref or ref.startswith(('#', 'javascript:', 'mailto:', 'data:')) or '?' in ref: continue
            u = urllib.parse.urlsplit(urllib.parse.urljoin(cur, ref))
            if u.netloc.lower() != 'www.ilpalio.org' or not u.path.lower().endswith(IMG): continue
            t = urllib.parse.unquote(u.path).lstrip('/')
            if t not in have and t not in skipped and '..' not in t.split('/'): targets.setdefault(t, lp)
print('image targets to fetch', len(targets), flush=True)
class NR(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None
def get(t):
    url = BASE + '/' + urllib.parse.quote(t, safe="/%:@!$&'()*+,;=-._~")
    for i in range(4):
        try:
            with urllib.request.build_opener(NR).open(urllib.request.Request(url, headers={'User-Agent': 'palio-backup-for-orlando'}), timeout=40) as r:
                cl = r.headers.get('Content-Length')
                if (cl and int(cl) > MAXB) or 'html' in r.headers.get('Content-Type', '').lower(): return t, None, url
                d = r.read(MAXB + 1)
                return t, (d if len(d) <= MAXB else None), url
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410) or 300 <= e.code < 400: return t, None, url
        except Exception: pass
        time.sleep(1.5 * (i + 1))
    return t, None, url
def flush(rows):
    with open(os.path.join(ROOT, 'tools', 'MANIFEST.txt'), 'a', encoding='utf-8') as fh: fh.writelines(rows)
    open(SKIPF, 'w').write('\n'.join(sorted(skipped)) + '\n')
    if os.environ.get('COMMIT'):
        subprocess.run(['git', 'add', '-A'], cwd=ROOT)
        subprocess.run(['git', 'commit', '-qm', 'Image batch: %d images fetched so far' % saved], cwd=ROOT)
        subprocess.run(['git', 'push', '-q', 'origin', 'main'], cwd=ROOT)
saved = 0; rows = []
with ThreadPoolExecutor(6) as ex:
    for t, d, url in ex.map(get, sorted(targets)):
        if d is None: skipped.add(t); continue
        fp = os.path.join(ROOT, t)
        if os.path.isdir(fp): skipped.add(t); continue
        os.makedirs(os.path.dirname(fp) or ROOT, exist_ok=True); open(fp, 'wb').write(d)
        total += len(d); saved += 1
        rows.append('%s  %d  %s\n' % (hashlib.sha256(d).hexdigest(), len(d), url))
        if saved % BATCH == 0: flush(rows); rows = []; print(saved, 'images', '%dMB' % (total >> 20), flush=True)
        if total > MAXREPO: print('size cap reached'); break
flush(rows)
print('done: saved', saved, 'skipped(404/big)', len(skipped), flush=True)
