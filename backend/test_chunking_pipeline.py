#!/usr/bin/env python3
"""
Test script for RAGFlow-style legal document chunking pipeline.

This script demonstrates the template-based chunking functionality
for different types of legal documents.
"""

from app.workers.pipelines import create_pipeline, LegalDocumentTemplate


# Sample legal documents for testing
SAMPLE_CASE_LAW = """
SUPREME COURT OF THE UNITED STATES

SMITH v. JONES

No. 22-1234

Argued: January 15, 2024
Decided: March 1, 2024

Justice Roberts delivered the opinion of the Court.

I. SYLLABUS

This case concerns the interpretation of 42 U.S.C. § 1983 in the context of qualified immunity.
The petitioner, John Smith, alleges that Officer Jones violated his Fourth Amendment rights
during a traffic stop on May 1, 2022.

II. OPINION OF THE COURT

The question before us is whether a reasonable officer would have known that the conduct
at issue violated clearly established law. See Harlow v. Fitzgerald, 457 U.S. 800 (1982).

FACTS

On the evening of May 1, 2022, Officer Jones stopped the petitioner for a broken taillight.
During the stop, Officer Jones requested identification and ran a background check.
The stop lasted approximately 45 minutes.

DISCUSSION

Qualified immunity shields government officials from liability unless their conduct violates
clearly established statutory or constitutional rights. See Pearson v. Callahan, 555 U.S. 223 (2009).

The Fourth Amendment protects against unreasonable searches and seizures. U.S. Const. amend. IV.
A traffic stop is a seizure within the meaning of the Fourth Amendment. See Delaware v. Prouse,
440 U.S. 648 (1979).

CONCLUSION

For the foregoing reasons, we hold that the officer's conduct did not violate clearly established law.
The judgment of the Court of Appeals is affirmed.

It is so ordered.
"""

SAMPLE_CONTRACT = """
EMPLOYMENT AGREEMENT

This Employment Agreement (the "Agreement") is entered into as of January 1, 2024,
by and between TechCorp Inc., a Delaware corporation (the "Company"), and Jane Doe (the "Employee").

WHEREAS, the Company desires to employ the Employee, and the Employee desires to accept such employment;

NOW, THEREFORE, in consideration of the mutual covenants and agreements hereinafter set forth,
the parties agree as follows:

ARTICLE I - EMPLOYMENT AND DUTIES

Section 1.1 Position. The Company hereby employs the Employee as Chief Technology Officer,
and the Employee hereby accepts such employment.

Section 1.2 Duties. The Employee shall perform such duties and responsibilities as are
customarily associated with the position of Chief Technology Officer.

Section 1.3 Full Time. The Employee shall devote substantially all of the Employee's business
time and attention to the performance of the Employee's duties hereunder.

ARTICLE II - COMPENSATION AND BENEFITS

Section 2.1 Base Salary. The Company shall pay the Employee an annual base salary of $250,000,
payable in accordance with the Company's normal payroll practices.

Section 2.2 Bonus. The Employee shall be eligible to receive an annual performance bonus
of up to 30% of the Employee's base salary.

Section 2.3 Equity. The Employee shall receive stock options to purchase 10,000 shares
of the Company's common stock, subject to the terms of the Company's Stock Option Plan.

ARTICLE III - TERM AND TERMINATION

Section 3.1 Term. This Agreement shall commence on January 1, 2024, and shall continue
until terminated in accordance with this Article III.

Section 3.2 Termination. Either party may terminate this Agreement upon 30 days' written notice.

ARTICLE IV - CONFIDENTIALITY

Section 4.1 Confidential Information. The Employee acknowledges that during employment,
the Employee will have access to and become acquainted with confidential information.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first above written.
"""

