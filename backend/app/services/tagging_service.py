"""
Auto-Tagging Service

Provides automatic document tagging and categorization using LLM analysis.
Supports legal document types, topics, and custom tags.
"""
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..core.ollama import ollama_client, ensure_model_available
from ..core.config import settings
from ..models.document import Document

logger = logging.getLogger(__name__)


class AutoTaggingService:
    """Service for automatic document tagging"""

    def __init__(self):
        self.model = settings.OLLAMA_MODEL_TAGGING

        # Predefined legal document categories
        self.document_categories = {
            # Legal document types
            "contract": ["agreement", "contract", "settlement", "nda", "license"],
            "lawsuit": ["complaint", "petition", "motion", "brief", "defense"],
            "court_order": ["order", "judgment", "ruling", "decree", "mandate"],
            "statute": ["law", "statute", "code", "regulation", "ordinance"],
            "evidence": ["evidence", "testimony", "deposition", "affidavit", "exhibit"],
            "pleading": ["complaint", "answer", "counterclaim", "reply", "motion"],

            # Legal practice areas
            "corporate": ["incorporation", "merger", "acquisition", "shareholder", "board"],
            "litigation": ["lawsuit", "trial", "appeal", "arbitration", "mediation"],
            "employment": ["employment", "labor", "wage", "discrimination", "harassment"],
            "real_estate": ["property", "lease", "mortgage", "title", "easement"],
            "intellectual_property": ["patent", "trademark", "copyright", "trade_secret"],
            "family_law": ["divorce", "custody", "support", "adoption", "guardianship"],
            "criminal": ["criminal", "felony", "misdemeanor", "prosecution", "defense"],
            "bankruptcy": ["bankruptcy", "insolvency", "creditor", "debtor", "reorganization"],
            "tax": ["tax", "irs", "audit", "deduction", "liability"],
            "environmental": ["environmental", "epa", "contamination", "compliance"],

            # Document subtypes
            "brief": ["brief", "memorandum", "argument", "legal_brief"],
            "correspondence": ["letter", "email", "memo", "communication"],
            "financial": ["financial", "accounting", "budget", "invoice", "payment"],
            "administrative": ["administrative", "filing", "notice", "certificate"],
            "confidential": ["confidential", "privileged", "sensitive", "restricted"]
        }

        # Reverse mapping for tag lookup
        self.tag_to_category = {}
        for category, tags in self.document_categories.items():
            for tag in tags:
                self.tag_to_category[tag] = category

    async def tag_document(
        self,
        document_id: str,
        db: AsyncSession,
        custom_categories: Optional[List[str]] = None
    ) -> List[str]:
        """
        Auto-tag a document

        Args:
            document_id: Document ID to tag
            db: Database session
            custom_categories: Optional custom categories to use

        Returns:
            List of tags applied
        """
        try:
            # Get document
            doc_query = select(Document).where(Document.id == document_id)
            doc_result = await db.execute(doc_query)
            document = doc_result.scalar_one_or_none()

            if not document:
                logger.error(f"Document {document_id} not found")
                return []

            # Get document text (from chunks or summary)
            text = await self._get_document_text(document_id, db)
            if not text:
                logger.warning(f"No text available for document {document_id}")
                return []

            # Generate tags
            tags = await self._generate_tags(text, document.filename or "")

            if tags:
                # Update document with tags
                existing_tags = document.tags or []
                all_tags = list(set(existing_tags + tags))

                update_stmt = (
                    update(Document)
                    .where(Document.id == document_id)
                    .values(
                        tags=all_tags,
                        tagged_at=datetime.utcnow()
                    )
                )
                await db.execute(update_stmt)
                await db.commit()

                logger.info(f"Applied {len(tags)} tags to document {document_id}: {tags}")
                return tags

        except Exception as e:
            logger.error(f"Failed to tag document {document_id}: {e}")

        return []

    async def _get_document_text(self, document_id: str, db: AsyncSession) -> Optional[str]:
        """Get document text for tagging"""
        try:
            # Try to get from document summary first (faster)
            doc_query = select(Document.summary).where(Document.id == document_id)
            doc_result = await db.execute(doc_query)
            summary = doc_result.scalar()

            if summary and len(summary) > 100:
                return summary

            # Fall back to chunk text
            from ..models.chunk import Chunk
            chunk_query = select(Chunk.content).where(Chunk.document_id == document_id).limit(5)
            chunk_result = await db.execute(chunk_query)
            chunks = chunk_result.scalars().all()

            if chunks:
                return " ".join(chunks)

        except Exception as e:
            logger.error(f"Failed to get text for document {document_id}: {e}")

        return None

    async def _generate_tags(
        self,
        text: str,
        filename: str,
        max_tags: int = 5
    ) -> List[str]:
        """Generate tags using LLM"""
        # Ensure model is available
        if not await ensure_model_available(self.model):
            logger.error(f"Model {self.model} not available for tagging")
            return []

        # Create tagging prompt
        categories_text = "\n".join([
            f"- {category}: {', '.join(tags)}"
            for category, tags in self.document_categories.items()
        ])

        system_prompt = f"""You are a legal document classifier. Analyze documents and assign relevant tags from the following categories:

{categories_text}

Return only a comma-separated list of the most relevant tags (maximum {max_tags}). Focus on the primary document type and key legal topics."""

        prompt = f"""Analyze this document and provide the most relevant tags:

Filename: {filename}

Content:
{text[:3000]}

Tags:"""

        try:
            async with ollama_client as client:
                response = await client.generate(
                    model=self.model,
                    prompt=prompt,
                    system=system_prompt
                )

                # Parse tags
                tags = [tag.strip().lower() for tag in response.split(',') if tag.strip()]
                tags = tags[:max_tags]  # Limit number of tags

                # Validate tags against our taxonomy
                valid_tags = []
                for tag in tags:
                    # Check if tag exists in our categories
                    if tag in self.tag_to_category:
                        valid_tags.append(tag)
                    else:
                        # Try partial matches
                        for category_tags in self.document_categories.values():
                            if tag in category_tags:
                                valid_tags.append(tag)
                                break

                return valid_tags

        except Exception as e:
            logger.error(f"Failed to generate tags: {e}")
            return []

    async def suggest_tags(
        self,
        text: str,
        filename: str = "",
        num_suggestions: int = 10
    ) -> List[str]:
        """Suggest tags without saving to database"""
        # Ensure model is available
        if not await ensure_model_available(self.model):
            return []

        system_prompt = """You are a legal document classifier. Suggest relevant tags for legal documents.
Focus on document types, legal practice areas, and key topics. Be specific and relevant."""

        prompt = f"""Suggest {num_suggestions} relevant tags for this document:

Filename: {filename}

Content preview:
{text[:2000]}

Tags:"""

        try:
            async with ollama_client as client:
                response = await client.generate(
                    model=self.model,
                    prompt=prompt,
                    system=system_prompt
                )

                tags = [tag.strip().lower() for tag in response.split(',') if tag.strip()]
                return tags[:num_suggestions]

        except Exception as e:
            logger.error(f"Failed to suggest tags: {e}")
            return []

    async def categorize_document(
        self,
        document_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Categorize document into primary and secondary categories

        Args:
            document_id: Document ID
            db: Database session

        Returns:
            Categorization results
        """
        try:
            # Get document tags
            doc_query = select(Document.tags).where(Document.id == document_id)
            doc_result = await db.execute(doc_query)
            tags = doc_result.scalar() or []

            if not tags:
                return {"primary_category": None, "secondary_categories": [], "confidence": 0}

            # Map tags to categories
            category_scores = {}
            for tag in tags:
                category = self.tag_to_category.get(tag)
                if category:
                    category_scores[category] = category_scores.get(category, 0) + 1

            if not category_scores:
                return {"primary_category": None, "secondary_categories": [], "confidence": 0}

            # Sort categories by score
            sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)

            primary_category = sorted_categories[0][0]
            primary_score = sorted_categories[0][1]

            secondary_categories = [cat for cat, score in sorted_categories[1:3]]  # Top 2 secondary

            # Calculate confidence
            total_tags = len(tags)
            confidence = primary_score / total_tags if total_tags > 0 else 0

            return {
                "primary_category": primary_category,
                "secondary_categories": secondary_categories,
                "confidence": confidence,
                "tag_coverage": len(category_scores) / len(self.document_categories)
            }

        except Exception as e:
            logger.error(f"Failed to categorize document {document_id}: {e}")
            return {"primary_category": None, "secondary_categories": [], "confidence": 0}

    async def batch_tag_case(
        self,
        case_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Tag all documents in a case

        Args:
            case_id: Case ID
            db: Database session

        Returns:
            Tagging statistics
        """
        try:
            # Get all documents in case
            doc_query = select(Document).where(Document.case_id == case_id)
            doc_result = await db.execute(doc_query)
            documents = doc_result.scalars().all()

            if not documents:
                return {"total": 0, "tagged": 0, "errors": 0}

            tagged = 0
            errors = 0

            for doc in documents:
                try:
                    tags = await self.tag_document(doc.id, db)
                    if tags:
                        tagged += 1
                except Exception as e:
                    logger.error(f"Failed to tag document {doc.id}: {e}")
                    errors += 1

            # Generate case-level tags
            case_tags = await self._generate_case_tags(case_id, db)

            return {
                "total": len(documents),
                "tagged": tagged,
                "errors": errors,
                "case_tags": case_tags
            }

        except Exception as e:
            logger.error(f"Failed to batch tag case {case_id}: {e}")
            return {"total": 0, "tagged": 0, "errors": 0}

    async def _generate_case_tags(self, case_id: str, db: AsyncSession) -> List[str]:
        """Generate tags for the entire case"""
        try:
            # Get all document tags in case
            doc_query = select(Document.tags).where(
                Document.case_id == case_id,
                Document.tags.isnot(None)
            )
            doc_result = await db.execute(doc_query)
            all_tags = []

            for tags in doc_result.scalars():
                all_tags.extend(tags)

            if not all_tags:
                return []

            # Count tag frequencies
            from collections import Counter
            tag_counts = Counter(all_tags)

            # Return most common tags (limit to 10)
            common_tags = [tag for tag, count in tag_counts.most_common(10)]
            return common_tags

        except Exception as e:
            logger.error(f"Failed to generate case tags for {case_id}: {e}")
            return []

    async def get_tag_suggestions(
        self,
        partial_tag: str,
        limit: int = 10
    ) -> List[str]:
        """Get tag suggestions based on partial input"""
        matching_tags = []

        # Search in our predefined tags
        for category_tags in self.document_categories.values():
            for tag in category_tags:
                if partial_tag.lower() in tag.lower():
                    matching_tags.append(tag)

        # Remove duplicates and limit
        unique_tags = list(set(matching_tags))
        return unique_tags[:limit]

    async def validate_tags(self, tags: List[str]) -> Tuple[List[str], List[str]]:
        """Validate tags against our taxonomy"""
        valid_tags = []
        invalid_tags = []

        for tag in tags:
            if tag.lower() in self.tag_to_category:
                valid_tags.append(tag.lower())
            else:
                invalid_tags.append(tag)

        return valid_tags, invalid_tags


# Global service instance
tagging_service = AutoTaggingService()