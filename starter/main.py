"""
Customer Support AI Agent — Starter Code
==========================================
Your task is to complete this file by implementing all sections marked
with # TODO comments.

Reference the project instructions and rubric for guidance.
Work through each section yourself.

Run locally (after filling in config values):
  uv run main.py '{"prompt": "Hello", "customer_id": "CUST-123", "session_id": "s1"}'

Deploy to AgentCore:
  agentcore deploy

Invoke deployed agent:
  agentcore invoke '{"prompt": "Hello", "customer_id": "CUST-123", "session_id": "s1"}'
"""

# ── Imports ───────────────────────────────────────────────────────────────────
# These imports are provided. Do not remove them.
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamable_http_client
import argparse, json
import os, asyncio, boto3
from strands.hooks import (
    HookProvider, AfterInvocationEvent, HookRegistry, MessageAddedEvent,
)
import logging
import uuid
from typing import Dict
from bedrock_agentcore.tools.code_interpreter_client import code_session
from strands_tools.browser import AgentCoreBrowser


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("CSAI_Agent")

# ── TODO 1 — App Initialisation ───────────────────────────────────────────────
# Create a BedrockAgentCoreApp instance.
# This registers the ASGI server for AgentCore deployment.
# There must be exactly one instance per deployment.
#
# Hint: app = BedrockAgentCoreApp()

# TODO: Create the BedrockAgentCoreApp instance
app = BedrockAgentCoreApp()


# Suppress interactive tool-consent prompts (required in headless deployments).
os.environ["BYPASS_TOOL_CONSENT"] = "true"


# ── TODO 2 — Configuration ────────────────────────────────────────────────────
# Replace the placeholder strings with your actual AWS resource values.
# You collected these in the infrastructure setup section of the project instructions.
#
# GATEWAY_URL format: https://<alias>.gateway.bedrock-agentcore.<region>.amazonaws.com/mcp
# This starter uses an unsigned MCP connection and therefore assumes the
# project Gateway is configured with the NONE authorizer.
# KB_ID       format: 10-character alphanumeric string from the KB console
# REGION:     your AWS region, e.g. "us-east-1"
# MEMORY_ID   format: shown in the AgentCore Memory console

GATEWAY_URL = "https://customersupportgateway-wdnrcelcgg.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"   # TODO: Replace with your Gateway URL
KB_ID       = "0L01Q7LZNY"          # TODO: Replace with your Knowledge Base ID
REGION      = "us-east-1"        # TODO: Replace with your AWS region
MEMORY_ID   = "CustomerSupportMemory-yg39TZAwna"        # TODO: Replace with your Memory ID


# ── TODO 3 — Model and Clients ────────────────────────────────────────────────
# Create:
#   1. A BedrockModel using model_id "global.amazon.nova-2-lite-v1:0"
#   2. A MemoryClient with region_name=REGION
#   3. A boto3 client for the "bedrock-agent-runtime" service in REGION
#
# Hint: model = BedrockModel(model_id=model_id)

model_id = "global.amazon.nova-2-lite-v1:0"

# TODO: Create the BedrockModel instance
model = BedrockModel(model_id=model_id)

# TODO: Create the MemoryClient instance
memory_client = MemoryClient(region_name=REGION)

# TODO: Create the boto3 bedrock-agent-runtime client
_bedrock_runtime = boto3.client(
    "bedrock-agent-runtime",
    region_name = REGION
)  # Replace this line


# ── TODO 4 — Namespace Helper ─────────────────────────────────────────────────
def get_namespaces(mem_client: MemoryClient, memory_id: str) -> Dict:
    """Return a dict mapping strategy type → namespace template string."""
    strategies = mem_client.get_memory_strategies(memory_id)

    namespaces = {}

    for strategy in strategies:
        strategy_type = strategy.get("strategyType") or strategy.get("type")

        namespace_templates = strategy.get("namespaceTemplates")

        if not namespace_templates:
            namespace_templates = strategy.get("namespaces")

        if strategy_type and namespace_templates:
            namespaces[strategy_type] = namespace_templates[0]

    return namespaces


