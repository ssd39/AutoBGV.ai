"""
Prompt Builder — builds the Deepgram Voice Agent system prompt and tools schema.

Design decisions:
  • The system prompt is 100% STATIC — built once at session start, never
    regenerated. It gives the LLM the full list of what to collect and how to
    behave, but carries NO runtime state (no progress markers, no verification
    status, no "current item" pointer).

  • Runtime state is communicated exclusively through:
      - Tool call responses  (get_next_item, submit_answer, request_document)
      - InjectAgentMessage   (upload notifications, verification failures)

  • Only 3 tools: get_next_item · submit_answer · request_document.
    The agent never needs to query status itself — the system pushes all events.

Tools are OpenAI-compatible function schemas sent inside Deepgram's Settings.
"""
from __future__ import annotations

from typing import Any


# ─── Item Queue Builder ───────────────────────────────────────────────────────


def build_items_queue(
    documents_required: list[dict],
    questions: list[dict],
) -> list[dict[str, Any]]:
    """
    Combine workflow questions and documents into an ordered collection queue.

    Ordering strategy:
      1. Questions first (sorted by order_index) — gathered verbally over voice.
      2. Documents second (sorted by order_index) — requested via WhatsApp.

    Each entry is a plain dict tagged with 'type' = 'question' | 'document'.
    This queue is stored on the SessionState and is the source of truth for
    what needs to be collected.
    """
    items: list[dict[str, Any]] = []

    # ── Questions first ────────────────────────────────────────────────────
    for q in sorted(questions, key=lambda x: x.get("order_index", 0)):
        items.append(
            {
                "type": "question",
                "id": str(q.get("id", "")),
                "text": q.get("question_text", ""),
                "question_type": q.get("question_type", "text"),
                "options": q.get("options"),
                "is_required": q.get("is_required", True),
                "helper_text": q.get("helper_text"),
            }
        )

    # ── Documents second ───────────────────────────────────────────────────
    for d in sorted(documents_required, key=lambda x: x.get("order_index", 0)):
        items.append(
            {
                "type": "document",
                "key": d.get("document_type_key", ""),
                "name": d.get("display_name", d.get("document_type_key", "")),
                "is_required": d.get("is_required", True),
                "criteria_text": d.get("criteria_text"),
                "instructions": d.get("instructions"),
            }
        )

    return items


# ─── System Prompt Builder ────────────────────────────────────────────────────


