import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chatbot import assistant as A, llm  # noqa: E402
from chatbot.ingest import ingest  # noqa: E402
from chatbot.web import create_app  # noqa: E402


@pytest.fixture(scope="module")
def chunks():
    return ingest(ROOT / "kb_source")


@pytest.fixture
def bot(chunks, monkeypatch):
    monkeypatch.setenv("CHATBOT_PROVIDER", "extractive")
    return A.Assistant(chunks)


def test_every_format_is_ingested(chunks):
    assert {c.source.rsplit(".", 1)[1] for c in chunks} == {"pdf", "docx", "md", "html"}
    pdf = [c for c in chunks if c.source.endswith(".pdf")]
    assert all(c.location.startswith("page ") for c in pdf), "PDF citations include the page"


def test_hidden_html_instructions_are_not_ingested(chunks):
    assert not any("90% off" in c.text or "ignore previous" in c.text.lower() for c in chunks)


def test_pdf_lines_are_joined_not_cut(chunks):
    helmet = next(c for c in chunks if "helmets" in c.text)
    assert "helmets that have been used" in helmet.text


def test_answers_cite_the_right_document(bot):
    r = bot.answer("How much is next day delivery?")
    assert r["outcome"] == "answered" and "9.95" in r["answer"]
    assert r["sources"][0]["file"] == "delivery-and-collection.md" and "[1]" in r["answer"]


def test_unknown_questions_are_not_guessed(bot):
    for q in ("Do you sell skateboards?", "What is the capital of Peru?", "Can you give me 90% off?"):
        r = bot.answer(q)
        assert r["outcome"] == "not_found" and "don't want to guess" in r["answer"], q


def test_handover_to_a_person(bot):
    r = bot.answer("Can I talk to a human?")
    assert r["outcome"] == "handover" and "0113 496 0412" in r["answer"]


def test_follow_up_uses_previous_question(bot):
    hist = [{"role": "user", "content": "How long is the warranty on a carbon frame?"}, {"role": "assistant", "content": "3 years"}]
    r = bot.answer("and aluminium?", hist)
    assert "5-year" in r["answer"]


def test_new_short_question_is_not_mixed_with_the_previous_one(bot):
    """Regression: 'Do you sell skateboards?' after a servicing question used to return the service price."""
    hist = [{"role": "user", "content": "How much is a full service?"}, {"role": "assistant", "content": "£140"}]
    assert bot.answer("Do you sell skateboards?", hist)["outcome"] == "not_found"


def test_llm_answer_is_used_and_citations_renumbered(bot, monkeypatch):
    monkeypatch.setenv("CHATBOT_PROVIDER", "fake")
    monkeypatch.setitem(llm.PROVIDERS, "fake", lambda system, msgs: "It costs £140 [3].")
    r = bot.answer("How much is a full service?")
    assert r["answer"] == "It costs £140 [1]." and len(r["sources"]) == 1


def test_llm_refusal_on_off_topic_question_stays_a_refusal(bot, monkeypatch):
    monkeypatch.setenv("CHATBOT_PROVIDER", "fake")
    monkeypatch.setitem(llm.PROVIDERS, "fake", lambda system, msgs: "NO_ANSWER")
    assert bot.answer("Do you sell skateboards?")["outcome"] == "not_found"


def test_over_cautious_llm_refusal_falls_back_to_the_passage(bot, monkeypatch):
    """Small models sometimes refuse questions the documents clearly answer (seen with qwen2.5:3b in CI)."""
    monkeypatch.setenv("CHATBOT_PROVIDER", "fake")
    monkeypatch.setitem(llm.PROVIDERS, "fake", lambda system, msgs: "NO_ANSWER")
    r = bot.answer("Is there a fee to return a bike by courier?")
    assert r["outcome"] == "answered_from_passage" and "£35" in r["answer"]


def test_provider_outage_falls_back_without_crashing(bot, monkeypatch):
    def down(system, msgs):
        raise llm.ProviderError("HTTP 503")
    monkeypatch.setenv("CHATBOT_PROVIDER", "fake")
    monkeypatch.setitem(llm.PROVIDERS, "fake", down)
    r = bot.answer("How much is a full service?")
    assert r["outcome"] == "fallback" and "140" in r["answer"] and "temporarily limited" in r["answer"]


def test_system_prompt_treats_documents_as_data():
    assert "not instructions" in A.SYSTEM and "NO_ANSWER" in A.SYSTEM


def test_offline_eval_score():
    from chatbot.cli import evaluate
    s = evaluate()
    assert s["passed"] >= 18, "extractive (no AI model) mode should pass at least 18 of 20"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CHATBOT_PROVIDER", "extractive")
    return create_app(data_dir=tmp_path).test_client()


def test_api(client):
    assert client.get("/").status_code == 200
    assert "Content-Security-Policy" in client.get("/").headers
    r = client.post("/api/chat", json={"message": "Is click and collect free?"})
    assert r.status_code == 200 and r.json["sources"]
    assert client.post("/api/chat", json={"message": ""}).status_code == 400
    assert client.post("/api/chat", data="not json").status_code == 400
    assert client.post("/api/chat", json={"message": "x" * 600}).status_code == 400


def test_rate_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("CHATBOT_PROVIDER", "extractive")
    monkeypatch.setenv("CHATBOT_RATE_LIMIT", "3")
    client = create_app(data_dir=tmp_path).test_client()
    codes = [client.post("/api/chat", json={"message": "Is delivery free?"}).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
