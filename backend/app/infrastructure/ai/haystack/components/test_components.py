"""
Test utilities and sample data for custom Haystack components.

This module provides:
- Sample legal text for testing
- Sample Cellebrite export structures
- Validation functions
- Component testing helpers
"""

from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
import json

from haystack import Document


# Sample legal text with various citation types
SAMPLE_LEGAL_TEXT = """
SUPREME COURT OF THE UNITED STATES

ARTICLE I: BACKGROUND

In the landmark case of Brown v. Board of Education, 347 U.S. 483 (1954),
the Supreme Court held that racial segregation in public schools violated
the Equal Protection Clause of the Fourteenth Amendment. This decision
overturned the precedent established in Plessy v. Ferguson, 163 U.S. 537 (1896).

SECTION 1: STATUTORY FRAMEWORK

The Civil Rights Act, codified at 42 U.S.C. § 1983, provides a federal
remedy for violations of constitutional rights. See also 18 U.S.C. § 242,
which establishes criminal penalties for similar conduct.

SECTION 2: REGULATORY COMPLIANCE

Federal regulations at 26 C.F.R. § 1.501(c)(3) govern tax-exempt organizations.
California law requires compliance with Cal. Penal Code § 187.

WHEREAS, the parties acknowledge the precedent set forth in Smith v. Jones,
123 F.3d 456 (9th Cir. 2020), and

NOW THEREFORE, the parties agree to the terms set forth in Section 4.2 below.

See supra Part II for additional discussion. Id. at 123.
"""

# Sample contract text
SAMPLE_CONTRACT_TEXT = """
EMPLOYMENT AGREEMENT

This Employment Agreement ("Agreement") is entered into as of January 1, 2024.

ARTICLE I: DEFINITIONS

Section 1.1. "Employer" means ACME Corporation, a Delaware corporation.
Section 1.2. "Employee" means John Doe.
Section 1.3. "Effective Date" means January 1, 2024.

ARTICLE II: EMPLOYMENT TERMS

Section 2.1. Position and Duties
Employee shall serve as Chief Technology Officer, reporting to the CEO.

Section 2.2. Compensation
Employee shall receive an annual salary of $250,000, payable in accordance
with Section 3.4 of the Company's standard payroll practices.

ARTICLE III: CONFIDENTIALITY

Section 3.1. Non-Disclosure
Employee agrees to maintain confidentiality of all proprietary information
as defined in Section 1.1 above.

WHEREAS, Employee possesses specialized skills valuable to Employer, and

NOW THEREFORE, in consideration of the mutual covenants contained herein,
the parties agree as follows.
"""

# Sample Cellebrite message data
SAMPLE_CELLEBRITE_MESSAGES = [
    {
        "id": "msg-001",
        "body": "Hey, are you coming to the meeting?",
        "sender": "+1-555-0123",
        "recipient": "+1-555-0456",
        "timestamp": "2024-01-15T10:30:00",
        "platform": "SMS",
        "thread_id": "thread-001",
        "deleted": False,
    },
    {
        "id": "msg-002",
        "text": "Yes, I'll be there in 10 minutes",
        "from": "+1-555-0456",
        "to": "+1-555-0123",
        "time": "2024-01-15T10:32:00",
        "source": "WhatsApp",
        "conversation_id": "thread-001",
        "is_deleted": False,
        "attachments": [
            {"path": "/attachments/image_001.jpg", "type": "image"}
        ],
    },
    {
        "message_id": "msg-003",
        "message": "This message was deleted",
        "sender": "+1-555-0123",
        "timestamp": 1705320300,  # Unix timestamp
        "platform": "Signal",
        "thread_id": "thread-002",
        "deleted": True,
    },
]

