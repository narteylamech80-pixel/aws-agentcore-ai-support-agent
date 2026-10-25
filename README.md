# Customer Support AI Agent

A production-oriented customer support AI agent built with **Amazon Bedrock AgentCore**, **Strands Agents**, and AWS services. The agent provides customer support for an online retail environment by combining conversational AI with persistent memory, knowledge-base retrieval, order management, refund processing, loyalty calculations, and browser automation.

---

## Table of Contents

* [Overview](#overview)
* [Architecture](#architecture)
* [Features](#features)
* [Technologies](#technologies)
* [Project Configuration](#project-configuration)
* [Configuration Variables](#configuration-variables)
* [Agent Tools](#agent-tools)
* [Knowledge Base](#knowledge-base)
* [Customer Memory](#customer-memory)
* [Loyalty Discount Calculation](#loyalty-discount-calculation)
* [AgentCore Gateway](#agentcore-gateway)
* [Browser Automation](#browser-automation)
* [Agent Entrypoint](#agent-entrypoint)
* [Local Testing](#local-testing)
* [Example Requests](#example-requests)
* [Deployment](#deployment)
* [Error Handling](#error-handling)
* [Testing Status](#testing-status)
* [Important Notes](#important-notes)

---

# Overview

`main.py` is the primary application entry point for the Customer Support AI Agent.

The application uses a Strands `Agent` powered by an Amazon Bedrock model and connects the model to several specialized tools.

The agent can:

* Answer product and policy questions.
* Search a Bedrock Knowledge Base.
* Retrieve customer information.
* Retrieve order information and order status.
* Check refund status.
* Generate return-label information.
* Initiate refunds.
* Calculate loyalty discounts.
* Remember relevant customer preferences and previous interactions.
* Browse external websites when required.
* Execute calculations using AgentCore Code Interpreter.
* Operate through Amazon Bedrock AgentCore Runtime.

The agent is designed to ground its responses in tool results rather than inventing customer, order, policy, or transaction information.

---

# Architecture

The application combines the following components:

```text
                         Customer
                            |
                            v
                  +-------------------+
                  |   AgentCore App   |
                  |     main.py       |
                  +---------+---------+
                            |
                            v
                  +-------------------+
                  | Strands AI Agent  |
                  | Amazon Nova Model |
                  +---------+---------+
                            |
          +-----------------+------------------+
          |                 |                  |
          v                 v                  v
   Knowledge Base       AgentCore          Code Interpreter
       RAG              Gateway                |
          |                 |                  |
          |         +-------+-------+          |
          |         |               |          |
          |         v               v          |
          |    Order Tracker   Refund Processor|
          |         |               |          |
          |         v               v          |
          |      API Gateway      Lambda       |
          |                                     
          +------------------------------------+
                            |
                            v
                     AgentCore Memory
                            |
                            v
                    Customer Context
                            
                            +
                            
                     AgentCore Browser
                            |
                            v
                    External Websites
```

---

# Features

## 1. AI Customer Support

The application uses an Amazon Bedrock model through Strands Agents to understand customer requests and determine which tools are required.

The system prompt instructs the agent to:

* Provide concise and factual responses.
* Use tools when authoritative information is required.
* Avoid inventing tool results.
* Protect customer privacy.
* Ask for clarification when important information is missing.
* Explain when a request is outside the agent's capabilities.

---

## 2. Knowledge Base Retrieval

The `search_knowledge_base()` tool connects the agent to an Amazon Bedrock Knowledge Base.

It is used for information such as:

* Product specifications.
* Return policies.
* Warranty information.
* Loyalty-program rules.
* Order-status definitions.

The tool performs a Bedrock Knowledge Base retrieval operation and returns the relevant text chunks to the agent.

---

## 3. Persistent Customer Memory

The application uses **Amazon Bedrock AgentCore Memory** to maintain customer context between interactions.

Memory supports:

* Customer preferences.
* Previously provided customer information.
* Relevant historical support interactions.

The `MemoryHook` performs two main operations:

### Retrieval

Before an agent invocation, relevant memories are retrieved based on the customer's current query.

The memories are added to the customer's context so that the agent can use them when responding.

### Storage

After the agent completes an interaction, the customer's query and the assistant's response are saved to AgentCore Memory.

This allows information from one interaction to be available during a later interaction.

---

## 4. Loyalty Discount Calculation

The `calculate_loyalty_discount()` tool performs exact loyalty calculations using **AgentCore Code Interpreter**.

It accepts:

```text
loyalty_points
tier
order_total
product_category
```

Supported membership tiers include:

```text
Silver
Gold
Platinum
```

Supported product categories include:

```text
standard
device
fresh
```

The calculation includes:

* Points redeemed.
* Points discount.
* Membership-tier discount.
* Final order total.
* Total savings.
* Points earned.
* Remaining loyalty points.

The calculation is executed inside the Code Interpreter sandbox.

A fallback calculation is provided if Code Interpreter becomes unavailable.

---

# AgentCore Gateway

The application connects to an AgentCore Gateway using MCP.

The Gateway provides access to backend customer-support operations.

The Gateway currently exposes tools associated with:

## Customer operations

```text
order-tracker___get_customer
```

Retrieves customer information.

---

## Order operations

```text
order-tracker___get_order
```

Retrieves information about a specific order.

```text
order-tracker___get_customer_orders
```

Retrieves orders associated with a customer.

---

## Refund operations

```text
refund-processor___check_refund_status
```

Checks the status of a refund.

```text
refund-processor___get_return_label
```

Retrieves return-label information.

```text
refund-processor___initiate_refund
```

Initiates a refund request.

The Gateway dynamically discovers the available MCP tools using:

```python
mcp_client.list_tools_sync()
```

These tools are then added to the Strands Agent.

---

# Browser Automation

The application integrates **AgentCore Browser** for tasks that require visiting external websites.

The browser functionality supports operations such as:

* Opening a website.
* Reading webpage content.
* Extracting information from live webpages.

For dynamic websites such as Amazon, navigation uses a controlled browser-navigation approach rather than relying on a `networkidle` condition.

The browser workflow is:

```text
Customer Request
       |
       v
navigate_browser
       |
       v
Website Loaded
       |
       v
read_browser_page
       |
       v
Page Content
       |
       v
AI Response
```

This approach was implemented because highly dynamic websites can continue generating network activity and may not reliably reach the Playwright `networkidle` state.

---

# Configuration Variables

Before deployment, the application requires the following configuration values:

```python
GATEWAY_URL = "<gateway_url>"
KB_ID       = "<kbid>"
REGION      = "<region>"
MEMORY_ID   = "<mem_id>"
```

## GATEWAY_URL

The MCP endpoint for the AgentCore Gateway.

Example format:

```text
https://<gateway-alias>.gateway.bedrock-agentcore.<region>.amazonaws.com/mcp
```

---

## KB_ID

The ID of the Amazon Bedrock Knowledge Base used by the customer-support agent.

Example:

```text
0L01Q7LZNY
```

---

## REGION

The AWS region where the project's resources are deployed.

Example:

```text
us-east-1
```

---

## MEMORY_ID

The AgentCore Memory resource used for persistent customer context.

Example format:

```text
CustomerSupportMemory-XXXXXXXXXX
```

---

# Model Configuration

The application uses the following Amazon Bedrock model:

```python
model_id = "global.amazon.nova-2-lite-v1:0"
```

The model is initialized using:

```python
model = BedrockModel(model_id=model_id)
```

The application also initializes the AgentCore Memory client:

```python
memory_client = MemoryClient(region_name=REGION)
```

and the Bedrock Agent Runtime client:

```python
_bedrock_runtime = boto3.client(
    "bedrock-agent-runtime",
    region_name=REGION
)
```

---

# Agent Entrypoint

The main AgentCore entrypoint is:

```python
@app.entrypoint
async def invoke(payload, context=None):
```

The entrypoint accepts a payload containing the customer's request.

Expected payload:

```json
{
  "prompt": "What is the status of my order?",
  "customer_id": "CUST-123",
  "session_id": "session-001"
}
```

## Payload fields

### `prompt`

Required.

Contains the customer's message.

Example:

```text
"What is the status of order ORD-001?"
```

### `customer_id`

Optional.

Identifies the customer and is used as the AgentCore Memory actor ID.

Example:

```text
CUST-123
```

### `session_id`

Optional.

Identifies the current conversation session.

If one is not supplied, the application generates a UUID.

---

# Agent Processing Flow

Each request follows this general process:

```text
1. Receive request
        |
2. Extract prompt
        |
3. Identify customer
        |
4. Identify session
        |
5. Initialize customer memory
        |
6. Initialize browser
        |
7. Initialize local tools
        |
8. Connect to AgentCore Gateway
        |
9. Discover MCP tools
        |
10. Create Strands Agent
        |
11. Process customer request
        |
12. Invoke required tools
        |
13. Generate response
        |
14. Return response
```

---

# Local Testing

The application can be tested locally from the project directory.

Example:

```bash
python main.py '{"prompt":"Hello","customer_id":"CUST-123","session_id":"test-001"}'
```

Another example:

```bash
python main.py '{"prompt":"What is the status of order ORD-001?","customer_id":"CUST-123","session_id":"test-order-001"}'
```

---

# Example Requests

## Customer Information

```bash
python main.py '{"prompt":"Can you show me the customer information for customer CUST-123?","customer_id":"CUST-123","session_id":"customer-test-001"}'
```

The agent can retrieve customer information through the Gateway.

---

## Order Status

```bash
python main.py '{"prompt":"What is the status of order ORD-001?","customer_id":"CUST-123","session_id":"order-test-001"}'
```

The agent uses the order-tracking Gateway tool.

---

## Refund Status

```bash
python main.py '{"prompt":"Can you check the refund status for order ORD-001?","customer_id":"CUST-123","session_id":"refund-test-001"}'
```

---

## Return Label

```bash
python main.py '{"prompt":"Can you get me the return label for order ORD-001?","customer_id":"CUST-123","session_id":"return-test-001"}'
```

---

## Initiate Refund

```bash
python main.py '{"prompt":"I want to initiate a refund for order ORD-001.","customer_id":"CUST-123","session_id":"refund-init-001"}'
```

---

## Knowledge Base

```bash
python main.py '{"prompt":"What is the return policy for Wireless Headphones Pro?","customer_id":"CUST-123","session_id":"kb-test-001"}'
```

---

## Customer Memory

A customer can provide a preference:

```text
Please remember that I prefer UPS delivery for my orders.
```

A later request can retrieve that information:

```text
What delivery carrier do I prefer for my orders?
```

The memory system retrieves the stored preference and provides it as customer context to the agent.

---

## Browser

The browser can be tested with:

```bash
python main.py '{"prompt":"Open the Amazon website and tell me the title of the homepage.","customer_id":"CUST-123","session_id":"browser-test-001"}'
```

The successful browser workflow uses:

```text
Tool #1: navigate_browser
Tool #2: read_browser_page
```

The agent reads the actual webpage instead of relying on previously known information.

---

# Deployment

The application is designed to run on Amazon Bedrock AgentCore Runtime.

After configuring the required AWS resources, the application can be deployed using the AgentCore CLI:

```bash
agentcore deploy
```

After deployment, the agent can be invoked through AgentCore:

```bash
agentcore invoke '{"prompt":"Hello","customer_id":"CUST-123","session_id":"s1"}'
```

---

# Error Handling

The application includes error handling at multiple levels.

## Knowledge Base

If the Knowledge Base is unavailable, the tool returns an explanatory message rather than terminating the entire agent.

## Memory

Memory failures are logged and do not prevent the customer-support request from being processed.

This is important because memory is an enhancement to the support experience and should not become a single point of failure.

## Code Interpreter

If AgentCore Code Interpreter fails, the loyalty calculation tool uses a fallback calculation based on the customer's membership tier.

## Agent Invocation

Unexpected errors during agent execution are caught and logged.

The customer receives a general support message rather than an internal stack trace.

---

# Logging

The application uses Python's built-in `logging` module:

```python
logging.basicConfig(level=logging.WARNING)
```

The application logger is:

```python
logger = logging.getLogger("CSAI_Agent")
```

Warnings and exceptions can therefore be captured without exposing internal implementation details to customers.

---

# Testing Status

The following major components have been successfully tested:

| Component                    | Status |
| ---------------------------- | ------ |
| Amazon Bedrock model         | Passed |
| Knowledge Base retrieval     | Passed |
| Customer information         | Passed |
| Order status                 | Passed |
| Refund status                | Passed |
| Return label                 | Passed |
| Refund initiation            | Passed |
| Loyalty discount calculation | Passed |
| AgentCore Memory retrieval   | Passed |
| AgentCore Browser            | Passed |
| Browser navigation           | Passed |
| Live webpage reading         | Passed |
| AgentCore Gateway            | Passed |
| Lambda integration           | Passed |
| API Gateway integration      | Passed |

The customer-orders operation has a known validation issue in the full agent workflow and is not considered part of the successfully completed tests documented above.

---

# AWS Resources

The application depends on several AWS resources.

## Lambda Functions

```text
order-tracker
refund-processor
```

## API Gateway

```text
CustomerSupportOrderAPI
```

## AgentCore Gateway

```text
CustomerSupportGateway
```

## Knowledge Base

```text
CustomerSupportKB
```

## AgentCore Memory

```text
CustomerSupportMemory
```

## Model

```text
global.amazon.nova-2-lite-v1:0
```

---

# Security Considerations

The application is designed to avoid exposing unnecessary customer information.

The system prompt instructs the agent to:

* Protect customer privacy.
* Avoid requesting unnecessary sensitive information.
* Use authenticated/backend tools for customer-specific information.
* Never invent customer or order information.
* Only claim that an operation was completed when a tool confirms it.

The AgentCore Gateway execution role also requires appropriate IAM permissions for the Lambda functions it invokes.

For example, the Gateway execution role requires:

```text
lambda:InvokeFunction
```

for the relevant Lambda resources.

---

# Project Structure

A simplified project structure is:

```text
starter/
│
├── main.py
├── pyproject.toml
├── uv.lock
│
├── Lambda functions
│   ├── order_tracker.py
│   └── refund_processor.py
│
└── other AgentCore/AWS project configuration
```

The primary application logic is contained in:

```text
main.py
```

---

# Design Principles

The application follows several important design principles.

### Tool-grounded responses

The agent should use tools when authoritative information is available instead of relying on model-generated assumptions.

### Separation of responsibilities

Different services are responsible for different tasks:

```text
Knowledge Base       → Policies and product information
Gateway              → Backend operations
Lambda               → Business operations
Memory               → Customer context
Code Interpreter     → Exact calculations
Browser              → Live web information
Strands Agent        → Reasoning and orchestration
```

### Graceful degradation

Failure of an optional component such as memory or Code Interpreter should not unnecessarily terminate the entire customer-support interaction.

### Customer privacy

Only information necessary to complete the customer's request should be requested or processed.

### Verified actions

The agent should not claim that an operation was completed unless the corresponding tool confirms the operation.

---

# Conclusion

`main.py` serves as the central orchestration layer for the Customer Support AI Agent.

It brings together Amazon Bedrock, Strands Agents, AgentCore Runtime, AgentCore Gateway, AgentCore Memory, Knowledge Base retrieval, Code Interpreter, browser automation, API Gateway, and Lambda into a single customer-support workflow.

The resulting system can handle a broad range of e-commerce support tasks while grounding operational responses in backend tools and maintaining relevant customer context across interactions.

---
