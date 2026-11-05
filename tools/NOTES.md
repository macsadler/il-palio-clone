# Notes / problems (Track B)

- http:// redirects (301) to https://; the crawl uses https://www.ilpalio.org.
- The first crawl was interrupted before it wrote the manifest; MANIFEST.txt was rebuilt from the unmodified files on disk (tools/make_manifest.py, valid only before tools/rewrite.py is run). mirror.py can resume from disk files (RESUME=1).
- Image fetching is slow (~4/s with 6 connections); the crawl was stopped at the time limit. Images not yet fetched remain on the live site; re-run mirror.py with RESUME=1 to continue.
- Link rewriting is limited to absolute <a href> links to mirrored .htm/.html pages. <link rel=canonical>, scripts, images, forms and the iubenda script were left exactly as they were.
- index.html is an exact copy of index.htm (GitHub Pages serves index.html); it is not in the MANIFEST.
Image crawl stopped at time limit (~5.5k of ~25k queued URLs processed); remaining queue not fetched; crawl_log.json was not written because the crawl was stopped. MANIFEST built from disk.