# Sample ExportSummary.json structure
SAMPLE_EXPORT_SUMMARY = {
    "id": "export-uuid-12345",
    "summary": [
        {"name": "AXIOM version", "value": "7.11.0.38423"},
        {"name": "Total number of records", "value": "1,101,071"},
        {"name": "Number of records in export", "value": "50,000"},
        {"name": "Number of attachments in export", "value": "1,234"},
        {"name": "Start date", "value": "7/17/2025 9:48:42 AM"},
        {"name": "End date", "value": "7/17/2025 10:15:23 AM"},
        {"name": "Duration", "value": "00:26:41"},
        {"name": "Size (bytes)", "value": "50,223,053,681"},
        {"name": "Status", "value": "Completed"},
    ],
    "options": [
        {"name": "Export format", "value": "HTML with JSON"},
        {"name": "Include attachments", "value": "True"},
    ],
    "problems": [],
}


class ComponentTestHelper:
    """Helper class for testing custom Haystack components."""

    @staticmethod
    def create_sample_document(
        content: str = SAMPLE_LEGAL_TEXT,
        meta: Dict[str, Any] = None,
    ) -> Document:
        """
        Create a sample Haystack Document for testing.

        Args:
            content: Document content
            meta: Optional metadata

        Returns:
            Haystack Document
        """
        if meta is None:
            meta = {
                "file_path": "/path/to/document.pdf",
                "page_number": 1,
                "case_id": "test-case-123",
                "source_type": "LEGAL_DOCUMENT",
            }

        return Document(content=content, meta=meta)

    @staticmethod
    def create_sample_cellebrite_export(
        output_dir: Path,
        messages: List[Dict[str, Any]] = None,
    ) -> Path:
        """
        Create a sample Cellebrite export folder structure.

        Args:
            output_dir: Directory to create export in
            messages: Optional list of message data

        Returns:
            Path to export folder
        """
        if messages is None:
            messages = SAMPLE_CELLEBRITE_MESSAGES

        # Create export folder
        export_path = output_dir / "sample_cellebrite_export"
        export_path.mkdir(parents=True, exist_ok=True)

        # Create ExportSummary.json
        summary_file = export_path / "ExportSummary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(SAMPLE_EXPORT_SUMMARY, f, indent=2)

        # Create Report.html
        report_file = export_path / "Report.html"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("<html><body><h1>Cellebrite Export Report</h1></body></html>")

        # Create Resources folder
        resources_path = export_path / "Resources"
        resources_path.mkdir(exist_ok=True)

        # Create message files
        for idx, msg in enumerate(messages):
            msg_file = resources_path / f"messages_{idx:03d}.json"
            with open(msg_file, "w", encoding="utf-8") as f:
                json.dump({"messages": [msg]}, f, indent=2)

        return export_path

    @staticmethod
    def validate_chunked_document(doc: Document) -> bool:
        """
        Validate that a document has proper chunk metadata.

        Args:
            doc: Document to validate

        Returns:
            True if valid
        """
        meta = doc.meta

        # Check required fields
        required_fields = ["chunk_type", "position", "token_count", "has_citation"]

        for field in required_fields:
            if field not in meta:
                print(f"Missing required field: {field}")
                return False

        # Validate chunk_type
        valid_types = ["SUMMARY", "SECTION", "MICROBLOCK"]
        if meta["chunk_type"] not in valid_types:
            print(f"Invalid chunk_type: {meta['chunk_type']}")
            return False

        # Validate position
        if not isinstance(meta["position"], int) or meta["position"] < 0:
            print(f"Invalid position: {meta['position']}")
            return False

        return True

    @staticmethod
    def validate_citations(doc: Document) -> bool:
        """
        Validate that a document has proper citation metadata.

        Args:
            doc: Document to validate

        Returns:
            True if valid
        """
        meta = doc.meta

        # Check required fields
        if "citations" not in meta:
            print("Missing citations field")
            return False

        if "has_citations" not in meta:
            print("Missing has_citations field")
            return False

        if "citation_count" not in meta:
            print("Missing citation_count field")
            return False

        # Validate citations list
        citations = meta["citations"]
        if not isinstance(citations, list):
            print("Citations is not a list")
            return False

        # Validate each citation
        for citation in citations:
            required_fields = [
                "text",
                "type",
                "normalized",
                "components",
                "start_char",
                "end_char",
            ]

            for field in required_fields:
                if field not in citation:
                    print(f"Citation missing field: {field}")
                    return False

            # Validate citation type
            valid_types = ["CASE", "STATUTE", "REGULATION", "CROSS_REFERENCE"]
            if citation["type"] not in valid_types:
                print(f"Invalid citation type: {citation['type']}")
                return False

        # Validate consistency
        if meta["has_citations"] != (len(citations) > 0):
            print("has_citations inconsistent with citations list")
            return False

        if meta["citation_count"] != len(citations):
            print("citation_count inconsistent with citations list")
            return False

        return True

    @staticmethod
    def print_citation_summary(doc: Document):
        """
        Print a summary of citations found in a document.

        Args:
            doc: Document with citation metadata
        """
        meta = doc.meta
        citations = meta.get("citations", [])

        print(f"\n{'=' * 60}")
        print(f"Citation Summary")
        print(f"{'=' * 60}")
        print(f"Total citations: {len(citations)}")

        # Group by type
        by_type = {}
        for citation in citations:
            ctype = citation["type"]
            if ctype not in by_type:
                by_type[ctype] = []
            by_type[ctype].append(citation)

        for ctype, cits in by_type.items():
            print(f"\n{ctype}: {len(cits)}")
            for citation in cits:
                print(f"  - {citation['normalized']}")

        print(f"\n{'=' * 60}\n")


