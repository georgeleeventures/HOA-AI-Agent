"""Synthetic email scenarios for HouseKeep AI end-to-end testing.

Models a realistic 4-unit TIC building at 150 Twin Peaks Blvd, San Francisco.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Test residents
# ---------------------------------------------------------------------------

@dataclass
class TestResident:
    email: str
    name: str
    unit: str | None
    role: str  # resident | board_member | admin
    ownership_pct: float
    is_authorized: bool = True


TEST_RESIDENTS: dict[str, TestResident] = {
    "alice": TestResident(
        email="alice.chen.test@gmail.com",
        name="Alice Chen",
        unit="1",
        role="resident",
        ownership_pct=25.0,
    ),
    "bob": TestResident(
        email="bob.martinez.test@gmail.com",
        name="Bob Martinez",
        unit="2",
        role="resident",
        ownership_pct=25.0,
    ),
    "carol": TestResident(
        email="carol.davis.test@gmail.com",
        name="Carol Davis",
        unit="3",
        role="board_member",
        ownership_pct=25.0,
    ),
    "diana": TestResident(
        email="diana.park.test@gmail.com",
        name="Diana Park",
        unit="4",
        role="admin",
        ownership_pct=25.0,
    ),
    "eve": TestResident(
        email="eve.unknown.test@gmail.com",
        name="Eve Unknown",
        unit=None,
        role="resident",
        ownership_pct=0.0,
        is_authorized=False,
    ),
    "spammer": TestResident(
        email="random.spammer@example.com",
        name="Spammer McSpamface",
        unit=None,
        role="resident",
        ownership_pct=0.0,
        is_authorized=False,
    ),
}


# ---------------------------------------------------------------------------
# Attachment spec
# ---------------------------------------------------------------------------

@dataclass
class AttachmentSpec:
    """Describes a synthetic attachment to generate."""
    filename: str
    file_type: str  # pdf | jpg | png | docx | xlsx | empty_pdf
    generator_key: str  # key into DOCUMENT_CONTENT for content templates
    mime_type: str = ""

    def __post_init__(self):
        if not self.mime_type:
            self.mime_type = {
                "pdf": "application/pdf",
                "jpg": "image/jpeg",
                "png": "image/png",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "empty_pdf": "application/pdf",
            }.get(self.file_type, "application/octet-stream")


# ---------------------------------------------------------------------------
# Email scenario
# ---------------------------------------------------------------------------

@dataclass
class EmailScenario:
    name: str
    intent: str  # question | document_forward | thread_cc | correction | edge_case
    sender_key: str  # key into TEST_RESIDENTS
    subject: str
    body: str
    attachments: list[AttachmentSpec] = field(default_factory=list)
    is_reply_to: str | None = None  # name of another scenario (for threading)
    cc_list: list[str] = field(default_factory=list)  # additional CC email keys
    target_category: str | None = None
    target_subcategory: str | None = None
    is_forward: bool = False
    html_only: bool = False  # send as HTML-only (no text/plain)
    extra_headers: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Document content templates — facts for RAG retrieval
# ---------------------------------------------------------------------------

DOCUMENT_CONTENT: dict[str, dict] = {
    "ccrs": {
        "title": "Declaration of Covenants, Conditions & Restrictions — 150 Twin Peaks Blvd HOA",
        "body": """\
DECLARATION OF COVENANTS, CONDITIONS AND RESTRICTIONS
150 Twin Peaks Blvd Homeowners Association
San Francisco, California 94114

Recorded: March 15, 2018
Document No.: 2018-K892451

ARTICLE 1 — DEFINITIONS
1.1 "Association" means the 150 Twin Peaks Blvd Homeowners Association.
1.2 "Common Areas" include the roof, exterior walls, foundation, shared hallways, stairwells, garage, and landscaped areas.
1.3 "Unit" means each of the four residential units (Units 1 through 4).

ARTICLE 2 — OWNERSHIP AND USE
2.1 Each Unit Owner holds a 25% undivided interest in the Common Areas.
2.2 Units shall be used exclusively for residential purposes unless otherwise approved in writing by the Board.
2.3 No Owner shall make structural modifications to Common Areas without prior written Board approval and a 75% supermajority vote.

ARTICLE 3 — RESTRICTIONS
3.1 Short-Term Rentals: No Unit may be rented for periods of less than thirty (30) days. All lease agreements must be submitted to the Board for review.
3.2 Pets: Owners may keep up to two (2) domestic pets per unit. Dogs exceeding 25 pounds require prior written Board approval.
3.3 Quiet Hours: Quiet hours are observed from 10:00 PM to 8:00 AM daily. During these hours, residents shall refrain from excessive noise including loud music, power tools, and amplified sound.
3.4 Parking: Each unit is assigned one (1) garage parking space. Guest parking is available on a first-come, first-served basis in designated street areas only.

ARTICLE 4 — MODIFICATIONS AND IMPROVEMENTS
4.1 Interior Modifications: Owners may make non-structural interior modifications without Board approval, provided they do not affect plumbing, electrical, or load-bearing elements.
4.2 Exterior Modifications: All exterior modifications — including but not limited to satellite dishes, antennas, HVAC units, awnings, window treatments visible from outside, signage, and paint colors — require prior written approval from the Board of Directors. Requests must be submitted at least 30 days before the planned installation.
4.3 Flooring: Owners replacing flooring must install sound-dampening underlayment meeting a minimum STC rating of 50.

ARTICLE 5 — BUSINESS USE
5.1 Home Office: Quiet home office use is permitted provided it generates no customer foot traffic, signage, or deliveries exceeding normal residential volumes.
5.2 Commercial Use: No unit may be used for commercial purposes (retail, restaurant, salon, etc.) without written consent of all four owners and compliance with San Francisco zoning regulations.

ARTICLE 6 — INSURANCE
6.1 The Association shall maintain a master insurance policy covering the building structure, Common Areas, and liability. Each Owner is responsible for insuring their personal property and unit improvements (HO-6 policy recommended).

ARTICLE 7 — ASSESSMENTS
7.1 Regular monthly assessments shall be determined annually by the Board. Assessment amounts are proportional to ownership percentage.
7.2 Special assessments require a 75% supermajority vote and 30 days' written notice.
7.3 Assessments more than 60 days past due shall accrue interest at 10% per annum. The Association may file a lien after 90 days.

ARTICLE 8 — DISPUTE RESOLUTION
8.1 Disputes between Owners or between an Owner and the Association shall first be submitted to mediation. If mediation fails, binding arbitration under the rules of the American Arbitration Association shall apply.
""",
    },
    "tic_agreement": {
        "title": "Tenancy-in-Common Agreement — 150 Twin Peaks Blvd",
        "body": """\
TENANCY-IN-COMMON AGREEMENT
150 Twin Peaks Blvd, San Francisco, CA 94114

Effective Date: March 15, 2018
Parties: All Unit Owners

OWNERSHIP STRUCTURE:
Unit 1 — 25.00% ownership — Alice Chen
Unit 2 — 25.00% ownership — Bob Martinez
Unit 3 — 25.00% ownership — Carol Davis
Unit 4 — 25.00% ownership — Diana Park

