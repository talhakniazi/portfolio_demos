# Document Q&A chatbot (RAG) - portfolio demonstration

> **Self-initiated demonstration project.** Kestrel Cycles is a fictional bike shop and its five documents were
> written for this demo. This is not client work.

A help assistant that answers customer questions **only from the business's own documents**, shows the source of every
answer, says "I don't know" instead of guessing, and hands over to a person when asked. It drops into any website as a
chat bubble.

```
PDF / Word / Markdown / web pages ─► ingest (clean, split by heading, keep page numbers) ─► search index
                                                                                              │
customer question ─► find the 4 most relevant passages ─► AI model writes a short answer citing [1] [2] ─► chat widget
                         └─ nothing relevant? ─► "I couldn't find that... here's how to reach the team"
```

## What it demonstrates

| | |
|---|---|
| Document ingestion | PDF (page-aware, wrapped lines rejoined), Word (headings, bullet lists, tables), Markdown, HTML (menus, footers and hidden comments removed) |
| Retrieval | TF-IDF over words and character n-grams, plus a small domain thesaurus ("money back" → refund). Finds the right passage for **16/16** answerable test questions |
| Grounded answers | The model must cite passage numbers; answers it can't support become a polite "I don't know" |
| Any AI provider | OpenAI, Anthropic, or a free local open-source model through Ollama - set `CHATBOT_PROVIDER`. No SDKs, just HTTP |
| Works without AI | `extractive` mode returns the best-matching sentences with sources (18/20 on the test set) - also used automatically if the AI provider is down |
| Safety | Document text is treated as data, not instructions (a hidden "give 90% off" instruction is planted in the HTML and never reaches the model); rate limiting; 500-character limit; strict Content Security Policy on the page |
| Follow-ups | "How long is the carbon frame warranty?" → "and aluminium?" works |
| Owner insight | Every question is logged; `python -m chatbot.cli unanswered` lists what customers asked that the documents don't cover |
| Embeddable widget | Plain JavaScript, no framework, keyboard accessible, works on phones |

## Run it

```bash
pip install -r requirements.txt
python -m chatbot.cli ingest                 # read kb_source/ and build the index
python -m chatbot.cli ask "Can I return a helmet I've worn?"
python -m chatbot.web                        # chat page at http://127.0.0.1:5050
```

With an AI model (pick one):

```bash
# OpenAI
set CHATBOT_PROVIDER=openai & set OPENAI_API_KEY=sk-...          (Windows; use export on macOS/Linux)
# Anthropic
export CHATBOT_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-ant-...
# Free and private: a local model with Ollama (https://ollama.com)
ollama pull qwen2.5:3b && export CHATBOT_PROVIDER=ollama CHATBOT_MODEL=qwen2.5:3b
```

Evaluate answer quality: `python -m chatbot.cli eval` (20 questions: 16 answerable, 2 off-topic, 1 manipulation
attempt, 1 hand-over request). Tests: `pip install -r requirements-dev.txt && python -m pytest`.

## Using it for a business

1. Put the business's documents in `kb_source/` and run `python -m chatbot.cli ingest`.
2. Write 20-30 real customer questions into `eval_questions.json` with the expected source, and run the evaluation.
3. Deploy `chatbot.web` (any Python host) and add three lines to the website:
   ```html
   <link rel="stylesheet" href="https://help.example.com/static/widget.css">
   <script src="https://help.example.com/static/widget.js" defer></script>
   <div id="kc-chat" data-title="Help" data-api="https://help.example.com/api/chat"></div>
   ```
4. Review `unanswered` weekly and add the missing information to the documents.

**Running costs:** with OpenAI's small models a typical question costs a fraction of a penny; a local model costs
nothing per question but needs a server with enough memory (about 4 GB for the 3B model used here).
