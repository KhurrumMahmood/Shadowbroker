"""Simplified LLM caller for sub-agents.

Sync httpx.post with basic retry. No inline XML parsing, no response caching,
no provider-specific tweaks. Just the standard tool-calling loop.
"""
from __future__ import annotations

import json
import logging
import time

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 30  # seconds per LLM call


def call_llm_simple(
    provider: dict,
    messages: list[dict],
    tools: list[dict] | None = None,
    tool_executor=None,
    deadline: float = 0.0,
    max_tool_rounds: int = 2,
    max_tokens: int = 4096,
) -> dict:
    """Simplified LLM call for sub-agents.

    Args:
        provider: dict with api_key, base_url, model
        messages: conversation messages
        tools: OpenAI-format tool schemas (or None)
        tool_executor: callable(name, args) -> str for executing tool calls
        deadline: monotonic timestamp after which we bail (0 = no deadline)
        max_tool_rounds: max rounds of tool calling
        max_tokens: max tokens in response

    Returns:
        dict with keys: content (str), tool_calls_made (list[dict]), error (str|None)
    """
    api_key = provider.get("api_key", "")
    base_url = provider.get("base_url", "https://openrouter.ai/api/v1")
    model = provider.get("model", "")

    headers = {"Authorization": f"Bearer {api_key}"}
    tool_calls_made = []

    for round_num in range(max_tool_rounds + 1):
        if deadline and time.monotonic() > deadline:
            return {
                "content": "",
                "tool_calls_made": tool_calls_made,
                "error": "Deadline exceeded",
            }

        body: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if tools and round_num < max_tool_rounds:
            body["tools"] = tools

        try:
            resp = httpx.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=body,
                timeout=_TIMEOUT,
            )
        except Exception as e:
            # One retry on network error
            logger.warning(f"LLM call failed (attempt 1): {e}")
            try:
                resp = httpx.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=body,
                    timeout=_TIMEOUT,
                )
            except Exception as e2:
                return {
                    "content": "",
                    "tool_calls_made": tool_calls_made,
                    "error": f"LLM call failed: {e2}",
                }

        if resp.status_code != 200:
            return {
                "content": "",
                "tool_calls_made": tool_calls_made,
                "error": f"LLM returned HTTP {resp.status_code}",
            }

        data = resp.json()
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})

        # Check for tool calls
        msg_tool_calls = msg.get("tool_calls")
        if msg_tool_calls and tool_executor:
            # Add assistant message with tool calls
            messages.append(msg)

            for tc in msg_tool_calls:
                fn = tc.get("function", {})
                fn_name = fn.get("name", "")
                try:
                    fn_args = json.loads(fn.get("arguments", "{}"))
                except json.JSONDecodeError:
                    fn_args = {}

                tool_calls_made.append({"name": fn_name, "args": fn_args})

                # Execute the tool
                tool_result = tool_executor(fn_name, fn_args)

                # Add tool result message
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": tool_result,
                })

            continue  # Go to next round

        # No tool calls — final response
        content = msg.get("content", "") or ""
        return {
            "content": content,
            "tool_calls_made": tool_calls_made,
            "error": None,
        }

    # Exhausted rounds
    return {
        "content": "",
        "tool_calls_made": tool_calls_made,
        "error": "Max tool rounds exceeded",
    }
