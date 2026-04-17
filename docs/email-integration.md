# HouseKeep AI — Email Integration Guide

## Provider Abstraction

HouseKeep supports pluggable email providers via the `EmailProvider` interface (`app/email/provider.py`):

```python
class EmailProvider(ABC):
    async def send(self, from_email, to, subject, body, in_reply_to=None, references=None) -> str
    async def fetch_email(self, email_id) -> ParsedEmail
```

Two implementations:
- `ResendProvider` — production provider (free tier: 3,000 emails/month)
- `GmailProvider` — backward compatibility wrapper around existing `GmailClient`

Switch via config: `EMAIL_PROVIDER=resend` (or `gmail`).

## Resend Setup

### 1. Get API Key

Sign up at [resend.com](https://resend.com), create an API key, add to `.env`:
```
RESEND_API_KEY=re_xxxxxxxxxxxx
EMAIL_PROVIDER=resend
EMAIL_WEBHOOK_SECRET=your-random-secret
```

### 2. DNS Records

Add to your domain's DNS (`housekeep.click`):

| Type | Name | Value | Purpose |
|------|------|-------|---------|
| MX | `*.housekeep.click` | Resend's inbound servers | Receive email |
| TXT | `housekeep.click` | `v=spf1 include:resend.com ~all` | SPF |
| CNAME | `resend._domainkey.housekeep.click` | (from Resend dashboard) | DKIM |

### 3. Webhook URL

In the Resend dashboard, set the inbound webhook URL to:
```
https://housekeep.click/webhooks/email/your-random-secret
```

## Inbound Flow

```
Resident emails board@twinpeaks.housekeep.click
    ↓
Resend receives, sends webhook event (email.received)
    ↓
POST /webhooks/email/{secret}
    ↓
Fetch full email via Resend API (body + attachments)
    ↓
Extract HOA slug from To: address → hoa_id
    ↓
Verify sender (residents table + DKIM)
    ↓
Classify intent (question | document_forward | thread_cc | correction)
    ↓
Process and send reply via Resend API
```

## Outbound Flow

Replies are sent via the Resend API with threading headers:
- `In-Reply-To: <original-message-id>`
- `References: <original-message-id>`

This ensures replies appear in the same email thread in the recipient's inbox.

## Gmail Backward Compatibility

Set `EMAIL_PROVIDER=gmail` to use the original Gmail API flow. The `GmailProvider` wraps `GmailClient` with the same `EmailProvider` interface. Requires `GMAIL_REFRESH_TOKEN` in `.env`.

## Testing with Synthetic Data

The synthetic data injector (`scripts/testdata/run.py`) works with Gmail's insert API for testing. For Resend testing, send real emails to the configured inbound address and verify processing via the audit log.

```bash
# Dry run (no email provider needed)
python -m scripts.testdata.run --dry-run

# Inject into Gmail for testing
python -m scripts.testdata.run --method insert --hoa-email test@gmail.com ...
```
