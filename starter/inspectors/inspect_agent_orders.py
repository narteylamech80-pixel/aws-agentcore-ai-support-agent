from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamable_http_client

from main import GATEWAY_URL


def main():
    print("Connecting to Gateway...")

    model = BedrockModel(
        model_id="global.amazon.nova-2-lite-v1:0"
    )

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

        print("\nUsing tool:")
        print(orders_tool.tool_name)

        agent = Agent(
            model=model,
            tools=[orders_tool],
            system_prompt="""
You are a customer support agent.

When the customer asks about their orders,
use the order-tracker___get_customer_orders tool.

The customer's ID is CUST-123.

Do not ask for the customer ID because it has already been provided.
Do not invent order information.
""",
        )

        print("\n========== RUNNING AGENT ==========")

        try:
            response = agent(
                "What orders do I currently have?"
            )

            print("\n========== AGENT RESPONSE ==========")
            print(response)

            print("\n========== RESPONSE TYPE ==========")
            print(type(response))

        except Exception as exc:
            print("\n========== AGENT ERROR ==========")
            print(type(exc))
            print(exc)

            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
