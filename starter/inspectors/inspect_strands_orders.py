import asyncio
import traceback

from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamable_http_client

from main import GATEWAY_URL


async def main():
    print("Connecting to Gateway...")

    mcp_client = MCPClient(
        lambda: streamable_http_client(GATEWAY_URL)
    )

    with mcp_client:
        tools = mcp_client.list_tools_sync()

        orders_tool = next(
            tool
            for tool in tools
            if tool.tool_name == "order-tracker___get_customer_orders"
        )

        print("\nTool:", orders_tool.tool_name)
        print("MCP tool name:", orders_tool.mcp_tool.name)

        tool_use = {
            "toolUseId": "diagnostic-orders-001",
            "input": {
                "customer_id": "CUST-123"
            }
        }

        print("\n========== CALLING MCPAgentTool.stream() ==========")
        print("Tool use:")
        print(tool_use)

        try:
            async for event in orders_tool.stream(
                tool_use,
                {}
            ):
                print("\n========== EVENT ==========")
                print(event)
                print("\nEVENT TYPE:")
                print(type(event))

                if hasattr(event, "__dict__"):
                    print("\nEVENT ATTRIBUTES:")
                    print(vars(event))

        except Exception as exc:
            print("\n========== STREAM ERROR ==========")
            print(type(exc))
            print(exc)
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
