from strands_tools.browser import AgentCoreBrowser

print("Creating AgentCoreBrowser...")

browser_tool = AgentCoreBrowser(
    region="us-east-1"
)

print("Browser object created.")
print("Initializing browser session...")

try:
    result = browser_tool.browser(
        {
            "action": {
                "type": "init_session",
                "description": "AgentCore Browser Test",
                "session_name": "test-session"
            }
        }
    )

    print("\nINIT SESSION RESULT:")
    print(result)

    if result.get("status") != "success":
        raise RuntimeError(f"Browser session initialization failed: {result}")

    print("\nNavigating to Amazon...")

    result = browser_tool.browser(
        {
            "action": {
                "type": "navigate",
                "url": "https://www.amazon.com",
                "session_name": "test-session"
            }
        }
    )

    print("\nNAVIGATION RESULT:")
    print(result)

    print("\nGetting page text...")

    result = browser_tool.browser(
        {
            "action": {
                "type": "get_text",
                "selector": "body",
                "session_name": "test-session"
            }
        }
    )

    print("\nPAGE TEXT RESULT:")
    print(result)

    print("\nBROWSER TEST COMPLETED.")

except Exception as e:
    print("\nBROWSER ERROR:")
    print(type(e).__name__)
    print(str(e))

finally:
    try:
        browser_tool.browser(
            {
                "action": {
                    "type": "close",
                    "session_name": "test-session"
                }
            }
        )
        print("\nBrowser closed.")
    except Exception as e:
        print("\nCleanup error:", e)
