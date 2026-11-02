# Portfolio demonstrations

Self-initiated projects for fictional businesses, built to show working examples of four services. **None of this is
client work**, and every company, person and data set in it is invented.

| Folder | Service | What it is |
|---|---|---|
| [`sales-etl/`](sales-etl) | Python automation and data pipelines | Messy CSV + REST API + Excel → validated SQLite warehouse → Excel report with formulas and charts |
| [`docs-chatbot/`](docs-chatbot) | AI chatbots | Document Q&A assistant (RAG) with citations, honest "I don't know", and an embeddable chat widget |
| [`n8n-automations/`](n8n-automations) | Business automation workflows | Three n8n workflows: lead capture to CRM, weekly report, AI support triage |
| [`purespace-website/`](purespace-website) | Websites and landing pages | Full business website with quote form, database and admin area (Flask) |

Every push runs the demos in GitHub Actions (`.github/workflows/demos.yml`): the Python pipeline on Linux and Windows,
the chatbot evaluated with a real open-source AI model, and the n8n workflows executed in a real n8n instance. Results
and screenshots are committed to the `evidence` branch.
