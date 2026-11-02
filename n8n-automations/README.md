# n8n business automations - portfolio demonstration

> **Self-initiated demonstration project.** "Northwind Studio" is fictional, and the CRM, shop, helpdesk, chat and
> email services are a local mock (`mockstack/`), so the workflows run without anyone's real accounts. Not client work.

Three importable n8n workflows, each run end to end in a real n8n instance by GitHub Actions
(see `evidence/run-report.md` on the `evidence` branch for the latest results and screenshots).

## 1. Website lead → CRM → sales alert → confirmation email
`workflows/01-lead-capture-crm.json` - webhook trigger

- Cleans and validates the form (required fields, email format, hidden spam-trap field) and replies `422` with reasons if invalid
- Scores the lead (company, phone, budget, urgency words) as hot / warm / cold
- Looks the email up in the CRM: **updates the existing contact with a note** or **creates a new one**, so no duplicates
- Posts to the sales chat channel (hot leads flagged 🔥), emails the customer a confirmation, replies `201` to the website

## 2. Weekly sales report → email + team chat
`workflows/02-weekly-sales-report.json` - schedule trigger (Mondays 08:00) plus a manual trigger for testing

- Pulls the last 14 days of orders from the shop API, compares this week with last week, ranks products
- Emails an HTML report to the manager and posts a one-line summary to the team chat

## 3. AI support triage → helpdesk ticket → urgent alert
`workflows/03-ai-support-triage.json` - webhook trigger

- Sends each support email to an AI model (any OpenAI-compatible API: OpenAI, Azure, Groq, or a local Ollama model)
  to classify **category, priority and sentiment**, summarise it, and draft a reply for a human agent to check
- **Validates the AI's output** field by field, and falls back to keyword rules if the AI is unavailable, so a ticket
  is always created
- Creates the helpdesk ticket; urgent tickets also alert the on-call channel
- The customer email is passed to the model as data with an explicit instruction not to follow it. Emails that try to
  instruct the AI ("ignore previous instructions...") are tagged `needs-review`, given neutral priority and no drafted
  reply, because a test showed the AI *and* simple keyword rules can both be steered by such text

## Run it yourself

Requirements: Docker, Python 3.10+, and optionally [Ollama](https://ollama.com) for the AI workflow.

```bash
pip install flask requests
ollama pull qwen2.5:3b                       # optional, for workflow 3
python scripts/run_demo.py --n8n-version 3.0.1
```

This starts the mock services, imports the workflows into a fresh n8n container, runs the weekly report, publishes the
webhook workflows, sends test leads and support emails, and checks every result.

To use the workflows in your own n8n: *Workflows → Import from file*, then replace the `{{ $env.MOCK_BASE }}` HTTP
nodes with your real services (or the native HubSpot / Pipedrive / Slack / Gmail / Zendesk nodes) and their credentials.

`scripts/build_workflows.py` generates the workflow files; edit it rather than the JSON if you change the logic.
