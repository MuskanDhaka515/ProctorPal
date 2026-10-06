"""The LLM agent loop: Claude with tool use, tuned for spoken conversation."""
import json
import os
from datetime import date

import anthropic

from tools import TOOL_SCHEMAS, run_tool

MODEL = os.getenv("PROCTORPAL_MODEL", "claude-haiku-4-5-20251001")
MAX_TOOL_ROUNDS = 6

SYSTEM_PROMPT = """You are ProctorPal, the voice assistant for the Campus Testing Center.
Today is {weekday}, {today}.

Your replies are spoken aloud, so:
- Use one to three short sentences. No lists, markdown, or emoji.
- Say times naturally, like "2 PM", and dates like "Tuesday, October 13th".

How to help:
- For any policy question (hours, ID, rules, make-ups, accommodations, location), call
  search_policies first and answer only from what it returns. Never invent a policy.
- To book an exam, collect the student's full name, course, date, and start time.
  Turn relative dates like "next Tuesday" into YYYY-MM-DD using today's date.
  Call check_availability, offer the open times, then read back the details and
  get a clear yes before calling book_slot. Always say the confirmation code.
- If a tool returns an error, explain it simply and offer an alternative.
- If the student asks for a person, or the question isn't covered by policy, call
  escalate_to_staff and tell them staff will follow up.
- Stay on testing-center topics. Politely decline anything else."""


def _block_to_dict(block) -> dict:
    if block.type == "text":
        return {"type": "text", "text": block.text}
    if block.type == "tool_use":
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
    return {"type": block.type}


class ProctorPalAgent:
    def __init__(self, client=None, model: str = MODEL):
        self.client = client or anthropic.Anthropic()
        self.model = model

    def system_prompt(self) -> str:
        today = date.today()
        return SYSTEM_PROMPT.format(today=today.isoformat(), weekday=today.strftime("%A"))

    def respond(self, history: list[dict]) -> tuple[str, list[dict], list[dict]]:
        """Run one user turn. Returns (reply_text, updated_history, tool_events)."""
        messages = list(history)
        events = []
        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=400,
                system=self.system_prompt(),
                tools=TOOL_SCHEMAS,
                messages=messages,
            )
            messages.append({"role": "assistant",
                             "content": [_block_to_dict(b) for b in response.content]})
            if response.stop_reason != "tool_use":
                reply = " ".join(b.text for b in response.content if b.type == "text").strip()
                return reply or "Sorry, could you say that again?", messages, events

            results = []
            for block in response.content:
                if block.type == "tool_use":
                    output = run_tool(block.name, block.input)
                    events.append({"tool": block.name, "input": block.input, "output": output})
                    results.append({"type": "tool_result", "tool_use_id": block.id,
                                    "content": json.dumps(output)})
            messages.append({"role": "user", "content": results})

        return ("I'm having trouble with that request. Let me connect you with staff.",
                messages, events)
