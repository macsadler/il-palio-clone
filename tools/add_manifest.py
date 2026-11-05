#!/usr/bin/env python3
"""Append MANIFEST rows for files fetched after the first manifest (run before rewrite.py touches them)."""
import os, hashlib, urllib.parse, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
mf = os.path.join(ROOT, 'tools', 'MANIFEST.txt')
have = set(); 
for l in open(mf, encoding='utf-8'):
    if l[0] != '#' and l.strip():
        have.add(urllib.parse.unquote(urllib.parse.urlsplit(l.split()[2]).path).lstrip('/'))
SKIP = {'README.md', 'README.txt', 'robots.txt', '.gitignore'}
add = []
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in ('.git', 'tools')]
    for f in fn:
        rel = os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, '/')
        if rel in have or rel in SKIP: continue
        d = open(os.path.join(ROOT, rel), 'rb').read()
        add.append('%s  %d  https://www.ilpalio.org/%s\n' % (hashlib.sha256(d).hexdigest(), len(d), urllib.parse.quote(rel, safe="/%:@!$&'()*+,;=-._~")))
open(mf, 'a', encoding='utf-8').writelines(sorted(add))
print('added', len(add))
