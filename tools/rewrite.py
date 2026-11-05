#!/usr/bin/env python3
"""Step 3: change ONLY absolute <a href> links to mirrored pages into relative links.
Usage: python3 tools/rewrite.py   (run once on a fresh mirror; verify.py re-applies rewrite() to live bytes to compare)
"""
import os, re, sys, json, posixpath, urllib.parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# <a ...href="..."> only (navigational links); <link rel=canonical>, scripts, images, forms untouched
A_TAG = re.compile(rb'(<a\b[^>]*?\bhref\s*=\s*)(")([^"]*)(")|(<a\b[^>]*?\bhref\s*=\s*)(\')([^\']*)(\')', re.I | re.S)
ABS = re.compile(rb'^https?://(?:www\.)?ilpalio\.org(/[^?#]*)?(#.*)?$', re.I)

def local_path(path):
    p = urllib.parse.unquote(path)
    if p.endswith('/'):
        p += 'index.htm'
    return p.lstrip('/')

def rewrite(data, relfile, mirrored):
    """data: raw bytes of an HTML file whose repo-relative path is relfile. Returns (new bytes, n_changed)."""
    n = [0]
    d = posixpath.dirname(relfile)
    def sub(m):
        g = m.groups()
        pre, q, val, q2 = (g[0], g[1], g[2], g[3]) if g[0] else (g[4], g[5], g[6], g[7])
        mm = ABS.match(val.strip())
        if not mm or val != val.strip():
            return m.group(0)
        path = (mm.group(1) or b'/').decode('latin-1')
        frag = mm.group(2) or b''
        lp = local_path(path)
        if lp not in mirrored or not lp.lower().endswith(('.htm', '.html')):
            return m.group(0)
        rel = posixpath.relpath(lp, d or '.')
        n[0] += 1
        return pre + q + rel.encode('latin-1') + frag + q2
    return A_TAG.sub(sub, data), n[0]

def main():
    mirrored = set()
    for line in open(os.path.join(ROOT, 'tools', 'MANIFEST.txt'), encoding='utf-8'):
        if line.startswith('#') or not line.strip(): continue
        h, s, u = line.split()
        mirrored.add(local_path(urllib.parse.urlsplit(u).path))
    total = files = 0
    log = {}
    for lp in sorted(mirrored):
        if not lp.lower().endswith(('.htm', '.html')): continue
        full = os.path.join(ROOT, lp)
        data = open(full, 'rb').read()
        new, n = rewrite(data, lp, mirrored)
        if n:
            open(full, 'wb').write(new)
            total += n; files += 1; log[lp] = n
    json.dump(log, open(os.path.join(ROOT, 'tools', 'rewrite_log.json'), 'w'), indent=0, sort_keys=True)
    print('links rewritten', total, 'in files', files)

if __name__ == '__main__':
    main()
