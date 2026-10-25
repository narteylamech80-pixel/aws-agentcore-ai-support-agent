from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamable_http_client

from main import (
    GATEWAY_URL,
    search_knowledge_base,
    calculate_loyalty_discount,
    REGION,
)
from strands_tools.browser import AgentCoreBrowser


def main():
    print("Connecting to Gateway...")

    model = BedrockModel(
        model_id="global.amazon.nova-2-lite-v1:0"
    )

    agent_core_browser = AgentCoreBrowser(region=REGION)

    tools = [
        search_knowledge_base,
        calculate_loyalty_discount,
        agent_core_browser.browser,
    ]

    mcp_client = MCPClient(
        lambda: streamable_http_client(GATEWAY_URL)
    )

    with mcp_client:
        gateway_tools = mcp_client.list_tools_sync()

        print("\nGateway tools:")
        for tool in gateway_tools:
            print("-", tool.tool_name)

        tools.extend(gateway_tools)

        print("\nCreating agent WITHOUT MemoryHook...")

        agent = Agent(
            model=model,
            tools=tools,
            system_prompt="""
You are a professional e-commerce customer support AI agent.

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