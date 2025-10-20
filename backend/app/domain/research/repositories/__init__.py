"""Research domain repository interfaces."""

from .research_repository import (
    ResearchRunRepository,
    FindingRepository,
    HypothesisRepository,
    DossierRepository,
)

__all__ = [
    "ResearchRunRepository",
    "FindingRepository",
    "HypothesisRepository",
    "DossierRepository",
]
