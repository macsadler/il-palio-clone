ilpalio.org - safety copy (Track B)

WHAT THIS IS
An exact copy of Orlando Papei's website www.ilpalio.org (the Palio di Siena archive),
made so the site can live safely somewhere else. The pages are Orlando's own hand-written
HTML, copied byte for byte: no redesign, no edited text, no added marks, no new features.
The only change is that links between pages that are in this copy now point to the copy
(relative links) instead of to the live site. Cookie script and Google search form are untouched.
Site content is licensed CC BY-NC 4.0, as on the original site.

HOW IT IS ORGANISED
The site lives at the top level of this repository, with the original file names and folders
(the live site serves index.htm at its address; Orlando also has a separate small index.html, kept exactly as it is).
Names that differ only by upper/lower case are kept as separate files so both spellings work.
Tools and notes are in the tools/ folder and are never part of the pages:
  tools/MANIFEST.txt  sha256, size and address of every original file exactly as fetched
  tools/REPORT.txt    results of the checks (page counts, links, anything broken)
  tools/NOTES.md      problems met along the way
robots.txt asks search engines not to index this copy (the live site stays the real one).

HOW TO REFRESH FROM THE LIVE SITE (one command, from the top folder of this repository)
  bash tools/refresh.sh
It re-downloads the site, rewrites the internal links, and re-runs the checks. Then commit and push.

WHAT IT DOES NOT INCLUDE YET
- Large media: the big photo archive, images over 250 KB, video, audio, PDF and Word files were
  skipped in this first pass. Pages that refer to them will show gaps until a second pass,
  or until those links are pointed at the live site.
- Search: the Google search form runs on Google and the live site; it does not search this copy.
- Pages reached only through query-string addresses (those with a "?") were not copied.
