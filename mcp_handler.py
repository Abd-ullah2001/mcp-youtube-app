import asyncio
import json
import os
import re
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI


def get_nvidia_client():
    return AsyncOpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ.get("NVIDIA_API_KEY", "YOUR_NVIDIA_API_KEY")
    )


MODEL = "meta/llama-3.3-70b-instruct"

# ──────────────────────────────────────────────
# JSON fallback extraction (for when the model
# dumps tool calls as text instead of using API)
# ──────────────────────────────────────────────

def _extract_all_json_tool_calls(text: str) -> List[dict]:
    """
    Extract ALL JSON tool-call objects from LLM text output.
    Handles raw JSON, markdown code blocks, multiple objects, and mixed text.
    Returns a list of dicts, each with 'name' and 'arguments' keys.
    """
    if not text or "{" not in text:
        return []

    # Strip markdown code fences
    cleaned = re.sub(r'```(?:json)?\s*', '', text)
    cleaned = re.sub(r'```', '', cleaned)

    results = []
    brace_depth = 0
    start_idx = None

    for i, ch in enumerate(cleaned):
        if ch == '{':
            if brace_depth == 0:
                start_idx = i
            brace_depth += 1
        elif ch == '}':
            brace_depth -= 1
            if brace_depth == 0 and start_idx is not None:
                candidate = cleaned[start_idx:i + 1]
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict) and "name" in parsed:
                        args = parsed.get("parameters", parsed.get("arguments", {}))
                        results.append({"name": parsed["name"], "arguments": args})
                except json.JSONDecodeError:
                    pass
                start_idx = None

    return results


def _fix_tool_arguments(args: Any) -> dict:
    """Coerce string digits to int for tool arguments that expect numbers."""
    if not isinstance(args, dict):
        return {}
    fixed = {}
    for k, v in args.items():
        if isinstance(v, str) and v.isdigit():
            fixed[k] = int(v)
        else:
            fixed[k] = v
    return fixed


# ──────────────────────────────────────────────
# MCP tool discovery
# ──────────────────────────────────────────────

async def get_mcp_tools(session) -> List[Dict[str, Any]]:
    tools_result = await session.list_tools()
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            },
        }
        for tool in tools_result.tools
    ]


# ──────────────────────────────────────────────
# Core agentic loop
# ──────────────────────────────────────────────

async def _process_via_mcp_internal(
    query: str,
    server_script_path: str = "servers/youtube/server.py",
) -> str:
    nvidia = get_nvidia_client()

    async with AsyncExitStack() as exit_stack:
        server_params = StdioServerParameters(
            command="python", args=[server_script_path]
        )
        stdio_transport = await exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        stdio, write = stdio_transport
        session = await exit_stack.enter_async_context(ClientSession(stdio, write))

        await session.initialize()
        tools = await get_mcp_tools(session)

        # Build the tool name list so the system prompt is tool-aware
        tool_names = [t["function"]["name"] for t in tools]

        system_prompt = (
            "You are YOU-AI, an intelligent YouTube assistant. "
            f"You have access to the following tools: {', '.join(tool_names)}. "
            "When the user's request requires data from YouTube, call the appropriate tools. "
            "You may call MULTIPLE tools in a single response if needed. "
            "After receiving tool results, synthesize a comprehensive, well-structured answer. "
            "Always respond in clear, readable text — never output raw JSON to the user."
        )

        messages: list = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        # Tracks all tool results collected across turns for the safety-net
        all_tool_outputs: List[str] = []

        MAX_TURNS = 10  # enough headroom for complex multi-tool chains

        for turn in range(MAX_TURNS):
            response = await nvidia.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=1500,
            )

            assistant_msg = response.choices[0].message
            raw_content = assistant_msg.content or ""
            has_tool_calls = bool(
                assistant_msg.tool_calls and len(assistant_msg.tool_calls) > 0
            )

            # ── Path A: proper tool_calls API ──
            if has_tool_calls:
                messages.append(assistant_msg)

                for tool_call in assistant_msg.tool_calls:
                    try:
                        result = await session.call_tool(
                            tool_call.function.name,
                            arguments=json.loads(tool_call.function.arguments),
                        )
                        tool_output = result.content[0].text
                    except Exception as e:
                        tool_output = (
                            f"Error executing {tool_call.function.name}: {e}"
                        )

                    all_tool_outputs.append(
                        f"[{tool_call.function.name}]: {tool_output}"
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_output,
                    })

                # DON'T return yet — loop back so the LLM can:
                #   • call more tools if needed, OR
                #   • produce the final text answer
                continue

            # ── Path B: raw-JSON fallback (model broke out of tool API) ──
            fallback_calls = _extract_all_json_tool_calls(raw_content)

            if fallback_calls:
                # Execute every tool the model tried to call
                fallback_results: List[str] = []
                for fc in fallback_calls:
                    tool_name = fc["name"]
                    tool_args = _fix_tool_arguments(fc["arguments"])
                    try:
                        result = await session.call_tool(
                            tool_name, arguments=tool_args
                        )
                        output = result.content[0].text
                    except Exception as e:
                        output = f"Failed to execute {tool_name}: {e}"

                    all_tool_outputs.append(f"[{tool_name}]: {output}")
                    fallback_results.append(
                        f"**{tool_name}** result:\n{output}"
                    )

                # Inject results back into conversation as a user message
                # so the LLM can synthesise from all of them
                messages.append({
                    "role": "assistant",
                    "content": "I'll retrieve the requested data using the available tools.",
                })
                messages.append({
                    "role": "user",
                    "content": (
                        "Here are the tool results:\n\n"
                        + "\n\n---\n\n".join(fallback_results)
                        + "\n\nNow provide a comprehensive, well-formatted answer "
                        "based on ALL the data above. Do NOT output any JSON."
                    ),
                })

                # Loop back — the model might need more tools, or will answer
                continue

            # ── Path C: genuine text response — we're done ──
            # Final safety check: make sure it's not sneaking JSON through
            if _extract_all_json_tool_calls(raw_content):
                # Shouldn't happen after Path B, but just in case
                continue  # let the loop try again

            return raw_content

        # ── Exhausted MAX_TURNS — force a final text-only answer ──
        messages.append({
            "role": "user",
            "content": (
                "Please provide your final comprehensive answer now. "
                "Synthesize all the tool results you have received into a "
                "well-structured response. Do NOT call any more tools."
            ),
        })

        final_response = await nvidia.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="none",
            max_tokens=2000,
        )
        final_text = final_response.choices[0].message.content or ""

        # Ultimate safety net — if STILL JSON, return raw tool outputs
        if _extract_all_json_tool_calls(final_text):
            formatted = "\n\n---\n\n".join(all_tool_outputs)
            return (
                "Here are the results I gathered:\n\n" + formatted
                if all_tool_outputs
                else final_text
            )

        return final_text


def run_mcp_query(query: str) -> str:
    """Wrapper to run the async MCP orchestration from a sync Streamlit context."""
    return asyncio.run(_process_via_mcp_internal(query))