SAMPLE_STATUTE = """
TITLE 42 - THE PUBLIC HEALTH AND WELFARE

CHAPTER 21 - CIVIL RIGHTS

§ 1983. Civil action for deprivation of rights

Every person who, under color of any statute, ordinance, regulation, custom, or usage,
of any State or Territory or the District of Columbia, subjects, or causes to be subjected,
any citizen of the United States or other person within the jurisdiction thereof to the
deprivation of any rights, privileges, or immunities secured by the Constitution and laws,
shall be liable to the party injured in an action at law, suit in equity, or other proper
proceeding for redress, except that in any action brought against a judicial officer for
an act or omission taken in such officer's judicial capacity, injunctive relief shall not
be granted unless a declaratory decree was violated or declaratory relief was unavailable.

For the purposes of this section, any Act of Congress applicable exclusively to the District
of Columbia shall be considered to be a statute of the District of Columbia.

§ 1988. Proceedings in vindication of civil rights

(a) Applicability of statutory and common law

The jurisdiction in civil and criminal matters conferred on the district courts by the
provisions of titles 13, 24, and 70 of the Revised Statutes for the protection of all
persons in the United States in their civil rights, and for their vindication, shall be
exercised and enforced in conformity with the laws of the United States, so far as such
laws are suitable to carry the same into effect.

(b) Attorney's fees

In any action or proceeding to enforce a provision of sections 1981, 1981a, 1982, 1983,
1985, and 1986 of this title, title IX of Public Law 92-318, the Religious Freedom
Restoration Act of 1993, the Religious Land Use and Institutionalized Persons Act of 2000,
title VI of the Civil Rights Act of 1964, or section 13981 of this title, the court,
in its discretion, may allow the prevailing party, other than the United States,
a reasonable attorney's fee as part of the costs.
"""

SAMPLE_BRIEF = """
IN THE UNITED STATES COURT OF APPEALS
FOR THE NINTH CIRCUIT

Case No. 23-5678

JOHN DOE, Plaintiff-Appellant,

v.

CITY OF METROPOLIS, et al., Defendants-Appellees.

APPELLANT'S OPENING BRIEF

I. STATEMENT OF JURISDICTION

This Court has jurisdiction pursuant to 28 U.S.C. § 1291. The district court entered
final judgment on September 15, 2023. Appellant filed a timely notice of appeal on
October 1, 2023.

II. STATEMENT OF ISSUES PRESENTED

1. Whether the district court erred in granting summary judgment to defendants on
   appellant's claim under 42 U.S.C. § 1983 for violation of the Fourth Amendment.

2. Whether the district court erred in concluding that the defendant officers were
   entitled to qualified immunity.

III. STATEMENT OF THE CASE

A. Nature of the Case

This is a civil rights action arising from an unlawful search and seizure that occurred
on March 15, 2022. Appellant alleges that defendant police officers violated his Fourth
Amendment rights when they conducted a warrantless search of his residence.

B. Procedural History

Appellant filed his complaint in the United States District Court for the District of
Metropolis on June 1, 2022. The defendants moved for summary judgment on the basis of
qualified immunity. The district court granted the motion on September 15, 2023.

IV. STATEMENT OF FACTS

On March 15, 2022, at approximately 8:00 PM, defendant officers arrived at appellant's
residence without a warrant. The officers claimed they received an anonymous tip about
suspicious activity. Over appellant's objection, the officers entered the residence
and conducted a search.

V. SUMMARY OF ARGUMENT

The district court erred in granting summary judgment. First, the warrantless search
of appellant's home violated the Fourth Amendment. Second, the law was clearly established
that such a search would be unconstitutional. Therefore, the officers are not entitled
to qualified immunity.

VI. ARGUMENT

A. Standard of Review

This Court reviews de novo a district court's grant of summary judgment. See Celotex Corp.
v. Catrett, 477 U.S. 317 (1986).

B. The Warrantless Search Violated the Fourth Amendment

The Fourth Amendment protects "[t]he right of the people to be secure in their persons,
houses, papers, and effects, against unreasonable searches and seizures." U.S. Const.
amend. IV. Warrantless searches are per se unreasonable, subject only to a few specific
exceptions. See Katz v. United States, 389 U.S. 347 (1967).

Here, the officers had no warrant and no valid exception to the warrant requirement applied.
The officers' claim that they received an anonymous tip does not justify the warrantless
entry and search. See Florida v. J.L., 529 U.S. 266 (2000).

C. The Officers Are Not Entitled to Qualified Immunity

Qualified immunity shields officers from liability unless they violated clearly established
law. See Harlow v. Fitzgerald, 457 U.S. 800 (1982). Here, it was clearly established that
a warrantless search of a home based solely on an anonymous tip violates the Fourth Amendment.

VII. CONCLUSION

For the foregoing reasons, this Court should reverse the district court's grant of summary
judgment and remand for further proceedings.

Respectfully submitted,

/s/ Attorney for Appellant
Jane Smith, Esq.
Smith & Associates
123 Legal Street
Metropolis, ST 12345
(555) 555-5555
"""


def print_separator(title: str = ""):
    """Print a visual separator."""
    print("\n" + "=" * 80)
    if title:
        print(f" {title} ".center(80, "="))
        print("=" * 80)
    print()


