from fastmcp import Client
from mcp_debugger import mcp
import asyncio
import json

async def main():
    # client = Client(mcp) # This works according to overload signatures!

    # Using 'with' context manager for automatic connection/cleanup
    # Note: Client might be async. Let's assume standard usage pattern.
    # FastMCP client docs usually imply sync usage for simple scripts or async.
    # Given the __init__ signature didn't show async, but `run_async` did...
    # The overload `Client(transport: FastMCP)` returns a Client.

    print("Connecting to MCP Server...")
    async with Client(mcp) as client:
        print("\n--- Listing Tools ---")
        tools = await client.list_tools()
        for tool in tools:
            print(f"- {tool.name}: {tool.description}")

        print("\n--- Calling get_database_stats ---")
        result = await client.call_tool("get_database_stats")
        # FastMCP CallToolResult usually has 'content' or is iterable?
        # Let's print the raw result to see what we got
        print(f"Result type: {type(result)}")
        print(f"Result content: {result}")

        # If it has content, usually it's a list of TextContent or ImageContent path
        if hasattr(result, 'content'):
             for content in result.content:
                 if hasattr(content, 'text'):
                     print(content.text)

        print(f"\n--- Calling get_recent_events (limit=2) ---")
        result_events = await client.call_tool("get_recent_events", arguments={"limit": 2})
        if hasattr(result_events, 'content'):
             for content in result_events.content:
                 if hasattr(content, 'text'):
                     print(content.text)

if __name__ == "__main__":
    asyncio.run(main())