VOTING RIGHTS:
Each owner's voting power is proportional to their ownership percentage. Ordinary decisions require a simple majority (>50%). Amendments to this agreement require a 75% supermajority.

RIGHT OF FIRST REFUSAL:
If any owner wishes to sell their interest, they must first offer it to the remaining owners at the proposed sale price. Remaining owners have 30 days to exercise this right. If declined, the selling owner may proceed with the third-party sale.

EXPENSE ALLOCATION:
All shared building expenses (insurance, maintenance, reserves, property tax for common areas) are divided proportionally by ownership percentage. Unit-specific expenses (interior repairs, personal insurance) are the sole responsibility of that unit's owner.

GOVERNANCE:
Owners shall elect a Board consisting of at least two members. The Board manages day-to-day operations, vendor relationships, and maintenance scheduling. Board members serve 2-year terms.
""",
    },
    "house_rules": {
        "title": "House Rules — 150 Twin Peaks Blvd HOA (Revised January 2026)",
        "sections": [
            ("Pets", "Pets weighing 25 pounds or less are permitted without prior approval. Dogs over 25 pounds require written Board approval. All pets must be leashed in common areas. Owners are responsible for immediate cleanup of pet waste. Aggressive animals may be required to be removed at the Board's discretion."),
            ("Noise and Quiet Hours", "Quiet hours are 10:00 PM to 8:00 AM daily, including weekends. During quiet hours, residents must refrain from loud music, power tools, TV at excessive volume, and heavy footfall activities (e.g., exercise equipment). Musical instrument practice is limited to 8:00 AM – 9:00 PM."),
            ("Grills and Open Flame", "No barbecue grills, charcoal grills, propane grills, or open flame devices are permitted on balconies, decks, or within 10 feet of the building exterior. This is per San Francisco Fire Code Section 308.1.4."),
            ("Smoking", "Smoking (including e-cigarettes and vaping) is prohibited in all common areas, shared hallways, stairwells, the garage, and within 15 feet of any building entrance or window. Smoking is permitted only inside individual units with windows closed."),
            ("Parking", "Each unit is assigned one garage parking space. Vehicles must be registered with the HOA. No vehicle repairs or oil changes in the garage. Motorcycles and bicycles must use designated areas. Guest vehicles may not occupy garage spaces overnight."),
            ("Common Areas", "Common areas (hallways, stairwell, laundry room, garage) must be kept clear of personal belongings. Temporary storage in common areas is not permitted. The shared laundry room is available 7:00 AM – 10:00 PM."),
            ("Trash and Recycling", "Trash pickup is every Tuesday and Friday. Recycling pickup is every Wednesday. Bins must be brought in from the curb by 8:00 PM on pickup day. Bulk items require a special pickup request through SF Recology."),
            ("Holiday Decorations", "Holiday decorations in common areas require Board approval and must be removed within 7 days after the holiday. No decorations that damage surfaces or present a fire hazard."),
            ("Move-In / Move-Out", "Moving must be scheduled at least 72 hours in advance with the Board. Moving hours are 8:00 AM – 6:00 PM, Monday through Saturday. A $200 refundable deposit is required for elevator/common area protection. No Sunday moves."),
            ("Electric Vehicles", "EV chargers may be installed in the owner's assigned garage space with Board approval and a licensed electrician. The installing owner bears all costs and is responsible for the charger's maintenance and insurance."),
            ("Satellite Dishes and Antennas", "Dishes under 1 meter in diameter may be installed within the owner's exclusive-use area. Roof-mounted installations require Board approval. All wiring must be professionally installed."),
        ],
    },
    "annual_budget": {
        "title": "150 Twin Peaks Blvd HOA — Annual Operating Budget FY 2026",
        "body": """\
150 TWIN PEAKS BLVD HOA
ANNUAL OPERATING BUDGET — FISCAL YEAR 2026

INCOME:
  Monthly Assessments (4 units × $1,000/month)    $48,000
  Interest Income                                      $340
  TOTAL INCOME                                     $48,340

OPERATING EXPENSES:
  Landscaping & Grounds Maintenance                 $6,000
  Building Insurance (Hartford Policy)              $8,000
  Water / Sewer / Garbage                           $4,800
  Common Area Electricity                           $1,800
  Pest Control                                      $1,200
  General Maintenance & Repairs                     $5,400
  Property Management Software                        $600
  Legal & Accounting                                $2,400
  Miscellaneous / Contingency                       $2,140
  TOTAL OPERATING EXPENSES                         $32,340

RESERVE CONTRIBUTION:
  Monthly Reserve Contribution                     $16,000
  (4 units × $333.33/month)

TOTAL EXPENSES + RESERVES                          $48,340

ASSESSMENT BREAKDOWN PER UNIT:
  Operating: $666.67/month
  Reserve:   $333.33/month
  Total:   $1,000.00/month

Approved by Board vote on January 15, 2026 (3-1, Carol Davis opposed).
""",
    },
    "reserve_study": {
        "title": "Reserve Study — 150 Twin Peaks Blvd HOA (2026 Update)",
        "rows": [
            ["Component", "Useful Life (yr)", "Remaining Life (yr)", "Replacement Cost", "Annual Contribution"],
            ["Roof (flat, modified bitumen)", "25", "2", "$80,000", "$4,000"],
            ["Exterior Paint", "8", "3", "$24,000", "$1,500"],
            ["Elevator Modernization", "30", "4", "$45,000", "$1,875"],
            ["Garage Door & Mechanism", "15", "7", "$8,000", "$400"],
            ["Plumbing (main line)", "40", "15", "$35,000", "$875"],
            ["HVAC Common Areas", "20", "10", "$12,000", "$600"],
            ["Fire Alarm System", "15", "5", "$10,000", "$500"],
            ["Sidewalk & Driveway", "25", "12", "$15,000", "$375"],
            ["Intercom / Entry System", "12", "2", "$6,000", "$250"],
            ["TOTAL", "", "", "$235,000", "$10,375"],
        ],
        "summary": """\
RESERVE FUND SUMMARY:
  Current Balance (as of January 1, 2026): $120,000
  Annual Contribution: $16,000 ($10,375 required + $5,625 cushion)
  Projected Balance Dec 31, 2026: $136,000
  Funded Percentage: 73% (target: 70-100%)

NEAR-TERM PROJECTS:
  - Roof replacement: projected 2028, estimated $80,000
  - Intercom replacement: projected 2028, estimated $6,000
  - Elevator modernization: projected 2030, estimated $45,000

Prepared by: Pacific Reserve Studies, Inc.
Date: February 10, 2026
""",
    },
    "meeting_minutes_jan": {
        "title": "Board Meeting Minutes — January 15, 2026",
        "body": """\
150 TWIN PEAKS BLVD HOA
BOARD MEETING MINUTES
January 15, 2026 — 7:00 PM — Unit 3 (Carol Davis residence)

