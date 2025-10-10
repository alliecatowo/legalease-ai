"""
Summarization Service

Provides document summarization using Ollama local LLMs.
Supports different types of legal documents with specialized prompts.
"""
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..core.ollama import summarize_text, ollama_client, ensure_model_available
from ..core.config import settings
from ..models.document import Document
from ..models.chunk import Chunk

logger = logging.getLogger(__name__)


class SummarizationService:
    """Service for document summarization"""

    def __init__(self):
        self.model = settings.OLLAMA_MODEL_SUMMARIZATION

    async def summarize_document(
        self,
        document_id: str,
        db: AsyncSession,
        summary_type: str = "general",
        max_length: int = 500
    ) -> Optional[str]:
        """
        Summarize a document

        Args:
            document_id: Document ID to summarize
            db: Database session
            summary_type: Type of summary (general, legal, executive)
            max_length: Maximum summary length in words

        Returns:
            Summary text or None if failed
        """
        try:
            # Get document and its chunks
            doc_query = select(Document).where(Document.id == document_id)
            doc_result = await db.execute(doc_query)
            document = doc_result.scalar_one_or_none()

            if not document:
                logger.error(f"Document {document_id} not found")
                return None

            # Get document text from chunks
            chunk_query = select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index)
            chunk_result = await db.execute(chunk_query)
            chunks = chunk_result.scalars().all()

            if not chunks:
                logger.warning(f"No chunks found for document {document_id}")
                return None

            # Combine chunk text
            full_text = "\n".join([chunk.content for chunk in chunks])

            # Generate summary based on type
            summary = await self._generate_typed_summary(
                full_text,
                document.filename or "",
                summary_type,
                max_length
            )

            if summary:
                # Update document with summary
                update_stmt = (
                    update(Document)
                    .where(Document.id == document_id)
                    .values(
                        summary=summary,
                        summarized_at=datetime.utcnow()
                    )
                )
                await db.execute(update_stmt)
                await db.commit()

                logger.info(f"Generated {summary_type} summary for document {document_id}")
                return summary

        except Exception as e:
            logger.error(f"Failed to summarize document {document_id}: {e}")

        return None

    async def summarize_chunk(
        self,
        chunk_id: str,
        db: AsyncSession,
        summary_type: str = "general"
    ) -> Optional[str]:
        """
        Summarize a specific chunk

        Args:
            chunk_id: Chunk ID to summarize
            db: Database session
            summary_type: Type of summary

        Returns:
            Chunk summary or None if failed
        """
        try:
            chunk_query = select(Chunk).where(Chunk.id == chunk_id)
            chunk_result = await db.execute(chunk_query)
            chunk = chunk_result.scalar_one_or_none()

            if not chunk:
                logger.error(f"Chunk {chunk_id} not found")
                return None

            summary = await self._generate_typed_summary(
                chunk.content,
                f"Chunk {chunk.chunk_index}",
                summary_type,
                max_length=100  # Shorter for chunks
            )

            if summary:
                # Update chunk with summary
                update_stmt = (
                    update(Chunk)
                    .where(Chunk.id == chunk_id)
                    .values(
                        summary=summary,
                        summarized_at=datetime.utcnow()
                    )
                )
                await db.execute(update_stmt)
                await db.commit()

                return summary

        except Exception as e:
            logger.error(f"Failed to summarize chunk {chunk_id}: {e}")

        return None

    async def _generate_typed_summary(
        self,
        text: str,
        context: str,
        summary_type: str,
        max_length: int
    ) -> Optional[str]:
        """
        Generate summary based on type

        Args:
            text: Text to summarize
            context: Context (filename, etc.)
            summary_type: Type of summary
            max_length: Maximum length

        Returns:
            Summary text
        """
        # Ensure model is available
        if not await ensure_model_available(self.model):
            logger.error(f"Model {self.model} not available for summarization")
            return None

        # Create type-specific prompts
        prompts = {
            "general": self._general_summary_prompt(text, context, max_length),
            "legal": self._legal_summary_prompt(text, context, max_length),
            "executive": self._executive_summary_prompt(text, context, max_length),
            "contract": self._contract_summary_prompt(text, context, max_length),
            "case": self._case_summary_prompt(text, context, max_length)
        }

        prompt_data = prompts.get(summary_type, prompts["general"])

        try:
            async with ollama_client as client:
                summary = await client.generate(
                    model=self.model,
                    prompt=prompt_data["prompt"],
                    system=prompt_data["system"]
                )

                # Clean up and truncate if needed
                summary = summary.strip()
                if len(summary.split()) > max_length:
                    summary = " ".join(summary.split()[:max_length]) + "..."

                return summary

        except Exception as e:
            logger.error(f"Failed to generate {summary_type} summary: {e}")
            return None

    def _general_summary_prompt(self, text: str, context: str, max_length: int) -> Dict[str, str]:
        """General summary prompt"""
        return {
            "system": "You are a professional document summarizer. Create clear, concise summaries that capture the main points and key information.",
            "prompt": f"""Please summarize the following document:

Context: {context}

Text:
{text[:4000]}

Provide a concise summary in {max_length} words or less:"""
        }

    def _legal_summary_prompt(self, text: str, context: str, max_length: int) -> Dict[str, str]:
        """Legal document summary prompt"""
        return {
            "system": """You are a legal document analyzer. Focus on:
- Key parties and their roles
- Legal issues and claims
- Important dates and deadlines
- Outcomes and decisions
- Citations to laws or precedents
- Financial amounts and obligations

Be objective, factual, and use appropriate legal terminology.""",
            "prompt": f"""Analyze and summarize this legal document:

Context: {context}

Document Text:
{text[:4000]}

Provide a legal summary highlighting key facts, parties, issues, and outcomes:"""
        }

    def _executive_summary_prompt(self, text: str, context: str, max_length: int) -> Dict[str, str]:
        """Executive summary prompt"""
        return {
            "system": "You are an executive assistant. Create high-level summaries for busy professionals, focusing on actionable insights and key decisions.",
            "prompt": f"""Create an executive summary of this document:

Context: {context}

Content:
{text[:4000]}

Focus on:
- Main purpose/objective
- Key decisions or recommendations
- Important deadlines or milestones
- Financial implications
- Next steps or action items

Keep it brief and actionable:"""
        }

    def _contract_summary_prompt(self, text: str, context: str, max_length: int) -> Dict[str, str]:
        """Contract summary prompt"""
        return {
            "system": """You are a contract analyst. Focus on:
- Parties to the agreement
- Key obligations and responsibilities
- Term and termination conditions
- Payment terms and amounts
- Important dates and deadlines
- Special clauses or conditions
- Risk factors""",
            "prompt": f"""Summarize this contract:

Context: {context}

Contract Text:
{text[:4000]}

Highlight the essential terms, obligations, and conditions:"""
        }

    def _case_summary_prompt(self, text: str, context: str, max_length: int) -> Dict[str, str]:
        """Legal case summary prompt"""
        return {
            "system": """You are a legal case analyst. Focus on:
- Case name and citation
- Court and jurisdiction
- Key parties (plaintiff, defendant, etc.)
- Legal issues and questions presented
- Court's holding and reasoning
- Precedent value
- Dissenting opinions if any""",
            "prompt": f"""Summarize this legal case:

Context: {context}

Case Text:
{text[:4000]}

Provide a case brief with key facts, procedural posture, issues, holding, and reasoning:"""
        }

    async def batch_summarize_case(
        self,
        case_id: str,
        db: AsyncSession,
        summary_type: str = "legal"
    ) -> Dict[str, Any]:
        """
        Summarize all documents in a case

        Args:
            case_id: Case ID
            db: Database session
            summary_type: Type of summary

        Returns:
            Summary statistics
        """
        try:
            # Get all documents in case
            doc_query = select(Document).where(Document.case_id == case_id)
            doc_result = await db.execute(doc_query)
            documents = doc_result.scalars().all()

            if not documents:
                return {"total": 0, "summarized": 0, "errors": 0}

            summarized = 0
            errors = 0

            for doc in documents:
                try:
                    summary = await self.summarize_document(
                        doc.id,
                        db,
                        summary_type
                    )
                    if summary:
                        summarized += 1
                    else:
                        errors += 1
                except Exception as e:
                    logger.error(f"Failed to summarize document {doc.id}: {e}")
                    errors += 1

            # Generate case-level summary
            case_summary = await self._generate_case_level_summary(case_id, db, summary_type)

            return {
                "total": len(documents),
                "summarized": summarized,
                "errors": errors,
                "case_summary": case_summary
            }

        except Exception as e:
            logger.error(f"Failed to batch summarize case {case_id}: {e}")
            return {"total": 0, "summarized": 0, "errors": 0, "error": str(e)}

    async def _generate_case_level_summary(
        self,
        case_id: str,
        db: AsyncSession,
        summary_type: str
    ) -> Optional[str]:
        """Generate a summary of the entire case"""
        try:
            # Get all document summaries
            doc_query = (
                select(Document.filename, Document.summary)
                .where(Document.case_id == case_id, Document.summary.isnot(None))
            )
            doc_result = await db.execute(doc_query)
            doc_summaries = doc_result.all()

            if not doc_summaries:
                return None

            # Combine document summaries
            combined_text = "\n\n".join([
                f"Document: {filename}\nSummary: {summary}"
                for filename, summary in doc_summaries
            ])

            # Generate case-level summary
            case_prompt = {
                "system": "You are a legal case analyst. Create a cohesive summary of an entire case from individual document summaries.",
                "prompt": f"""Synthesize these document summaries into a comprehensive case overview:

{combined_text[:6000]}

Provide a unified summary that connects the documents and shows the complete case narrative:"""
            }

            async with ollama_client as client:
                return await client.generate(
                    model=self.model,
                    prompt=case_prompt["prompt"],
                    system=case_prompt["system"]
                )

        except Exception as e:
            logger.error(f"Failed to generate case-level summary for {case_id}: {e}")
            return None


# Global service instance
summarization_service = SummarizationService()