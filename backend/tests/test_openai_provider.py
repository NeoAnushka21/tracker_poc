"""Message/tool translation for the OpenAI-compatible provider (Groq, Gemini, Ollama...)."""
import json

from app.llm.provider import to_openai_messages, to_openai_tools
from app.llm.tools import TOOLS, ToolContext, ToolInputError, run_tool


def test_tools_translate_to_function_schema():
    out = to_openai_tools(TOOLS)
    assert [t["function"]["name"] for t in out] == [t["name"] for t in TOOLS]
    assert out[0]["type"] == "function"
    assert out[0]["function"]["parameters"] == TOOLS[0]["input_schema"]


def test_tool_loop_messages_translate():
    messages = [
        {"role": "user", "content": "had a guava"},
        {"role": "assistant", "content": [
            {"type": "text", "text": "Let me log that."},
            {"type": "tool_use", "id": "call_1", "name": "propose_entry", "input": {"summary": "Guava"}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "call_1", "content": '{"proposal_id": 1}', "is_error": False},
        ]},
    ]
    out = to_openai_messages(messages)
    assert out[0] == {"role": "user", "content": "had a guava"}
    assert out[1]["role"] == "assistant"
    assert out[1]["content"] == "Let me log that."
    assert out[1]["tool_calls"][0]["id"] == "call_1"
    assert json.loads(out[1]["tool_calls"][0]["function"]["arguments"]) == {"summary": "Guava"}
    assert out[2] == {"role": "tool", "tool_call_id": "call_1", "content": '{"proposal_id": 1}'}


def test_assistant_tool_call_without_text_has_null_content():
    out = to_openai_messages([{"role": "assistant", "content": [
        {"type": "tool_use", "id": "c", "name": "get_logs", "input": {}},
    ]}])
    assert out[0]["content"] is None


def test_missing_or_invalid_args_become_tool_errors(client, user):
    from app.db import SessionLocal
    from app.models import User

    with SessionLocal() as db:
        ctx = ToolContext(db=db, user=db.get(User, user["id"]), raw_user_message="x")
        for args in ({"summary": "no items or times"}, {"__invalid_json__": "{oops"}):
            try:
                run_tool(ctx, "propose_entry", args)
                raise AssertionError("expected ToolInputError")
            except ToolInputError:
                pass