# Quick test function
def quick_test_components():
    """
    Quick test of all components.

    Run this to verify components are working correctly.
    """
    from .cellebrite_converter import CellebriteConverter
    from .legal_chunker import LegalChunker
    from .citation_extractor import CitationExtractor

    print("Testing Custom Haystack Components")
    print("=" * 60)

    # Test LegalChunker
    print("\n1. Testing LegalChunker...")
    doc = ComponentTestHelper.create_sample_document()
    chunker = LegalChunker(chunk_level="SECTION")
    result = chunker.run(documents=[doc])
    chunks = result["documents"]
    print(f"   Created {len(chunks)} section chunks")

    if chunks:
        print(f"   First chunk type: {chunks[0].meta['chunk_type']}")
        is_valid = ComponentTestHelper.validate_chunked_document(chunks[0])
        print(f"   Validation: {'PASS' if is_valid else 'FAIL'}")

    # Test CitationExtractor
    print("\n2. Testing CitationExtractor...")
    extractor = CitationExtractor()
    result = extractor.run(documents=[doc])
    enriched_docs = result["documents"]

    if enriched_docs:
        enriched_doc = enriched_docs[0]
        print(f"   Found {enriched_doc.meta.get('citation_count', 0)} citations")
        is_valid = ComponentTestHelper.validate_citations(enriched_doc)
        print(f"   Validation: {'PASS' if is_valid else 'FAIL'}")

        if enriched_doc.meta.get("citations"):
            ComponentTestHelper.print_citation_summary(enriched_doc)

    # Test CellebriteConverter (requires temp directory)
    print("\n3. Testing CellebriteConverter...")
    try:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = ComponentTestHelper.create_sample_cellebrite_export(
                Path(tmpdir)
            )
            converter = CellebriteConverter(case_id="test-case-123")
            result = converter.run(export_path=str(export_path))
            docs = result["documents"]
            print(f"   Converted {len(docs)} messages")

            if docs:
                first_doc = docs[0]
                print(f"   First message platform: {first_doc.meta.get('platform')}")
                print(f"   First message sender: {first_doc.meta.get('sender')}")
    except Exception as e:
        print(f"   Error: {e}")

    print("\n" + "=" * 60)
    print("Component testing complete!")


if __name__ == "__main__":
    quick_test_components()