ATTENDEES:
  Carol Davis (Board President, Unit 3) — Present
  Diana Park (Board Secretary/Treasurer, Unit 4) — Present
  Alice Chen (Unit 1) — Present
  Bob Martinez (Unit 2) — Absent (proxy submitted)

QUORUM: Yes (3 of 4 owners present or represented by proxy)

1. CALL TO ORDER
   Meeting called to order at 7:05 PM by Carol Davis.

2. APPROVAL OF PREVIOUS MINUTES
   Minutes from October 2025 meeting approved unanimously.

3. FINANCIAL REPORT
   Diana Park presented Q4 2025 financials. Operating expenses were $800 under budget. Reserve fund balance stands at $120,000 as of December 31, 2025.

4. 2026 BUDGET APPROVAL
   MOTION: Increase monthly assessments from $970 to $1,000 per unit (approximately 3% increase) to maintain adequate reserve funding per the 2026 reserve study.
   VOTE: 3 in favor (Alice, Bob proxy, Diana), 1 opposed (Carol).
   MOTION CARRIED.

5. MAINTENANCE UPDATES
   a. Roof Inspection: Carol reported that Bay Area Roofing completed the annual inspection in December. Minor patching was done. Full replacement recommended within 2-3 years.
   b. Fire Alarm: Annual fire inspection scheduled for March 15, 2026 with SF Fire Prevention.
   c. Plumbing: Bob (via proxy) reported intermittent low water pressure in Unit 2. Board approved calling Bay Area Plumbing for assessment.

6. OLD BUSINESS
   a. EV Charger Request (Alice Chen, Unit 1): Board reviewed the installation plan and electrician's proposal. APPROVED with conditions: Alice bears all costs, must use a licensed electrician, and must carry additional liability insurance.

7. NEW BUSINESS
   a. Noise Complaint: Diana reported repeated late-night noise from Unit 2. Board will send a formal reminder about quiet hours to all residents.
   b. Entry System: The intercom system is increasingly unreliable. Carol will obtain quotes for replacement.

8. NEXT MEETING
   Scheduled for April 16, 2026 at 7:00 PM, location TBD.

9. ADJOURNMENT
   Meeting adjourned at 8:35 PM.

Minutes recorded by Diana Park, Board Secretary.
""",
    },
    "meeting_agenda_apr": {
        "title": "Board Meeting Agenda — April 16, 2026",
        "body": """\
150 TWIN PEAKS BLVD HOA
BOARD MEETING AGENDA
April 16, 2026 — 7:00 PM — Unit 4 (Diana Park residence)

1. Call to Order
2. Approval of January 2026 Meeting Minutes
3. Financial Report — Q1 2026
4. Maintenance Updates
   a. Roof inspection follow-up
   b. Fire alarm inspection results (March 15)
   c. Unit 2 plumbing assessment results
   d. Intercom replacement quotes
5. Old Business
   a. EV charger installation status (Unit 1)
   b. Noise complaint follow-up
6. New Business
   a. Exterior painting schedule (2027-2028)
   b. Summer landscaping plan
7. Open Forum
8. Next Meeting Date
9. Adjournment

Please submit any agenda additions to Diana Park by April 10, 2026.
""",
    },
    "insurance_policy": {
        "title": "Certificate of Insurance — 150 Twin Peaks Blvd HOA",
        "body": """\
CERTIFICATE OF INSURANCE

Named Insured: 150 Twin Peaks Blvd Homeowners Association
Address: 150 Twin Peaks Blvd, San Francisco, CA 94114

Insurance Provider: Hartford Property Insurance Company
Agent: Pacific Coast Insurance Brokers, San Francisco
Policy Number: HP-2024-88831
Policy Period: January 1, 2025 to December 31, 2025

COVERAGE SUMMARY:

1. Commercial General Liability
   Per Occurrence Limit:        $1,000,000
   General Aggregate:           $2,000,000
   Products/Completed Ops:      $1,000,000
   Personal & Advertising:        $500,000
   Damage to Rented Premises:     $100,000
   Medical Expense per Person:      $5,000

2. Property Coverage
   Building Value:              $1,800,000
   Replacement Cost Basis
   Deductible:                     $5,000
   Earthquake Coverage:         NOT INCLUDED (separate policy recommended)

3. Directors & Officers (D&O) Liability
   Each Claim:                    $500,000
   Aggregate:                   $1,000,000

4. Workers' Compensation
   Per Statute / $500,000 each accident

ANNUAL PREMIUM: $8,000
Payment: Two installments ($4,000 each, Jan 1 and Jul 1)

RENEWAL: Policy expires December 31, 2025. Renewal quote requested.

Issued by: Hartford Property Insurance Company
Date: December 15, 2024
""",
    },
    "attorney_letter": {
        "title": "Legal Opinion — Fence Dispute with 148 Twin Peaks Blvd",
        "body": """\
GOLDSTEIN & WONG, LLP
Attorneys at Law
456 Market Street, Suite 900
San Francisco, CA 94105

March 10, 2026

Board of Directors
150 Twin Peaks Blvd HOA
150 Twin Peaks Blvd
San Francisco, CA 94114

Re: Boundary Fence Dispute — 148 Twin Peaks Blvd

Dear Board Members:

This letter summarizes our legal analysis of the fence dispute with the property at 148 Twin Peaks Blvd.

BACKGROUND:
The owner of 148 Twin Peaks Blvd erected a 7-foot wooden fence along the shared property boundary in January 2026 without notice to your Association. The fence encroaches approximately 8 inches onto your property based on the survey conducted by Bay Area Land Surveyors on February 20, 2026.

LEGAL ANALYSIS:
1. San Francisco Planning Code Section 136(d) limits residential fence height to 6 feet in rear yards and 3 feet in front yards. The 7-foot fence violates this height restriction.
2. The 8-inch encroachment onto your property constitutes a trespass under California Civil Code Section 1002.
3. Under California Civil Code Section 841, adjoining landowners share responsibility for boundary fences, but modifications require mutual agreement.

RECOMMENDATION:
We recommend sending a formal demand letter requesting:
(a) Reduction of fence height to comply with SF Planning Code
(b) Removal of the encroaching portion from your property
(c) A 30-day compliance deadline before escalation to code enforcement and/or civil action

We estimate legal costs for this matter at $3,000–$5,000 if resolved through demand letter, or $15,000–$25,000 if litigation is required.

Please advise how you wish to proceed.

Sincerely,
Margaret Wong, Esq.
Goldstein & Wong, LLP
""",
    },
    "owner_roster": {
        "title": "Owner Roster — 150 Twin Peaks Blvd (Updated January 2026)",
        "body": """\
150 TWIN PEAKS BLVD HOA — OWNER ROSTER
Updated: January 15, 2026

UNIT 1:
  Owner: Alice Chen
  Email: alice.chen.test@gmail.com
  Phone: (415) 555-0101
  Ownership: 25.00%
  Occupancy: Owner-Occupied
  Move-In Date: March 2018

UNIT 2:
  Owner: Bob Martinez
  Email: bob.martinez.test@gmail.com
  Phone: (415) 555-0102
  Ownership: 25.00%
  Occupancy: Owner-Occupied
  Move-In Date: March 2018

