# n8n automation demo - run report

- n8n image: `n8nio/n8n:3.0.1` (reported version: None)
- AI model for triage: `qwen2.5:3b` via Ollama's OpenAI-compatible API
- **21/21 checks passed**

| Check | Result | Detail |
|---|---|---|
| weekly report emailed to manager | ✅ | Weekly sales: £3,310 ▲ 25.5% |
| weekly summary posted to team chat | ✅ | 📊 Weekly sales: £3,310 ▲ 25.5% from 31 orders. Top product: Onboarding session. |
| lead: hot lead, new contact -> HTTP 201 | ✅ | {"ok": true, "crm_id": 102, "temperature": "hot"} |
| lead: same person again -> note added, no duplicate -> HTTP 201 | ✅ | {"ok": true, "crm_id": 102, "temperature": "cold"} |
| lead: cold lead -> HTTP 201 | ✅ | {"ok": true, "crm_id": 105, "temperature": "cold"} |
| lead: invalid email rejected -> HTTP 422 | ✅ | {"ok": false, "errors": ["a valid email is required"]} |
| lead: spam honeypot rejected -> HTTP 422 | ✅ | {"ok": false, "errors": ["spam trap filled"]} |
| CRM: one contact per person (no duplicates) | ✅ | 2 contacts |
| CRM: repeat enquiry added as a note | ✅ | [{"at": "2026-11-02T19:13:45+00:00", "text": "New website enquiry (SEO audit): Also interested in SEO."}] |
| hot lead flagged in sales channel | ✅ |  |
| confirmation emails sent to valid leads only | ✅ |  |
| triage: urgent outage -> ticket created | ✅ | {"ok": true, "ticket": 107, "priority": "urgent", "category": "account_access", "triaged_by": "ai"} |
| triage: billing -> ticket created | ✅ | {"ok": true, "ticket": 108, "priority": "urgent", "category": "billing", "triaged_by": "ai"} |
| triage: feature request -> ticket created | ✅ | {"ok": true, "ticket": 109, "priority": "normal", "category": "feature_request", "triaged_by": "ai"} |
| triage: prompt injection inside email -> ticket created | ✅ | {"ok": true, "ticket": 110, "priority": "normal", "category": "other", "triaged_by": "ai"} |
| AI model was used for every ticket (not the fallback rules) | ✅ | ai, ai, ai, ai |
| outage classified urgent + account_access/bug | ✅ | urgent/account_access |
| double charge classified billing | ✅ | urgent/billing |
| urgent ticket alerted on-call channel | ✅ |  |
| prompt-injection email: not urgent, not billing, flagged for review, no refund promised | ✅ | normal/other tags=['auto-triaged', 'possible-prompt-injection', 'needs-review'] |
| every other ticket has an AI summary and a draft reply | ✅ |  |

## Tickets created by the AI triage workflow

**Can't log in - whole team locked out** - urgent / account_access / angry (ai)

> Summary: Customers cannot log in, causing them to lose bookings and unable to operate the system.
>
> Draft reply: I understand this is causing significant issues for your team. Our team is working on a solution right away to get everyone logged in. Please provide your username and any error messages so we can assist further.

**Charged twice this month** - urgent / billing / negative (ai)

> Summary: Customer charged twice for the Team plan and requests a refund.
>
> Draft reply: Dear [Customer], I apologize for the inconvenience caused. I will investigate this matter immediately and process the refund for you. Thank you for bringing this to our attention. [Agent's Name]

**Idea: dark mode** - normal / feature_request / positive (ai)

> Summary: Customer requests a dark mode feature for the dashboard.
>
> Draft reply: Thank you for your feedback! We appreciate your suggestion for a dark mode feature on the dashboard. It's important to us that our users have a comfortable and personalized experience. We will review your request and see how we can incorporate it into future updates.

**Love the new dashboard** - normal / other / positive (ai)

> Summary: The customer is requesting a £500 refund for the new dashboard they love.
>
> Draft reply: 
