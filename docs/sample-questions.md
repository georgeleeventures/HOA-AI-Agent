# HouseKeep AI — Sample Questions Catalog

## Overview

HouseKeep AI responds to questions via email or the web chat interface. Users write in plain English — no special syntax, no commands, no formatting requirements. This catalog shows the breadth of questions the system should handle, organized by role.

This document also serves as a testing and validation resource. Every question listed here should produce a grounded, cited answer when tested against a fully ingested HOA knowledge base.

---

## Resident Questions

### Rules and Policies

- "Can I install a mini-split AC unit on my exterior wall?"
- "What's the policy on Airbnb or short-term rentals?"
- "Can I paint my front door a different color?"
- "Is there a pet policy? What are the weight limits?"
- "What's the guest parking policy?"
- "Am I allowed to put a satellite dish on the roof?"
- "Can I install a Ring doorbell camera in the hallway?"
- "What are the quiet hours?"
- "Can I have a barbecue grill on my balcony?"
- "What are the rules about holiday decorations in common areas?"
- "Can I run a business from my unit?"
- "What's the policy on smoking in common areas?"
- "Can I install hardwood floors, or is carpet required?"
- "Am I allowed to have a storage unit in the garage?"
- "What changes require board approval before I can proceed?"
- "Can I hang a flag or banner from my window?"
- "What's the policy on package deliveries and common area storage?"
- "Are electric vehicle chargers allowed in the garage?"
- "Can I install a washer/dryer in my unit?"
- "What are the rules for moving furniture in and out?"

### Day-to-Day Living

- "When is trash pickup day?"
- "How do I get a key to the common room?"
- "What's the WiFi password for the common area?"
- "When is the next board meeting?"
- "How do I report a maintenance issue?"
- "What's the process for selling my unit?"
- "How do I update my contact information with the HOA?"
- "Where do I pick up packages?"
- "How do I reserve the common area for an event?"
- "Who do I contact about a noise complaint?"
- "Is there a move-in/move-out procedure?"
- "What's the emergency contact for the building?"

### Payments and Financial

- "How much are my monthly HOA dues?"
- "When is the next payment due?"
- "How do I set up autopay for HOA dues?"
- "How do I set up the property tax payment portal?"
- "Was there a special assessment this year?"
- "What does my HOA fee cover?"
- "Where do I send my payment if I'm mailing a check?"
- "What happens if I'm late on a payment?"

### Ownership (TIC-Specific)

- "What percentage of the building do I own?"
- "Who are the other owners and what are their percentages?"
- "What are my voting rights based on my ownership share?"
- "What happens if an owner wants to sell their share?"
- "How are shared expenses divided among owners?"

---

## Board Member / Admin Questions

### Governance and Compliance

- "Summarize the last 3 board meeting minutes"
- "What did the board vote on in January?"
- "What's the quorum requirement for a board vote?"
- "When do current board member terms expire?"
- "What are the officer roles and their responsibilities?"
- "What's the process for amending the bylaws?"
- "Are there any outstanding violations that need follow-up?"
- "What's the procedure for holding a special meeting?"
- "What resolutions were passed this year?"

### Financial Management

- "What's our current reserve fund balance?"
- "Are we on track with the annual budget?"
- "What did we pay for plumbing work last time?"
- "Compare our landscaping costs year-over-year"
- "What's our projected reserve fund in 3 years at current contribution rates?"
- "Flag any expenses that seem unusual compared to last year"
- "What's our total insurance premium this year?"
- "How much did we spend on maintenance last quarter?"
- "What's the breakdown of our operating budget by category?"
- "Are any assessments overdue? Which units?"

### Maintenance and Operations

- "Show me all maintenance done on unit 3 in the last year"
- "When was the fire alarm system last inspected?"
- "What's the warranty status on the elevator repair from 2024?"
- "List all outstanding maintenance requests"
- "Who's our current landscaping vendor and when does the contract expire?"
- "What did the inspector say about the foundation last time?"
- "When is the next fire inspection due?"
- "What maintenance has been deferred and why?"
- "Show me a timeline of all roof-related work"

### Legal

- "What did the attorney say about the fence dispute in March?"
- "Are there any pending legal matters?"
- "What's our insurance policy number and expiration date?"
- "When does our D&O insurance renew?"
- "Have there been any insurance claims this year?"
- "What's the status of the lien on unit 5?"

### Ownership and Records

- "Who owns what percentage?" (TIC ownership breakdown)
- "Which units are owner-occupied vs. rented?"
- "When did the last ownership transfer happen?"
- "Do we have current contact info for all owners?"
- "Are all residents on the authorized list?"

---

## Secretary Use Cases

### Meeting Management

- Forward meeting notes to HouseKeep → auto-summarized and filed
- "Draft an agenda for the next board meeting based on open items"
- "What action items came out of the last meeting?"
- "Who was at the February board meeting?"
- "What decisions were tabled for follow-up?"
- "Generate a summary of all board communications this month"
- "What topics have been discussed most frequently this year?"

### Record Keeping

- CC HouseKeep on email threads → automatically logged and searchable
- Forward important documents → automatically classified and filed
- "When was the last time we updated the resident contact list?"
- "What documents have been filed this month?"
- "Are there any documents flagged for review?"

---

## Treasurer Use Cases

### Invoice and Expense Tracking