def build_system_prompt(session: Any) -> str:
    """
    Build the static system prompt for the Deepgram Voice Agent.

    This is called exactly once per session (at Deepgram connection time).
    It never changes. Dynamic state flows through tool responses and
    InjectAgentMessage — not here.
    """
    customer_name = session.customer_name or "the customer"
    workflow_name = session.workflow_name or "document verification"
    queue: list[dict] = session.items_queue

    # ── Full collection list (static reference — no status markers) ────────
    items_lines: list[str] = []
    for i, item in enumerate(queue):
        if item["type"] == "question":
            line = (
                f"{i + 1}. QUESTION\n"
                f"   id:  {item['id']}\n"
                f"   Ask: {item['text']}"
            )
            if item.get("options"):
                line += f"\n   Options: {', '.join(item['options'])}"
            if item.get("helper_text"):
                line += f"\n   Hint: {item['helper_text']}"
        else:
            line = (
                f"{i + 1}. DOCUMENT\n"
                f"   key:  {item['key']}\n"
                f"   Name: {item['name']}"
            )
            if item.get("criteria_text"):
                line += f"\n   Requirements: {item['criteria_text']}"
            if item.get("instructions"):
                line += f"\n   Customer instructions: {item['instructions']}"
        items_lines.append(line)

    items_text = "\n\n".join(items_lines) if items_lines else "  (no items to collect)"

    greeting = session.welcome_message or (
        f"Hello {customer_name}! This is an automated call regarding your "
        f"{workflow_name}. I'll guide you through a few quick questions and "
        "then request some documents via WhatsApp. It'll only take a few minutes."
    )
    completion = session.completion_message or (
        "Thank you for completing the process! We have received everything "
        "we need and will be in touch shortly. Have a great day!"
    )

    return f"""You are an AI verification assistant conducting a {workflow_name} call.

CUSTOMER: {customer_name}
PHONE:    {session.customer_phone}

━━━━━━━━━━━━━━━━━━━━━━━━━━
GREETING:
The system has ALREADY spoken the greeting automatically when the call started.
Do NOT repeat the greeting. Immediately call get_next_item() to begin.

COMPLETION MESSAGE (for reference — say it ONLY when the system tells you to):
"{completion}"

━━━━━━━━━━━━━━━━━━━━━━━━━━
ITEMS TO COLLECT (full list for your reference):
{items_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO OPERATE:

STEP 1 — After the greeting, call get_next_item() immediately.
  The system returns the first pending item (question or document).

STEP 2a — If the item is a QUESTION:
  Ask the question verbally. When the customer answers, call
  submit_answer(question_id="<id>", answer="<answer>").
  The response will include the next instruction.

STEP 2b — If the item is a DOCUMENT:
  The system has ALREADY sent a WhatsApp message to the customer automatically.
  The response from get_next_item() will confirm this with "whatsapp_sent: true".
  Tell them: "I've sent a WhatsApp message requesting your [Document Name].
  Please upload it when you can."
  Then WAIT — do NOT call get_next_item() yourself.
  Do NOT call request_document() — the WhatsApp was already sent by the system.
  The system will inject a message when the document arrives.

STEP 3 — On upload notification:
  Acknowledge receipt ("Got it, thank you!") then call get_next_item().

STEP 4 — When get_next_item() returns status="all_submitted":
  Tell the customer their documents are under review and that you'll stay on
  the line. Do NOT say the completion message yet. Do NOT end the call.
  WAIT for verification result notifications from the system.

STEP 5 — On verification failure notification (system injects a message):
  Call get_next_item() immediately. It will auto-send the WhatsApp re-request
  and tell you exactly what to say to the customer. Then WAIT for the
  new upload notification.

STEP 6 — When the system notifies that ALL documents are verified:
  Say the COMPLETION MESSAGE verbatim. Then call terminate_call() to end the call.

STEP 7 — If the customer says they have NOT received the WhatsApp message:
  Call request_document(document_key="<key>") to resend it manually.
  Then tell the customer it has been resent and WAIT.

RULES:
  - One item at a time. Never ask for two things simultaneously.
  - Use display names ("Aadhaar Card"), never internal keys ("aadhaar_card").
  - Be friendly, clear, and patient. If the customer is confused, explain what
    is needed in simple terms using the requirements/instructions above.
  - Never reveal session IDs, document keys, or technical details.
"""


# ─── Tools Schema ─────────────────────────────────────────────────────────────


def build_tools_schema() -> list[dict]:
    """
    Four-tool schema for the Deepgram Voice Agent LLM (OpenAI function format).

    get_next_item    — pulls the next pending item from the server-side queue.
    submit_answer    — records a verbal question answer, advances the queue.
    request_document — resends a WhatsApp message (only on explicit customer request).
    terminate_call   — ends the Twilio call after the completion message is spoken.
    """
    return [
        {
            "name": "get_next_item",
            "description": (
                "Returns the next item to collect (question or document). "
                "Call immediately after the greeting, and after every upload "
                "notification. Do NOT call after request_document — wait for "
                "the system's upload notification first."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "submit_answer",
            "description": (
                "Records the customer's verbal answer to the current question "
                "and advances the queue. Call as soon as the customer finishes "
                "answering. Returns a hint about the next step."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question_id": {
                        "type": "string",
                        "description": "The 'id' of the question from the ITEMS TO COLLECT list",
                    },
                    "answer": {
                        "type": "string",
                        "description": "The customer's answer, verbatim or concisely summarised",
                    },
                },
                "required": ["question_id", "answer"],
            },
        },
        {
            "name": "request_document",
            "description": (
                "Resends a WhatsApp message for a document. Only call this when "
                "the customer explicitly says they have NOT received the WhatsApp "
                "notification. The system sends WhatsApp automatically in all other "
                "cases — do NOT call this proactively. After calling, tell the "
                "customer the message has been resent and WAIT for the upload."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "document_key": {
                        "type": "string",
                        "description": "The 'key' of the document from the ITEMS TO COLLECT list",
                    },
                },
                "required": ["document_key"],
            },
        },
        {
            "name": "terminate_call",
            "description": (
                "Ends the Twilio call. Call this ONLY after you have said the "
                "COMPLETION MESSAGE verbatim and all documents have been verified. "
                "Do NOT call this at any other time — the system will notify you "
                "when it is appropriate via a [SYSTEM NOTIFICATION]."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    ]
