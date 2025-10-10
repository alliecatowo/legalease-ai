"""
Process seeded documents through the real Docling pipeline.

This script:
1. Creates sample legal text documents
2. Uploads them to MinIO
3. Processes them through the full Docling pipeline
4. Verifies indexing in Qdrant
5. Tests search functionality
"""

import sys
import os
import io

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.core.minio_client import minio_client
from app.workers.pipelines.document_pipeline import DocumentProcessor

# Sample legal document content - matching actual seeded filenames
SAMPLE_DOCUMENTS = {
    "employment_agreement.pdf": """
EMPLOYMENT AGREEMENT

This Employment Agreement ("Agreement") is entered into as of January 1, 2024, by and between Acme Corporation, a Delaware corporation ("Company"), and John Johnson ("Employee").

1. POSITION AND DUTIES
Employee agrees to serve as Senior Software Engineer. Employee shall report to the Chief Technology Officer and shall perform such duties and responsibilities as are customarily associated with such position.

2. COMPENSATION
2.1 Base Salary: Company shall pay Employee an annual base salary of One Hundred Fifty Thousand Dollars ($150,000), payable in accordance with the Company's standard payroll practices.

2.2 Benefits: Employee shall be entitled to participate in all employee benefit programs maintained by the Company for its employees, subject to the terms and conditions of such programs.

3. CONFIDENTIALITY
Employee acknowledges that during employment, Employee may have access to and become acquainted with various trade secrets, confidential information, and proprietary information of the Company, including but not limited to technical data, customer lists, business strategies, and financial information.

Employee agrees to hold in strict confidence and not to disclose to any third party any such confidential information without the prior written consent of the Company.

4. NON-COMPETE
During employment and for a period of twelve (12) months following termination of employment, Employee shall not, directly or indirectly, engage in any business that competes with the Company within a fifty (50) mile radius of any Company facility.

5. TERMINATION
5.1 At-Will Employment: Employment is at-will and may be terminated by either party at any time, with or without cause, with thirty (30) days written notice.

5.2 Company Termination for Cause: Company may terminate Employee immediately for cause, including but not limited to: material breach of this Agreement, gross misconduct, conviction of a felony, or willful refusal to perform duties.

6. INTELLECTUAL PROPERTY
All inventions, discoveries, improvements, software, and works of authorship created by Employee during employment shall be the sole property of the Company.

7. GOVERNING LAW
This Agreement shall be governed by and construed in accordance with the laws of the State of California.

IN WITNESS WHEREOF, the parties have executed this Employment Agreement as of the date first written above.

ACME CORPORATION                    EMPLOYEE
By: Jane Smith                      John Johnson
Title: CEO                          Date: January 1, 2024
Date: January 1, 2024
""",

    "nda.pdf": """
NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is entered into as of March 15, 2024, by and between Tech Innovations Inc. ("Disclosing Party") and Global Partners LLC ("Receiving Party").

RECITALS
WHEREAS, the parties wish to explore a potential business relationship; and
WHEREAS, in connection with such discussions, Disclosing Party may disclose certain confidential and proprietary information to Receiving Party;

NOW, THEREFORE, in consideration of the mutual covenants and agreements contained herein, the parties agree as follows:

1. DEFINITION OF CONFIDENTIAL INFORMATION
"Confidential Information" means all information disclosed by Disclosing Party to Receiving Party, whether orally, in writing, or in any other form, including but not limited to:
   a) Technical data, trade secrets, know-how, research, product plans, software, inventions
   b) Customer information, customer lists, supplier information
   c) Financial information, pricing, costs, profits, sales data
   d) Business plans, marketing strategies, market research
   e) Any other information that is marked as "Confidential" or should reasonably be understood to be confidential

2. OBLIGATIONS OF RECEIVING PARTY
Receiving Party agrees to:
   a) Hold all Confidential Information in strict confidence
   b) Not disclose Confidential Information to any third parties without prior written consent
   c) Use Confidential Information solely for the purpose of evaluating the potential business relationship
   d) Protect Confidential Information using the same degree of care as it uses for its own confidential information
   e) Limit access to Confidential Information to employees and agents with a legitimate need to know

3. EXCLUSIONS FROM CONFIDENTIAL INFORMATION
Confidential Information shall not include information that:
   a) Was publicly known at the time of disclosure
   b) Becomes publicly known through no breach of this Agreement
   c) Was rightfully in Receiving Party's possession prior to disclosure
   d) Is independently developed by Receiving Party without use of Confidential Information
   e) Is rightfully received from a third party without breach of confidentiality obligation

4. TERM
This Agreement shall commence on the date first written above and shall continue for a period of five (5) years.

5. RETURN OF MATERIALS
Upon termination of discussions or upon request by Disclosing Party, Receiving Party shall promptly return or destroy all Confidential Information and all copies thereof.

6. REMEDIES
Receiving Party acknowledges that disclosure of Confidential Information would cause irreparable harm to Disclosing Party. Accordingly, Disclosing Party shall be entitled to seek equitable relief, including injunction and specific performance, in addition to all other remedies available at law or in equity.

7. GOVERNING LAW
This Agreement shall be governed by the laws of the State of Delaware, without regard to its conflict of laws principles.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.

TECH INNOVATIONS INC.              GLOBAL PARTNERS LLC
By: Robert Chen                    By: Maria Garcia
Title: CTO                         Title: VP Business Development
Date: March 15, 2024              Date: March 15, 2024
""",

    "service_agreement.pdf": """
PROFESSIONAL SERVICES AGREEMENT

This Professional Services Agreement ("Agreement") is entered into as of February 10, 2024, between Consulting Experts LLC, a California limited liability company ("Consultant"), and Enterprise Solutions Corp ("Client").

1. SERVICES
Consultant agrees to provide the following professional services ("Services"):
   - Software architecture design and review
   - System integration consulting
   - Technical documentation and training
   - Code review and quality assurance
   - Performance optimization and scalability analysis

2. TERM
This Agreement shall commence on March 1, 2024 and continue until December 31, 2024, unless earlier terminated in accordance with Section 8.

3. COMPENSATION
3.1 Fees: Client shall pay Consultant at the rate of Two Hundred Dollars ($200.00) per hour for Services rendered.

3.2 Expenses: Client shall reimburse Consultant for all reasonable, pre-approved out-of-pocket expenses incurred in connection with the Services, including travel, lodging, and meals.

3.3 Invoicing: Consultant shall submit invoices on a monthly basis. Payment is due within thirty (30) days of receipt of invoice.

4. INDEPENDENT CONTRACTOR
Consultant is an independent contractor and not an employee of Client. Consultant shall be responsible for all taxes, insurance, and benefits.

5. WORK PRODUCT
5.1 Ownership: All work product, deliverables, inventions, and intellectual property created by Consultant in the course of performing Services shall be considered "work made for hire" and shall be the sole and exclusive property of Client.

5.2 Assignment: To the extent any work product is not considered work made for hire, Consultant hereby assigns all right, title, and interest in such work product to Client.

6. CONFIDENTIALITY
Consultant agrees to maintain the confidentiality of all Client information and shall not disclose such information to any third party without Client's prior written consent.

7. WARRANTIES
7.1 Professional Standards: Consultant warrants that Services shall be performed in a professional and workmanlike manner consistent with industry standards.

7.2 Authority: Each party represents that it has full authority to enter into this Agreement.

7.3 No Conflicts: Consultant represents that performance of Services does not violate any agreement or obligation to any third party.

8. TERMINATION
8.1 Convenience: Either party may terminate this Agreement upon thirty (30) days written notice.

8.2 Cause: Either party may terminate immediately upon written notice if the other party materially breaches this Agreement and fails to cure such breach within fifteen (15) days of written notice.

8.3 Effect of Termination: Upon termination, Client shall pay Consultant for all Services performed through the termination date.

9. LIABILITY
9.1 Limitation: Consultant's total liability under this Agreement shall not exceed the total fees paid by Client in the twelve (12) months preceding the claim.

9.2 Exclusions: Neither party shall be liable for indirect, incidental, consequential, or punitive damages.

10. GENERAL PROVISIONS
10.1 Entire Agreement: This Agreement constitutes the entire agreement between the parties.

10.2 Amendment: This Agreement may only be amended in writing signed by both parties.

10.3 Governing Law: This Agreement shall be governed by California law.

10.4 Assignment: Neither party may assign this Agreement without the other party's written consent.

IN WITNESS WHEREOF, the parties have executed this Agreement.

CONSULTING EXPERTS LLC             ENTERPRISE SOLUTIONS CORP
By: David Williams                 By: Sarah Johnson
Title: Managing Partner            Title: COO
Date: February 10, 2024           Date: February 10, 2024
""",

    "partnership_agreement.pdf": """
PARTNERSHIP AGREEMENT

This Partnership Agreement ("Agreement") is entered into as of April 1, 2024, by and between the following individuals (collectively, the "Partners"):

Jennifer Martinez
Michael Thompson
Patricia Lee

The Partners desire to form a general partnership (the "Partnership") for the purpose of operating a legal technology consulting business.

1. PARTNERSHIP NAME AND BUSINESS
1.1 Name: The Partnership shall operate under the name "LegalTech Advisors."

1.2 Principal Place of Business: The principal office shall be located at 100 Market Street, San Francisco, CA 94103.

1.3 Purpose: The purpose of the Partnership is to provide legal technology consulting, software implementation, and training services to law firms and corporate legal departments.

2. TERM
The Partnership shall commence on April 1, 2024, and shall continue until dissolved in accordance with this Agreement or by operation of law.

3. CAPITAL CONTRIBUTIONS
3.1 Initial Contributions: Each Partner shall contribute Fifty Thousand Dollars ($50,000) as initial capital. Contributions shall be made by April 15, 2024.

3.2 Additional Contributions: Additional capital contributions may be required by unanimous vote of the Partners.

3.3 Capital Accounts: A separate capital account shall be maintained for each Partner.

4. PROFIT AND LOSS DISTRIBUTION
Net profits and losses of the Partnership shall be distributed to the Partners in equal shares (one-third each), unless otherwise agreed in writing.

5. MANAGEMENT AND CONTROL
5.1 Equal Management Rights: Each Partner shall have equal rights in the management and conduct of Partnership business.

5.2 Voting: Except as otherwise provided, all decisions shall be made by majority vote.

5.3 Unanimous Consent Required: The following actions require unanimous consent:
   a) Admission of new partners
   b) Amendment of this Agreement
   c) Sale of substantially all Partnership assets
   d) Merger or dissolution of Partnership
   e) Loans or guarantees exceeding $25,000
   f) Purchase of real property

6. DUTIES AND RESTRICTIONS
6.1 Full-Time Devotion: Each Partner shall devote full time and best efforts to Partnership business.

6.2 Competing Activities: No Partner shall engage in any business that competes with the Partnership without written consent of all other Partners.

6.3 Compensation: Partners shall not receive salaries but may draw against anticipated profits as agreed by majority vote.

7. BOOKS AND RECORDS
7.1 Accounting: The Partnership shall maintain complete and accurate books of account using the accrual method.

7.2 Fiscal Year: The fiscal year shall be the calendar year.

7.3 Bank Accounts: All Partnership funds shall be deposited in bank accounts in the Partnership name. Checks shall require signatures of any two Partners.

8. TRANSFER OF PARTNERSHIP INTEREST
8.1 Restriction on Transfer: No Partner may transfer, sell, or assign their Partnership interest without written consent of all other Partners.

8.2 Right of First Refusal: Before any permitted transfer to a third party, remaining Partners shall have a right of first refusal to purchase the interest on the same terms.

9. WITHDRAWAL AND DISSOLUTION
9.1 Voluntary Withdrawal: A Partner may voluntarily withdraw by giving ninety (90) days written notice.

9.2 Automatic Dissolution: The Partnership shall automatically dissolve upon:
   a) Written agreement of all Partners
   b) Death or bankruptcy of any Partner
   c) Any event that makes it unlawful to continue Partnership business

9.3 Winding Up: Upon dissolution, the Partnership shall be wound up, assets shall be liquidated, and proceeds distributed in the following order:
   a) Payment of debts and liabilities
   b) Return of capital contributions
   c) Distribution of remaining assets according to profit-sharing ratio

10. DISPUTE RESOLUTION
10.1 Mediation: Any dispute shall first be submitted to mediation.

10.2 Arbitration: If mediation is unsuccessful, the dispute shall be resolved by binding arbitration in San Francisco, California.

11. GENERAL PROVISIONS
11.1 Entire Agreement: This Agreement constitutes the entire agreement among the Partners.

11.2 Amendment: This Agreement may be amended only by written agreement of all Partners.

11.3 Governing Law: This Agreement shall be governed by California law.

11.4 Severability: If any provision is invalid, the remaining provisions shall continue in effect.

IN WITNESS WHEREOF, the Partners have executed this Agreement.

_________________________          Date: _______________
Jennifer Martinez

_________________________          Date: _______________
Michael Thompson

_________________________          Date: _______________
Patricia Lee
""",

    "lease_agreement.pdf": """
COMMERCIAL LEASE AGREEMENT

This Commercial Lease Agreement ("Lease") is entered into as of May 1, 2024, between Pacific Properties LLC ("Landlord") and TechStart Inc. ("Tenant").

1. PREMISES
Landlord hereby leases to Tenant the following premises ("Premises"):
   Address: 123 Main Street, Suite 400, San Francisco, CA 94105
   Square Footage: 2,500 square feet
   Use: General office purposes

2. TERM
2.1 Initial Term: The initial lease term shall be five (5) years, commencing on June 1, 2024 and ending on May 31, 2029.

2.2 Renewal Options: Tenant shall have two (2) options to renew for additional five-year terms, exercisable by written notice given at least one hundred eighty (180) days prior to expiration.

3. RENT
3.1 Base Rent: Tenant shall pay monthly base rent of Five Thousand Dollars ($5,000), payable on or before the first day of each month.

3.2 Late Charges: Rent not paid within five (5) days of due date shall incur a late charge of five percent (5%) of the unpaid amount.

3.3 Rent Increases: Base rent shall increase by three percent (3%) annually on each anniversary of the commencement date.

4. ADDITIONAL CHARGES
4.1 Operating Expenses: Tenant shall pay its proportionate share (12.5%) of building operating expenses, including:
   - Property taxes and assessments
   - Building insurance premiums
   - Common area maintenance (CAM) charges
   - Utilities for common areas
   - Management fees

4.2 Utilities: Tenant shall pay directly for all utilities consumed in the Premises, including electricity, gas, water, sewer, telephone, and internet.

5. SECURITY DEPOSIT
Tenant shall deposit with Landlord Ten Thousand Dollars ($10,000) as security. The deposit shall be held without interest and may be applied to cure any default by Tenant.

6. USE OF PREMISES
6.1 Permitted Use: The Premises shall be used solely for general office purposes consistent with a Class A office building.

6.2 Prohibited Uses: Tenant shall not use the Premises for any illegal, hazardous, or nuisance-creating activities.

6.3 Compliance with Laws: Tenant shall comply with all applicable federal, state, and local laws, ordinances, and regulations.

7. MAINTENANCE AND REPAIRS
7.1 Landlord's Obligations: Landlord shall maintain and repair:
   - Structural elements (roof, foundation, exterior walls)
   - Building systems (HVAC, plumbing, electrical in common areas)
   - Common areas (lobbies, hallways, elevators, parking)

7.2 Tenant's Obligations: Tenant shall maintain and repair:
   - Interior of Premises (walls, floors, ceilings)
   - Interior fixtures and equipment
   - HVAC system serving the Premises
   - Any damage caused by Tenant's negligence or misuse

8. ALTERATIONS
Tenant shall not make any alterations, additions, or improvements to the Premises without Landlord's prior written consent. All approved alterations shall become Landlord's property upon installation.

9. INSURANCE
9.1 Landlord's Insurance: Landlord shall maintain property insurance on the building and liability insurance for common areas.

9.2 Tenant's Insurance: Tenant shall maintain:
   - Commercial general liability insurance ($2,000,000 minimum)
   - Property insurance on Tenant's fixtures and personal property
   - Workers' compensation insurance as required by law

Tenant shall name Landlord as additional insured on liability policies.

10. ASSIGNMENT AND SUBLETTING
Tenant shall not assign this Lease or sublet the Premises without Landlord's prior written consent, which shall not be unreasonably withheld.

11. DEFAULT AND REMEDIES
11.1 Events of Default: The following shall constitute default:
   - Failure to pay rent within ten (10) days of due date
   - Violation of any Lease term not cured within thirty (30) days of written notice
   - Bankruptcy or insolvency of Tenant
   - Abandonment of Premises

11.2 Landlord's Remedies: Upon default, Landlord may:
   - Terminate this Lease
   - Re-enter and take possession of Premises
   - Sue for damages and unpaid rent
   - Exercise any remedy available at law or in equity

12. TERMINATION
Either party may terminate this Lease upon material breach by the other party that remains uncured after the applicable cure period.

13. GENERAL PROVISIONS
13.1 Entire Agreement: This Lease constitutes the entire agreement between the parties.

13.2 Amendment: This Lease may be amended only by written instrument signed by both parties.

13.3 Governing Law: This Lease shall be governed by California law.

13.4 Notices: All notices shall be in writing and delivered by certified mail or personal delivery.

13.5 Severability: If any provision is invalid, the remaining provisions shall remain in effect.

IN WITNESS WHEREOF, the parties have executed this Lease.

LANDLORD:                          TENANT:
PACIFIC PROPERTIES LLC             TECHSTART INC.

By: ________________________       By: ________________________
Name: Robert Wilson               Name: Lisa Chen
Title: Managing Member            Title: CEO
Date: May 1, 2024                Date: May 1, 2024
""",

    "purchase_agreement.pdf": """
ASSET PURCHASE AGREEMENT

This Asset Purchase Agreement ("Agreement") is made as of June 15, 2024, by and between DataSoft Solutions Inc., a Delaware corporation ("Seller"), and Innovation Systems Corp., a California corporation ("Buyer").

RECITALS
WHEREAS, Seller is engaged in the business of developing and licensing customer relationship management software; and
WHEREAS, Buyer desires to purchase, and Seller desires to sell, substantially all of the assets of Seller's business;

NOW, THEREFORE, in consideration of the mutual covenants contained herein, the parties agree as follows:

1. PURCHASE AND SALE OF ASSETS
1.1 Assets to be Purchased: Seller agrees to sell, transfer, and deliver to Buyer, and Buyer agrees to purchase, the following assets (collectively, the "Purchased Assets"):

   a) Tangible Assets:
      - All equipment, furniture, fixtures, and supplies
      - Computer hardware and servers
      - Office equipment and furnishings

   b) Intangible Assets:
      - All intellectual property rights (patents, trademarks, copyrights)
      - Software code and technical documentation
      - Customer lists and contracts
      - Vendor agreements and relationships
      - Domain names and websites
      - Goodwill associated with the business

   c) Contracts and Agreements:
      - All customer licensing agreements
      - Maintenance and support contracts
      - Vendor and supplier contracts (with consent)

1.2 Excluded Assets: The following assets shall be retained by Seller:
   - Cash and cash equivalents
   - Accounts receivable as of the closing date
   - Seller's corporate minute books and stock records
   - Insurance policies

2. PURCHASE PRICE
2.1 Total Consideration: The total purchase price for the Purchased Assets shall be One Million Dollars ($1,000,000) (the "Purchase Price").

2.2 Payment Terms:
   a) Closing Payment: Five Hundred Thousand Dollars ($500,000) shall be paid at closing by wire transfer of immediately available funds

   b) Deferred Payments: Five Hundred Thousand Dollars ($500,000) shall be paid in twelve (12) equal monthly installments of $41,666.67, plus interest at 5% per annum, beginning thirty (30) days after closing

2.3 Allocation: The Purchase Price shall be allocated among the Purchased Assets as set forth in Exhibit A.

3. ASSUMPTION OF LIABILITIES
3.1 Assumed Liabilities: Buyer shall assume and agree to pay, perform, and discharge only the following liabilities:
   - Obligations under customer contracts in the ordinary course
   - Accrued but unpaid expenses under assumed contracts

3.2 Excluded Liabilities: Buyer shall not assume any other liabilities of Seller, including:
   - Any debt, loans, or credit obligations
   - Tax liabilities for periods prior to closing
   - Any litigation or contingent liabilities
   - Employment-related liabilities

4. REPRESENTATIONS AND WARRANTIES OF SELLER
Seller represents and warrants to Buyer as follows:

4.1 Organization and Authority: Seller is duly organized and validly existing. Seller has full power and authority to execute this Agreement and consummate the transactions contemplated hereby.

4.2 Title to Assets: Seller has good and marketable title to all Purchased Assets, free and clear of all liens, encumbrances, and claims.

4.3 Financial Statements: The financial statements provided to Buyer fairly present Seller's financial condition and have been prepared in accordance with GAAP.

4.4 No Undisclosed Liabilities: Seller has no liabilities except as disclosed in writing to Buyer.

4.5 Compliance with Laws: Seller has complied with all applicable laws and regulations.

4.6 Intellectual Property: Seller owns or has valid licenses for all intellectual property used in the business. There are no claims or proceedings regarding Seller's intellectual property.

4.7 Contracts: All material contracts are valid and enforceable. Seller is not in default under any material contract.

4.8 Litigation: There is no pending or threatened litigation against Seller or affecting the Purchased Assets.

4.9 Employees: Seller has provided Buyer with a complete list of all employees, including compensation and benefits.

5. REPRESENTATIONS AND WARRANTIES OF BUYER
Buyer represents and warrants to Seller as follows:

5.1 Organization and Authority: Buyer is duly organized and validly existing. Buyer has full power and authority to execute this Agreement.

5.2 Financial Capability: Buyer has sufficient funds to complete the purchase.

6. COVENANTS OF SELLER
6.1 Conduct of Business: Between execution and closing, Seller shall:
   - Operate the business in the ordinary course
   - Maintain assets in good condition
   - Not enter into any material contracts without Buyer's consent
   - Maintain adequate insurance coverage

6.2 Access to Information: Seller shall provide Buyer reasonable access to books, records, and facilities for due diligence.

6.3 Non-Competition: For a period of three (3) years following closing, Seller shall not, directly or indirectly:
   - Engage in any business competitive with the business
   - Solicit customers or employees of the business
   - Use or disclose any confidential information

7. CONDITIONS TO CLOSING
7.1 Conditions to Buyer's Obligations:
   - Representations and warranties of Seller shall be true and accurate
   - No material adverse change in the business
   - Satisfactory completion of due diligence
   - Receipt of necessary third-party consents

7.2 Conditions to Seller's Obligations:
   - Representations and warranties of Buyer shall be true and accurate
   - Receipt of Purchase Price payment

8. CLOSING
8.1 Closing Date: The closing shall take place on July 15, 2024, or such other date as mutually agreed.

8.2 Closing Deliveries by Seller:
   - Bill of sale and assignment documents
   - Assignments of intellectual property
   - Customer contract assignments
   - Good standing certificates

8.3 Closing Deliveries by Buyer:
   - Payment of closing portion of Purchase Price
   - Assumption agreement for Assumed Liabilities

9. INDEMNIFICATION
9.1 Indemnification by Seller: Seller shall indemnify Buyer against any losses arising from:
   - Breach of Seller's representations or warranties
   - Excluded Liabilities
   - Any misrepresentation or omission by Seller

9.2 Indemnification by Buyer: Buyer shall indemnify Seller against any losses arising from:
   - Breach of Buyer's representations or warranties
   - Assumed Liabilities

9.3 Indemnification Procedures: Claims must be made in writing within two (2) years of closing.

9.4 Limitations: Indemnification shall not exceed the Purchase Price.

10. TERMINATION
This Agreement may be terminated:
   a) By mutual written consent
   b) By either party if closing has not occurred by August 31, 2024
   c) By either party upon material breach by the other party

11. GENERAL PROVISIONS
11.1 Entire Agreement: This Agreement constitutes the entire agreement between the parties.

11.2 Amendment: This Agreement may be amended only by written instrument signed by both parties.

11.3 Governing Law: This Agreement shall be governed by Delaware law.

11.4 Dispute Resolution: Any disputes shall be resolved by binding arbitration in Delaware.

11.5 Expenses: Each party shall bear its own expenses.

11.6 Confidentiality: All information exchanged shall remain confidential.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.

SELLER:                            BUYER:
DATASOFT SOLUTIONS INC.            INNOVATION SYSTEMS CORP.

By: ________________________       By: ________________________
Name: Thomas Anderson             Name: Catherine Lee
Title: CEO                        Title: President
Date: June 15, 2024              Date: June 15, 2024
""",

    "termination_letter.pdf": """
NOTICE OF EMPLOYMENT TERMINATION

Date: March 15, 2024

To: Sarah Williams
    Employee ID: EMP-4521
    Position: Marketing Manager

FROM: Human Resources Department
      Acme Corporation

SUBJECT: Notice of Employment Termination

Dear Ms. Williams,

This letter serves as formal notification that your employment with Acme Corporation will be terminated effective April 1, 2024.

REASON FOR TERMINATION:
This decision has been made due to continued performance issues that have not improved despite multiple written warnings and performance improvement plans implemented over the past six months. Specifically:

1. Failure to meet quarterly sales targets for three consecutive quarters
2. Repeated missed deadlines for marketing campaign deliverables
3. Inadequate communication with team members and management
4. Non-compliance with company attendance policies

TERMINATION DETAILS:
- Last Day of Work: March 31, 2024
- Final Paycheck: You will receive your final paycheck on April 7, 2024, including:
  * Salary through March 31, 2024
  * Accrued vacation time (10 days)
  * Pro-rated bonus (if applicable)

BENEFITS CONTINUATION:
- Health Insurance: Coverage will continue through April 30, 2024
- COBRA: You will receive information about continuing your health insurance under COBRA
- 401(k): Your 401(k) account will remain active. Contact the plan administrator regarding distribution options

RETURN OF COMPANY PROPERTY:
You are required to return all company property on or before your last day of work, including:
- Company laptop (Serial #: AC-2024-4521)
- Mobile phone (555-0123)
- Building access badge
- Company credit card
- Any proprietary documents or materials

CONFIDENTIALITY AND NON-COMPETE:
Please be reminded that your obligations under the Employment Agreement, including confidentiality and non-compete provisions, remain in effect after termination.

SEVERANCE PACKAGE:
In consideration of your three years of service, the Company is offering a severance package of four weeks' salary ($8,000), contingent upon signing the attached Release and Waiver agreement within twenty-one (21) days.

UNEMPLOYMENT BENEFITS:
You may be eligible for unemployment benefits. Contact the California Employment Development Department (EDD) for information.

REFERENCES:
The Company will provide employment verification only, including dates of employment and position held. No performance-related information will be disclosed without your written authorization.

If you have any questions regarding this termination or the information provided above, please contact Human Resources at hr@acmecorp.com or (555) 555-5555.

We wish you success in your future endeavors.

Sincerely,

Jennifer Martinez
Director of Human Resources
Acme Corporation
""",

    "performance_reviews.pdf": """
ANNUAL PERFORMANCE REVIEW

Employee Information:
Name: Michael Chen
Employee ID: EMP-7832
Position: Senior Software Engineer
Department: Engineering - Backend Services
Review Period: January 1, 2024 - December 31, 2024
Review Date: January 15, 2025
Reviewer: David Thompson, Engineering Manager

OVERALL RATING: Exceeds Expectations (4.5/5.0)

=== PERFORMANCE CATEGORIES ===

1. TECHNICAL SKILLS (5.0/5.0) - Outstanding
   Strengths:
   - Demonstrated mastery of Python, Go, and distributed systems architecture
   - Successfully designed and implemented the new microservices infrastructure
   - Mentored three junior engineers, significantly improving team capabilities
   - Contributed to 15 open-source projects, enhancing company reputation

   Areas for Development:
   - Could expand knowledge of frontend technologies to better collaborate with UI team

2. QUALITY OF WORK (4.5/5.0) - Exceeds Expectations
   Strengths:
   - Code consistently passes review with minimal revisions
   - Implemented comprehensive testing strategy resulting in 40% reduction in bugs
   - Documentation is thorough and well-maintained
   - Proactive in addressing technical debt

   Areas for Development:
   - Occasionally over-engineers solutions; balance between perfection and delivery

3. PRODUCTIVITY (4.5/5.0) - Exceeds Expectations
   Strengths:
   - Completed 95% of assigned tasks on time or ahead of schedule
   - Delivered critical payment processing system two weeks early
   - Effectively manages multiple priorities and competing deadlines
   - Reduced average API response time by 60%

   Areas for Development:
   - Could improve estimation accuracy for complex projects

4. COLLABORATION & TEAMWORK (4.0/5.0) - Meets Expectations
   Strengths:
   - Excellent communicator in technical discussions
   - Willingly shares knowledge and assists colleagues
   - Positive attitude and constructive in team meetings
   - Successfully led cross-functional API integration project

   Areas for Development:
   - Be more proactive in seeking input from non-technical stakeholders
   - Work on diplomacy when disagreeing with architectural decisions

5. LEADERSHIP & INITIATIVE (5.0/5.0) - Outstanding
   Strengths:
   - Independently identified and resolved critical security vulnerabilities
   - Proposed and implemented automated deployment pipeline, saving 10 hours/week
   - Led architecture review committee, improving system design quality
   - Volunteered to present at industry conference, enhancing company visibility

=== KEY ACCOMPLISHMENTS ===

1. Microservices Migration Project
   - Led the migration of monolithic application to microservices architecture
   - Reduced deployment time from 2 hours to 15 minutes
   - Improved system scalability to handle 10x traffic growth

2. Payment Processing System
   - Designed and implemented PCI-DSS compliant payment processing system
   - Integrated with three major payment gateways
   - Achieved 99.99% uptime SLA

3. Technical Mentorship
   - Mentored three junior engineers who were promoted within the year
   - Created comprehensive onboarding documentation
   - Established code review best practices for the team

4. Open Source Contributions
   - Made significant contributions to company's open-source projects
   - Presented at two industry conferences on behalf of company
   - Attracted high-quality engineering candidates through technical blog posts

=== GOALS FOR NEXT REVIEW PERIOD ===

1. Technical Growth
   - Obtain AWS Solutions Architect Professional certification
   - Lead the implementation of machine learning pipeline for product recommendations
   - Expand expertise in Kubernetes and cloud-native technologies

2. Leadership Development
   - Mentor two additional junior engineers
   - Present at three industry conferences or meetups
   - Contribute to hiring by conducting technical interviews

3. Business Impact
   - Reduce infrastructure costs by 25% through optimization
   - Improve API performance benchmarks by 30%
   - Lead evaluation and adoption of new monitoring tools

=== COMPENSATION ADJUSTMENT ===

Based on exceptional performance, the following adjustments are approved:

- Base Salary Increase: 8% ($120,000 → $129,600)
- Performance Bonus: $15,000 (Target achieved: 120%)
- Stock Options: Additional 1,000 options granted
- Effective Date: February 1, 2025

=== EMPLOYEE COMMENTS ===

"I'm grateful for the opportunities to lead significant projects this year. The microservices migration was challenging but incredibly rewarding. I appreciate the trust placed in me to mentor junior engineers and represent the company at conferences. I'm excited about the goals for next year, particularly the ML pipeline project. I would like more exposure to product strategy discussions to better align technical decisions with business objectives."

=== MANAGER'S SUMMARY ===

Michael continues to be one of our top performers and a key technical leader on the team. His technical expertise, combined with his willingness to mentor others and take on challenging projects, makes him invaluable to the organization. His contributions have directly impacted our ability to scale and compete in the market. I recommend him for promotion to Staff Engineer to be considered in Q3 2025.

===================================

EMPLOYEE SIGNATURE: _____________________ DATE: _______

MANAGER SIGNATURE: _____________________ DATE: _______

HR REPRESENTATIVE: _____________________ DATE: _______
""",

    "medical_records.pdf": """
CONFIDENTIAL MEDICAL RECORDS

PATIENT INFORMATION:
Name: Patricia Johnson
Date of Birth: 08/15/1975
Patient ID: MRN-458921
Date of Records: January 1, 2024 - December 31, 2024

MEDICAL HISTORY SUMMARY

CHIEF COMPLAINTS:
- Chronic lower back pain following workplace incident
- Limited mobility and range of motion
- Sleep disturbance due to pain
- Anxiety related to work injury

RELEVANT MEDICAL HISTORY:
1. Workplace Incident (March 15, 2024):
   - Lifting injury while moving file boxes at office
   - Immediate onset of acute lower back pain
   - Initial treatment at workplace clinic

2. Subsequent Medical Treatment:
   - Emergency Room visit (March 15, 2024)
   - Primary care physician visits (ongoing)
   - Physical therapy (12 weeks, April-June 2024)
   - Pain management specialist consultation (July 2024)
   - MRI and diagnostic imaging (May 2024)

DIAGNOSTIC FINDINGS:

MRI Lumbar Spine (May 20, 2024):
- L4-L5 disc herniation with nerve root impingement
- Moderate degenerative disc disease at L3-L4 and L5-S1
- Mild spinal stenosis
- No evidence of fracture or tumor

Functional Capacity Evaluation (August 10, 2024):
- Reduced lifting capacity: Maximum 15 lbs (pre-injury: 50 lbs)
- Limited bending and twisting ability
- Prolonged sitting tolerance: 20 minutes maximum
- Standing tolerance: 30 minutes maximum
- Walking distance: 1/4 mile before pain onset

TREATMENT HISTORY:

Medications:
1. Ibuprofen 800mg three times daily (ongoing)
2. Cyclobenzaprine 10mg at bedtime for muscle spasms
3. Gabapentin 300mg three times daily for nerve pain
4. Tramadol 50mg as needed for breakthrough pain (prescribed June 2024)

Physical Therapy (April 1 - June 30, 2024):
- 24 sessions completed
- Core strengthening exercises
- Manual therapy and mobilization
- Pain management techniques
- Home exercise program established

Interventional Procedures:
- Epidural steroid injection (June 15, 2024) - Moderate temporary relief
- Trigger point injections (July 22, 2024) - Minimal improvement

Work Restrictions (Effective March 16, 2024 - Present):
- No lifting greater than 15 pounds
- No prolonged sitting (>20 minutes without break)
- No bending, twisting, or reaching overhead
- Ability to alternate between sitting and standing
- No climbing ladders or stairs
- Limited to 4-hour work days initially, gradually increased to 6 hours

FUNCTIONAL LIMITATIONS:
Based on medical evaluation and functional capacity assessment, patient demonstrates the following persistent limitations:

1. Physical Capacity:
   - Reduced to light-duty work capacity
   - Cannot return to previous administrative assistant position requiring filing and document management
   - Requires ergonomic workspace with adjustable desk
   - Needs frequent position changes

2. Activities of Daily Living Impact:
   - Difficulty with household chores (vacuuming, laundry)
   - Reduced recreational activities (previously active in hiking, gardening)
   - Sleep quality impaired due to pain
   - Dependence on others for heavy lifting tasks

3. Psychological Impact:
   - Anxiety regarding re-injury
   - Frustration with limited mobility
   - Concern about job security and career prospects
   - Mild depression related to chronic pain (referred to counseling)

PROGNOSIS:
Based on clinical findings and response to treatment:
- Guarded prognosis for return to pre-injury functional level
- Permanent partial disability likely
- Ongoing pain management required
- Future surgical intervention may be considered if conservative treatment fails
- Maximum medical improvement not yet reached as of December 2024
- Continued physical therapy and pain management recommended

WORK STATUS ASSESSMENT:
- Patient is currently capable of sedentary to light-duty work only
- Unable to return to previous position requiring regular lifting and filing
- Accommodations required: ergonomic workstation, frequent breaks, modified schedule
- Vocational rehabilitation may be beneficial for retraining in suitable occupation

MEDICAL NECESSITY FOR ONGOING TREATMENT:
Continued medical treatment is medically necessary and directly related to the workplace injury, including:
- Monthly pain management appointments
- Ongoing physical therapy (maintenance program)
- Medication management
- Periodic diagnostic imaging to monitor condition
- Potential surgical consultation if condition worsens

===================================

PHYSICIAN CERTIFICATION:

I certify that the above represents an accurate summary of Patricia Johnson's medical condition, treatment, and functional limitations resulting from the workplace injury sustained on March 15, 2024.

Dr. Robert Martinez, MD
Board Certified - Physical Medicine and Rehabilitation
License #: CA-MD-89234
Date: December 31, 2024

CONFIDENTIALITY NOTICE:
These records contain privileged medical information protected by HIPAA regulations. Unauthorized disclosure is prohibited by law.
""",

    "expert_opinion.pdf": """
EXPERT MEDICAL OPINION

Case: Johnson v. Acme Corporation
Case Number: CV-2024-003421
Expert: Dr. Elizabeth Chen, MD, FAAPMR
Board Certification: Physical Medicine and Rehabilitation
License: California Medical Board #CA-MD-45892
Date of Opinion: November 15, 2024

Re: Medical Causation Analysis - Patricia Johnson Workplace Injury

I. QUALIFICATIONS

I am a board-certified physician in Physical Medicine and Rehabilitation with 18 years of clinical experience. My curriculum vitae is attached. I am qualified to offer expert medical opinion regarding workplace injuries, disability assessment, and causation analysis. I have testified as an expert witness in over 50 cases involving occupational injuries.

II. MATERIALS REVIEWED

In forming this opinion, I reviewed the following materials:
1. Complete medical records from March 15, 2024 through October 31, 2024
2. MRI imaging studies and radiology reports
3. Physical therapy progress notes and discharge summary
4. Functional Capacity Evaluation report dated August 10, 2024
5. Deposition transcript of Patricia Johnson
6. Incident report from Acme Corporation dated March 15, 2024
7. Job description for Administrative Assistant position
8. Witness statements from three co-workers
9. Prior medical records dating back five years

III. INDEPENDENT MEDICAL EXAMINATION

I personally examined Ms. Johnson on October 25, 2024, at my office. The examination included:
- Comprehensive medical history interview
- Physical examination of spine and extremities
- Range of motion measurements
- Neurological assessment
- Functional testing
- Review of imaging with the patient

IV. MEDICAL CAUSATION ANALYSIS

Question 1: Did the workplace incident on March 15, 2024, cause Ms. Johnson's current medical condition?

OPINION: Yes, to a reasonable degree of medical certainty (probability greater than 51%), the workplace incident was the direct and proximate cause of Ms. Johnson's lumbar disc herniation and associated symptoms.

REASONING:
1. Temporal Relationship: The onset of symptoms immediately followed the lifting incident with no intervening trauma or event.

2. Mechanism of Injury: The described mechanism (lifting heavy file boxes while twisting) is consistent with the type of force that causes lumbar disc herniation.

3. Absence of Pre-existing Condition: Review of prior medical records reveals no complaints or treatment for lower back problems in the five years preceding the incident. While mild degenerative changes are present on MRI, these were asymptomatic prior to the injury.

4. Diagnostic Findings: MRI confirms L4-L5 disc herniation with nerve root impingement, which correlates with the patient's symptoms and examination findings.

5. Clinical Course: The progression of symptoms and response to treatment is consistent with traumatic disc herniation rather than degenerative processes.

Question 2: Are Ms. Johnson's ongoing symptoms and limitations causally related to the workplace incident?

OPINION: Yes, to a reasonable degree of medical certainty, the ongoing symptoms and functional limitations are a direct result of the March 15, 2024, workplace injury.

REASONING:
1. The herniated disc documented on MRI provides an objective anatomical basis for ongoing pain and limitation.

2. The treatment timeline and response are consistent with acute disc herniation rather than chronic degenerative disease.

3. The functional limitations observed in the Functional Capacity Evaluation correlate with the known sequelae of L4-L5 disc herniation with nerve involvement.

4. Alternative explanations for the symptoms have been reasonably excluded through diagnostic workup.

V. DISABILITY ASSESSMENT

Current Disability Status:
Based on my examination and review of records, Ms. Johnson has sustained permanent partial disability. Using the American Medical Association Guides to the Evaluation of Permanent Impairment, 6th Edition, I assign:

- Whole Person Impairment: 18%
- DRE Category III (Radiculopathy)
- Permanent Work Restrictions:
  * Lifting limit: 15 pounds maximum
  * Frequent position changes required
  * No prolonged sitting (maximum 30 minutes)
  * No repetitive bending, twisting, or reaching
  * Sedentary to light-duty work capacity only

Maximum Medical Improvement: Not yet reached. Patient would benefit from additional treatment including possible epidural injections and evaluation for minimally invasive surgical intervention.

VI. FUTURE MEDICAL NEEDS

To a reasonable degree of medical certainty, Ms. Johnson will require ongoing medical treatment causally related to the workplace injury:

1. Immediate Term (0-6 months):
   - Monthly pain management visits
   - Continued physical therapy maintenance program
   - Medications for pain and nerve symptoms
   - Possible additional epidural steroid injection

2. Intermediate Term (6-24 months):
   - Ongoing pain management
   - Periodic diagnostic imaging
   - Evaluation for minimally invasive disc procedure
   - Possible surgical intervention if conservative treatment insufficient

3. Long Term (2+ years):
   - Annual follow-up evaluations
   - Ongoing medication management
   - Periodic physical therapy as needed
   - Potential for accelerated degenerative changes requiring future treatment

Estimated Future Medical Costs: $75,000 - $125,000 over lifetime

VII. VOCATIONAL IMPACT

Opinion on Return to Work:
Ms. Johnson is permanently precluded from returning to her previous position as Administrative Assistant, which required regular lifting, filing, and document management activities.

Alternative Employment:
With appropriate accommodations and restrictions, she could potentially perform sedentary work such as:
- Computer-based office work with ergonomic workstation
- Telephone customer service with ability to alternate positions
- Administrative tasks not requiring physical filing or lifting

Vocational rehabilitation would be beneficial to identify suitable alternative employment within her medical restrictions.

VIII. APPORTIONMENT

Question: What percentage of Ms. Johnson's current condition is attributable to the workplace injury versus pre-existing degenerative changes?

OPINION: 90% of the current symptomatic condition and functional limitation is directly attributable to the workplace injury. While mild degenerative changes were present, these were asymptomatic and non-disabling prior to the March 15, 2024, incident.

The workplace injury was the triggering event that converted an asymptomatic degenerative condition into a symptomatic, disabling condition. Under legal principles of causation, the industrial injury is considered the substantial contributing cause.

IX. CONCLUSIONS

To a reasonable degree of medical certainty:

1. The March 15, 2024, workplace incident directly caused Ms. Johnson's L4-L5 disc herniation and associated symptoms.

2. The current symptoms, functional limitations, and disability are causally related to the workplace injury.

3. Ms. Johnson has sustained permanent partial disability (18% whole person impairment).

4. She is permanently restricted to sedentary to light-duty work and cannot return to her previous position.

5. Ongoing medical treatment is medically necessary and causally related to the injury.

6. Future medical costs related to this injury are estimated at $75,000-$125,000.

7. Vocational rehabilitation is recommended given her permanent work restrictions.

===================================

This opinion is rendered to a reasonable degree of medical certainty based on my training, experience, examination of the patient, and review of relevant medical records.

___________________________________
Dr. Elizabeth Chen, MD, FAAPMR
Board Certified - Physical Medicine and Rehabilitation
Date: November 15, 2024

CV Attached
Fee Schedule: $500/hour for record review, $750/hour for examination, $350/hour for report preparation
Total fees for this matter: $4,200
""",

    "construction_contract.pdf": """
CONSTRUCTION CONTRACT AGREEMENT

Project: Office Building Renovation
Date: February 1, 2024

This Construction Contract ("Contract") is entered into by and between:

OWNER:
Corporate Plaza LLC
123 Business Park Drive
San Francisco, CA 94105
Tax ID: 94-1234567

CONTRACTOR:
Premier Construction Services Inc.
456 Industrial Way
Oakland, CA 94601
License #: CA-B-987654
Tax ID: 94-7654321

PROJECT DESCRIPTION:
Complete interior renovation of the 4th floor office space located at 123 Business Park Drive, San Francisco, CA 94105, consisting of approximately 10,000 square feet.

SCOPE OF WORK:
The Contractor agrees to furnish all labor, materials, equipment, and services necessary to complete the following work in accordance with the plans and specifications:

1. DEMOLITION AND SITE PREPARATION
   - Remove existing interior partition walls
   - Remove outdated electrical and HVAC systems
   - Demolish existing flooring and ceiling systems
   - Properly dispose of all demolition debris
   - Protect adjacent areas during demolition

2. STRUCTURAL WORK
   - Install new steel beam supports as shown on structural drawings
   - Reinforce existing floor system per engineer specifications
   - Install new interior partition walls per architectural plans
   - Frame new conference rooms and private offices

3. ELECTRICAL SYSTEMS
   - Install new electrical service panel with 400-amp capacity
   - Run new electrical wiring throughout space
   - Install LED lighting fixtures (approx. 120 units)
   - Install power outlets, data ports, and USB charging stations
   - Provide emergency lighting and exit signs
   - All work to meet current California Electrical Code

4. MECHANICAL SYSTEMS (HVAC)
   - Install new HVAC system with 15-ton capacity
   - Install ductwork throughout space
   - Provide individual zone controls for temperature management
   - Install air filtration system meeting ASHRAE standards
   - Balance and commission system upon completion

5. PLUMBING
   - Upgrade existing plumbing for expanded break room
   - Install new water heater (50-gallon capacity)
   - Install fixtures in restrooms (to remain in current locations)
   - Test all plumbing systems for leaks

6. INTERIOR FINISHES
   - Install drywall on all new partition walls
   - Tape, mud, and finish all drywall surfaces
   - Prime and paint all walls and ceilings
   - Install luxury vinyl plank flooring in office areas (6,000 sq ft)
   - Install carpet tiles in conference rooms (2,500 sq ft)
   - Install ceramic tile in break room and restrooms (1,500 sq ft)

7. DOORS AND HARDWARE
   - Install 18 interior doors with frames and hardware
   - Install glass doors for conference rooms (4 units)
   - Install ADA-compliant hardware throughout
   - Provide keyed entry systems

8. MILLWORK AND CABINETRY
   - Install custom reception desk
   - Install break room cabinetry and countertops
   - Build custom shelving units in storage areas
   - Install window blinds throughout (30 windows)

CONTRACT PRICE:
The Owner agrees to pay the Contractor a total sum of Six Hundred Fifty Thousand Dollars ($650,000) for completion of all work described above.

PAYMENT SCHEDULE:
1. Initial Payment (10%): $65,000 due upon signing
2. Progress Payment 1 (20%): $130,000 due upon completion of demolition and rough-in
3. Progress Payment 2 (25%): $162,500 due upon completion of drywall and mechanical systems
4. Progress Payment 3 (25%): $162,500 due upon substantial completion
5. Final Payment (20%): $130,000 due upon final completion and acceptance, minus retainage

RETAINAGE: Owner shall retain 5% of each progress payment ($32,500 total) until final completion and acceptance of all work, plus 30-day warranty period.

CONTRACT TIME:
Commencement Date: February 15, 2024
Substantial Completion: June 15, 2024 (120 calendar days)
Final Completion: June 30, 2024

LIQUIDATED DAMAGES:
If Contractor fails to achieve Substantial Completion by the Contract Time, Owner may deduct $1,000 per calendar day as liquidated damages, not as a penalty.

TIME EXTENSIONS:
Contractor may be entitled to time extensions for:
- Owner-requested changes or additions
- Unforeseen conditions (hidden structural issues, hazardous materials)
- Acts of God (earthquakes, fires, floods)
- Labor strikes or material shortages beyond Contractor's control

CHANGES IN THE WORK:
Owner may order changes in the work. Any change requiring adjustment to Contract Price or Contract Time must be documented in a written Change Order signed by both parties prior to proceeding.

No work shall be performed on changed or extra work without a signed Change Order. Contractor shall not be entitled to additional compensation for work performed without proper authorization.

PERMITS AND INSPECTIONS:
Contractor shall obtain and pay for all necessary permits, licenses, and inspections required for the work. All work shall comply with applicable building codes and regulations.

Required permits:
- Building permit
- Electrical permit
- Mechanical permit
- Plumbing permit

INSURANCE:
Contractor shall maintain the following insurance coverage throughout the Contract:
- Commercial General Liability: $2,000,000 per occurrence
- Workers' Compensation: Statutory limits
- Auto Liability: $1,000,000 combined single limit
- Builder's Risk: Full replacement value

Owner shall be named as additional insured on all liability policies.

WARRANTY:
Contractor warrants that:
1. All work shall be free from defects in materials and workmanship for one (1) year from final completion
2. All materials and equipment shall be new unless otherwise specified
3. Work shall conform to Contract Documents
4. Work shall comply with applicable building codes

Manufacturer warranties shall be assigned to Owner at completion.

SAFETY:
Contractor shall be solely responsible for job site safety and shall comply with all OSHA regulations. Contractor shall maintain a written safety program and conduct regular safety meetings.

CLEANUP:
Contractor shall keep the site clean and orderly during construction and shall perform final cleanup prior to final payment, leaving the premises in broom-clean condition.

INDEMNIFICATION:
Contractor shall indemnify and hold harmless Owner from any claims, damages, or expenses arising from Contractor's performance of the work, except to the extent caused by Owner's negligence.

DISPUTE RESOLUTION:
Any disputes arising from this Contract shall be resolved as follows:
1. Good faith negotiations between parties
2. Mediation using mutually agreed mediator
3. Binding arbitration if mediation unsuccessful

TERMINATION:
Owner may terminate this Contract for:
- Contractor's material breach not cured within 10 days of written notice
- Contractor's bankruptcy or insolvency
- Contractor's persistent failure to supply workers or materials
- Contractor's disregard of safety regulations

Contractor may terminate if:
- Work is stopped for 30 consecutive days through no fault of Contractor
- Owner fails to make payments when due

GENERAL CONDITIONS:
1. Contractor is an independent contractor, not an employee of Owner
2. Contractor shall supervise and direct the work
3. Contractor may not assign this Contract without Owner's written consent
4. This Contract represents the entire agreement between parties
5. Any modifications must be in writing signed by both parties
6. Contract shall be governed by California law
7. All notices shall be in writing and delivered by certified mail
8. If any provision is invalid, remaining provisions shall continue in effect

CONTRACTOR RESPONSIBILITIES:
- Provide qualified superintend

ent on site daily
- Schedule and coordinate all trades and suppliers
- Provide temporary utilities during construction
- Protect Owner's property during construction
- Maintain project schedule and provide weekly progress reports
- Submit shop drawings and material samples for approval
- Coordinate with building management for access and logistics
- Provide as-built drawings at completion

OWNER RESPONSIBILITIES:
- Make payments in accordance with payment schedule
- Provide access to the premises
- Review and approve submittals in timely manner
- Designate representative for decision-making
- Provide architectural and engineering services as needed
- Occupy premises only after final completion and acceptance

EXHIBITS ATTACHED:
- Exhibit A: Architectural Plans and Specifications
- Exhibit B: Payment Schedule Detail
- Exhibit C: Insurance Certificate Requirements
- Exhibit D: Material and Equipment Schedule

IN WITNESS WHEREOF, the parties have executed this Construction Contract as of the date first written above.

OWNER:                                    CONTRACTOR:
CORPORATE PLAZA LLC                       PREMIER CONSTRUCTION SERVICES INC.

By: _________________________            By: _________________________
Name: Thomas Richardson                   Name: Miguel Rodriguez
Title: Managing Member                    Title: President
Date: February 1, 2024                   Date: February 1, 2024

Witness: ____________________           Witness: ____________________
"""
}


