"""Command line:  python -m chatbot.cli ingest | ask "question" | eval | unanswered"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from . import llm
from .assistant import Assistant
from .ingest import ingest, load, save

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data" / "chunks.json"


def bot():
    if not INDEX.exists():
        save(ingest(ROOT / "kb_source"), INDEX)
    return Assistant(load(INDEX), log_dir=ROOT / "data" / "logs")


def evaluate(out_path: Path | None = None) -> dict:
    a = bot()
    cases = json.loads((ROOT / "eval_questions.json").read_text())
    rows, passed = [], 0
    for c in cases:
        r = a.answer(c["q"])
        ok_outcome = r["outcome"] == c["expect"] or (c["expect"] == "answered" and r["outcome"] in ("fallback", "answered_from_passage"))
        ok_source = c.get("source") is None or any(s["file"] == c["source"] for s in r["sources"])
        ok_facts = all(f.lower() in r["answer"].lower() for f in c.get("facts", []))
        ok_forbid = not any(f.lower() in r["answer"].lower() for f in c.get("forbid", []))
        ok = ok_outcome and ok_source and ok_facts and ok_forbid
        passed += ok
        rows.append({**c, "answer": r["answer"], "outcome": r["outcome"], "sources": r["sources"], "ms": r["ms"], "pass": ok})
        print(f"{'PASS' if ok else 'FAIL'}  {c['q']}\n      -> {r['answer']}")
    import os
    by = Counter(x["outcome"] for x in rows)
    summary = {"provider": llm.provider_name(), "model": os.environ.get("CHATBOT_MODEL"), "passed": passed, "total": len(cases),
               "outcomes": dict(by), "cases": rows}
    print(f"\n{passed}/{len(cases)} passed with provider '{summary['provider']}' model '{summary['model']}' - outcomes {dict(by)}")
    if out_path:
        out_path.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def main():
    ap = argparse.ArgumentParser(prog="chatbot")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest", help="read kb_source/ and rebuild the index")
    a = sub.add_parser("ask"); a.add_argument("question")
    e = sub.add_parser("eval"); e.add_argument("--out", type=Path)
    sub.add_parser("unanswered", help="questions the assistant couldn't answer: gaps to fill in the documents")
    args = ap.parse_args()
    if args.cmd == "ingest":
        chunks = ingest(ROOT / "kb_source")
        save(chunks, INDEX)
        for name, n in Counter(c.source for c in chunks).items():
            print(f"{n:3d} passages  {name}")
        print(f"Index saved: {INDEX}")
    elif args.cmd == "ask":
        r = bot().answer(args.question)
        print(r["answer"])
        for i, s in enumerate(r["sources"], 1):
            print(f"  [{i}] {s['file']}, {s['where']}")
    elif args.cmd == "eval":
        s = evaluate(args.out)
        sys.exit(0 if s["passed"] == s["total"] else 1)
    elif args.cmd == "unanswered":
        f = ROOT / "data" / "logs" / "questions.jsonl"
        recs = [json.loads(l) for l in f.read_text().splitlines()] if f.exists() else []
        miss = Counter(r["question"].lower() for r in recs if r["outcome"] == "not_found")
        print("Questions the assistant couldn't answer (most asked first):")
        for q, n in miss.most_common(30):
            print(f"{n:3d}  {q}")


if __name__ == "__main__":
    main()
