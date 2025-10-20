"""
API v2 Routes Package.

Exports all route modules for easy import.
"""

from app.api.v2.routes import research, evidence, graph

__all__ = ["research", "evidence", "graph"]
