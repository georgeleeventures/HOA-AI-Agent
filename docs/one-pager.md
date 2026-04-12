# HouseKeep AI — Product One-Pager

## The Problem

Homeowners Associations generate a mountain of documents, emails, and records — but none of it is searchable or easy to find. The result:

- **Rules and policies are buried.** CC&Rs, TIC agreements, bylaws, and house rules live in email attachments and filing cabinets. Finding the answer to "Can I install a satellite dish?" means digging through dozens of documents.
- **Board members are overwhelmed.** Volunteer board members spend hours answering the same questions from different residents. It's practically a part-time job — unpaid.
- **Finding good contractors is unreasonably hard.** When something breaks, nobody knows who to call. Past invoices, vendor contacts, and work history are scattered across old email threads.
- **Records are disorganized.** Meeting minutes, maintenance logs, financial reports, and inspection records exist but aren't centralized or searchable.
- **Non-technical residents are stuck.** Most HOA members aren't going to learn new software. They need answers, not another app.

## The Solution

**HouseKeep AI** is an AI assistant that lives in your HOA's email inbox. It reads and organizes all of your HOA's historical emails and documents, builds a searchable knowledge base, and answers questions — all via email.

Think of it as an always-available, infinitely patient HOA assistant that has read every document your HOA has ever produced.

## How It Works

| Step | What Happens |
|------|-------------|
| **1. Connect** | Link your HOA's Gmail account. HouseKeep ingests all historical emails and attachments — a one-time setup. |
| **2. Classify** | Every document is automatically categorized (governing docs, financials, maintenance records, meeting minutes, insurance, legal, etc.) and OCR'd if scanned. |
| **3. Ask** | Email HouseKeep or use the web dashboard to ask questions. Get answers grounded in your HOA's actual documents, with citations. |
| **4. Track** | CC HouseKeep on email threads to automatically log conversations. Forward documents for instant filing. Maintenance updates, meeting notes, and financial records are tracked as they arrive. |

## Who It's For

| Role | What HouseKeep Does For You |
|------|----------------------------|
| **Residents** | Ask about rules, trash schedules, payment portals, what modifications are allowed, pet policies, parking rules |
| **Board Members / President** | Reduce repetitive Q&A, get instant policy citations, track compliance, review maintenance history |
| **Secretary** | Auto-summarize meeting notes, maintain a searchable record of all board communications |
| **Treasurer** | Budget tracking, reserve fund projections, year-over-year cost comparisons, automatic invoice filing |
| **Property Managers** | Full maintenance history, contractor records, inspection schedules, vendor contract tracking |

## Why Email-First

- **Zero learning curve.** Everyone knows how to send an email. No app to download, no account to create, no training needed.
- **Meets people where they are.** HOA members are not technical users. Email is the tool they already use for HOA communication.
- **Passive tracking.** CC HouseKeep on any thread and it silently logs the conversation. No extra steps.
- **Works with any device.** Phone, tablet, laptop, desktop — if it can send email, it works with HouseKeep.

A simple web dashboard is also available for residents who want a richer experience — browse documents by category, chat in real time, view maintenance timelines, and search across everything.

## Example Questions

**Residents ask:**
- "Can I install a mini-split AC on my exterior wall?"
- "When is trash pickup day?"
- "How do I set up autopay for HOA dues?"
- "What's the pet policy?"

**Board members ask:**
- "Summarize the last 3 board meeting minutes"
- "What's our current reserve fund balance?"
- "What did we pay for plumbing last time?"
- "Are we on track with the annual budget?"

**Secretaries forward meeting notes** and get back an auto-generated summary, filed and searchable.

**Treasurers forward invoices** and they're automatically categorized, logged, and available for future cost analysis.

## What It Costs

**Free for all HOA residents and administrators.** No subscription, no per-user fees, no hidden charges.

HouseKeep is sustained through a contractor and service provider marketplace. When maintenance needs come up, HouseKeep can suggest vetted local professionals — plumbers, electricians, handymen, painters. Contractors pay for the opportunity to reach verified, active property management contacts. Suggestions are always clearly labeled and transparent.

## Technical Summary

- **Hosting:** Single Google Cloud VM (~$7/month base infrastructure)
- **AI:** Google Gemini for document understanding, OCR, classification, and question answering
- **Email:** Gmail API integration with push notifications for real-time processing
- **Security:** Email sender verification (SPF/DKIM/DMARC), role-based access, encrypted data at rest and in transit, full audit logging
- **Data:** All data stays within the HOA's own isolated environment. No data is shared between HOAs.

## Getting Started

1. An HOA administrator connects the HOA's Gmail account (one-time, 5-minute setup)
2. HouseKeep ingests all historical emails and documents
3. Authorized residents are added by email address
4. Residents receive a welcome email with the HouseKeep address and sample questions
5. Start asking questions

No app to install. No training required. Just email.
