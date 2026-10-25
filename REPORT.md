# TECHNICAL ISSUES ENCOUNTERED AND SUCCESSFULLY RESOLVED DURING THE DEVELOPMENT OF THE CUSTOMER SUPPORT AI AGENT

## 1. Introduction

The development of the Customer Support AI Agent using Amazon Bedrock AgentCore involved the integration of several AWS services and supporting technologies, including Amazon Bedrock Knowledge Bases, AgentCore Gateway, AWS Lambda, Amazon API Gateway, AgentCore Memory, AgentCore Code Interpreter, and AgentCore Browser. During implementation and testing, a number of technical issues were encountered.

The issues described in this report are limited to those that were successfully diagnosed and resolved. Each issue was investigated through testing, configuration checks, source-code inspection, and repeated validation. The solutions implemented resulted in successful operation of the respective components.

---

# 2. AgentCore Gateway Target Creation Failure

## 2.1 Issue Encountered

During the creation of the AgentCore Gateway targets for the customer-support tools, the API Gateway target failed validation.

The error indicated that some of the API Gateway paths did not contain the required `responses` definitions. The affected endpoints included:

* `/orders/{order_id}`
* `/customers/{customer_id}`
* `/customers/{customer_id}/orders}`

AgentCore Gateway requires the API specification to contain appropriate response definitions for the API operations before the API can be synchronized as a Gateway target.

## 2.2 Investigation

The API Gateway configuration and exported OpenAPI specification were inspected. It was discovered that the affected `GET` operations did not have properly defined HTTP response sections.

This prevented AgentCore Gateway from correctly interpreting the API operations and generating the corresponding MCP tools.

## 2.3 Solution Implemented

A `200` response was added to each affected API operation in the API Gateway/OpenAPI specification.

The response definitions were configured to describe the expected JSON responses from the Lambda-backed endpoints.

The API Gateway was subsequently redeployed and the AgentCore Gateway target was synchronized again.

## 2.4 Result

The API Gateway target was successfully synchronized and changed to a **READY** state.

The resulting Gateway exposed the order-related MCP tools successfully, including:

* `get_customer`
* `get_customer_orders`
* `get_order`

This allowed the customer-support agent to communicate with the order-tracking system through AgentCore Gateway.

---

# 3. Incorrect Response Model for Customer Orders

## 3.1 Issue Encountered

After resolving the missing response definitions, the `/customers/{customer_id}/orders` endpoint still required additional configuration to correctly describe its response.

The endpoint's method response was using an `Empty` response model, which did not accurately represent the JSON structure returned by the Lambda function.

## 3.2 Investigation

The API Gateway method response configuration was examined and compared with the actual response returned by the Lambda function.

The endpoint returns structured customer-order information, including customer identification and an array of orders. Therefore, an empty response model was not appropriate.

## 3.3 Solution Implemented

A dedicated `CustomerOrdersResponse` schema was configured for the endpoint.

The resulting response definition referenced the appropriate schema:

```json
{
  "description": "200 response",
  "content": {
    "application/json": {
      "schema": {
        "$ref": "#/components/schemas/CustomerOrdersResponse"
      }
    }
  }
}
```

The API was then redeployed and the AgentCore Gateway target was synchronized.

## 3.4 Result

The Gateway successfully recognized the customer-orders endpoint and exposed it as an MCP tool.

The underlying MCP operation was also tested directly and successfully returned the customer's order information.

---

# 4. AgentCore Gateway Lambda Permission Error

## 4.1 Issue Encountered

The AgentCore Gateway was configured to use the `refund-processor` Lambda function. However, the Gateway initially did not have permission to invoke the Lambda function.

This prevented refund-related MCP operations from executing successfully.

## 4.2 Investigation

The Gateway execution role was examined to determine whether it had the required Lambda invocation permission.

The issue was identified as an IAM authorization problem. The Gateway execution role did not initially have the required:

```text
lambda:InvokeFunction
```

permission for the Lambda functions used by the Gateway.

## 4.3 Solution Implemented

An IAM policy named `GatewayInvokeLambda` was added to the Gateway execution role.

The policy granted the Gateway permission to invoke the required Lambda functions:

```json
{
  "Effect": "Allow",
  "Action": "lambda:InvokeFunction",
  "Resource": [
    "arn:aws:lambda:us-east-1:067105747809:function:refund-processor",
    "arn:aws:lambda:us-east-1:067105747809:function:order-tracker"
  ]
}
```

## 4.4 Result

The Gateway obtained the required permissions and the refund-processing tools became operational.

The following refund-related operations were successfully tested:

* Check refund status
* Get return label
* Initiate refund

---

# 5. AgentCore Memory Integration Issue

## 5.1 Issue Encountered

The customer-support agent needed to remember information from previous customer interactions. An initial implementation using a memory hook resulted in complications because the memory functionality interacted with the internal Strands Agent message and MCP tool-call processing.

This created unnecessary complexity when memory operations were combined with other agent operations.

## 5.2 Investigation

The memory implementation was reviewed to separate customer-memory operations from the internal agent message-processing lifecycle.

