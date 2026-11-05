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

def rewrite(data, relfile, mirrored, unmirrored_to_live=None):
    """data: raw bytes of an HTML file at repo path relfile. Returns (new bytes, n_changed, edits).
    edits = [(pos_in_new, new_value, orig_value)] so the change can be reversed exactly (see reverse())."""
    d = posixpath.dirname(relfile)
    out = []; edits = []; last = 0; outlen = 0
    for m in A_TAG.finditer(data):
        g = m.groups()
        pre, q, val, q2 = (g[0], g[1], g[2], g[3]) if g[0] else (g[4], g[5], g[6], g[7])
        mm = ABS.match(val.strip())
        if not mm or val != val.strip():
            continue
        path = (mm.group(1) or b'/').decode('latin-1')
        frag = mm.group(2) or b''
        lp = local_path(path)
        if lp not in mirrored or not lp.lower().endswith(('.htm', '.html')):
            continue
        rel = posixpath.relpath(lp, d or '.').encode('latin-1') + frag
        vstart = m.start() + len(pre) + len(q)
        chunk = data[last:vstart]
        out.append(chunk); outlen += len(chunk)
        edits.append((outlen, rel.decode('latin-1'), val.decode('latin-1')))
        out.append(rel); outlen += len(rel)
        last = vstart + len(val)
    out.append(data[last:])
    return b''.join(out), len(edits), edits

def reverse(new, edits):
    out = []; last = 0
    for pos, nv, ov in edits:
        out.append(new[last:pos]); out.append(ov.encode('latin-1')); last = pos + len(nv.encode('latin-1'))
    out.append(new[last:])
    return b''.join(out)

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
        new, n, edits = rewrite(data, lp, mirrored)
        if n:
            open(full, 'wb').write(new)
            total += n; files += 1; log[lp] = edits
    json.dump(log, open(os.path.join(ROOT, 'tools', 'rewrite_log.json'), 'w'), indent=0, sort_keys=True)
    print('links rewritten', total, 'in files', files)
    json.dump(log, open(os.path.join(ROOT, 'tools', 'rewrite_log.json'), 'w'), sort_keys=True)

if __name__ == '__main__':
    main()
