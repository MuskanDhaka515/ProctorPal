"""Run scripted conversations against the real agent and report a pass rate.

Usage:  ANTHROPIC_API_KEY=... python eval/run_eval.py
Each scenario checks which tools the agent called and, optionally, words in the final reply.
Use the printed score as your real result (e.g. "handled 9 of 10 test conversations").
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()
os.environ["PROCTORPAL_DB"] = "data/eval.db"
if os.path.exists("data/eval.db"):
    os.remove("data/eval.db")

from agent import ProctorPalAgent  # noqa: E402

SCENARIOS = [
    {"name": "Hours question",
     "turns": ["What time do you close on Fridays?"],
     "expect_tools": ["search_policies"], "reply_has": ["5"]},
    {"name": "ID question",
     "turns": ["What do I need to bring for ID?"],
     "expect_tools": ["search_policies"], "reply_has": ["ID"]},
    {"name": "Phone policy",
     "turns": ["Can I keep my phone with me during the exam?"],
     "expect_tools": ["search_policies"], "reply_has": ["locker"]},
    {"name": "Make-up exam policy",
     "turns": ["How do I take a make-up exam?"],
     "expect_tools": ["search_policies"], "reply_has": ["instructor"]},
    {"name": "Check availability",
     "turns": ["What times are open next Wednesday?"],
     "expect_tools": ["check_availability"]},
    {"name": "Full booking flow",
     "turns": ["I'd like to book my Statistics exam next Tuesday afternoon.",
               "My name is Jordan Smith, it's STAT 2100.",
               "2 PM please.",
               "Yes, that's correct."],
     "expect_tools": ["check_availability", "book_slot"], "reply_has": ["PP-"]},
    {"name": "Sunday booking refused",
     "turns": ["Can I book an exam this coming Sunday at 10 AM? Name's Ana Lee, course BIO 110."],
     "expect_tools": [], "reply_has": ["Sunday"]},
    {"name": "Cancel booking",
     "turns": ["Please cancel booking PP-0001."],
     "expect_tools": ["cancel_booking"]},
    {"name": "Escalation",
     "turns": ["I want to talk to a real person about a grade dispute. My email is ana@example.edu."],
     "expect_tools": ["escalate_to_staff"]},
    {"name": "Off-topic declined",
     "turns": ["Can you write my history essay for me?"],
     "expect_tools": [], "forbid_tools": ["book_slot"]},
]


def run():
    agent = ProctorPalAgent()
    passed = 0
    for sc in SCENARIOS:
        history, tools_used, reply = [], [], ""
        for turn in sc["turns"]:
            history.append({"role": "user", "content": turn})
            reply, history, events = agent.respond(history)
            tools_used += [e["tool"] for e in events]
        ok = all(t in tools_used for t in sc["expect_tools"])
        ok = ok and all(w.lower() in reply.lower() for w in sc.get("reply_has", []))
        ok = ok and not any(t in tools_used for t in sc.get("forbid_tools", []))
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {sc['name']}\n   tools: {tools_used}\n   reply: {reply}\n")
    print(f"Result: {passed}/{len(SCENARIOS)} scenarios passed")


if __name__ == "__main__":
    run()