It was determined that customer memory did not need to directly modify the agent's internal messages in order to provide the required functionality.

## 5.3 Solution Implemented

A dedicated `MemoryManager` was implemented.

The manager provides two primary functions:

1. Retrieve relevant customer context from AgentCore Memory.
2. Save completed customer-support interactions to AgentCore Memory.

The retrieval process searches the configured memory namespaces and retrieves relevant customer information based on the current query.

The interaction-saving function records the customer's query together with the assistant's response.

The implementation uses AgentCore Memory's semantic and user-preference namespaces.

## 5.4 Result

Memory retrieval was successfully tested.

For example, the system was previously given the preference:

> “Please remember that I prefer UPS delivery for my orders.”

The information was stored in AgentCore Memory.

A later request asking which delivery carrier the customer prefers successfully retrieved the stored preference and returned:

**UPS**

This confirmed that persistent customer-memory retrieval was functioning correctly.

---

# 6. Knowledge Base / RAG Integration

## 6.1 Issue Encountered

The customer-support agent needed to answer questions about company policies and product information using the configured Amazon Bedrock Knowledge Base.

The Knowledge Base needed to be integrated into the agent so that responses could be based on the organization's stored support information rather than relying solely on the language model.

## 6.2 Investigation

The Knowledge Base configuration was tested independently using the customer-support application.

The retrieval functionality was verified by submitting questions relating to product return policies.

## 6.3 Solution Implemented

The `search_knowledge_base` functionality was integrated into the Strands Agent as a callable tool.

The agent was configured to use the Knowledge Base when answering questions requiring company-specific information.

## 6.4 Result

The Knowledge Base integration successfully returned relevant policy information.

For example, when asked about the return policy for the Wireless Headphones Pro, the agent successfully retrieved the applicable policy information, including the applicable return periods for unopened and opened products.

This confirmed that the RAG component was functioning correctly.

---

# 7. AgentCore Code Interpreter and Loyalty Discount Calculation

## 7.1 Issue Encountered

The customer-support agent needed to perform customer-specific loyalty calculations involving loyalty points, membership level, discounts, and the final purchase amount.

These calculations needed to be performed reliably rather than being generated as unsupported numerical estimates by the language model.

## 7.2 Solution Implemented

The AgentCore Code Interpreter was integrated into the customer-support workflow through a dedicated loyalty-discount calculation function.

The function calculates:

* Loyalty-point discount
* Membership-level discount
* Total discount
* Final purchase price
* Total customer savings
* Remaining loyalty points
* Newly earned points

## 7.3 Result

The calculation was successfully tested using a customer with:

* 2,500 loyalty points
* Gold membership
* A $200 device

The system calculated:

* Points discount: **$25**
* Gold membership discount: **$17.50**
* Final price: **$157.50**
* Total savings: **$42.50**
* Earned points: **400**

The successful result confirmed that the Code Interpreter functionality was integrated correctly.

---

# 8. AgentCore Browser Navigation Failure with Dynamic Websites

## 8.1 Issue Encountered

The initial browser implementation successfully opened simple websites such as `example.com`, but navigation to Amazon encountered a timeout.

The problem occurred because the standard browser navigation implementation waited for the page to reach the Playwright:

```text
networkidle
```

state.

Amazon is a highly dynamic website with continuous network activity, which caused the browser operation to wait until the timeout period was reached.

## 8.2 Investigation

The installed Strands browser implementation was inspected.

The navigation implementation was found to perform:

```python
await page.goto(action.url)
await page.wait_for_load_state("networkidle")
```

Testing demonstrated that:

* `example.com` successfully reached the `networkidle` state.
* Amazon did not reliably reach that state within the configured timeout.

Therefore, the problem was not with AgentCore Browser itself but with the navigation strategy used for highly dynamic websites.

## 8.3 Solution Implemented

A dedicated `navigate_browser` tool was created.

Instead of waiting for `networkidle`, the custom navigation function uses:

```python
await page.goto(
    url,
    wait_until="domcontentloaded",
    timeout=30000
)
```

This allows the browser to proceed once the initial HTML document has loaded instead of waiting for all continuing network activity to stop.

A second controlled tool, `read_browser_page`, was implemented to retrieve the actual page content after navigation.

The generic browser navigation action was removed from the agent's available tools to prevent the model from repeatedly invoking the problematic navigation method.

The browser workflow was therefore changed to:

```text
navigate_browser
        ↓
read_browser_page
```

## 8.4 Result

The revised browser implementation successfully passed the Amazon test.

The test:

```bash
python main.py '{"prompt":"Open the Amazon website and tell me the title of the homepage.","customer_id":"CUST-123","session_id":"test-browser-004"}'
```

produced the successful tool sequence:

```text
Tool #1: navigate_browser

Tool #2: read_browser_page
```

The agent retrieved the live Amazon page and correctly identified the homepage title as:

**“Amazon.com. Spend less. Smile more.”**

This confirmed that the browser integration was successfully resolved.

---

# 9. Customer Information Retrieval Through AgentCore Gateway