def main():
    """Process seeded documents through the real pipeline."""
    print("🚀 Processing seeded documents through Docling pipeline\n")

    db = SessionLocal()

    try:
        # Get all seeded documents
        documents = db.query(Document).all()

        if not documents:
            print("❌ No documents found. Run seed_data.py first.")
            return

        print(f"Found {len(documents)} seeded documents\n")

        # Initialize the document processor
        print("Initializing DocumentProcessor with Docling...")
        # Use a simpler model to avoid transformers bug
        processor = DocumentProcessor(
            use_ocr=True,
            use_bm25=True,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",  # Smaller, more stable model
        )
        print("✅ Processor initialized\n")

        processed_count = 0
        failed_count = 0

        for doc in documents:
            print(f"📄 Processing: {doc.filename}")
            print(f"   Document ID: {doc.id}, Case ID: {doc.case_id}")

            # Get sample content for this document type
            if doc.filename not in SAMPLE_DOCUMENTS:
                print(f"   ⚠️  No sample content for {doc.filename}, skipping")
                continue

            content = SAMPLE_DOCUMENTS[doc.filename]
            file_bytes = content.encode('utf-8')

            # Change filename to .txt so Docling treats it as text, not PDF
            original_filename = doc.filename
            txt_filename = doc.filename.replace('.pdf', '.txt')
            doc.filename = txt_filename
            db.flush()

            # Upload to MinIO
            try:
                print(f"   📤 Uploading to MinIO: {doc.file_path}")
                minio_client.upload_file(
                    file_data=io.BytesIO(file_bytes),
                    object_name=doc.file_path,
                    content_type="text/plain",
                    length=len(file_bytes),
                )
                print(f"   ✅ Uploaded {len(file_bytes)} bytes")
            except Exception as e:
                print(f"   ❌ MinIO upload failed: {e}")
                doc.filename = original_filename  # Restore original
                db.flush()
                failed_count += 1
                continue

            # Process through pipeline
            try:
                print(f"   🔄 Processing through Docling pipeline...")
                result = processor.process(
                    file_content=file_bytes,
                    filename=txt_filename,  # Use .txt extension
                    document_id=doc.id,
                    case_id=doc.case_id,
                    mime_type="text/plain",
                )

                if result.success:
                    print(f"   ✅ Processing successful!")
                    print(f"      Stage: {result.stage}")
                    print(f"      Chunks: {result.data.get('chunks_count', 0)}")
                    print(f"      Text length: {result.data.get('text_length', 0)}")

                    # Update document status
                    doc.status = DocumentStatus.COMPLETED
                    doc.meta_data = result.data
                    db.commit()

                    processed_count += 1
                else:
                    print(f"   ❌ Processing failed: {result.message}")
                    print(f"      Error: {result.error}")
                    doc.status = DocumentStatus.FAILED
                    db.commit()
                    failed_count += 1

            except Exception as e:
                print(f"   ❌ Pipeline error: {e}")
                import traceback
                traceback.print_exc()
                doc.status = DocumentStatus.FAILED
                db.commit()
                failed_count += 1

            print()  # Blank line between documents

        # Summary
        print("=" * 60)
        print(f"✨ Processing Complete!")
        print(f"   Successfully processed: {processed_count}/{len(documents)}")
        print(f"   Failed: {failed_count}/{len(documents)}")
        print("=" * 60)

        if processed_count > 0:
            print("\n✅ Documents are now indexed in Qdrant and ready for search!")
            print("\nTest the search API:")
            print("   curl 'http://localhost:8000/api/v1/search?q=employment&limit=5'")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