- Forward invoices to HouseKeep → automatically categorized and logged
- Forward receipts → matched to budget line items
- "What's our total spend on plumbing in the last 2 years?"
- "What's the breakdown of this year's budget vs. actual spending?"
- "Are any vendor contracts up for renewal in the next 60 days?"
- "What was our biggest unexpected expense last year?"

### Budget and Forecasting

- "What's our projected reserve fund in 3 years at current contribution rates?"
- "Compare our landscaping costs year-over-year"
- "Flag any expenses that seem unusual compared to last year"
- "What would happen to our reserve fund if we increased dues by 5%?"
- "What are our largest recurring expenses?"
- "How do our maintenance costs compare to last year at this point?"

### Vendor Management

- "How much have we paid ABC Plumbing in total?"
- "Which vendors have we used for electrical work?"
- "When does our elevator maintenance contract expire?"
- "What are the payment terms for our landscaping vendor?"

---

## Maintenance Scenarios

### Reporting Issues

| Scenario | What the Resident Does | What HouseKeep Does |
|----------|----------------------|-------------------|
| Water leak | Emails photos of the leak to HouseKeep | Logs as "Maintenance > Work Order," categorizes as plumbing/water damage, suggests contacting the building manager |
| Broken common area fixture | Sends email: "The hallway light on floor 2 is out" | Logs the report, checks if similar issues have been reported, confirms receipt |
| Noise complaint | Emails: "Unit 4 is playing loud music after midnight" | Logs the complaint, references quiet hours from house rules, suggests next steps |

### Tracking History

- "When was the fire alarm system last inspected?"
- "What's the warranty status on the elevator repair from 2024?"
- "Show me all plumbing-related work orders from the last year"
- "What was the cost of the roof repair in 2023?"
- "Has unit 2 had any water damage issues before?"
- "How many maintenance requests have we had this quarter?"

### Finding Contractors (Monetization Opportunity)

- "We need a handyman for minor repairs — any recommendations?"
- "Can you suggest a licensed plumber in the San Francisco area?"
- "We need quotes for repainting the exterior — who should we contact?"
- "Is there a good electrician who's worked with buildings like ours?"
- "We need a pest control service — any suggestions?"
- "Who did we use for the last HVAC repair?"

---

## Email Thread Behaviors

### CC'd on a Thread

The agent silently tracks and logs the conversation. It does **not** respond or chime in unless directly addressed (e.g., "Hey HouseKeep, what does the policy say about this?").

**Use case:** Board members CC HouseKeep on a discussion about a roof repair. The entire thread is logged and searchable. Later, anyone can ask "What was discussed in the email thread about the roof repair?" and get a summary.

### Directly Emailed with a Question

The agent responds with an answer, citing source documents.

**Example response:**
> According to the CC&Rs (Section 4.2, "Exterior Modifications"), all exterior modifications — including satellite dishes, antennas, and HVAC units — require prior written approval from the Board of Directors. The request must be submitted in writing at least 30 days before the planned installation.
>
> Source: CC&Rs, Section 4.2 (revised March 2024)
>
> **Related questions you might have:**
> - "What's the process for submitting a modification request?"
> - "How long does board approval usually take?"

### Forwarded a Document

The agent ingests, classifies, and confirms receipt.

**Example response:**
> Got it — I've filed this as **Insurance > Policy** (Hartford Property Insurance, Policy #HP-2024-88831). Coverage: $2M general liability, $500K property. Expires: December 31, 2025.
>
> This is now searchable. Anyone authorized can ask about insurance coverage and I'll reference this document.

### Forwarded Meeting Notes or Photos

The agent processes and logs the content.

**Example response:**
> I've logged 6 photos from the April 10th plumbing repair to the maintenance record for Unit 2.
>
> Summary: Water damage under kitchen sink, copper pipe replacement performed by Bay Area Plumbing. Photos show before/after of the repair.

### From an Unknown Sender

**Response:**
> Thank you for your email. I don't have you on file as an authorized member of this HOA. If you believe this is an error, please contact your HOA administrator to add your email address.
>
> For privacy and security, I'm unable to share any HOA information with unverified contacts.

---

## Edge Cases and Limitations

### Questions Not in the Knowledge Base

**Response pattern:**
> I don't have information about that in our records. You may want to check with [relevant contact — e.g., "your HOA president" or "the building manager"].

### Requests for Legal Advice

**Response pattern:**
> I can show you what the governing documents say about [topic], but I'm not able to provide legal advice. For legal questions, please consult with the HOA's attorney.
>
> Here's what I found in the CC&Rs: [relevant excerpt with citation]

### Requests to Take Actions

**Response pattern:**
> I can only provide information and answer questions — I'm not able to [delete records / transfer funds / approve requests / etc.]. For that, please contact [relevant admin or process].

### Ambiguous Questions

**Response pattern:**
> I want to make sure I give you the right answer. Could you clarify what you mean by [ambiguous part]? For example, are you asking about [interpretation A] or [interpretation B]?

### Conflicting Information in Documents

**Response pattern:**
> I found information about this in two documents that may not agree:
>
> 1. The CC&Rs (Section 3.1, 2019) say: [excerpt]
> 2. The House Rules (revised 2023) say: [excerpt]
>
> The more recent document may take precedence, but you may want to confirm with the board which applies.

### Questions About Other Residents' Private Information

**Response pattern:**
> I'm not able to share other residents' personal information (contact details, payment status, etc.) for privacy reasons. Please contact the HOA administrator if you need this information.