UNIT 3:
  Owner: Carol Davis
  Email: carol.davis.test@gmail.com
  Phone: (415) 555-0103
  Ownership: 25.00%
  Occupancy: Owner-Occupied
  Move-In Date: June 2019
  Board Role: President

UNIT 4:
  Owner: Diana Park
  Email: diana.park.test@gmail.com
  Phone: (415) 555-0104
  Ownership: 25.00%
  Occupancy: Owner-Occupied
  Move-In Date: March 2018
  Board Role: Secretary / Treasurer

EMERGENCY CONTACTS:
  Building Manager: Carol Davis — (415) 555-0103
  Plumber (emergency): Bay Area Plumbing — (415) 555-8200
  Fire/Police/Ambulance: 911
  Non-Emergency Police: (415) 553-0123
""",
    },
    "vendor_contract": {
        "title": "Service Agreement — Bay Area Plumbing",
        "body": """\
SERVICE AGREEMENT

Between: 150 Twin Peaks Blvd Homeowners Association ("Client")
And:     Bay Area Plumbing, Inc. ("Contractor")

Effective Date: January 1, 2024
Expiration Date: December 31, 2025

SCOPE OF SERVICES:
Bay Area Plumbing agrees to provide the following services:
1. Monthly preventive maintenance inspection of common area plumbing
2. Priority emergency response (within 4 hours) for plumbing emergencies
3. Annual main line inspection and cleaning
4. Quarterly water heater inspection and maintenance

COMPENSATION:
  Monthly Retainer: $200.00 (covers items 1-4 above)
  Emergency Repairs: Billed at $150/hour + materials at cost
  Major Projects: Quoted separately, requiring Board approval for work exceeding $1,000

PAYMENT TERMS:
  Net 15 days from invoice date
  Late fees: 1.5% per month on overdue balances

INSURANCE:
  Contractor maintains general liability insurance ($2M aggregate) and workers' compensation coverage. Certificates on file with HOA.

TERMINATION:
  Either party may terminate with 30 days' written notice.

LICENSE:
  California Contractor License #892451 (C-36 Plumbing)

SIGNATURES:
  Carol Davis, Board President      Date: December 15, 2023
  Mike Reyes, Bay Area Plumbing     Date: December 15, 2023
""",
    },
    "newsletter": {
        "title": "Twin Peaks HOA Newsletter — Spring 2026",
        "body": """\
🏠 150 TWIN PEAKS BLVD HOA — SPRING NEWSLETTER
March 2026

HELLO NEIGHBORS!

Welcome to the Spring 2026 edition of our community newsletter.

UPCOMING EVENTS:
• Board Meeting: April 16, 2026 at 7 PM in Unit 4
• Annual BBQ Potluck: May 18, 2026 at noon in the back garden (weather permitting)
• Fire Inspection: Completed March 15 — we passed! Certificate on file.

MAINTENANCE UPDATES:
The roof inspection in December showed our roof is in fair condition but will need full replacement within 2-3 years. The Board is gathering contractor bids and will present options at the April meeting. Our reserve fund is well-positioned at $120,000.

Bay Area Plumbing assessed the low water pressure issue in Unit 2. The cause was a partially corroded valve in the main line. Repair was completed on February 28 at a cost of $850.

REMINDERS:
• HOA dues increased to $1,000/month effective January 1 (3% increase)
• Trash: Tuesdays and Fridays | Recycling: Wednesdays
• Quiet hours: 10 PM – 8 AM daily
• Please keep common areas clear of personal belongings

WELCOME:
No ownership changes this quarter. We remain a stable community of four owner-occupants.

Questions? Email HouseKeep at any time — our AI assistant is here to help!

Best,
Diana Park
Board Secretary / Treasurer
""",
    },
    "work_order": {
        "title": "Work Order #WO-2026-003 — Unit 2 Plumbing Repair",
        "body": """\
WORK ORDER

Work Order #: WO-2026-003
Date Reported: January 20, 2026
Date Completed: February 28, 2026

PROPERTY: 150 Twin Peaks Blvd, San Francisco, CA 94114
UNIT: 2 (Bob Martinez)
REPORTED BY: Bob Martinez

ISSUE TYPE: Plumbing
PRIORITY: Medium
DESCRIPTION: Intermittent low water pressure in kitchen and bathroom. Issue started approximately January 15, 2026.

ASSESSMENT:
Bay Area Plumbing inspected on February 15, 2026. Found partially corroded shut-off valve in the main water line feeding Unit 2. Valve was approximately 60% occluded.

WORK PERFORMED:
- Isolated water supply to Unit 2
- Removed corroded gate valve
- Installed new quarter-turn ball valve
- Tested water pressure at all fixtures — restored to normal (55 PSI)
- Inspected adjacent valves — no further corrosion detected

CONTRACTOR: Bay Area Plumbing, Inc.
TECHNICIAN: Mike Reyes
LICENSE: CA #892451

COST:
  Labor (3 hours @ $150/hr):  $450
  Materials (valve + fittings): $120
  Emergency markup:              $0
  TOTAL:                       $570

Note: This repair falls within the maintenance budget. Covered under the Bay Area Plumbing retainer agreement. Additional $370 beyond retainer billed separately.

STATUS: Completed
FOLLOW-UP: Recommend annual valve inspection for all units. Added to preventive maintenance schedule.
""",
    },
    "invoice_plumbing": {
        "title": "Invoice #BAP-2026-0847 — Bay Area Plumbing",
        "body": """\
INVOICE

Bay Area Plumbing, Inc.
123 Mission Street, Suite 200
San Francisco, CA 94105
Phone: (415) 555-8200
License: CA #892451

BILL TO:
150 Twin Peaks Blvd HOA
150 Twin Peaks Blvd
San Francisco, CA 94114
Attn: Diana Park, Treasurer

Invoice Number: BAP-2026-0847
Invoice Date: March 1, 2026
Due Date: March 15, 2026
Work Order Reference: WO-2026-003

DESCRIPTION OF SERVICES:
Unit 2 — Water pressure repair (corroded gate valve replacement)
Service Date: February 28, 2026

CHARGES:
  Labor — 3 hours @ $150/hr              $450.00
  Materials — 1" ball valve + fittings     $120.00
  SUBTOTAL                                 $570.00
  Less: Monthly retainer credit           -$200.00
  AMOUNT DUE                               $370.00

PAYMENT TERMS: Net 15 days
LATE FEE: 1.5% per month on overdue balance

Make checks payable to: Bay Area Plumbing, Inc.
Or pay online: bayareaplumbing.com/pay

Thank you for your business!
""",
    },
    "lien_violation": {
        "title": "Notice of Violation — Unit 2, Unauthorized Storage in Common Area",
        "body": """\
150 TWIN PEAKS BLVD HOA
NOTICE OF VIOLATION

Date: February 1, 2026
To: Bob Martinez, Unit 2

Re: Violation of House Rules — Unauthorized Storage in Common Area

Dear Mr. Martinez:

