"""Place-name normalisation used for cross-source matching."""
from __future__ import annotations

import re
import unicodedata

_STRIP = re.compile(r"[.,'()\-/]")
_WS = re.compile(r"\s+")
_SUFFIXES = (" district", " dist", " zila", " jilla")


def normalize_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower().replace("&", "and")
    s = _STRIP.sub("", s)
    s = _WS.sub(" ", s).strip()
    if s.startswith("the "):
        s = s[4:]
    for suf in _SUFFIXES:
        if s.endswith(suf):
            s = s[: -len(suf)]
            break
    return s.strip()
