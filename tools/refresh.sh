#!/bin/bash
# One command refresh: re-mirror from the live site, rewrite links, verify.
set -e
cd "$(dirname "$0")/.."
python3 tools/mirror.py
python3 tools/rewrite.py
[ -f index.htm ] && cp index.htm index.html
python3 tools/verify.py