## 9.1 Issue Encountered

The customer-support agent needed to retrieve customer-specific information through the order-tracking system.

The Gateway had to correctly expose the API Gateway-backed customer endpoint to the agent.

## 9.2 Solution Implemented

The API Gateway was connected to AgentCore Gateway as an API Gateway target.

The Gateway was configured to expose the customer endpoint:

```text
GET /customers/{customer_id}
```

The corresponding MCP tool became available to the agent.

## 9.3 Result

The following request was successfully processed:

> “Can you show me the customer information for customer CUST-123?”

The agent retrieved the customer information, including:

* Customer name: Jane Smith
* Loyalty points: 4,250
* Membership tier: Gold

This confirmed successful integration between the customer-support agent, AgentCore Gateway, API Gateway, and Lambda-backed customer service.

---

# 10. Order Status and Tracking Integration

## 10.1 Issue Encountered

The agent needed to provide customers with real-time order information through the order-tracking service.

This required successful communication between the Strands Agent, AgentCore Gateway, API Gateway, and the `order-tracker` Lambda function.

## 10.2 Solution Implemented

The order-tracking API was configured as an AgentCore Gateway target.

The following endpoint was exposed:

```text
GET /orders/{order_id}
```

The resulting MCP tool was made available to the agent as:

```text
order-tracker___get_order
```

## 10.3 Result

The agent successfully processed requests for order status.

For example, a request concerning `ORD-001` successfully returned information including:

* Order status: SHIPPED
* Product: Wireless Headphones Pro
* Order total: $89.99
* Carrier: UPS
* Tracking information
* Estimated delivery information

This confirmed successful order-tracking integration.

---

# 11. Refund Status Integration

## 11.1 Issue Encountered

The customer-support agent needed to determine the status of customer refunds.

The refund functionality required communication between the order-tracking service and the refund-processing Lambda through AgentCore Gateway.

## 11.2 Solution Implemented

The refund-processing Lambda was exposed through AgentCore Gateway.

The agent was given access to the refund-status MCP tool:

```text
refund-processor___check_refund_status
```

The agent could first retrieve the relevant order information and then use the refund-processing functionality to determine the refund status.

## 11.3 Result

The refund-status test was successfully completed.

For `ORD-001`, the agent returned that the refund was:

**Processing**

and indicated that the expected completion period was approximately:

**2–3 business days.**

This confirmed that the refund-status workflow was operational.

---

# 12. Return Label Generation

## 12.1 Issue Encountered

Customers needed to obtain return labels for eligible orders through the support agent.

This required successful integration of the return-label operation into the AgentCore Gateway and Strands Agent.

## 12.2 Solution Implemented

The refund processor exposed the following MCP operation:

```text
refund-processor___get_return_label
```

The agent was configured to invoke this tool when customers requested a return label.

## 12.3 Result

The return-label test successfully completed.

For `ORD-001`, the agent returned:

* Return label URL
* Carrier: UPS
* Validity information

The agent also provided relevant return information associated with the order.

This confirmed that the return-label workflow was functioning successfully.

---

# 13. Refund Initiation

## 13.1 Issue Encountered

The support agent needed to allow customers to initiate refunds through the refund-processing service.

The operation required successful communication between the agent, AgentCore Gateway, and the refund-processing Lambda.

## 13.2 Solution Implemented

The following MCP tool was exposed and made available to the agent:

```text
refund-processor___initiate_refund
```

The agent was instructed to use this tool when a customer explicitly requested a refund.

## 13.3 Result

The refund initiation test successfully executed.

For `ORD-001`, the system generated a refund record containing:

* Refund ID
* Order ID
* Refund status
* Refund amount information
* Credit timeline
* Creation timestamp

The refund was successfully processed by the underlying tool.

A minor data-quality inconsistency was observed in the returned refund amount, where the tool output displayed `$0` while the accompanying response stated that the full `$89.99` order amount would be refunded. The **tool execution itself was successful**, so this was recorded as a data consistency issue rather than an integration failure.

---

# 14. Conclusion

The development and testing of the Customer Support AI Agent involved resolving several integration and configuration challenges across AWS services and the Strands Agent framework.

The successfully resolved issues primarily involved:

* AgentCore Gateway API specification validation
* API response-model configuration
* IAM permissions for Lambda invocation
* Persistent AgentCore Memory integration
* Knowledge Base retrieval
* Code Interpreter calculations
* Browser navigation for dynamic websites
* Customer information retrieval
* Order tracking
* Refund status checking
* Return-label retrieval
* Refund initiation

Following these resolutions, the major customer-support capabilities tested were successfully operational. The resulting architecture integrates AWS Lambda, API Gateway, AgentCore Gateway, AgentCore Memory, Amazon Bedrock Knowledge Base, Code Interpreter, AgentCore Browser, and the Strands Agent framework into a functioning customer-support system.

The testing process also demonstrated the importance of validating individual components independently before combining them into the complete agent. This approach made it possible to isolate configuration, permission, API specification, browser automation, and memory-integration issues and address them systematically.
