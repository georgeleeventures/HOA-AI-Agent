"""Hardcoded demo data for the demo mode experience."""

DEMO_DOCUMENTS = [
    {
        "id": "demo-doc-1",
        "title": "CC&Rs — Declaration of Covenants, Conditions & Restrictions",
        "source_filename": "CCRs_2019_Amended.pdf",
        "category": "Governing",
        "subcategory": "CC&Rs",
        "created_at": "2024-06-15T10:00:00Z",
    },
    {
        "id": "demo-doc-2",
        "title": "Bylaws of Maplewood Terrace HOA",
        "source_filename": "Bylaws_Maplewood_Terrace.pdf",
        "category": "Governing",
        "subcategory": "Bylaws",
        "created_at": "2024-06-15T10:05:00Z",
    },
    {
        "id": "demo-doc-3",
        "title": "2025 Annual Operating Budget",
        "source_filename": "2025_Budget_Approved.xlsx",
        "category": "Financial",
        "subcategory": "Budget",
        "created_at": "2025-01-10T09:30:00Z",
    },
    {
        "id": "demo-doc-4",
        "title": "Reserve Fund Study — 2024 Update",
        "source_filename": "Reserve_Study_2024.pdf",
        "category": "Financial",
        "subcategory": "Reserve Study",
        "created_at": "2024-09-20T14:00:00Z",
    },
    {
        "id": "demo-doc-5",
        "title": "Board Meeting Minutes — March 2026",
        "source_filename": "Minutes_March_2026.pdf",
        "category": "Meeting",
        "subcategory": "Minutes",
        "created_at": "2026-03-18T19:00:00Z",
    },
    {
        "id": "demo-doc-6",
        "title": "Board Meeting Minutes — February 2026",
        "source_filename": "Minutes_Feb_2026.pdf",
        "category": "Meeting",
        "subcategory": "Minutes",
        "created_at": "2026-02-15T19:00:00Z",
    },
    {
        "id": "demo-doc-7",
        "title": "Insurance Policy — General Liability",
        "source_filename": "Liability_Policy_2025.pdf",
        "category": "Insurance",
        "subcategory": "General Liability",
        "created_at": "2025-04-01T08:00:00Z",
    },
    {
        "id": "demo-doc-8",
        "title": "Landscaping Contract — GreenScape LLC",
        "source_filename": "GreenScape_Contract_2025.pdf",
        "category": "Vendor",
        "subcategory": "Landscaping",
        "created_at": "2025-03-01T11:00:00Z",
    },
    {
        "id": "demo-doc-9",
        "title": "Roof Inspection Report — January 2026",
        "source_filename": "Roof_Inspection_Jan2026.pdf",
        "category": "Maintenance",
        "subcategory": "Inspections",
        "created_at": "2026-01-22T10:30:00Z",
    },
    {
        "id": "demo-doc-10",
        "title": "Pet Policy — Rules and Regulations Addendum",
        "source_filename": "Pet_Policy_Addendum.pdf",
        "category": "Governing",
        "subcategory": "Rules",
        "created_at": "2023-08-10T15:00:00Z",
    },
]

DEMO_MAINTENANCE = [
    {
        "id": "demo-maint-1",
        "unit": "203",
        "description": "Water heater replacement — unit reported no hot water. Plumber diagnosed failed heating element and recommended full replacement due to age (12 years).",
        "issue_type": "Plumbing",
        "status": "completed",
        "photos": [],
        "contractor": "Bay Area Plumbing Co.",
        "cost": 2850.00,
        "reported_by": "tenant@example.com",
        "created_at": "2026-03-28T09:15:00Z",
        "updated_at": "2026-04-02T16:00:00Z",
    },
    {
        "id": "demo-maint-2",
        "unit": "Common Area",
        "description": "Annual fire alarm system inspection and testing. All units passed. Two smoke detectors replaced in hallway.",
        "issue_type": "Fire Safety",
        "status": "completed",
        "photos": [],
        "contractor": "SafeGuard Fire Systems",
        "cost": 780.00,
        "reported_by": "admin@example.com",
        "created_at": "2026-03-15T08:00:00Z",
        "updated_at": "2026-03-15T12:30:00Z",
    },
    {
        "id": "demo-maint-3",
        "unit": "105",
        "description": "Kitchen faucet leak — steady drip from base of faucet. Maintenance scheduled.",
        "issue_type": "Plumbing",
        "status": "in_progress",
        "photos": [],
        "contractor": "Bay Area Plumbing Co.",
        "cost": None,
        "reported_by": "resident105@example.com",
        "created_at": "2026-04-08T11:20:00Z",
        "updated_at": "2026-04-10T09:00:00Z",
    },
    {
        "id": "demo-maint-4",
        "unit": "Common Area",
        "description": "Garage door opener motor grinding noise. Technician found worn gear and chain tension issue.",
        "issue_type": "Structural",
        "status": "completed",
        "photos": [],
        "contractor": "Pacific Door & Gate",
        "cost": 425.00,
        "reported_by": "admin@example.com",
        "created_at": "2026-02-20T14:00:00Z",
        "updated_at": "2026-02-25T11:00:00Z",
    },
    {
        "id": "demo-maint-5",
        "unit": "101",
        "description": "Exterior window seal deterioration on north-facing windows. Water intrusion reported during heavy rain.",
        "issue_type": "Weatherproofing",
        "status": "reported",
        "photos": [],
        "contractor": None,
        "cost": None,
        "reported_by": "demo@housekeep.click",
        "created_at": "2026-04-11T16:45:00Z",
        "updated_at": "2026-04-11T16:45:00Z",
    },
    {
        "id": "demo-maint-6",
        "unit": "Common Area",
        "description": "Spring landscaping — seasonal planting, mulch refresh, irrigation system startup and calibration.",
        "issue_type": "Landscaping",
        "status": "completed",
        "photos": [],
        "contractor": "GreenScape LLC",
        "cost": 1200.00,
        "reported_by": "admin@example.com",
        "created_at": "2026-03-01T07:00:00Z",
        "updated_at": "2026-03-05T17:00:00Z",
    },
]

