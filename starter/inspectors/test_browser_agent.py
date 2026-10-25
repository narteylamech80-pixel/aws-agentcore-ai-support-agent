from strands import Agent
from strands_tools.browser import AgentCoreBrowser

REGION = "us-east-1"

print("Creating AgentCoreBrowser...")

browser_tool = AgentCoreBrowser(
    region=REGION,
    session_timeout=300,
)

print("Creating Strands agent...")

agent = Agent(
    tools=[browser_tool.browser],
    system_prompt="""
You are a browser testing agent.

Use the browser tool to:
1. Initialize a browser session.
2. Navigate to https://example.com
3. Read the page title.
4. Return the page title only.

Do not repeatedly retry the same browser action.
If navigation fails, report the browser error and stop.
"""
)

print("Running agent...\n")

try:
    response = agent(
        "Open example.com and tell me the page title."
    )

    print("\nAGENT RESPONSE:")

    if hasattr(response, "message"):
        message = response.message
        if isinstance(message, dict):
            content = message.get("content", [])
            if content:
                print(content[0].get("text", content[0]))
            else:
                print(response)
        else:
            print(message)
    else:
        print(response)

except Exception as e:
    print("\nERROR:")
    print(type(e).__name__)
    print(str(e))