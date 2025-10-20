"""
Domain layer for LegalEase application.

This package contains the core business logic organized using Domain-Driven Design (DDD)
and hexagonal architecture principles. The domain is independent of infrastructure
concerns like databases, APIs, and external services.

Structure:
    evidence/    - Evidence management domain (documents, transcripts, communications)
    research/    - Legal research domain (research runs, findings, hypotheses)
    knowledge/   - Knowledge graph domain (entities, events, relationships)

Each domain contains:
    entities/         - Domain entities with identity and business logic
    value_objects/    - Immutable value objects without identity
    repositories/     - Abstract repository interfaces (ports)
"""
