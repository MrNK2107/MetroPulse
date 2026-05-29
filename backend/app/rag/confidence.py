from __future__ import annotations

from app.rag.models import EvidencePack


def evidence_confidence(pack: EvidencePack) -> float:
    return pack.overall_evidence_confidence
