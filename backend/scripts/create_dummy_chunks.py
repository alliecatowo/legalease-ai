"""
Create dummy chunks for seeded documents to test search functionality.

This script creates sample text chunks for documents that were seeded but not processed.
This allows testing the search API without needing to upload and process real PDFs.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.chunk import Chunk
from datetime import datetime


# Sample legal text for different document types
SAMPLE_LEGAL_TEXTS = {
    "Employment Agreement": [
        "This Employment Agreement is entered into between Acme Corp and John Johnson, "
        "effective January 1, 2024. The Employee agrees to serve as Senior Software Engineer.",

        "Compensation: The Employee shall receive an annual base salary of $150,000, "
        "payable in accordance with the Company's standard payroll practices.",

        "Confidentiality: The Employee acknowledges that during employment, they may have "
        "access to confidential information and trade secrets belonging to the Company.",

        "Non-Compete Clause: During employment and for twelve (12) months thereafter, "
        "Employee shall not engage in any business competitive with the Company.",

        "Termination: Either party may terminate this agreement with thirty (30) days "
        "written notice. The Company may terminate for cause immediately.",
    ],

    "NDA": [
        "This Non-Disclosure Agreement (NDA) is entered into by and between the parties "
        "to protect confidential information shared during business discussions.",

        "Definition of Confidential Information: All technical and business information "
        "disclosed by either party, including trade secrets, proprietary data, and customer lists.",

        "Obligations: The receiving party shall maintain confidential information in strict "
        "confidence and not disclose to third parties without prior written consent.",

        "Term: This agreement shall remain in effect for a period of five (5) years "
        "from the effective date, unless terminated earlier by mutual agreement.",

        "Remedies: Any breach of this agreement may result in irreparable harm, "
        "and the disclosing party shall be entitled to equitable relief including injunction.",
    ],

    "Service Agreement": [
        "This Service Agreement governs the provision of consulting services by "
        "Consultant to Client for the development of custom software solutions.",

        "Scope of Work: Consultant shall provide software development, system design, "
        "and technical consulting services as outlined in attached Statement of Work.",

        "Payment Terms: Client agrees to pay Consultant $200 per hour for services rendered, "
        "with invoices due within thirty (30) days of receipt.",

        "Intellectual Property: All work product created under this agreement shall be "
        "considered work made for hire and shall be owned exclusively by Client.",

        "Warranties: Consultant warrants that services shall be performed in a professional "
        "and workmanlike manner consistent with industry standards.",
    ],

    "Partnership Agreement": [
        "This Partnership Agreement establishes a general partnership between the parties "
        "for the purpose of operating a legal technology consulting business.",

        "Capital Contributions: Each partner shall contribute $50,000 as initial capital. "
        "Additional contributions may be required by unanimous consent of partners.",

        "Profit and Loss Distribution: Net profits and losses shall be distributed equally "
        "among partners in proportion to their capital contributions.",

        "Management and Control: All partners shall have equal rights in management decisions. "
        "Major decisions require unanimous approval of all partners.",

        "Dissolution: The partnership may be dissolved by mutual written agreement of partners "
        "or automatically upon death or bankruptcy of any partner.",
    ],

    "Lease Agreement": [
        "This Commercial Lease Agreement is for office space located at 123 Main Street, "
        "Suite 400, with a total area of 2,500 square feet.",

        "Term: The initial lease term shall be five (5) years commencing on January 1, 2024, "
        "with two (2) additional five-year renewal options at Tenant's discretion.",

        "Rent: Base rent of $5,000 per month, payable on the first day of each month, "
        "plus proportionate share of operating expenses and property taxes.",

        "Use: The premises shall be used solely for general office purposes and not for "
        "any illegal or hazardous activities. Tenant shall comply with all zoning laws.",

        "Maintenance: Landlord shall maintain structural elements and common areas. "
        "Tenant responsible for interior maintenance and repairs within the premises.",
    ],

    "Purchase Agreement": [
        "This Asset Purchase Agreement governs the sale of substantially all assets "
        "of Seller to Buyer for a purchase price of $1,000,000.",

        "Assets Included: All equipment, inventory, intellectual property, customer lists, "
        "contracts, and goodwill associated with the business operations.",

        "Purchase Price: Total consideration of one million dollars ($1,000,000) payable "
        "$500,000 at closing and $500,000 in twelve monthly installments.",

        "Representations and Warranties: Seller represents that assets are free of liens, "
        "seller has good title, and there are no undisclosed liabilities or litigation.",

        "Indemnification: Seller shall indemnify Buyer against any losses arising from "
        "breach of representations or pre-closing liabilities for a period of two years.",
    ],
}

# Default legal text if document type not recognized
DEFAULT_TEXT = [
    "This legal document contains provisions governing the rights and obligations "
    "of the parties hereto. Each party acknowledges reading and understanding these terms.",

    "The parties agree to act in good faith and deal fairly with each other "
    "in all matters relating to this agreement and the transactions contemplated hereby.",

    "This agreement shall be governed by and construed in accordance with the laws "
    "of the State of California, without regard to conflict of law principles.",

    "Any dispute arising under this agreement shall be resolved through binding arbitration "
    "in accordance with the rules of the American Arbitration Association.",

    "This agreement constitutes the entire agreement between the parties and supersedes "
    "all prior negotiations, understandings, and agreements relating to the subject matter.",
]


def create_chunks_for_document(doc: Document, db: SessionLocal) -> int:
    """
    Create sample chunks for a document.

    Args:
        doc: Document object
        db: Database session

    Returns:
        Number of chunks created
    """
    # Infer document type from filename
    filename_lower = doc.filename.lower()
    doc_type = "Unknown"

    if "employment" in filename_lower or "employment_agreement" in filename_lower:
        doc_type = "Employment Agreement"
    elif "nda" in filename_lower or "non_disclosure" in filename_lower:
        doc_type = "NDA"
    elif "service" in filename_lower:
        doc_type = "Service Agreement"
    elif "partnership" in filename_lower:
        doc_type = "Partnership Agreement"
    elif "lease" in filename_lower:
        doc_type = "Lease Agreement"
    elif "purchase" in filename_lower:
        doc_type = "Purchase Agreement"

    # Get appropriate sample text based on document type
    sample_texts = SAMPLE_LEGAL_TEXTS.get(doc_type, DEFAULT_TEXT)

    chunks_created = 0

    for position, text in enumerate(sample_texts):
        chunk = Chunk(
            document_id=doc.id,
            text=text,
            chunk_type="microblock",  # Could vary: summary, section, microblock
            position=position,
            page_number=(position // 2) + 1,  # Simulate pages
            meta_data={
                "source": "seed_script",
                "generated": True,
                "doc_type": doc_type,
            },
            created_at=datetime.utcnow(),
        )
        db.add(chunk)
        chunks_created += 1

    return chunks_created


def main():
    """Main function to create chunks for all documents."""
    print("🔧 Creating dummy chunks for seeded documents...\n")

    db = SessionLocal()
    try:
        # Get all documents
        documents = db.query(Document).all()

        if not documents:
            print("⚠️  No documents found. Run seed_data.py first.")
            return

        print(f"Found {len(documents)} documents\n")

        total_chunks = 0

        for doc in documents:
            # Check if document already has chunks
            existing_chunks = db.query(Chunk).filter(Chunk.document_id == doc.id).count()

            if existing_chunks > 0:
                print(f"  ⏭️  Skipping {doc.filename} (already has {existing_chunks} chunks)")
                total_chunks += existing_chunks
                continue

            # Create chunks
            chunks_created = create_chunks_for_document(doc, db)
            total_chunks += chunks_created

            # Update document status
            doc.status = DocumentStatus.COMPLETED
            doc.processed_at = datetime.utcnow()

            print(f"  ✅ Created {chunks_created} chunks for {doc.filename}")

        # Commit all changes
        db.commit()

        print(f"\n✨ Successfully created {total_chunks} total chunks across {len(documents)} documents")
        print("\nDocuments are now ready for indexing into Qdrant!")

    except Exception as e:
        print(f"\n❌ Error creating chunks: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