# ── TODO 5 — Memory Hook ──────────────────────────────────────────────────────
# Implement MemoryHook, a HookProvider subclass that adds long-term memory.
#
# The class needs:
#   __init__(self, actor_id, session_id, memory_client, memory_id)
#     — store all four as instance attributes
#     — call get_namespaces() and store the result as self.namespaces
#
#   retrieve_customer_context(self, event: MessageAddedEvent)
#     — only runs for plain-text user messages (not tool results)
#     — for each strategy namespace, call memory_client.retrieve_memories(
#          memory_id, namespace (formatted with actorId), query, top_k=5)
#     — collect non-empty memory texts tagged with their strategy type
#     — if any memories found, prepend them to the user message as:
#          "Customer Context:\n<memories>\n\n<original_message>"
#
#   save_support_interaction(self, event: AfterInvocationEvent)
#     — walk the message list backwards to find the last plain-text user
#       query and the last assistant response
#     — call memory_client.create_event(memory_id, actor_id, session_id,
#          messages=[(customer_query, "USER"), (agent_response, "ASSISTANT")])
#
#   register_hooks(self, registry: HookRegistry)
#     — register retrieve_customer_context on MessageAddedEvent
#     — register save_support_interaction on AfterInvocationEvent

class MemoryHook(HookProvider):
    """Long-term memory hook for the customer support agent."""

    def __init__(
        self,
        actor_id: str,
        session_id: str,
        memory_client: MemoryClient,
        memory_id: str,
    ):
        self.actor_id = actor_id
        self.session_id = session_id
        self.memory_client = memory_client
        self.memory_id = memory_id

        self.namespaces = get_namespaces(
            memory_client,
            memory_id,
        )

    def retrieve_customer_context(self, event: MessageAddedEvent):
        """Retrieve relevant memories and prepend them to the user message."""

        try:
            messages = event.agent.messages

            if not messages:
                return

            last_message = messages[-1]

            if last_message.get("role") != "user":
                return

            content = last_message.get("content")

            if not isinstance(content, list):
                return

            text_parts = []

            for item in content:
                if isinstance(item, dict) and "text" in item:
                    text_parts.append(item["text"])

            if not text_parts:
                return

            query = "\n".join(text_parts).strip()

            if not query:
                return

            memories = []

            for strategy_type, namespace_template in self.namespaces.items():

                namespace = namespace_template.replace(
                    "{actorId}",
                    self.actor_id,
                )

                try:
                    results = self.memory_client.retrieve_memories(
                        self.memory_id,
                        namespace,
                        query,
                        top_k=5,
                    )

                    if not results:
                        continue

                    for result in results:
                        memory_text = None

                        if isinstance(result, str):
                            memory_text = result

                        elif isinstance(result, dict):
                            memory_text = (
                                result.get("memory")
                                or result.get("text")
                                or result.get("content")
                            )

                        if memory_text:
                            memories.append(
                                f"[{strategy_type}] {memory_text}"
                            )

                except Exception as exc:
                    logger.warning(
                        "Memory retrieval failed for %s: %s",
                        strategy_type,
                        exc,
                    )

            if not memories:
                return

            context = (
                "Customer Context:\n"
                + "\n".join(memories)
                + "\n\n"
                + query
            )

            last_message["content"] = [
                {"text": context}
            ]

        except Exception as exc:
            logger.warning(
                "Unable to retrieve customer context: %s",
                exc,
            )

    def save_support_interaction(self, event: AfterInvocationEvent):
        """Save the completed turn to memory after the agent responds."""

        try:
            messages = event.agent.messages

            customer_query = None
            agent_response = None

            for message in reversed(messages):

                role = message.get("role")
                content = message.get("content")

                if not isinstance(content, list):
                    continue

                text_parts = []

                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        text_parts.append(item["text"])

                if not text_parts:
                    continue

                text = "\n".join(text_parts).strip()

                if not text:
                    continue

                if role == "assistant" and agent_response is None:
                    agent_response = text

                elif role == "user" and customer_query is None:
                    customer_query = text

                if customer_query and agent_response:
                    break

            if not customer_query or not agent_response:
                return

            self.memory_client.create_event(
                self.memory_id,
                self.actor_id,
                self.session_id,
                messages=[
                    (customer_query, "USER"),
                    (agent_response, "ASSISTANT"),
                ],
            )

        except Exception as exc:
            logger.warning(
                "Unable to save support interaction: %s",
                exc,
            )

    def register_hooks(self, registry: HookRegistry) -> None:
        """Register both memory callbacks."""

        registry.add_callback(
            MessageAddedEvent,
            self.retrieve_customer_context,
        )

        registry.add_callback(
            AfterInvocationEvent,
            self.save_support_interaction,
        )


