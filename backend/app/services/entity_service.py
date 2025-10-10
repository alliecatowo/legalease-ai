"""
Entity Extraction Service

Provides entity extraction using GLiNER (zero-shot NER) and LexNLP (legal-specific extraction).
Supports legal entities, dates, amounts, citations, and more.
"""
import logging
import re
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert

from ..core.config import settings
from ..models.entity import Entity, EntityMention

logger = logging.getLogger(__name__)


class EntityExtractionService:
    """Service for extracting entities from documents"""

    def __init__(self):
        self.gliner_model = None
        self.legal_entity_types = [
            "PERSON", "ORGANIZATION", "LAW_FIRM", "COURT",
            "JUDGE", "ATTORNEY", "CLIENT", "PARTY",
            "COMPANY", "GOVERNMENT_AGENCY", "FINANCIAL_INSTITUTION"
        ]

        # Initialize GLiNER model (lazy loading)
        self._gliner_initialized = False

    async def initialize_gliner(self):
        """Initialize GLiNER model"""
        if self._gliner_initialized:
            return

        try:
            from gliner import GLiNER
            logger.info("Initializing GLiNER model...")
            # Using a legal-specific model if available, otherwise base model
            self.gliner_model = GLiNER.from_pretrained("urchade/gliner_multi-v2.1")
            self._gliner_initialized = True
            logger.info("GLiNER model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GLiNER: {e}")
            self.gliner_model = None

    async def extract_entities(
        self,
        document_id: str,
        text: str,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Extract entities from document text using multiple methods

        Args:
            document_id: Document ID
            text: Document text
            db: Database session

        Returns:
            List of extracted entities
        """
        entities = []

        try:
            # Method 1: GLiNER for named entities
            gliner_entities = await self._extract_gliner_entities(text)
            entities.extend(gliner_entities)

            # Method 2: LexNLP for legal-specific entities
            lexnlp_entities = await self._extract_lexnlp_entities(text)
            entities.extend(lexnlp_entities)

            # Method 3: Regex patterns for additional entities
            regex_entities = await self._extract_regex_entities(text)
            entities.extend(regex_entities)

            # Remove duplicates and save to database
            unique_entities = self._deduplicate_entities(entities)

            # Save entities to database
            await self._save_entities(document_id, unique_entities, db)

            logger.info(f"Extracted {len(unique_entities)} entities from document {document_id}")
            return unique_entities

        except Exception as e:
            logger.error(f"Failed to extract entities from document {document_id}: {e}")
            return []

    async def _extract_gliner_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities using GLiNER"""
        if not self._gliner_initialized:
            await self.initialize_gliner()

        if not self.gliner_model:
            return []

        try:
            # Split text into chunks to avoid model limits
            chunks = self._chunk_text(text, 1000)
            all_entities = []

            for chunk in chunks:
                entities = self.gliner_model.predict_entities(
                    chunk,
                    self.legal_entity_types,
                    threshold=0.5  # Confidence threshold
                )

                # Convert to our format
                for entity in entities:
                    all_entities.append({
                        "text": entity["text"],
                        "type": entity["label"],
                        "confidence": entity["score"],
                        "start": entity["start"],
                        "end": entity["end"],
                        "source": "gliner"
                    })

            return all_entities

        except Exception as e:
            logger.error(f"GLiNER extraction failed: {e}")
            return []

    async def _extract_lexnlp_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract legal entities using LexNLP"""
        entities = []

        try:
            # Import LexNLP modules
            from lexnlp.extract.en import (
                acts, amounts, citations, companies, conditions,
                constraints, copyright, courts, currencies, dates,
                definitions, distances, durations, entities, geoentities,
                money, percents, phones, pii, ratios, regulations,
                trademarks, urls
            )

            # Extract various legal entities
            entities.extend(await self._extract_citations(text))
            entities.extend(await self._extract_dates(text))
            entities.extend(await self._extract_amounts(text))
            entities.extend(await self._extract_companies(text))
            entities.extend(await self._extract_courts(text))
            entities.extend(await self._extract_acts(text))

        except ImportError:
            logger.warning("LexNLP not available, skipping legal entity extraction")
        except Exception as e:
            logger.error(f"LexNLP extraction failed: {e}")

        return entities

    async def _extract_citations(self, text: str) -> List[Dict[str, Any]]:
        """Extract legal citations"""
        entities = []
        try:
            from lexnlp.extract.en import citations

            for citation in citations.get_citations(text):
                entities.append({
                    "text": citation,
                    "type": "CITATION",
                    "confidence": 0.9,
                    "source": "lexnlp"
                })
        except:
            pass
        return entities

    async def _extract_dates(self, text: str) -> List[Dict[str, Any]]:
        """Extract dates"""
        entities = []
        try:
            from lexnlp.extract.en import dates

            for date in dates.get_dates(text):
                entities.append({
                    "text": str(date),
                    "type": "DATE",
                    "confidence": 0.95,
                    "source": "lexnlp"
                })
        except:
            pass
        return entities

    async def _extract_amounts(self, text: str) -> List[Dict[str, Any]]:
        """Extract monetary amounts"""
        entities = []
        try:
            from lexnlp.extract.en import amounts

            for amount in amounts.get_amounts(text):
                entities.append({
                    "text": f"${amount}",
                    "type": "AMOUNT",
                    "confidence": 0.95,
                    "source": "lexnlp"
                })
        except:
            pass
        return entities

    async def _extract_companies(self, text: str) -> List[Dict[str, Any]]:
        """Extract company names"""
        entities = []
        try:
            from lexnlp.extract.en import companies

            for company in companies.get_companies(text):
                entities.append({
                    "text": company,
                    "type": "COMPANY",
                    "confidence": 0.8,
                    "source": "lexnlp"
                })
        except:
            pass
        return entities

    async def _extract_courts(self, text: str) -> List[Dict[str, Any]]:
        """Extract court names"""
        entities = []
        try:
            from lexnlp.extract.en import courts

            for court in courts.get_courts(text):
                entities.append({
                    "text": court,
                    "type": "COURT",
                    "confidence": 0.9,
                    "source": "lexnlp"
                })
        except:
            pass
        return entities

    async def _extract_acts(self, text: str) -> List[Dict[str, Any]]:
        """Extract legislative acts"""
        entities = []
        try:
            from lexnlp.extract.en import acts

            for act in acts.get_act_list(text):
                entities.append({
                    "text": act,
                    "type": "ACT",
                    "confidence": 0.85,
                    "source": "lexnlp"
                })
        except:
            pass
        return entities

    async def _extract_regex_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities using regex patterns"""
        entities = []

        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            entities.append({
                "text": match.group(),
                "type": "EMAIL",
                "confidence": 0.99,
                "start": match.start(),
                "end": match.end(),
                "source": "regex"
            })

        # Phone pattern (US)
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        for match in re.finditer(phone_pattern, text):
            entities.append({
                "text": match.group(),
                "type": "PHONE",
                "confidence": 0.95,
                "start": match.start(),
                "end": match.end(),
                "source": "regex"
            })

        # Case number patterns
        case_patterns = [
            r'\b\d{2}[-]\d{4}[-]\w+',  # Common federal case format
            r'\b\d+:\d{2}[-]\w+',      # State case format
        ]

        for pattern in case_patterns:
            for match in re.finditer(pattern, text):
                entities.append({
                    "text": match.group(),
                    "type": "CASE_NUMBER",
                    "confidence": 0.9,
                    "start": match.start(),
                    "end": match.end(),
                    "source": "regex"
                })

        return entities

    def _chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Split text into chunks for processing"""
        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)

        return chunks

    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate entities"""
        seen = set()
        unique_entities = []

        for entity in entities:
            # Create a key based on text and type
            key = (entity["text"].lower(), entity["type"])

            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)

        return unique_entities

    async def _save_entities(
        self,
        document_id: str,
        entities: List[Dict[str, Any]],
        db: AsyncSession
    ):
        """Save entities to database"""
        try:
            for entity_data in entities:
                # Create or get entity
                entity_query = select(Entity).where(
                    Entity.text == entity_data["text"],
                    Entity.type == entity_data["type"]
                )
                entity_result = await db.execute(entity_query)
                entity = entity_result.scalar_one_or_none()

                if not entity:
                    # Create new entity
                    entity = Entity(
                        text=entity_data["text"],
                        type=entity_data["type"],
                        source=entity_data.get("source", "unknown"),
                        confidence=entity_data.get("confidence", 0.5),
                        created_at=datetime.utcnow()
                    )
                    db.add(entity)
                    await db.flush()  # Get the ID

                # Create mention relationship
                mention = EntityMention(
                    document_id=document_id,
                    entity_id=entity.id,
                    start_position=entity_data.get("start"),
                    end_position=entity_data.get("end"),
                    context=entity_data.get("context"),
                    confidence=entity_data.get("confidence", 0.5)
                )
                db.add(mention)

            await db.commit()

        except Exception as e:
            logger.error(f"Failed to save entities for document {document_id}: {e}")
            await db.rollback()

    async def get_document_entities(
        self,
        document_id: str,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get all entities for a document"""
        try:
            query = (
                select(Entity, EntityMention)
                .join(EntityMention, Entity.id == EntityMention.entity_id)
                .where(EntityMention.document_id == document_id)
            )

            result = await db.execute(query)
            entities = []

            for entity, mention in result:
                entities.append({
                    "id": entity.id,
                    "text": entity.text,
                    "type": entity.type,
                    "source": entity.source,
                    "confidence": mention.confidence,
                    "start_position": mention.start_position,
                    "end_position": mention.end_position,
                    "context": mention.context
                })

            return entities

        except Exception as e:
            logger.error(f"Failed to get entities for document {document_id}: {e}")
            return []

    async def get_entity_stats(self, case_id: Optional[str] = None, db: AsyncSession = None) -> Dict[str, Any]:
        """Get entity statistics"""
        try:
            # This would require complex queries - for now return basic stats
            return {
                "total_entities": 0,
                "entity_types": {},
                "top_entities": []
            }
        except Exception as e:
            logger.error(f"Failed to get entity stats: {e}")
            return {}


# Global service instance
entity_service = EntityExtractionService()