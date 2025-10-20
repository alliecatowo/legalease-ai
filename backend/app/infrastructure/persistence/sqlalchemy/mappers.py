"""
Mappers for converting between ORM models and domain entities.

These mappers handle the translation between SQLAlchemy ORM models
and domain entities, including value objects.
"""

from typing import List, Dict, Any
from uuid import UUID
from datetime import datetime

from app.domain.research.entities import (
    ResearchRun,
    Finding,
    Hypothesis,
    Dossier,
    DossierSection,
    ResearchStatus,
    ResearchPhase,
    FindingType,
)
from app.domain.knowledge.entities import (
    Entity,
    Event,
    Relationship,
    EntityType,
    EventType,
    RelationshipType,
)
from .models import (
    ResearchRunModel,
    FindingModel,
    HypothesisModel,
    DossierModel,
    EntityModel,
    EventModel,
    RelationshipModel,
)


# ============================================================================
# Research Domain Mappers
# ============================================================================


def to_domain_research_run(model: ResearchRunModel) -> ResearchRun:
    """
    Convert ResearchRunModel to ResearchRun domain entity.

    Args:
        model: SQLAlchemy ORM model

    Returns:
        ResearchRun domain entity
    """
    # Convert findings list (stored as JSON strings) to UUIDs
    findings_uuids = [UUID(f) for f in model.findings] if model.findings else []

    return ResearchRun(
        id=model.id,
        case_id=model.case_id,
        status=ResearchStatus(model.status),
        phase=ResearchPhase(model.phase),
        query=model.query,
        findings=findings_uuids,
        config=model.config or {},
        started_at=model.started_at,
        completed_at=model.completed_at,
        dossier_path=model.dossier_path,
        metadata=model.metadata or {},
    )


def to_model_research_run(entity: ResearchRun) -> ResearchRunModel:
    """
    Convert ResearchRun domain entity to ResearchRunModel.

    Args:
        entity: ResearchRun domain entity

    Returns:
        SQLAlchemy ORM model
    """
    # Convert UUIDs to strings for JSON storage
    findings_strings = [str(f) for f in entity.findings]

    return ResearchRunModel(
        id=entity.id,
        case_id=entity.case_id,
        status=entity.status.value,
        phase=entity.phase.value,
        query=entity.query,
        findings=findings_strings,
        config=entity.config,
        started_at=entity.started_at,
        completed_at=entity.completed_at,
        dossier_path=entity.dossier_path,
        metadata=entity.metadata,
    )


def to_domain_finding(model: FindingModel) -> Finding:
    """
    Convert FindingModel to Finding domain entity.

    Args:
        model: SQLAlchemy ORM model

    Returns:
        Finding domain entity
    """
    # Convert JSON arrays to UUID lists
    entities_uuids = [UUID(e) for e in model.entities] if model.entities else []
    citations_uuids = [UUID(c) for c in model.citations] if model.citations else []

    return Finding(
        id=model.id,
        research_run_id=model.research_run_id,
        finding_type=FindingType(model.finding_type),
        text=model.text,
        entities=entities_uuids,
        citations=citations_uuids,
        confidence=model.confidence,
        relevance=model.relevance,
        tags=model.tags or [],
        metadata=model.metadata or {},
    )


def to_model_finding(entity: Finding) -> FindingModel:
    """
    Convert Finding domain entity to FindingModel.

    Args:
        entity: Finding domain entity

    Returns:
        SQLAlchemy ORM model
    """
    # Convert UUIDs to strings for JSON storage
    entities_strings = [str(e) for e in entity.entities]
    citations_strings = [str(c) for c in entity.citations]

    return FindingModel(
        id=entity.id,
        research_run_id=entity.research_run_id,
        finding_type=entity.finding_type.value,
        text=entity.text,
        entities=entities_strings,
        citations=citations_strings,
        confidence=entity.confidence,
        relevance=entity.relevance,
        tags=entity.tags,
        metadata=entity.metadata,
    )


def to_domain_hypothesis(model: HypothesisModel) -> Hypothesis:
    """
    Convert HypothesisModel to Hypothesis domain entity.

    Args:
        model: SQLAlchemy ORM model

    Returns:
        Hypothesis domain entity
    """
    # Convert JSON arrays to UUID lists
    supporting = [UUID(f) for f in model.supporting_findings] if model.supporting_findings else []
    contradicting = [UUID(f) for f in model.contradicting_findings] if model.contradicting_findings else []

    return Hypothesis(
        id=model.id,
        research_run_id=model.research_run_id,
        hypothesis_text=model.hypothesis_text,
        supporting_findings=supporting,
        contradicting_findings=contradicting,
        confidence=model.confidence,
        metadata=model.metadata or {},
    )


def to_model_hypothesis(entity: Hypothesis) -> HypothesisModel:
    """
    Convert Hypothesis domain entity to HypothesisModel.

    Args:
        entity: Hypothesis domain entity

    Returns:
        SQLAlchemy ORM model
    """
    # Convert UUIDs to strings for JSON storage
    supporting_strings = [str(f) for f in entity.supporting_findings]
    contradicting_strings = [str(f) for f in entity.contradicting_findings]

    return HypothesisModel(
        id=entity.id,
        research_run_id=entity.research_run_id,
        hypothesis_text=entity.hypothesis_text,
        supporting_findings=supporting_strings,
        contradicting_findings=contradicting_strings,
        confidence=entity.confidence,
        metadata=entity.metadata,
    )