# ── TODO 6 — Knowledge Base Tool ─────────────────────────────────────────────
# Implement search_knowledge_base(query) using the @tool decorator.
#
# Steps:
#   1. Guard: if KB_ID is empty return "Knowledge base not configured."
#   2. Call _bedrock_runtime.retrieve(
#          knowledgeBaseId=KB_ID,
#          retrievalQuery={"text": query}
#      )
#   3. Extract resp["retrievalResults"]; return a message if empty
#   4. Join the text chunks with "\n---\n" and return the result
#
# The docstring is the tool description — the model uses it to decide when
# to call this tool, so keep it clear and accurate.

@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the Amazon product catalog and support knowledge base.
    Use this for product specifications, return policies, warranty
    information, loyalty program details, and order status definitions.

    Args:
        query: The question or topic to search for

    Returns:
        Relevant information retrieved from the knowledge base
    """

    if not KB_ID:
        return "Knowledge base not configured."

    try:
        response = _bedrock_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={
                "text": query
            },
        )

        results = response.get("retrievalResults", [])

        if not results:
            return "No relevant information was found in the knowledge base."

        chunks = []

        for result in results:
            content = result.get("content", {})
            text = content.get("text")

            if text:
                chunks.append(text)

        if not chunks:
            return "No relevant information was found in the knowledge base."

        return "\n---\n".join(chunks)

    except Exception as exc:
        logger.exception("Knowledge Base retrieval failed")

        return (
            "Unable to search the knowledge base at this time. "
            f"Error: {exc}"
        )


# ── TODO 7 — Loyalty Discount Tool (Code Interpreter) ────────────────────────
# Implement calculate_loyalty_discount() using the @tool decorator.
#
# The tool must:
#   1. Build a self-contained Python code string that:
#        • Defines earn_rates: {"standard": 1, "device": 2, "fresh": 5}
#        • Defines tier_rates: {"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}
#        • Calculates points_redeemed (floor to nearest 500, cap at 50% of order)
#        • Calculates tier_discount (applied to subtotal after points)
#        • Calculates final_total, total_savings, points_earned, remaining_points
#        • Prints a JSON result dict
#   2. Execute the code with code_session(REGION).invoke("executeCode", {...})
#      using language="python" and clearContext=True
#   3. Return the first result event as a JSON string
#   4. Include a fallback that computes only the tier discount if the
#      Code Interpreter is unavailable

@tool
def calculate_loyalty_discount(
    loyalty_points: int,
    tier: str,
    order_total: float,
    product_category: str = "standard",
) -> str:
    """
    Calculate the customer's loyalty discount using Amazon Bedrock
    AgentCore Code Interpreter.

    Args:
        loyalty_points: Customer's current loyalty points.
        tier: Customer loyalty tier: Silver, Gold, or Platinum.
        order_total: Total order amount in USD.
        product_category: Product category: standard, device, or fresh.

    Returns:
        JSON string containing the complete loyalty calculation.
    """

    code = f"""
import json
import math

loyalty_points = {int(loyalty_points)}
tier = {json.dumps(tier)}
order_total = {float(order_total)}
product_category = {json.dumps(product_category)}

earn_rates = {{
    "standard": 1,
    "device": 2,
    "fresh": 5
}}

tier_rates = {{
    "Silver": 0.00,
    "Gold": 0.10,
    "Platinum": 0.15
}}

earn_rate = earn_rates.get(product_category, 1)
tier_rate = tier_rates.get(tier, 0.00)

# Customers can redeem points in multiples of 500.
# Each 100 points equals $1.
# Points can cover at most 50% of the order value.

maximum_points_value = order_total * 0.50
maximum_points = int(maximum_points_value * 100)

usable_points = min(
    loyalty_points,
    maximum_points
)

points_redeemed = (
    usable_points // 500
) * 500

points_discount = points_redeemed / 100

subtotal_after_points = max(
    0,
    order_total - points_discount
)

tier_discount = (
    subtotal_after_points * tier_rate
)

final_total = max(
    0,
    subtotal_after_points - tier_discount
)

total_savings = (
    order_total - final_total
)

points_earned = math.floor(
    order_total * earn_rate
)

remaining_points = (
    loyalty_points - points_redeemed
)

result = {{
    "loyalty_points": loyalty_points,
    "tier": tier,
    "order_total": round(order_total, 2),
    "product_category": product_category,
    "points_redeemed": points_redeemed,
    "points_discount": round(points_discount, 2),
    "tier_discount_rate": tier_discount_rate,
    "tier_discount_pct": round(tier_discount_rate * 100, 2),
    "tier_discount": round(tier_discount, 2),
    "final_total": round(final_total, 2),
    "total_savings": round(total_savings, 2),
    "points_earned": points_earned,
    "remaining_points": remaining_points
}}