This letter serves as a formal notice that personal items belonging to Unit 2 have been observed stored in the shared hallway and garage common area in violation of Section 6 (Common Areas) of the House Rules.

SPECIFIC VIOLATIONS OBSERVED:
1. Two bicycles chained to the stairwell railing (observed January 25 and January 30, 2026)
2. Cardboard boxes stacked near the garage entrance (observed January 28, 2026)
3. A surfboard leaned against the hallway wall (observed multiple dates)

REQUIRED ACTION:
Please remove all personal items from common areas within 14 days of this notice (by February 15, 2026). Bicycles must be stored in the designated bike rack area or within your unit.

CONSEQUENCES:
Failure to comply may result in:
- A fine of $50 per occurrence per day after the deadline
- Removal of items at the owner's expense
- Recording of the violation in HOA records

We appreciate your prompt attention to this matter. If you have questions or need to discuss storage alternatives, please contact the Board.

Sincerely,
Carol Davis
Board President
150 Twin Peaks Blvd HOA
""",
    },
    "fire_inspection": {
        "title": "Fire & Life Safety Inspection Report — 150 Twin Peaks Blvd",
        "body": """\
SAN FRANCISCO FIRE DEPARTMENT
FIRE PREVENTION DIVISION

FIRE & LIFE SAFETY INSPECTION REPORT

Property: 150 Twin Peaks Blvd, San Francisco, CA 94114
Inspection Date: March 15, 2026
Inspector: Captain James Okoro, Badge #4521
Inspection Type: Annual Building Inspection

RESULTS: PASS (with minor recommendations)

ITEMS INSPECTED:
1. Fire Alarm System — PASS
   - Smoke detectors in all units and common areas: functional
   - Pull stations on each floor: functional
   - Panel communication to monitoring company: verified
   - Battery backup: tested, operational
   - Last serviced: September 2025

2. Fire Extinguishers — PASS
   - Garage (1x 10-lb ABC): current tag, charged
   - Hallway Floor 1 (1x 5-lb ABC): current tag, charged
   - Hallway Floor 2 (1x 5-lb ABC): current tag, charged
   - Laundry room (1x 5-lb ABC): current tag, charged

3. Emergency Lighting — PASS
   - Exit signs illuminated: yes
   - Battery backup tested: functional (>90 minute runtime)
   - Emergency lights in stairwell: functional

4. Egress — PASS
   - Hallways and stairwells clear of obstructions
   - Exit doors operable without special knowledge
   - Emergency exit signage: adequate

5. Sprinkler System — N/A
   (Building pre-dates sprinkler requirement; not retrofit-required)

RECOMMENDATIONS (non-mandatory):
- Consider adding a smoke detector in the garage (not currently required but recommended)
- Replace fire extinguisher in garage — approaching 6-year maintenance interval (due September 2026)

NEXT INSPECTION DUE: March 2027

Signed: Captain James Okoro
San Francisco Fire Department, Fire Prevention Division
""",
    },
    "contractor_bid_roof": {
        "title": "Roof Replacement Bid — Summit Roofing Co.",
        "body": """\
PROPOSAL / BID

Summit Roofing Co.
789 Industrial Way
South San Francisco, CA 94080
License: CA #1045892 (C-39 Roofing)

Date: March 20, 2026
Proposal #: SR-2026-0412

TO:
150 Twin Peaks Blvd HOA
Attn: Carol Davis, Board President

RE: Full Roof Replacement — 150 Twin Peaks Blvd

SCOPE OF WORK:
1. Remove existing modified bitumen roofing system (approx. 2,200 sq ft)
2. Inspect and repair roof decking as needed
3. Install new 60-mil TPO single-ply membrane roofing system
4. Replace all roof flashing, drip edges, and penetration boots
5. Install new overflow drains (2)
6. Apply reflective coating for energy efficiency (Title 24 compliant)
7. 20-year manufacturer warranty + 5-year workmanship warranty

COST BREAKDOWN:
  Tear-off & disposal:           $8,500
  Decking repairs (estimated):   $3,000
  TPO membrane & installation:  $42,000
  Flashing & details:            $6,500
  Drains & overflow:             $4,000
  Reflective coating:            $3,500
  Permits & inspections:         $2,500
  Contingency (5%):              $3,500
  TOTAL:                        $73,500

TIMELINE:
  Start date: 2-3 weeks after signed contract
  Duration: 8-10 working days (weather dependent)

PAYMENT TERMS:
  30% deposit at signing:       $22,050
  40% at midpoint:              $29,400
  30% upon completion:          $22,050

This proposal is valid for 60 days.

Submitted by:
Tom Nakamura, Project Manager
Summit Roofing Co.
(650) 555-7890
""",
    },
    "maintenance_photo_water": {
        "description": "MAINTENANCE PHOTO\n\nUnit 2 — Kitchen Sink Area\nDate: January 20, 2026\nReported by: Bob Martinez\n\nWater damage visible under\nkitchen sink cabinet.\nDiscoloration on cabinet floor.\nMinor mold growth on back wall.\nDripping from corroded valve.",
    },
    "inspection_scan": {
        "description": "ELEVATOR INSPECTION CERTIFICATE\n\nProperty: 150 Twin Peaks Blvd\nSF Permit #: EL-2025-4821\nInspection Date: Nov 15, 2025\nResult: PASS\nNext Due: Nov 2026\n\nInspector: R. Tanaka\nCA License #EI-7823",
    },
    "warranty_doc": {
        "title": "Warranty Certificate — Elevator Modernization",
        "body": """\
WARRANTY CERTIFICATE

Equipment: ThyssenKrupp Residential Elevator, Model TAC-20
Location: 150 Twin Peaks Blvd, San Francisco, CA 94114
Installation Date: June 15, 2020
Warranty Period: 5 years (expires June 15, 2025)

COVERAGE:
This warranty covers all defects in materials and workmanship for the elevator cab, motor, controller, and safety systems. Coverage includes:
- Motor and drive system
- Controller and circuit boards
- Door operator and safety edges
- Cab interior and lighting
- Emergency phone and alarm

EXCLUSIONS:
- Damage from misuse, vandalism, or acts of God
- Routine maintenance items (lubrication, cleaning, bulb replacement)
- Modifications made by unauthorized personnel

SERVICE PROVIDER: Bay Area Elevator Services
Contact: (415) 555-3300
Emergency Line: (415) 555-3301 (24/7)