def test_pipeline_with_document(doc_text: str, doc_type: str, template: str = None):
    """Test the pipeline with a sample document."""
    print_separator(f"Testing {doc_type}")

    # Create pipeline
    pipeline = create_pipeline(
        chunk_sizes=[512, 256, 128],
        overlap=50
    )

    # Process document
    result = pipeline.process(
        document_text=doc_text,
        document_id=None,
        template=template,
        preserve_structure=True
    )

    # Print results
    print(f"Document Type: {result.metadata.document_type.value}")
    print(f"Processing Time: {result.processing_time:.3f} seconds")
    print(f"Total Chunks: {result.chunk_count}")
    print()

    # Print metadata
    print("Extracted Metadata:")
    print(f"  Case Number: {result.metadata.case_number}")
    print(f"  Parties: {result.metadata.parties}")
    print(f"  Court: {result.metadata.court}")
    print(f"  Judge: {result.metadata.judge}")
    print(f"  Date Filed: {result.metadata.date_filed}")
    print(f"  Contract Parties: {result.metadata.contract_parties}")
    print(f"  Effective Date: {result.metadata.effective_date}")
    print(f"  Statute Citation: {result.metadata.statute_citation}")
    print()

    # Group chunks by size
    chunks_by_size = {}
    for chunk in result.chunks:
        chunk_type = chunk.metadata.chunk_type
        if chunk_type not in chunks_by_size:
            chunks_by_size[chunk_type] = []
        chunks_by_size[chunk_type].append(chunk)

    # Print chunk statistics
    print("Chunk Statistics by Size:")
    for chunk_type in sorted(chunks_by_size.keys()):
        chunks = chunks_by_size[chunk_type]
        total_tokens = sum(c.metadata.token_count for c in chunks)
        avg_tokens = total_tokens / len(chunks) if chunks else 0
        print(f"  {chunk_type}:")
        print(f"    Count: {len(chunks)}")
        print(f"    Total Tokens: {total_tokens}")
        print(f"    Avg Tokens/Chunk: {avg_tokens:.1f}")

        # Show citations if any
        all_citations = []
        for chunk in chunks:
            all_citations.extend(chunk.metadata.citations)
        if all_citations:
            unique_citations = list(set(all_citations))
            print(f"    Citations Found: {len(unique_citations)}")
            if unique_citations:
                print(f"    Sample Citations: {unique_citations[:3]}")

    print()

    # Print sample chunks
    print("Sample Chunks (first 2 from largest size):")
    largest_size = sorted(chunks_by_size.keys(), reverse=True)[0]
    for i, chunk in enumerate(chunks_by_size[largest_size][:2], 1):
        print(f"\n  Chunk {i} ({chunk.metadata.chunk_type}):")
        print(f"    Position: {chunk.metadata.position}")
        print(f"    Tokens: {chunk.metadata.token_count}")
        print(f"    Section Type: {chunk.metadata.custom_fields.get('section_type')}")
        print(f"    Section Title: {chunk.metadata.section_title}")
        print(f"    Text Preview: {chunk.text[:200]}...")
        if chunk.metadata.citations:
            print(f"    Citations: {chunk.metadata.citations[:3]}")


def main():
    """Run all tests."""
    print_separator("RAGFlow-style Legal Document Chunking Pipeline Test")
    print("This script demonstrates template-based chunking for legal documents.")
    print("It processes different document types and creates multi-size chunks.")

    # Test 1: Case Law
    test_pipeline_with_document(SAMPLE_CASE_LAW, "Case Law", template="case_law")

    # Test 2: Contract
    test_pipeline_with_document(SAMPLE_CONTRACT, "Contract", template="contract")

    # Test 3: Statute
    test_pipeline_with_document(SAMPLE_STATUTE, "Statute", template="statute")

    # Test 4: Brief
    test_pipeline_with_document(SAMPLE_BRIEF, "Legal Brief", template="brief")

    # Test 5: Auto-detection
    print_separator("Auto-Detection Test")
    print("Testing automatic document type detection...")
    print()

    test_pipeline_with_document(SAMPLE_CASE_LAW, "Case Law (Auto-Detected)", template=None)

    print_separator("Tests Complete")
    print("The chunking pipeline successfully processed all document types!")
    print()
    print("Key Features Demonstrated:")
    print("  - Template-based chunking (case_law, contract, statute, brief)")
    print("  - Multi-size chunks (512/256/128 tokens)")
    print("  - Structure preservation (sections, articles, etc.)")
    print("  - Citation extraction")
    print("  - Metadata extraction (case numbers, parties, dates, etc.)")
    print("  - Automatic document type detection")


if __name__ == "__main__":
    main()