print(json.dumps(result))
"""

    try:
        with code_session(REGION) as session:

            response = session.invoke(
                "executeCode",
                {
                    "language": "python",
                    "code": code,
                    "clearContext": True,
                },
            )

            stream = response.get("stream")

            if stream is None:
                raise RuntimeError(
                    "Code Interpreter response did not contain a stream."
                )

            events = list(stream)

            if not events:
                raise RuntimeError(
                    "Code Interpreter returned no events."
                )

            for event in events:

                result = event.get("result")

                if not result:
                    continue

                if result.get("isError"):
                    error_text = (
                        result
                        .get("content", [{}])[0]
                        .get("text", "Code execution failed.")
                    )

                    raise RuntimeError(error_text)

                structured_content = result.get(
                    "structuredContent"
                )

                if structured_content:
                    stdout = structured_content.get(
                        "stdout",
                        "",
                    ).strip()

                    if stdout:
                        return stdout

                content = result.get(
                    "content",
                    [],
                )

                for item in content:

                    if (
                        isinstance(item, dict)
                        and item.get("type") == "text"
                    ):
                        text = item.get(
                            "text",
                            "",
                        ).strip()

                        if text:
                            return text

            raise RuntimeError(
                "Code Interpreter completed without returning output."
            )

    except Exception as exc:

        logger.warning(
            "Code Interpreter failed: %s",
            exc,
        )

        # Safe fallback calculation.
        tier_rates = {
            "Silver": 0.00,
            "Gold": 0.10,
            "Platinum": 0.15,
        }

        tier_rate = tier_rates.get(
            tier,
            0.00,
        )

        maximum_points = int(
            order_total * 0.50 * 100
        )

        usable_points = min(
            loyalty_points,
            maximum_points,
        )

        points_redeemed = (
            usable_points // 500
        ) * 500

        points_discount = (
            points_redeemed / 100
        )

        subtotal_after_points = max(
            0,
            order_total - points_discount,
        )

        tier_discount = (
            subtotal_after_points * tier_rate
        )

        final_total = max(
            0,
            subtotal_after_points - tier_discount,
        )

        fallback = {
            "loyalty_ponts": loyalty_points,
            "order_total": round(order_total, 2),
            "tier": tier,
            "tier_discount_rate": tier_rate,
            "tier_discount_pct": round(tier_rate * 100, 2),
            "tier_discount": round(tier_discount, 2),
            "product_category": product_category,
            "points_redeemed": points_redeemed,
            "points_discount": round(
                points_discount,
                2,
            ),
            "tier_discount": round(
                tier_discount,
                2,
            ),
            "final_total": round(
                final_total,
                2,
            ),
            "total_savings": round(
                order_total - final_total,
                2,
            ),
            "points_earned": 0,
            "remaining_points": (
                loyalty_points
                - points_redeemed
            ),
            "fallback": True,
            "reason": str(exc),
        }

        return json.dumps(fallback)


# ── TODO 8 — Agent Entrypoint ─────────────────────────────────────────────────
# Implement the invoke() function decorated with @app.entrypoint.
#
# Steps:
#   1. Extract user_input, actor_id, and session_id from the payload
#      (generate a UUID if session_id is missing)
#   2. Instantiate MemoryHook for this actor/session
#   3. Instantiate AgentCoreBrowser(region=REGION)
#   4. Build the tools list: [search_knowledge_base, calculate_loyalty_discount,
#                              agent_core_browser.browser]
#   5. Connect to the Gateway via MCPClient, load gateway_tools, extend tools list
#   6. Create and invoke the Agent with all tools, hooks, and system_prompt
#   7. Return the text from the first content block of the response
#   8. Handle exceptions gracefully

@app.entrypoint
async def invoke(payload, context=None):
    """
    Main handler called by AgentCore for every incoming request.

    Expected payload keys:
      prompt      (str, required) — the customer's message
      customer_id (str, optional) — unique customer identifier
      session_id  (str, optional) — session identifier; generated if absent
    """

    try:
        user_input = payload.get("prompt")

        if not user_input:
            return "Please provide a customer support question."

        actor_id = payload.get(
            "customer_id",
            "anonymous-customer",
        )

        session_id = payload.get("session_id")

        if not session_id:
            session_id = str(uuid.uuid4())

        memory_hook = MemoryHook(
            actor_id=actor_id,
            session_id=session_id,
            memory_client=memory_client,
            memory_id=MEMORY_ID,
        )

        agent_core_browser = AgentCoreBrowser(
            region=REGION
        )

        browser_session_name = f"browser-{session_id}"

        browser_init = agent_core_browser.browser(
            {
                "action": {
                    "type": "init_session",
                    "description": "Customer support browser session",
                    "session_name": browser_session_name,
                }
            }
        )

        if browser_init.get("status") != "success":
            raise RuntimeError(
                f"Browser session initialization failed: {browser_init}"
            )

        @tool(
            name="navigate_browser",
            description=(
                "Navigate the customer support browser to a URL. "
                "Use this instead of the standard browser navigate action "
                "for dynamic websites such as Amazon."
            ),
        )
        def navigate_browser(url: str) -> str:
            """
            Navigate using DOMContentLoaded instead of networkidle.
            """

            try:
                page = agent_core_browser.get_session_page(
                    browser_session_name
                )

                if not page:
                    return (
                        "Browser error: no active browser page "
                        "for the current session."
                    )

                async def navigate():
                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=30000,
                    )

                agent_core_browser._execute_async(navigate())

                return (
                    f"Successfully navigated to {url}. "
                    "The page DOM has loaded."
                )

            except Exception as exc:
                return f"Browser navigation failed: {exc}"


        @tool(
            name="read_browser_page",
            description=(
                "Read the visible text from the currently open browser page. "
                "Use this after navigate_browser."
            ),
        )
        def read_browser_page() -> str:
            """
            Read the current browser page without using browser navigation.
            """

            try:
                page = agent_core_browser.get_session_page(
                    browser_session_name
                )

                if not page:
                    return "Browser error: no active browser page."

                async def read_page():
                    return await page.locator("body").inner_text(
                        timeout=15000
                    )

                text = agent_core_browser._execute_async(read_page())

                return str(text)

            except Exception as exc:
                return f"Browser page reading failed: {exc}"

        tools = [
            search_knowledge_base,
            calculate_loyalty_discount,
            navigate_browser,
            read_browser_page,
        ]

        mcp_client = MCPClient(
            lambda: streamable_http_client(
                GATEWAY_URL
            )
        )

        with mcp_client:

            gateway_tools = mcp_client.list_tools_sync()

            tools.extend(gateway_tools)

            system_prompt = """