# Pre-built chat responses for common demo questions
DEMO_CHAT_RESPONSES = {
    "default": {
        "answer": "Based on the HOA governing documents, I found the following information.\n\nThis is a demo response — in a live environment, HouseKeep searches through all of your HOA's emails, documents, and records to provide cited answers specific to your community.\n\nTry asking about pet policies, trash schedules, reserve funds, or maintenance history to see more examples.",
        "sources": [
            {"document_title": "CC&Rs — Declaration of Covenants, Conditions & Restrictions", "category": "Governing"},
        ],
        "confidence": "high",
        "audit_id": "demo-audit-0",
        "needs_clarification": False,
    },
    "pet": {
        "answer": "According to the Pet Policy Addendum (updated August 2023), residents may keep up to two domestic pets per unit. The following rules apply:\n\n1. Dogs must be leashed in all common areas\n2. Pet waste must be picked up immediately\n3. Pets over 50 lbs require written board approval\n4. No exotic animals (reptiles, birds of prey, etc.)\n5. A $200 refundable pet deposit is required\n\nViolations may result in fines starting at $50 per incident. If you need to register a pet or request an exception, contact the board at the next monthly meeting.",
        "sources": [
            {"document_title": "Pet Policy — Rules and Regulations Addendum", "category": "Governing"},
            {"document_title": "CC&Rs — Declaration of Covenants, Conditions & Restrictions", "category": "Governing"},
        ],
        "confidence": "high",
        "audit_id": "demo-audit-1",
        "needs_clarification": False,
    },
    "trash": {
        "answer": "Trash pickup is every Tuesday and Friday morning. Here are the details:\n\n- Regular trash: Tuesday & Friday (bins out by 7 AM)\n- Recycling: Tuesday only (blue bins)\n- Green waste / compost: Friday only (green bins)\n- Bulk item pickup: First Saturday of each month (schedule with waste management 48 hours in advance)\n\nBins must be brought back from the curb by 8 PM on pickup day. Per Section 4.12 of the CC&Rs, bins may not be stored in visible areas.",
        "sources": [
            {"document_title": "CC&Rs — Declaration of Covenants, Conditions & Restrictions", "category": "Governing"},
        ],
        "confidence": "high",
        "audit_id": "demo-audit-2",
        "needs_clarification": False,
    },
    "reserve": {
        "answer": "Based on the 2024 Reserve Fund Study and the 2025 Annual Budget:\n\n- Current reserve fund balance: $142,500\n- Recommended minimum: $120,000\n- Funding level: 118% (well-funded)\n- Monthly contribution: $1,200/month from HOA dues\n\nMajor upcoming expenses projected:\n- Roof replacement (2028): estimated $45,000\n- Exterior paint (2027): estimated $18,000\n- Elevator modernization (2030): estimated $35,000\n\nThe reserve fund is currently in healthy standing according to the 2024 study.",
        "sources": [
            {"document_title": "Reserve Fund Study — 2024 Update", "category": "Financial"},
            {"document_title": "2025 Annual Operating Budget", "category": "Financial"},
        ],
        "confidence": "high",
        "audit_id": "demo-audit-3",
        "needs_clarification": False,
    },
    "meeting": {
        "answer": "Here's a summary of the March 2026 board meeting:\n\n**Key Decisions:**\n- Approved the landscaping contract renewal with GreenScape LLC ($1,200/quarter)\n- Voted to repair Unit 105 kitchen faucet under HOA maintenance coverage\n- Tabled discussion on EV charging station installation until April meeting\n\n**Action Items:**\n- Secretary to distribute updated parking rules by April 1\n- Treasurer to get two additional bids for exterior painting\n- Property manager to schedule roof follow-up inspection\n\n**Next Meeting:** April 15, 2026 at 7:00 PM",
        "sources": [
            {"document_title": "Board Meeting Minutes — March 2026", "category": "Meeting"},
        ],
        "confidence": "high",
        "audit_id": "demo-audit-4",
        "needs_clarification": False,
    },
    "budget": {
        "answer": "Based on the 2025 Annual Operating Budget, here's the current status:\n\n**Budget Overview (Year-to-Date through March 2026):**\n- Total annual budget: $86,400\n- Spent through Q1: $19,850 (23% — on track)\n- Remaining: $66,550\n\n**Top Expense Categories:**\n- Insurance: $12,000/year (paid annually in January)\n- Landscaping: $4,800/year ($1,200/quarter)\n- Utilities (common areas): $6,000/year\n- Maintenance reserve: $14,400/year\n- Property management: $9,600/year\n\n**Notable:** No unexpected major expenses so far this year. The water heater replacement in Unit 203 ($2,850) was covered from the maintenance reserve.",
        "sources": [
            {"document_title": "2025 Annual Operating Budget", "category": "Financial"},
            {"document_title": "Reserve Fund Study — 2024 Update", "category": "Financial"},
        ],
        "confidence": "high",
        "audit_id": "demo-audit-5",
        "needs_clarification": False,
    },
    "satellite": {
        "answer": "According to Section 7.3 of the CC&Rs, satellite dish installation requires prior written approval from the HOA board. Here are the guidelines:\n\n1. Dishes up to 1 meter in diameter are permitted under FCC regulations\n2. Installation must be on your unit's exclusive-use area (balcony or patio)\n3. Roof-mounted installations are not allowed without board exception\n4. Submit an Architectural Modification Request form to the board\n5. Board review typically takes 15-30 days\n\nThe FCC's Over-the-Air Reception Devices (OTARD) rule does protect your right to install a dish, but placement restrictions for safety and aesthetics can still apply.",
        "sources": [
            {"document_title": "CC&Rs — Declaration of Covenants, Conditions & Restrictions", "category": "Governing"},
        ],
        "confidence": "high",
        "audit_id": "demo-audit-6",
        "needs_clarification": False,
    },
    "maintenance": {
        "answer": "Here are the outstanding and recent maintenance items:\n\n**Open / In Progress:**\n- Unit 105: Kitchen faucet leak (plumber scheduled)\n- Unit 101: Window seal deterioration — reported April 11, awaiting contractor assessment\n\n**Recently Completed:**\n- Unit 203: Water heater replaced — $2,850 (Bay Area Plumbing Co.)\n- Common Area: Fire alarm inspection — $780 (SafeGuard Fire Systems)\n- Common Area: Garage door motor repair — $425 (Pacific Door & Gate)\n- Common Area: Spring landscaping — $1,200 (GreenScape LLC)\n\nTotal maintenance spend this quarter: $5,255",
        "sources": [
            {"document_title": "Board Meeting Minutes — March 2026", "category": "Meeting"},
        ],
        "confidence": "high",
        "audit_id": "demo-audit-7",
        "needs_clarification": False,
    },
}


def match_demo_response(question: str) -> dict:
    """Match a question to a demo response using simple keyword matching."""
    q = question.lower()
    if any(w in q for w in ("pet", "dog", "cat", "animal")):
        return DEMO_CHAT_RESPONSES["pet"]
    if any(w in q for w in ("trash", "garbage", "recycl", "waste", "bin")):
        return DEMO_CHAT_RESPONSES["trash"]
    if any(w in q for w in ("reserve", "fund balance")):
        return DEMO_CHAT_RESPONSES["reserve"]
    if any(w in q for w in ("meeting", "minutes", "summarize", "board meeting")):
        return DEMO_CHAT_RESPONSES["meeting"]
    if any(w in q for w in ("budget", "on track", "expense", "spending")):
        return DEMO_CHAT_RESPONSES["budget"]
    if any(w in q for w in ("satellite", "dish", "install", "antenna")):
        return DEMO_CHAT_RESPONSES["satellite"]
    if any(w in q for w in ("maintenance", "repair", "outstanding", "fix")):
        return DEMO_CHAT_RESPONSES["maintenance"]
    return DEMO_CHAT_RESPONSES["default"]
