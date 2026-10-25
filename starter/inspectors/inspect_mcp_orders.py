import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from main import GATEWAY_URL


async def main():
    print("Connecting to Gateway...")
    print(GATEWAY_URL)

    async with streamable_http_client(GATEWAY_URL) as streams:
        read_stream, write_stream = streams

        async with ClientSession(read_stream, write_stream) as session:
            print("\nInitializing MCP session...")
            await session.initialize()

            print("\nCalling get_customer_orders...")
            result = await session.call_tool(
                "order-tracker___get_customer_orders",
                {
                    "customer_id": "CUST-123"
                }
            )

            print("\n========== RAW MCP RESULT ==========")
            print(result)

            print("\n========== RESULT TYPE ==========")
            print(type(result))

            print("\n========== RESULT ATTRIBUTES ==========")
            print(vars(result))


if __name__ == "__main__":
    asyncio.run(main())