def to_domain_dossier(model: DossierModel) -> Dossier:
    """
    Convert DossierModel to Dossier domain entity.

    Args:
        model: SQLAlchemy ORM model

    Returns:
        Dossier domain entity
    """
    # Convert sections from JSON to DossierSection value objects
    sections = [
        DossierSection(
            title=s["title"],
            content=s["content"],
            order=s["order"],
            metadata=s.get("metadata", {}),
        )
        for s in (model.sections or [])
    ]

    return Dossier(
        id=model.id,
        research_run_id=model.research_run_id,
        executive_summary=model.executive_summary,
        sections=sections,
        citations_appendix=model.citations_appendix,
        generated_at=model.generated_at,
        metadata=model.metadata or {},
    )


def to_model_dossier(entity: Dossier) -> DossierModel:
    """
    Convert Dossier domain entity to DossierModel.

    Args:
        entity: Dossier domain entity

    Returns:
        SQLAlchemy ORM model
    """
    # Convert DossierSection value objects to JSON
    sections_json = [
        {
            "title": s.title,
            "content": s.content,
            "order": s.order,
            "metadata": s.metadata,
        }
        for s in entity.sections
    ]

    return DossierModel(
        id=entity.id,
        research_run_id=entity.research_run_id,
        executive_summary=entity.executive_summary,
        sections=sections_json,
        citations_appendix=entity.citations_appendix,
        generated_at=entity.generated_at,
        metadata=entity.metadata,
    )


# ============================================================================
# Knowledge Domain Mappers
# ============================================================================


def to_domain_entity(model: EntityModel) -> Entity:
    """
    Convert EntityModel to Entity domain entity.

    Args:
        model: SQLAlchemy ORM model

    Returns:
        Entity domain entity
    """
    # Convert citation strings to UUIDs
    citations = [UUID(c) for c in model.source_citations] if model.source_citations else []

    return Entity(
        id=model.id,
        entity_type=EntityType(model.entity_type),
        name=model.name,
        aliases=model.aliases or [],
        attributes=model.attributes or {},
        first_seen=model.first_seen,
        last_seen=model.last_seen,
        source_citations=citations,
        metadata=model.metadata or {},
    )


def to_model_entity(entity: Entity) -> EntityModel:
    """
    Convert Entity domain entity to EntityModel.

    Args:
        entity: Entity domain entity

    Returns:
        SQLAlchemy ORM model
    """
    # Convert UUIDs to strings for JSON storage
    citations_strings = [str(c) for c in entity.source_citations]

    return EntityModel(
        id=entity.id,
        entity_type=entity.entity_type.value,
        name=entity.name,
        aliases=entity.aliases,
        attributes=entity.attributes,
        first_seen=entity.first_seen,
        last_seen=entity.last_seen,
        source_citations=citations_strings,
        metadata=entity.metadata,
    )


def to_domain_event(model: EventModel) -> Event:
    """
    Convert EventModel to Event domain entity.

    Args:
        model: SQLAlchemy ORM model

    Returns:
        Event domain entity
    """
    # Convert participant and citation strings to UUIDs
    participants = [UUID(p) for p in model.participants] if model.participants else []
    citations = [UUID(c) for c in model.source_citations] if model.source_citations else []

    # Handle location (can be UUID or string)
    location = None
    if model.location:
        try:
            location = UUID(model.location)
        except ValueError:
            location = model.location

    return Event(
        id=model.id,
        event_type=EventType(model.event_type),
        description=model.description,
        participants=participants,
        timestamp=model.timestamp,
        source_citations=citations,
        location=location,
        duration=model.duration,
        metadata=model.metadata or {},
    )


def to_model_event(entity: Event) -> EventModel:
    """
    Convert Event domain entity to EventModel.

    Args:
        entity: Event domain entity

    Returns:
        SQLAlchemy ORM model
    """
    # Convert UUIDs to strings for JSON storage
    participants_strings = [str(p) for p in entity.participants]
    citations_strings = [str(c) for c in entity.source_citations]

    # Handle location (can be UUID or string)
    location_str = None
    if entity.location is not None:
        location_str = str(entity.location)

    return EventModel(
        id=entity.id,
        event_type=entity.event_type.value,
        description=entity.description,
        participants=participants_strings,
        timestamp=entity.timestamp,
        source_citations=citations_strings,
        location=location_str,
        duration=entity.duration,
        metadata=entity.metadata,
    )


def to_domain_relationship(model: RelationshipModel) -> Relationship:
    """
    Convert RelationshipModel to Relationship domain entity.

    Args:
        model: SQLAlchemy ORM model

    Returns:
        Relationship domain entity
    """
    # Convert citation strings to UUIDs
    citations = [UUID(c) for c in model.source_citations] if model.source_citations else []

    return Relationship(
        id=model.id,
        from_entity_id=model.from_entity_id,
        to_entity_id=model.to_entity_id,
        relationship_type=RelationshipType(model.relationship_type),
        strength=model.strength,
        source_citations=citations,
        temporal_start=model.temporal_start,
        temporal_end=model.temporal_end,
        metadata=model.metadata or {},
    )


def to_model_relationship(entity: Relationship) -> RelationshipModel:
    """
    Convert Relationship domain entity to RelationshipModel.

    Args:
        entity: Relationship domain entity

    Returns:
        SQLAlchemy ORM model
    """
    # Convert UUIDs to strings for JSON storage
    citations_strings = [str(c) for c in entity.source_citations]

    return RelationshipModel(
        id=entity.id,
        from_entity_id=entity.from_entity_id,
        to_entity_id=entity.to_entity_id,
        relationship_type=entity.relationship_type.value,
        strength=entity.strength,
        source_citations=citations_strings,
        temporal_start=entity.temporal_start,
        temporal_end=entity.temporal_end,
        metadata=entity.metadata,
    )
