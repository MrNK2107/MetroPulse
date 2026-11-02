"""Atomic directory publish: build in a temp sibling, then swap into place."""
from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Callable


def publish_dir(final: Path, writer: Callable[[Path], None]) -> Path:
    """Run `writer(tmp)` on a `<final>.tmp-<uuid>` sibling, then install it as `final`.

    An existing `final` is renamed aside first, so the window with no final dir is
    just two renames; it is restored if the install fails. `tmp` is removed on any
    failure and `final` is left as it was.
    """
    final = Path(final)
    final.parent.mkdir(parents=True, exist_ok=True)
    tmp = final.with_name(f"{final.name}.tmp-{uuid.uuid4().hex}")
    tmp.mkdir()
    aside: Path | None = None
    try:
        writer(tmp)
        if final.exists():
            aside = final.with_name(f"{final.name}.old-{uuid.uuid4().hex}")
            os.replace(final, aside)
        try:
            os.replace(tmp, final)
        except BaseException:
            if aside is not None:
                os.replace(aside, final)
                aside = None
            raise
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    if aside is not None:
        shutil.rmtree(aside, ignore_errors=True)
    return final
