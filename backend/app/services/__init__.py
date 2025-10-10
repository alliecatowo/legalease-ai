"""Services for LegalEase application."""

# Import services with optional error handling
__all__ = []

try:
    from app.services.case_service import CaseService
    __all__.extend(["CaseService"])
except ImportError as e:
    print(f"Warning: Could not import CaseService: {e}")

try:
    from app.services.search_service import HybridSearchEngine, get_search_engine
    __all__.extend(["HybridSearchEngine", "get_search_engine"])
except ImportError as e:
    print(f"Warning: Could not import search_service: {e}")