You are a professional e-commerce customer support AI agent.

Your responsibilities are to help customers with:
- Product information
- Product specifications
- Warranty information
- Returns and refunds
- Loyalty rewards
- Order status
- Order tracking
- Customer orders
- Appropriate refund processing

Use the Knowledge Base for product catalog and support-policy
information.

Use the order and refund tools provided through the MCP Gateway
for live customer/order operations.

Use the loyalty discount tool for loyalty calculations.

BROWSER RULES:

When the customer asks you to browse a website:

1. Use navigate_browser to open the requested URL.
2. Do not use any other tool to navigate to a URL.
3. After navigation succeeds, use read_browser_page to read the page.
4. Do not repeatedly retry browser operations.
5. Do not provide information from general knowledge when the customer
   explicitly asks you to inspect a live webpage.
6. Only report information that you actually retrieved from the webpage.
7. If navigation or page reading fails, clearly report the failure.

Use customer memory when it is available and relevant.

Never invent order information, refund information, product
specifications, policies, or customer information.

When information is unavailable, clearly tell the customer.

Be concise, professional, helpful, and accurate.
"""

            agent = Agent(
                model=model,
                tools=tools,
                hooks=[memory_hook],
                system_prompt=system_prompt,
            )

            response = agent(user_input)

            if hasattr(response, "message"):
                message = response.message
            else:
                message = response

            if isinstance(message, dict):
                content = message.get("content", [])

                if content:
                    first_content = content[0]

                    if isinstance(first_content, dict):
                        return first_content.get(
                            "text",
                            str(first_content),
                        )

                    return str(first_content)

            return str(response)

    except Exception as exc:
        logger.exception(
            "Agent invocation failed"
        )

        return (
            "I’m sorry, but I encountered an error while "
            "processing your request. Please try again."
        )


# ── CLI entry point (do not modify) ──────────────────────────────────────────
def main():
    """Run one invocation from the command line for local testing."""
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=str)
    args = parser.parse_args()
    asyncio.run(invoke(json.loads(args.payload)))


if __name__ == "__main__":
    # app.run()
    # Uncomment the line below and comment app.run() for local CLI testing:
    main()
