#!/usr/bin/env python3
"""Rebuild tools/MANIFEST.txt from the files on disk (only valid BEFORE tools/rewrite.py has run)."""
import os, hashlib, urllib.parse
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SKIP = {'README.md', 'README.txt', 'robots.txt', '.gitignore', 'index.html'}
rows = []
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in ('.git', 'tools')]
    for f in fn:
        full = os.path.join(dp, f); rel = os.path.relpath(full, ROOT).replace(os.sep, '/')
        if rel in SKIP: continue
        d = open(full, 'rb').read()
        rows.append((rel, hashlib.sha256(d).hexdigest(), len(d)))
rows.sort()
with open(os.path.join(ROOT, 'tools', 'MANIFEST.txt'), 'w', encoding='utf-8') as fh:
    fh.write('# sha256  size  url  (raw bytes exactly as fetched, before any change)\n')
    for rel, h, s in rows:
        fh.write('%s  %d  https://www.ilpalio.org/%s\n' % (h, s, urllib.parse.quote(rel, safe="/%:@!$&'()*+,;=-._~")))
print(len(rows), 'files')
