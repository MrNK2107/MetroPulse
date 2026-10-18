"""Place-name normalisation used for cross-source matching."""
from __future__ import annotations

import re
import unicodedata

_STRIP = re.compile(r"[.,'()\-/]")
_WS = re.compile(r"\s+")
_SUFFIXES = (" district", " dist", " zila", " jilla")


def normalize_state_code(code: str | None) -> str | None:
    """Two-digit LGD state code: '6' and ' 06 ' -> '06'; blank -> None; non-numeric kept."""
    if code is None:
        return None
    s = str(code).strip()
    if not s:
        return None
    return s.zfill(2) if s.isdigit() else s


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
