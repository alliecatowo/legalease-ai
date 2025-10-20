"""Research domain entities."""

from .research_run import ResearchRun, ResearchPhase, ResearchStatus
from .finding import Finding, FindingType
from .hypothesis import Hypothesis
from .dossier import Dossier, DossierSection

__all__ = [
    "ResearchRun",
    "ResearchPhase",
    "ResearchStatus",
    "Finding",
    "FindingType",
    "Hypothesis",
    "Dossier",
    "DossierSection",
]
