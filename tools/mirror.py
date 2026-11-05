#!/usr/bin/env python3
"""Mirror www.ilpalio.org into the repo root, byte-for-byte, original paths.
Usage: python3 tools/mirror.py [--root DIR] [--max-asset KB]
Writes tools/MANIFEST.txt (sha256, size, URL of raw bytes as fetched) and tools/crawl_log.json.
"""
import sys, os, re, json, time, hashlib, argparse, threading
import urllib.request, urllib.error, urllib.parse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

HOST = 'www.ilpalio.org'
BASE = 'https://' + HOST
UA = 'palio-backup-for-orlando'
HTML_EXT = ('.htm', '.html')
IMG_EXT = ('.jpg', '.jpeg', '.gif', '.png', '.ico', '.svg', '.webp', '.bmp')
CODE_EXT = ('.css', '.js')
SKIP_EXT = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar', '.mp3', '.mp4', '.wav',
            '.avi', '.wmv', '.mov', '.mpg', '.mpeg', '.flv', '.wma', '.swf', '.rtf', '.txt', '.exe', '.7z', '.m4a', '.ogg')

ap = argparse.ArgumentParser()
ap.add_argument('--root', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ap.add_argument('--max-asset', type=int, default=250, help='max image size in KB')
ap.add_argument('--max-total-mb', type=int, default=400)
ap.add_argument('--start', default='/')
args = ap.parse_args()
ROOT = os.path.abspath(args.root)
MAXA = args.max_asset * 1024
MAXTOTAL = args.max_total_mb * 1024 * 1024

ATTR = re.compile(rb'''(?:href|src|action|background|data-src)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>"']+))''', re.I)
JSSTR = re.compile(rb'''["']([^"'\s<>()]+\.(?:html?|css|js|jpe?g|gif|png))["']''', re.I)
CSSURL = re.compile(rb'''url\(\s*["']?([^)"']+)["']?\s*\)''', re.I)
IMPORT = re.compile(rb'''@import\s+["']([^"']+)["']''', re.I)

def local_path(path):
    p = urllib.parse.unquote(path)
    if p.endswith('/'):
        p += 'index.htm'
    return p.lstrip('/')

def norm(ref, cur):
    """Return absolute URL path (case kept) on our host, or None."""
    try:
        ref = ref.decode('latin-1').strip()
    except AttributeError:
        ref = ref.strip()
    if not ref or ref.startswith(('#', 'javascript:', 'mailto:', 'tel:', 'data:', 'about:')):
        return None
    ref = ref.replace('\\', '/')
    u = urllib.parse.urljoin(cur, ref)
    s = urllib.parse.urlsplit(u)
    if s.scheme not in ('http', 'https') or s.netloc.lower() not in (HOST, HOST.replace('www.', '')):
        return None
    if s.query:
        return ('Q', s.path + '?' + s.query)
    return s.path or '/'

def fetch(path):
    lp0 = local_path(path)
    full0 = os.path.join(ROOT, lp0)
    if '..' not in lp0.split('/') and os.path.isfile(full0) and os.environ.get('RESUME'):
        data = open(full0, 'rb').read()
        return dict(status='ok', data=data, ct='text/html' if classify(path) == 'html' else '', url=BASE + urllib.parse.quote(path, safe="/%:@!$&'()*+,;=-._~"))
    url = BASE + urllib.parse.quote(path, safe="/%:@!$&'()*+,;=-._~")
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            class NoRedir(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *a, **k): return None
            op = urllib.request.build_opener(NoRedir)
            with op.open(req, timeout=40) as r:
                ct = r.headers.get('Content-Type', '')
                cl = r.headers.get('Content-Length')
                ext = os.path.splitext(path.lower())[1]
                if ext in IMG_EXT and cl and int(cl) > MAXA:
                    return dict(status='skip-big', size=int(cl), ct=ct)
                if cl and int(cl) > 5 * 1024 * 1024:
                    return dict(status='skip-big', size=int(cl), ct=ct)
                data = r.read(5 * 1024 * 1024 + 1)
                if len(data) > 5 * 1024 * 1024:
                    return dict(status='skip-big', size=len(data), ct=ct)
                if ext in IMG_EXT and len(data) > MAXA:
                    return dict(status='skip-big', size=len(data), ct=ct)
                return dict(status='ok', data=data, ct=ct, url=url)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                return dict(status='redirect', code=e.code, loc=e.headers.get('Location'))
            if e.code in (404, 410, 403):
                return dict(status='http%d' % e.code)
            last = 'HTTP %d' % e.code
        except Exception as e:
            last = repr(e)
        time.sleep(1.5 * (attempt + 1))
    return dict(status='error', err=last)

def classify(path):
    if path.endswith('/'):
        return 'html'
    ext = os.path.splitext(path.lower())[1]
    if ext in HTML_EXT: return 'html'
    if ext in CODE_EXT: return 'code'
    if ext in IMG_EXT: return 'img'
    if ext in SKIP_EXT: return 'skip'
    return 'other'

def extract(data, cur, kind):
    out = set()
    pats = [CSSURL, IMPORT] if kind == 'code' and cur.lower().endswith('.css') else ([JSSTR] if kind == 'code' else [ATTR, JSSTR, CSSURL, IMPORT])
    for pat in pats:
        for m in pat.finditer(data):
            g = [x for x in m.groups() if x is not None]
            if g:
                n = norm(g[0], cur)
                if n: out.add(n)
    return out

def main():
    os.makedirs(os.path.join(ROOT, 'tools'), exist_ok=True)
    seen = {}      # path -> result record
    refs = {}      # path -> first referrer
    queue = [args.start]
    seen_set = {args.start}
    manifest = []
    total = 0
    lock = threading.Lock()
    pending = {}
    t0 = time.time()
    with ThreadPoolExecutor(6) as ex:
        while queue or pending:
            queue.sort(key=lambda q: 0 if classify(q) in ('html', 'code') else 1)
            while queue and len(pending) < 6:
                p = queue.pop(0)
                pending[ex.submit(fetch, p)] = p
            done, _ = wait(list(pending), return_when=FIRST_COMPLETED)
            for f in done:
                p = pending.pop(f)
                res = f.result()
                kind = classify(p)
                rec = dict(status=res['status'], kind=kind, ref=refs.get(p))
                if res['status'] == 'ok':
                    data = res['data']
                    ct = res['ct'].lower()
                    if kind == 'other':
                        kind = 'html' if 'html' in ct else 'otherfile'
                        rec['kind'] = kind
                    if kind in ('html', 'code') or kind == 'img' or kind == 'otherfile':
                        if 'text/html' in ct and kind == 'img':
                            rec['status'] = 'notimage'
                        elif total + len(data) > MAXTOTAL and kind != 'html':
                            rec['status'] = 'skip-budget'
                        else:
                            lp = local_path(p)
                            full = os.path.join(ROOT, lp)
                            if '..' in lp.split('/') or os.path.isdir(full):
                                rec['status'] = 'bad-path'
                            else:
                                os.makedirs(os.path.dirname(full) or ROOT, exist_ok=True)
                                with open(full, 'wb') as fh: fh.write(data)
                                total += len(data)
                                rec['size'] = len(data)
                                rec['file'] = lp
                                manifest.append((hashlib.sha256(data).hexdigest(), len(data), res['url'], lp))
                                if kind in ('html', 'code'):
                                    for n in extract(data, BASE + p, kind):
                                        if isinstance(n, tuple):
                                            seen.setdefault(n[1], dict(status='query-skipped', kind='query', ref=p))
                                            continue
                                        if n not in seen_set:
                                            seen_set.add(n); refs[n] = p; queue.append(n)
                else:
                    rec.update({k: v for k, v in res.items() if k not in ('status', 'data')})
                seen[p] = rec
                if len(seen) % 200 == 0:
                    print(len(seen), 'done', len(queue), 'queued', '%ds' % (time.time() - t0), flush=True)
            # skip kinds that we never fetch
            queue[:] = [q for q in queue if not (classify(q) == 'skip' and not seen.setdefault(q, dict(status='skip-type', kind='skip', ref=refs.get(q))))]
    manifest.sort(key=lambda m: m[3])
    with open(os.path.join(ROOT, 'tools', 'MANIFEST.txt'), 'w', encoding='utf-8') as fh:
        fh.write('# sha256  size  url  (raw bytes exactly as fetched, before any change)\n')
        for h, s, u, lp in manifest:
            fh.write('%s  %d  %s\n' % (h, s, u))
    with open(os.path.join(ROOT, 'tools', 'crawl_log.json'), 'w', encoding='utf-8') as fh:
        json.dump(seen, fh, indent=0, sort_keys=True, ensure_ascii=False)
    from collections import Counter
    print(Counter((r['kind'], r['status']) for r in seen.values()))
    print('files', len(manifest), 'bytes', total)

main()
