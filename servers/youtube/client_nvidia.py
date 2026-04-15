import asyncio
import json
import os
from contextlib import AsyncExitStack
from typing import Any, Dict, List

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI

# Load environment variables (looking for NVIDIA_API_KEY)
load_dotenv("../../.env")  # Assuming .env is at the root
load_dotenv()

# Global variables to store session state
session = None
exit_stack = AsyncExitStack()

# Initialize OpenAI client pointed to NVIDIA's free API
openai_client = AsyncOpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY", "YOUR_NVIDIA_API_KEY")
)

# You can change this to another free NVIDIA model that supports function calling
model = "meta/llama-3.3-70b-instruct"

async def connect_to_server(server_script_path: str):
    """Connect to the YouTube MCP server."""
    global session, exit_stack

    server_params = StdioServerParameters(
        command="python",
        args=[server_script_path],
    )

    stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
    stdio, write = stdio_transport
    session = await exit_stack.enter_async_context(ClientSession(stdio, write))
    await session.initialize()
    print("\n[+] Connected to YouTube MCP Server!")


async def get_mcp_tools() -> List[Dict[str, Any]]:
    """Get available tools from the MCP server in OpenAI format."""
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


async def process_query(query: str) -> str:
    """Process a query using NVIDIA LLM and YouTube MCP tool."""
    print(f"\n[?] Asking LLM: {query}\n")
    tools = await get_mcp_tools()

    try:
        # 1. Ask the LLM how to resolve the query
        response = await openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": query}],
            tools=tools,
            tool_choice="auto",
            max_tokens=1024,
        )
    except Exception as e:
        return f"! LLM Error (Check NVIDIA API Key): {str(e)}"

    assistant_message = response.choices[0].message

    messages = [
        {"role": "user", "content": query},
        assistant_message,
    ]

    # 2. Check if LLM decided it needs to use a tool (get_transcript)
    if assistant_message.tool_calls:
        for tool_call in assistant_message.tool_calls:
            print(f"- LLM invoked tool: {tool_call.function.name} - Fetching video...")
            
            # 3. Actually run the MCP python tool locally
            result = await session.call_tool(
                tool_call.function.name,
                arguments=json.loads(tool_call.function.arguments),
            )
            
            print("- Transcript fetched! Sending back to LLM for final summary...\n")

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result.content[0].text,
                }
            )

        # 4. Give the transcript text back to the LLM to get the final answer
        final_response = await openai_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="none",
            max_tokens=1024,
        )
        return final_response.choices[0].message.content

    return assistant_message.content


async def cleanup():
    await exit_stack.aclose()


async def main():
    # Make sure to set your NVIDIA_API_KEY in your console or .env file
    if not os.environ.get("NVIDIA_API_KEY"):
        print("WARNING: NVIDIA_API_KEY is not set. The LLM request will likely fail.")
        print("Please grab a free key from build.nvidia.com and set it in your .env file.\n")
    
    # Start the local connection to the YouTube server script
    await connect_to_server("server.py")

    # Ask the user for the video URL
    video_url = input("\nEnter the YouTube video URL you want to summarize: ").strip()
    if not video_url:
        print("No URL provided. Exiting.")
        await cleanup()
        return

    query = f"Can you give me everything about this video in 5 main points? The URL is {video_url}"

    response = await process_query(query)
    
    print("\n================== 5 MAIN POINTS ==================")
    print(response)
    print("===================================================\n")

    await cleanup()


if __name__ == "__main__":
    asyncio.run(main())
