#!/usr/bin/env python3
"""Fetch .htm/.html pages that mirrored pages link to (relative links) but that are not yet in the repo.
Run BEFORE tools/rewrite.py, or it will treat rewritten links normally (relative links are unaffected). Saves raw bytes.
"""
import os, re, sys, urllib.parse, urllib.request, urllib.error, time
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
BASE = 'https://www.ilpalio.org'
ATTR = re.compile(rb'''(?:href|src|background)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>"']+))''', re.I)
JSSTR = re.compile(rb'''["']([^"'\s<>()]+\.html?)["']''', re.I)
def files():
    s = set()
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in ('.git', 'tools')]
        for f in fn: s.add(os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, '/'))
    return s
def missing(have, only=None):
    out = {}
    for lp in have:
        if not lp.lower().endswith(('.htm', '.html')): continue
        if only is not None and lp not in only: continue
        data = open(os.path.join(ROOT, lp), 'rb').read()
        cur = BASE + '/' + urllib.parse.quote(lp)
        for pat in (ATTR, JSSTR):
            for m in pat.finditer(data):
                ref = [x for x in m.groups() if x is not None][0].decode('latin-1').strip().replace('\\', '/')
                if not ref or ref.startswith(('#', 'javascript:', 'mailto:', 'tel:', 'data:')) or '?' in ref: continue
                u = urllib.parse.urlsplit(urllib.parse.urljoin(cur, ref))
                if u.netloc.lower() != 'www.ilpalio.org' or not u.path.lower().endswith(('.htm', '.html')): continue
                t = urllib.parse.unquote(u.path).lstrip('/')
                if t not in have and '..' not in t.split('/'): out[t] = lp
    return out
def get(t):
    url = BASE + '/' + urllib.parse.quote(t, safe="/%:@!$&'()*+,;=-._~")
    for i in range(5):
        try:
            class NR(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *a, **k): return None
            with urllib.request.build_opener(NR).open(urllib.request.Request(url, headers={'User-Agent': 'palio-backup-for-orlando'}), timeout=40) as r:
                if len(r.headers.get('Content-Type', '')) and 'html' not in r.headers.get('Content-Type', '').lower(): return t, None
                return t, r.read(5 * 1024 * 1024)
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410) or 300 <= e.code < 400: return t, None
        except Exception: pass
        time.sleep(1.5 * (i + 1))
    return t, None
LIMIT = int(os.environ.get('LIMIT', '0'))
DF = os.path.join(ROOT, 'tools', 'dead_links.txt')
have = files(); only = None; n = 0
dead = set(open(DF).read().split('\n')) - {''} if os.path.exists(DF) else set()
for rnd in range(6):
    miss = {t: r for t, r in missing(have, only).items() if t not in dead}
    if LIMIT: miss = dict(sorted(miss.items())[:max(0, LIMIT - n)])
    print('round', rnd, 'missing', len(miss), flush=True)
    if not miss: break
    new = set()
    with ThreadPoolExecutor(6) as ex:
        for t, data in ex.map(get, sorted(miss)):
            if data is None: dead.add(t); continue
            fp = os.path.join(ROOT, t)
            if os.path.isdir(fp): dead.add(t); continue
            os.makedirs(os.path.dirname(fp) or ROOT, exist_ok=True)
            open(fp, 'wb').write(data); new.add(t); have.add(t); n += 1
            if n % 200 == 0: print(n, 'saved', flush=True)
    only = new
    if LIMIT and n >= LIMIT: break
print('MISSING_LEFT', len([t for t in missing(have) if t not in dead]), flush=True)
print('saved', n, 'dead(404 on original)', len(dead))
open(DF, 'w').write('\n'.join(sorted(dead)) + '\n')