NOTE: Warranty has expired as of June 15, 2025. Extended warranty or new service contract recommended. Elevator modernization projected for 2030 per reserve study.
""",
    },
}


# ---------------------------------------------------------------------------
# Scenario catalog
# ---------------------------------------------------------------------------

def build_scenarios() -> list[EmailScenario]:
    """Return all ~45 synthetic email scenarios."""
    scenarios = []

    # -----------------------------------------------------------------------
    # A. QUESTION INTENT (12 scenarios)
    # -----------------------------------------------------------------------

    scenarios.append(EmailScenario(
        name="q_rules_ac_unit",
        intent="question",
        sender_key="alice",
        subject="Can I install a mini-split AC unit?",
        body="Hi HouseKeep,\n\nI'm thinking about installing a mini-split AC unit on my exterior wall. Is that something I need approval for, or can I just go ahead and hire someone? Thanks!\n\n— Alice",
    ))

    scenarios.append(EmailScenario(
        name="q_financial_dues",
        intent="question",
        sender_key="bob",
        subject="Monthly dues question",
        body="How much are my monthly HOA dues? And when did they last change? I want to make sure I'm paying the right amount.\n\nBob",
    ))

    scenarios.append(EmailScenario(
        name="q_ownership_pct",
        intent="question",
        sender_key="alice",
        subject="What percentage of the building do I own?",
        body="Hi, quick question — what's my ownership percentage, and how does that affect my voting rights? Also, what are the other owners' percentages?\n\nThanks,\nAlice",
    ))

    scenarios.append(EmailScenario(
        name="q_maintenance_history",
        intent="question",
        sender_key="bob",
        subject="Fire alarm inspection",
        body="When was the fire alarm system last inspected? Did we pass? When's the next one due?\n\nBob",
    ))

    scenarios.append(EmailScenario(
        name="q_board_financial",
        intent="question",
        sender_key="carol",
        subject="Reserve fund balance",
        body="What's our current reserve fund balance and are we on track with the reserve study projections?\n\n— Carol",
    ))

    scenarios.append(EmailScenario(
        name="q_ambiguous_short",
        intent="question",
        sender_key="alice",
        subject="parking",
        body="parking",
    ))

    scenarios.append(EmailScenario(
        name="q_needs_clarification",
        intent="question",
        sender_key="bob",
        subject="what happened?",
        body="what happened?",
    ))

    scenarios.append(EmailScenario(
        name="q_not_in_knowledge_base",
        intent="question",
        sender_key="alice",
        subject="Seismic rating",
        body="What is our building's seismic rating? Has there been a seismic retrofit done?\n\nAlice",
    ))

    scenarios.append(EmailScenario(
        name="q_legal_adjacent",
        intent="question",
        sender_key="carol",
        subject="Fence dispute update",
        body="What did the attorney say about the fence dispute with 148 Twin Peaks? What are our options and estimated legal costs?\n\nCarol",
    ))

    scenarios.append(EmailScenario(
        name="q_multi_topic",
        intent="question",
        sender_key="alice",
        subject="Pet rules and next meeting",
        body="Two quick questions:\n1. What's the pet weight limit? My sister is offering me her dog who's about 30 lbs.\n2. When is the next board meeting?\n\nThanks!\nAlice",
    ))

    scenarios.append(EmailScenario(
        name="q_unauthorized_sender",
        intent="question",
        sender_key="eve",
        subject="Can I see the HOA budget?",
        body="Hi, I'm interested in buying a unit in your building. Can you share the annual budget and reserve study?\n\nThanks,\nEve",
    ))

    scenarios.append(EmailScenario(
        name="q_unknown_spammer",
        intent="question",
        sender_key="spammer",
        subject="FREE ROOFING ESTIMATE - LIMITED TIME!!!",
        body="Dear homeowner, we noticed your roof may need repair. Click here for a FREE estimate! We serve the Twin Peaks area. ACT NOW! Reply to claim your 50% discount!!!!",
    ))

    # -----------------------------------------------------------------------
    # B. DOCUMENT FORWARD INTENT (16 scenarios)
    # -----------------------------------------------------------------------

    scenarios.append(EmailScenario(
        name="doc_ccrs",
        intent="document_forward",
        sender_key="diana",
        subject="Fwd: CC&Rs for our building",
        body="Here's a copy of our CC&Rs for the records.\n\n— Diana",
        attachments=[AttachmentSpec("150_Twin_Peaks_CCRs.pdf", "pdf", "ccrs")],
        is_forward=True,
        target_category="Governing",
        target_subcategory="CC&Rs",
    ))

    scenarios.append(EmailScenario(
        name="doc_budget",
        intent="document_forward",
        sender_key="diana",
        subject="Fwd: 2026 Annual Budget — Approved",
        body="Attached is the approved 2026 annual budget.\n\nDiana",
        attachments=[AttachmentSpec("2026_Annual_Budget.pdf", "pdf", "annual_budget")],
        is_forward=True,
        target_category="Financial",
        target_subcategory="Budget",
    ))

    scenarios.append(EmailScenario(
        name="doc_meeting_minutes",
        intent="document_forward",
        sender_key="diana",
        subject="Fwd: January Board Meeting Minutes",
        body="Attached are the minutes from our January board meeting.\n\nDiana Park\nBoard Secretary",
        attachments=[AttachmentSpec("Board_Minutes_Jan_2026.pdf", "pdf", "meeting_minutes_jan")],
        is_forward=True,
        target_category="Meeting",
        target_subcategory="Minutes",
    ))

    scenarios.append(EmailScenario(
        name="doc_work_order",
        intent="document_forward",
        sender_key="carol",
        subject="Fwd: Work Order — Unit 2 Plumbing",
        body="Filing the completed work order for Bob's plumbing repair.\n\nCarol",
        attachments=[AttachmentSpec("WO-2026-003_Plumbing.pdf", "pdf", "work_order")],
        is_forward=True,
        target_category="Maintenance",
        target_subcategory="Work Order",
    ))

    scenarios.append(EmailScenario(
        name="doc_insurance",
        intent="document_forward",
        sender_key="diana",
        subject="Fwd: Insurance Certificate 2025",
        body="Here's our current insurance certificate. Note it expires end of year — we need to start the renewal process.\n\nDiana",
        attachments=[AttachmentSpec("Hartford_Insurance_Certificate.pdf", "pdf", "insurance_policy")],
        is_forward=True,
        target_category="Insurance",
        target_subcategory="Policy",
    ))

    scenarios.append(EmailScenario(
        name="doc_attorney_letter",
        intent="document_forward",
        sender_key="carol",
        subject="Fwd: Attorney Opinion — Fence Dispute",
        body="Got this back from our attorney regarding the fence issue with 148. Please review.\n\nCarol",
        attachments=[AttachmentSpec("Goldstein_Wong_Fence_Opinion.pdf", "pdf", "attorney_letter")],
        is_forward=True,
        target_category="Legal",
        target_subcategory="Attorney",
    ))

    scenarios.append(EmailScenario(
        name="doc_roster",
        intent="document_forward",
        sender_key="diana",
        subject="Fwd: Updated Owner Roster — January 2026",
        body="Updated roster with current contact info for all units.\n\nDiana",
        attachments=[AttachmentSpec("Owner_Roster_2026.pdf", "pdf", "owner_roster")],
        is_forward=True,
        target_category="Ownership",
        target_subcategory="Roster",
    ))

    scenarios.append(EmailScenario(
        name="doc_vendor_contract",
        intent="document_forward",
        sender_key="carol",
        subject="Fwd: Bay Area Plumbing Service Agreement",
        body="Filing our plumbing service contract. Expires end of 2025 — need to discuss renewal.\n\nCarol",
        attachments=[AttachmentSpec("Bay_Area_Plumbing_Contract.pdf", "pdf", "vendor_contract")],
        is_forward=True,
        target_category="Vendor",
        target_subcategory="Contract",
    ))

    scenarios.append(EmailScenario(
        name="doc_newsletter",
        intent="document_forward",
        sender_key="diana",
        subject="Fwd: Spring 2026 Newsletter",
        body="Here's the newsletter I sent out to everyone. Filing for records.\n\nDiana",
        attachments=[AttachmentSpec("Newsletter_Spring_2026.pdf", "pdf", "newsletter")],
        is_forward=True,
        target_category="Correspondence",
        target_subcategory="Newsletter",
    ))

    scenarios.append(EmailScenario(
        name="doc_house_rules_docx",
        intent="document_forward",
        sender_key="carol",
        subject="Fwd: Updated House Rules — January 2026",
        body="Attached is the revised house rules document. Updated the pet and EV charger sections.\n\nCarol",
        attachments=[AttachmentSpec("House_Rules_2026.docx", "docx", "house_rules")],
        is_forward=True,
        target_category="Governing",
        target_subcategory="House Rules",
    ))

    scenarios.append(EmailScenario(
        name="doc_reserve_study_xlsx",
        intent="document_forward",
        sender_key="diana",
        subject="Fwd: 2026 Reserve Study Spreadsheet",
        body="The reserve study from Pacific Reserve Studies. Spreadsheet format with all the projections.\n\nDiana",
        attachments=[AttachmentSpec("Reserve_Study_2026.xlsx", "xlsx", "reserve_study")],
        is_forward=True,
        target_category="Financial",
        target_subcategory="Reserve Study",
    ))

    scenarios.append(EmailScenario(
        name="doc_maintenance_photo",
        intent="document_forward",
        sender_key="bob",
        subject="Water damage under kitchen sink",
        body="Found water damage under my kitchen sink. See attached photo. Can we get someone to look at this?\n\nBob",
        attachments=[AttachmentSpec("kitchen_sink_damage.jpg", "jpg", "maintenance_photo_water")],
        target_category="Maintenance",
        target_subcategory="Photo/Evidence",
    ))

    scenarios.append(EmailScenario(
        name="doc_inspection_scan",
        intent="document_forward",
        sender_key="carol",
        subject="Fwd: Elevator Inspection Certificate",
        body="Scanned the elevator inspection certificate. Filing for records.\n\nCarol",
        attachments=[AttachmentSpec("elevator_inspection_2025.png", "png", "inspection_scan")],
        is_forward=True,
        target_category="Maintenance",
        target_subcategory="Inspection",
    ))

    scenarios.append(EmailScenario(
        name="doc_invoice",
        intent="document_forward",
        sender_key="diana",
        subject="Fwd: Invoice from Bay Area Plumbing — Unit 2 Repair",
        body="Invoice for the plumbing work in Bob's unit. $370 after retainer credit. Due March 15.\n\nDiana",
        attachments=[AttachmentSpec("BAP_Invoice_2026_0847.pdf", "pdf", "invoice_plumbing")],
        is_forward=True,
        target_category="Financial",
        target_subcategory="Invoice/Receipt",
    ))

    scenarios.append(EmailScenario(
        name="doc_lien_violation",
        intent="document_forward",
        sender_key="carol",
        subject="Fwd: Violation Notice — Unit 2 Common Area Storage",
        body="Sent this to Bob about the stuff in the hallway. Filing a copy.\n\nCarol",
        attachments=[AttachmentSpec("Violation_Notice_Unit2.pdf", "pdf", "lien_violation")],
        is_forward=True,
        target_category="Legal",
        target_subcategory="Lien/Violation",
    ))

    scenarios.append(EmailScenario(
        name="doc_multi_attachment",
        intent="document_forward",
        sender_key="carol",
        subject="Fwd: April Meeting Materials",
        body="Here's the agenda for the April meeting plus the roof replacement bid from Summit Roofing for discussion.\n\nCarol",
        attachments=[
            AttachmentSpec("April_2026_Agenda.pdf", "pdf", "meeting_agenda_apr"),
            AttachmentSpec("Summit_Roofing_Bid.pdf", "pdf", "contractor_bid_roof"),
        ],
        is_forward=True,
        target_category="Meeting",
        target_subcategory="Agenda",
    ))

    # -----------------------------------------------------------------------
    # C. THREAD CC INTENT (5 scenarios)
    # -----------------------------------------------------------------------

    scenarios.append(EmailScenario(
        name="cc_roof_discussion_1",
        intent="thread_cc",
        sender_key="carol",
        subject="Roof replacement timeline",
        body="Hi all,\n\nI got the bid back from Summit Roofing — $73,500 for full replacement. We should discuss at the April meeting. I'd like to get at least one more bid before we decide.\n\nThoughts?\n\nCarol",
        cc_list=["diana", "alice", "bob"],
    ))

    scenarios.append(EmailScenario(
        name="cc_roof_discussion_2",
        intent="thread_cc",
        sender_key="diana",
        subject="Re: Roof replacement timeline",
        body="Agreed, let's get 2-3 bids. I can reach out to Pacific Roofing as well. Our reserve fund can cover it but we should be strategic about timing.\n\nDiana",
        is_reply_to="cc_roof_discussion_1",
        cc_list=["carol", "alice", "bob"],
    ))

    scenarios.append(EmailScenario(
        name="cc_roof_discussion_3",
        intent="thread_cc",
        sender_key="alice",
        subject="Re: Roof replacement timeline",
        body="Makes sense. Is there any urgency or can we wait until fall when prices might be lower? Also, does our insurance cover any of this?\n\nAlice",
        is_reply_to="cc_roof_discussion_2",
        cc_list=["carol", "diana", "bob"],
    ))

    scenarios.append(EmailScenario(
        name="cc_plumbing_thread_1",
        intent="thread_cc",
        sender_key="bob",
        subject="Low water pressure in Unit 2",
        body="Hey Carol and Diana,\n\nI've been having really low water pressure in my kitchen and bathroom for the past week. It's getting worse. Can we get Bay Area Plumbing to take a look?\n\nBob",
        cc_list=["carol", "diana"],
    ))

    scenarios.append(EmailScenario(
        name="cc_plumbing_thread_2",
        intent="thread_cc",
        sender_key="carol",
        subject="Re: Low water pressure in Unit 2",
        body="Bob — I'll call Bay Area Plumbing tomorrow morning. They're on retainer so they should be able to come within a few days. Diana, can you note this as a maintenance item?\n\nCarol",
        is_reply_to="cc_plumbing_thread_1",
        cc_list=["bob", "diana"],
    ))

    # -----------------------------------------------------------------------
    # D. CORRECTION INTENT (4 scenarios)
    # -----------------------------------------------------------------------

    scenarios.append(EmailScenario(
        name="correction_thats_wrong",
        intent="correction",
        sender_key="carol",
        subject="Re: Pet rules and next meeting",
        body="That's wrong — the pet weight limit is 25 pounds, not 20 pounds. Please correct your answer.\n\nCarol",
        is_reply_to="q_multi_topic",
    ))

    scenarios.append(EmailScenario(
        name="correction_factual",
        intent="correction",
        sender_key="diana",
        subject="Re: Monthly dues question",
        body="Actually, the dues went up to $1,000 in January 2026, not January 2025 as your response said. The increase was approved at the January 15, 2026 board meeting.\n\nDiana",
        is_reply_to="q_financial_dues",
    ))

    scenarios.append(EmailScenario(
        name="correction_date",
        intent="correction",
        sender_key="bob",
        subject="Re: Fire alarm inspection",
        body="Incorrect — the fire inspection was on March 15, 2026, not March 10. I was there when it happened.\n\nBob",
        is_reply_to="q_maintenance_history",
    ))

    scenarios.append(EmailScenario(
        name="correction_polite",
        intent="correction",
        sender_key="alice",
        subject="Re: Seismic rating",
        body="I think there might be an error in your response — you mentioned the building was built in 1985, but I'm pretty sure it was built in 1978. My deed says 1978. Could you double check?\n\nAlice",
        is_reply_to="q_not_in_knowledge_base",
    ))

    # -----------------------------------------------------------------------
    # E. EDGE CASES (8 scenarios)
    # -----------------------------------------------------------------------

    scenarios.append(EmailScenario(
        name="edge_no_body",
        intent="edge_case",
        sender_key="alice",
        subject="When is trash pickup?",
        body="",
    ))

    scenarios.append(EmailScenario(
        name="edge_html_only",
        intent="edge_case",
        sender_key="bob",
        subject="Quick question about quiet hours",
        body="<html><body><div style='font-family: Arial;'><p>Hi HouseKeep,</p><p>What are the <b>quiet hours</b>? My neighbor has been doing construction late at night and I want to know if they're violating the rules.</p><p>Thanks,<br><span style='color: #666;'>Bob Martinez<br>Unit 2</span></p></div></body></html>",
        html_only=True,
    ))

    scenarios.append(EmailScenario(
        name="edge_inline_image_plus_pdf",
        intent="edge_case",
        sender_key="diana",
        subject="Fwd: Fire inspection report + photo",
        body="Here's the fire inspection report along with a photo of the new extinguisher location.\n\n[Inline signature image]\n\nDiana Park\nBoard Secretary",
        attachments=[
            AttachmentSpec("Fire_Inspection_2026.pdf", "pdf", "fire_inspection"),
            AttachmentSpec("extinguisher_location.jpg", "jpg", "maintenance_photo_water"),
        ],
        is_forward=True,
        target_category="Maintenance",
        target_subcategory="Inspection",
    ))

    scenarios.append(EmailScenario(
        name="edge_unicode_subject",
        intent="edge_case",
        sender_key="alice",
        subject="Pregunta sobre las reglas del edificio 🏠",
        body="Hi HouseKeep,\n\nMi mamá va a visitarme y quiere saber — can she park in the guest parking area overnight? She'll be staying for a week. Also, she has a small dog (chihuahua, about 6 lbs). Are pets allowed for guests?\n\nGracias,\nAlice Chen\n陳雅琳",
    ))

    scenarios.append(EmailScenario(
        name="edge_very_long_body",
        intent="edge_case",
        sender_key="bob",
        subject="Detailed maintenance concerns",
        body="Hi HouseKeep,\n\nI have a very long and detailed list of maintenance concerns I'd like to document.\n\n" + "\n\n".join(
            f"Issue #{i+1}: I've noticed that the {'hallway light on floor ' + str((i % 2) + 1) if i % 3 == 0 else 'garage door mechanism' if i % 3 == 1 else 'stairwell railing on floor ' + str((i % 2) + 1)} has been {'flickering intermittently' if i % 3 == 0 else 'making unusual grinding noises' if i % 3 == 1 else 'feeling loose when you grab it'}. "
            f"This has been happening since approximately {'January' if i % 4 == 0 else 'February' if i % 4 == 1 else 'March' if i % 4 == 2 else 'early April'} 2026. "
            f"I've mentioned this to {'Carol' if i % 2 == 0 else 'Diana'} in passing but wanted to make sure it's officially documented. "
            f"{'I think this might be related to the water pressure issue we had.' if i % 5 == 0 else 'This seems like it could be a safety concern.' if i % 5 == 1 else 'Not urgent but should be addressed before it gets worse.' if i % 5 == 2 else 'Other residents have mentioned this too.' if i % 5 == 3 else 'Please add this to the maintenance log.'}"
            for i in range(80)
        ) + "\n\nThanks for logging all of this.\n\nBob",
    ))

    scenarios.append(EmailScenario(
        name="edge_corrupted_pdf",
        intent="edge_case",
        sender_key="carol",
        subject="Fwd: Warranty document (might be corrupted)",
        body="The scanner might have messed this up. Can you try to read it?\n\nCarol",
        attachments=[AttachmentSpec("warranty_corrupted.pdf", "empty_pdf", "warranty_doc")],
        is_forward=True,
        target_category="Vendor",
        target_subcategory="Warranty",
    ))

    scenarios.append(EmailScenario(
        name="edge_triple_forward",
        intent="edge_case",
        sender_key="diana",
        subject="Fwd: Fwd: Fwd: Original insurance renewal notice",
        body="---------- Forwarded message ---------\nFrom: Pacific Coast Insurance <agent@pcib.com>\nDate: March 1, 2026\nSubject: Insurance Renewal — 150 Twin Peaks Blvd\n\n---------- Forwarded message ---------\nFrom: Carol Davis\nDate: March 5, 2026\n\nDiana, see below. We need to handle this.\n\n---------- Forwarded message ---------\nFrom: Diana Park\nDate: March 10, 2026\n\nFiling this with HouseKeep for tracking. Our insurance renewal is coming up.\n\nOriginal message:\nDear 150 Twin Peaks Blvd HOA,\n\nYour property insurance policy (HP-2024-88831) expires on December 31, 2025. Please contact our office to discuss renewal options. We recommend scheduling a review at least 60 days before expiration.\n\nBest regards,\nPacific Coast Insurance Brokers",
        is_forward=True,
    ))

    scenarios.append(EmailScenario(
        name="edge_three_photos",
        intent="edge_case",
        sender_key="bob",
        subject="Garage door damage — 3 photos",
        body="Found damage on the garage door. Looks like someone scraped it. Here are photos from three angles.\n\nBob",
        attachments=[
            AttachmentSpec("garage_damage_1.jpg", "jpg", "maintenance_photo_water"),
            AttachmentSpec("garage_damage_2.jpg", "jpg", "maintenance_photo_water"),
            AttachmentSpec("garage_damage_3.jpg", "jpg", "maintenance_photo_water"),
        ],
        target_category="Maintenance",
        target_subcategory="Photo/Evidence",
    ))

    return scenarios


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

ALL_SCENARIOS = build_scenarios()
SCENARIO_BY_NAME: dict[str, EmailScenario] = {s.name: s for s in ALL_SCENARIOS}
