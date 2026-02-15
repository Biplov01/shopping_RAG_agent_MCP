# 🏗️ MCP Deep Dive: Architecture, Protocol & LLM Communication

## Table of Contents
1. [MCP Architecture Overview](#architecture)
2. [Protocol Specification](#protocol)
3. [LLM Communication Flow](#llm-communication)
4. [Message Types & Structure](#messages)
5. [Transport Layers](#transport)
6. [Security & Authentication](#security)
7. [Real Implementation Examples](#examples)

---

## 🏛️ MCP Architecture Overview {#architecture}

### Three-Layer Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    LAYER 1: CLIENT                         │
│                  (AI Application Layer)                    │
│                                                            │
│  ┌──────────────────────────────────────────────────┐    │
│  │         LLM (Claude, GPT, etc.)                  │    │
│  │                                                   │    │
│  │  • Natural language understanding                │    │
│  │  • Tool selection logic                          │    │
│  │  • Response generation                           │    │
│  │  • Context management                            │    │
│  └──────────────────────────────────────────────────┘    │
│                          ↕                                 │
│  ┌──────────────────────────────────────────────────┐    │
│  │         MCP Client SDK                           │    │
│  │                                                   │    │
│  │  • Protocol handling                             │    │
│  │  • Message serialization                         │    │
│  │  • Connection management                         │    │
│  │  • Tool discovery                                │    │
│  └──────────────────────────────────────────────────┘    │
│                                                            │
└────────────────────────────────────────────────────────────┘
                             ↕
              ┌──────────────────────────┐
              │   MCP PROTOCOL LAYER     │
              │                          │
              │  • JSON-RPC 2.0 based   │
              │  • Bi-directional        │
              │  • Request/Response      │
              │  • Notifications         │
              └──────────────────────────┘
                             ↕
┌────────────────────────────────────────────────────────────┐
│              LAYER 2: TRANSPORT LAYER                      │
│                                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   stdio     │  │    HTTP     │  │  WebSocket  │      │
│  │             │  │             │  │             │      │
│  │ Processes   │  │ REST APIs   │  │ Real-time   │      │
│  │ communicate │  │ over network│  │ bidirectional│     │
│  │ via stdin/  │  │             │  │ connection   │     │
│  │ stdout      │  │             │  │             │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
│                                                            │
└────────────────────────────────────────────────────────────┘
                             ↕
┌────────────────────────────────────────────────────────────┐
│                  LAYER 3: SERVER                           │
│              (Tool Implementation Layer)                   │
│                                                            │
│  ┌──────────────────────────────────────────────────┐    │
│  │         MCP Server SDK                           │    │
│  │                                                   │    │
│  │  • Request routing                               │    │
│  │  • Tool registration                             │    │
│  │  • Schema validation                             │    │
│  │  • Error handling                                │    │
│  └──────────────────────────────────────────────────┘    │
│                          ↕                                 │
│  ┌──────────────────────────────────────────────────┐    │
│  │         Tool Implementations                     │    │
│  │                                                   │    │
│  │  🔧 Database queries                             │    │
│  │  🔧 File operations                              │    │
│  │  🔧 API integrations                             │    │
│  │  🔧 Business logic                               │    │
│  └──────────────────────────────────────────────────┘    │
│                          ↕                                 │
│  ┌──────────────────────────────────────────────────┐    │
│  │         Data Sources                             │    │
│  │                                                   │    │
│  │  💾 Databases (SQL, NoSQL)                       │    │
│  │  📁 File systems                                 │    │
│  │  🌐 External APIs                                │    │
│  │  ☁️  Cloud services                              │    │
│  └──────────────────────────────────────────────────┘    │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 📡 Protocol Specification {#protocol}

### JSON-RPC 2.0 Foundation

MCP is built on **JSON-RPC 2.0**, a lightweight remote procedure call protocol.

#### Core Message Structure

```json
{
  "jsonrpc": "2.0",           // Protocol version (required)
  "id": "unique-id-123",      // Request ID (required for requests)
  "method": "tools/call",     // Method name (required)
  "params": {                 // Parameters (optional)
    "name": "search_products",
    "arguments": {
      "query": "phones",
      "max_price": 1000
    }
  }
}
```

### Message Types

#### 1. **Request** (Client → Server)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "query_database",
    "arguments": {
      "sql": "SELECT * FROM products WHERE price < 1000"
    }
  }
}
```

**Key Fields:**
- `id`: Unique identifier to match response
- `method`: Which operation to perform
- `params`: Input data for the operation

---

#### 2. **Response** (Server → Client)

**Success Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Found 3 products: iPhone ($899), Samsung ($799), Google ($699)"
      }
    ]
  }
}
```

**Error Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32600,
    "message": "Invalid SQL syntax",
    "data": {
      "details": "Missing WHERE clause"
    }
  }
}
```

**Error Codes:**
```
-32700  Parse error (Invalid JSON)
-32600  Invalid Request
-32601  Method not found
-32602  Invalid params
-32603  Internal error
-32000 to -32099  Server-defined errors
```

---

#### 3. **Notification** (No response expected)

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/progress",
  "params": {
    "progress": 0.5,
    "message": "Processing 50% complete"
  }
}
```

**Note:** No `id` field = no response expected

---

### MCP-Specific Methods

#### Tool Discovery

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "search_products",
        "description": "Search for products in the database",
        "inputSchema": {
          "type": "object",
          "properties": {
            "query": {
              "type": "string",
              "description": "Search term"
            },
            "max_price": {
              "type": "number",
              "description": "Maximum price filter"
            }
          },
          "required": ["query"]
        }
      },
      {
        "name": "get_weather",
        "description": "Get weather for a city",
        "inputSchema": {
          "type": "object",
          "properties": {
            "city": {
              "type": "string",
              "description": "City name"
            }
          },
          "required": ["city"]
        }
      }
    ]
  }
}
```

---

#### Tool Execution

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "search_products",
    "arguments": {
      "query": "laptop",
      "max_price": 2000
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Found 2 laptops:\n1. MacBook Pro M3: $2499\n2. Dell XPS 15: $1799"
      }
    ],
    "isError": false
  }
}
```

---

#### Resource Access

**List Resources:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "resources/list"
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "resources": [
      {
        "uri": "file:///path/to/document.txt",
        "name": "Product Catalog",
        "mimeType": "text/plain",
        "description": "List of all products"
      },
      {
        "uri": "db://products/schema",
        "name": "Database Schema",
        "mimeType": "application/json",
        "description": "Product database structure"
      }
    ]
  }
}
```

**Read Resource:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "resources/read",
  "params": {
    "uri": "file:///path/to/document.txt"
  }
}
```

---

#### Prompts

**List Prompts:**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "prompts/list"
}
```

**Get Prompt:**
```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "prompts/get",
  "params": {
    "name": "analyze_sales",
    "arguments": {
      "period": "Q1 2024"
    }
  }
}
```

---

## 🤖 LLM Communication Flow {#llm-communication}

### Complete End-to-End Flow

```
┌──────────────────────────────────────────────────────────────┐
│ STEP 1: User Query                                           │
└──────────────────────────────────────────────────────────────┘

User types: "Find me gaming laptops under $2000"
                    ↓

┌──────────────────────────────────────────────────────────────┐
│ STEP 2: LLM Processing (Client Side)                         │
└──────────────────────────────────────────────────────────────┘

Claude receives user input and thinks:

Internal LLM Reasoning:
┌─────────────────────────────────────────────────┐
│ User wants: Gaming laptops                      │
│ Constraint: Price < $2000                       │
│ Task: Database search                           │
│                                                 │
│ I have these tools available via MCP:           │
│ 1. search_products(query, max_price)           │
│ 2. get_weather(city)                           │
│ 3. send_email(to, subject, body)              │
│                                                 │
│ Decision: Use tool #1 - search_products        │
│ Parameters:                                     │
│   - query: "gaming laptop"                     │
│   - max_price: 2000                            │
└─────────────────────────────────────────────────┘
                    ↓

┌──────────────────────────────────────────────────────────────┐
│ STEP 3: Tool Call Request (MCP Protocol)                     │
└──────────────────────────────────────────────────────────────┘

MCP Client constructs JSON-RPC request:

{
  "jsonrpc": "2.0",
  "id": "req-001",
  "method": "tools/call",
  "params": {
    "name": "search_products",
    "arguments": {
      "query": "gaming laptop",
      "max_price": 2000
    }
  }
}
                    ↓
              [Transport Layer]
         stdio / HTTP / WebSocket
                    ↓

┌──────────────────────────────────────────────────────────────┐
│ STEP 4: MCP Server Receives Request                          │
└──────────────────────────────────────────────────────────────┘

Server-side processing:

1. Parse JSON-RPC message ✓
2. Validate method: "tools/call" ✓
3. Find tool: "search_products" ✓
4. Validate arguments against schema ✓
5. Execute tool function
                    ↓

┌──────────────────────────────────────────────────────────────┐
│ STEP 5: Tool Execution                                       │
└──────────────────────────────────────────────────────────────┘

@app.tool()
async def search_products(query: str, max_price: float):
    # Connect to database
    conn = sqlite3.connect('products.db')
    
    # Build SQL
    sql = """
        SELECT title, price, category, rating
        FROM products
        WHERE category = 'Computers'
          AND title LIKE ?
          AND price <= ?
        ORDER BY rating DESC, price ASC
        LIMIT 5
    """
    
    # Execute
    results = conn.execute(sql, (f'%{query}%', max_price)).fetchall()
    
    # Format response
    formatted = []
    for row in results:
        formatted.append(
            f"• {row[0]}: ${row[1]} (Rating: {row[3]}/5)"
        )
    
    return "\n".join(formatted)

Execution result:
"• Dell XPS 15: $1799.99 (Rating: 4.6/5)
 • MacBook Pro M3: $2499.99 (Rating: 4.9/5)"
                    ↓

┌──────────────────────────────────────────────────────────────┐
│ STEP 6: MCP Server Response                                  │
└──────────────────────────────────────────────────────────────┘

{
  "jsonrpc": "2.0",
  "id": "req-001",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "• Dell XPS 15: $1799.99 (Rating: 4.6/5)"
      }
    ],
    "isError": false
  }
}
                    ↓
              [Transport Layer]
                    ↓

┌──────────────────────────────────────────────────────────────┐
│ STEP 7: LLM Receives Tool Result                             │
└──────────────────────────────────────────────────────────────┘

Claude processes the tool result:

Internal LLM Reasoning:
┌─────────────────────────────────────────────────┐
│ Tool returned: Found 1 laptop                   │
│   - Dell XPS 15: $1799.99, 4.6/5 rating        │
│                                                 │
│ MacBook appears but exceeds budget ($2499)      │
│                                                 │
│ User asked for laptops under $2000              │
│ Only Dell XPS qualifies                        │
│                                                 │
│ Should I provide more info?                     │
│ Should I suggest alternatives?                  │
│                                                 │
│ Decision: Inform user of result + note about    │
│ MacBook being over budget                       │
└─────────────────────────────────────────────────┘
                    ↓

┌──────────────────────────────────────────────────────────────┐
│ STEP 8: Generate Final Response                              │
└──────────────────────────────────────────────────────────────┘

Claude generates natural language response:

"I found a great gaming laptop under $2000:

**Dell XPS 15** - $1799.99
• Rating: 4.6/5 ⭐
• Premium Windows laptop
• Great for gaming and professional work

Note: The MacBook Pro M3 has a higher rating (4.9/5) 
but exceeds your budget at $2499.99. Would you like me 
to show you more options or provide details about the 
Dell XPS 15?"
                    ↓

┌──────────────────────────────────────────────────────────────┐
│ STEP 9: Display to User                                      │
└──────────────────────────────────────────────────────────────┘

User sees the formatted response in chat interface
```

---

### Multi-Turn Conversation

```
Turn 1:
User: "Find gaming laptops under $2000"
  ↓ [MCP: search_products] ↓
Claude: "Found Dell XPS 15 at $1799..."

Turn 2:
User: "What's the weather in Seattle today?"
  ↓ [MCP: get_weather] ↓
Claude: "Seattle: 15°C, Partly cloudy..."

Turn 3:
User: "Great, I'll buy the laptop. Send me a reminder email."
  ↓ [LLM checks conversation history] ↓
  ↓ [Knows "the laptop" = Dell XPS 15] ↓
  ↓ [MCP: send_email with laptop details] ↓
Claude: "Email reminder sent about Dell XPS 15!"
```

**Key Point:** LLM maintains context across MCP calls!

---

## 📨 Message Types & Structure {#messages}

### Detailed Message Anatomy

#### Tool Call Request (Complete)

```json
{
  // ============= STANDARD JSON-RPC FIELDS =============
  "jsonrpc": "2.0",              // Protocol version
  "id": "uuid-1234-5678",        // Unique request ID
  "method": "tools/call",        // MCP method
  
  // ============= MCP-SPECIFIC PARAMETERS =============
  "params": {
    "name": "search_products",   // Tool identifier
    
    "arguments": {               // Tool-specific inputs
      "query": "laptop",
      "max_price": 2000,
      "category": "Computers",
      "min_rating": 4.5
    },
    
    // Optional metadata
    "_meta": {
      "requestId": "user-req-789",
      "timestamp": "2024-02-03T10:30:00Z",
      "clientVersion": "1.0.0"
    }
  }
}
```

---

#### Tool Response (Complete)

```json
{
  // ============= STANDARD JSON-RPC FIELDS =============
  "jsonrpc": "2.0",
  "id": "uuid-1234-5678",        // Matches request ID
  
  // ============= RESULT (SUCCESS) =============
  "result": {
    // Content array (can have multiple content blocks)
    "content": [
      {
        "type": "text",          // Content type
        "text": "Found 2 laptops matching criteria:\n\n1. Dell XPS 15..."
      },
      {
        "type": "image",         // Can include images
        "data": "base64-encoded-image-data",
        "mimeType": "image/png"
      },
      {
        "type": "resource",      // Can reference resources
        "uri": "file:///tmp/results.json",
        "mimeType": "application/json"
      }
    ],
    
    // Error flag
    "isError": false,
    
    // Optional metadata
    "_meta": {
      "executionTime": 245,      // milliseconds
      "dataSource": "products.db",
      "rowsAffected": 2
    }
  }
}
```

---

#### Error Response (Complete)

```json
{
  "jsonrpc": "2.0",
  "id": "uuid-1234-5678",
  
  // ============= ERROR (FAILURE) =============
  "error": {
    "code": -32602,              // Standard JSON-RPC error code
    "message": "Invalid params", // Human-readable message
    
    // Detailed error information
    "data": {
      "field": "max_price",
      "reason": "Must be a positive number",
      "received": -100,
      "expected": "number > 0",
      
      // Stack trace (for debugging)
      "stack": "Error: Invalid params\n  at validateArgs...",
      
      // Suggestions
      "suggestions": [
        "Use a positive number for max_price",
        "Example: {\"max_price\": 2000}"
      ]
    }
  }
}
```

---

### Content Types

MCP supports multiple content types in responses:

#### 1. **Text Content**
```json
{
  "type": "text",
  "text": "Search found 5 products..."
}
```

#### 2. **Image Content**
```json
{
  "type": "image",
  "data": "base64-encoded-png-data",
  "mimeType": "image/png"
}
```

#### 3. **Resource Reference**
```json
{
  "type": "resource",
  "uri": "file:///path/to/data.json",
  "mimeType": "application/json"
}
```

#### 4. **Embedded Content**
```json
{
  "type": "embedded",
  "mimeType": "application/json",
  "content": {
    "products": [
      {"id": 1, "name": "Laptop", "price": 1799}
    ]
  }
}
```

---

## 🚀 Transport Layers {#transport}

### 1. Standard I/O (stdio) Transport

**Most common for local tools**

```
┌─────────────────┐         ┌─────────────────┐
│   MCP Client    │         │   MCP Server    │
│   (Claude.ai)   │         │   (Your tool)   │
│                 │         │                 │
│   Python/TS     │         │   Python/TS     │
└─────────────────┘         └─────────────────┘
        │                           │
        │  spawn subprocess         │
        │  ─────────────────────>   │
        │                           │
        │  stdin  (JSON-RPC)        │
        │  ─────────────────────>   │
        │                           │
        │  stdout (JSON-RPC)        │
        │  <─────────────────────   │
        │                           │
        │  stderr (logs/errors)     │
        │  <─────────────────────   │
        │                           │
```

**Implementation Example:**

**Client Side:**
```python
import subprocess
import json

# Start MCP server as subprocess
process = subprocess.Popen(
    ['python', 'mcp_server.py'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Send request via stdin
request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
}
process.stdin.write(json.dumps(request) + '\n')
process.stdin.flush()

# Read response from stdout
response_line = process.stdout.readline()
response = json.loads(response_line)
print(response)
```

**Server Side:**
```python
import sys
import json

def handle_request(request):
    if request['method'] == 'tools/list':
        return {
            "jsonrpc": "2.0",
            "id": request['id'],
            "result": {"tools": [...]}
        }

# Main loop: read from stdin, write to stdout
while True:
    line = sys.stdin.readline()
    if not line:
        break
    
    request = json.loads(line)
    response = handle_request(request)
    
    print(json.dumps(response), flush=True)
```

**Pros:**
- ✅ Simple process communication
- ✅ No network configuration needed
- ✅ Automatic process lifecycle management
- ✅ Secure (local only)

**Cons:**
- ❌ Local only (same machine)
- ❌ One client per server instance

---

### 2. HTTP Transport

**For remote/networked tools**

```
┌─────────────────┐                    ┌─────────────────┐
│   MCP Client    │                    │   MCP Server    │
│   (Your app)    │                    │   (Remote API)  │
└─────────────────┘                    └─────────────────┘
        │                                      │
        │  POST /mcp/tools/call               │
        │  Content-Type: application/json     │
        │  ──────────────────────────────────> │
        │                                      │
        │  {                                   │
        │    "jsonrpc": "2.0",                │
        │    "method": "tools/call",          │
        │    ...                              │
        │  }                                  │
        │                                      │
        │  HTTP/1.1 200 OK                    │
        │  Content-Type: application/json     │
        │  <────────────────────────────────── │
        │                                      │
        │  {                                   │
        │    "jsonrpc": "2.0",                │
        │    "result": {...}                  │
        │  }                                  │
        │                                      │
```

**Client Implementation:**
```python
import requests
import json

class MCPHttpClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.request_id = 0
    
    def call_tool(self, tool_name, arguments):
        self.request_id += 1
        
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = requests.post(
            f"{self.base_url}/mcp",
            json=request,
            headers={"Content-Type": "application/json"}
        )
        
        return response.json()

# Usage
client = MCPHttpClient("https://api.example.com")
result = client.call_tool("search_products", {
    "query": "laptop",
    "max_price": 2000
})
```

**Server Implementation (Flask):**
```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/mcp', methods=['POST'])
def mcp_endpoint():
    req = request.get_json()
    
    # Validate JSON-RPC
    if req.get('jsonrpc') != '2.0':
        return jsonify({
            "jsonrpc": "2.0",
            "id": req.get('id'),
            "error": {"code": -32600, "message": "Invalid Request"}
        }), 400
    
    # Route to method
    method = req.get('method')
    
    if method == 'tools/call':
        tool_name = req['params']['name']
        arguments = req['params']['arguments']
        
        # Execute tool
        result = execute_tool(tool_name, arguments)
        
        return jsonify({
            "jsonrpc": "2.0",
            "id": req['id'],
            "result": result
        })
    
    return jsonify({
        "jsonrpc": "2.0",
        "id": req.get('id'),
        "error": {"code": -32601, "message": "Method not found"}
    }), 404

if __name__ == '__main__':
    app.run(port=3000)
```

**Pros:**
- ✅ Works over network
- ✅ Standard HTTP infrastructure
- ✅ Easy to deploy
- ✅ Multiple clients supported

**Cons:**
- ❌ Requires web server
- ❌ Network latency
- ❌ Need authentication/security

---

### 3. WebSocket Transport

**For real-time bidirectional communication**

```
┌─────────────────┐                    ┌─────────────────┐
│   MCP Client    │                    │   MCP Server    │
└─────────────────┘                    └─────────────────┘
        │                                      │
        │  WebSocket Handshake                │
        │  ──────────────────────────────────> │
        │  <────────────────────────────────── │
        │       Connection Established         │
        │                                      │
        │  ════════════════════════════════════│
        │         Bidirectional Channel        │
        │  ════════════════════════════════════│
        │                                      │
        │  Request (JSON-RPC)                 │
        │  ──────────────────────────────────> │
        │                                      │
        │  Response (JSON-RPC)                │
        │  <────────────────────────────────── │
        │                                      │
        │  Notification (Progress)            │
        │  <────────────────────────────────── │
        │                                      │
        │  Another Request                    │
        │  ──────────────────────────────────> │
        │                                      │
```

**Client Implementation:**
```python
import asyncio
import websockets
import json

class MCPWebSocketClient:
    def __init__(self, url):
        self.url = url
        self.ws = None
        self.request_id = 0
        self.pending_requests = {}
    
    async def connect(self):
        self.ws = await websockets.connect(self.url)
        asyncio.create_task(self._listen())
    
    async def _listen(self):
        async for message in self.ws:
            data = json.loads(message)
            
            # Handle response
            if 'id' in data and data['id'] in self.pending_requests:
                future = self.pending_requests.pop(data['id'])
                future.set_result(data)
            
            # Handle notification
            elif 'method' in data:
                self._handle_notification(data)
    
    async def call_tool(self, tool_name, arguments):
        self.request_id += 1
        request_id = self.request_id
        
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        # Send request
        await self.ws.send(json.dumps(request))
        
        # Wait for response
        response = await future
        return response
    
    def _handle_notification(self, notification):
        # Handle server-initiated messages
        if notification['method'] == 'notifications/progress':
            print(f"Progress: {notification['params']['progress']}")

# Usage
async def main():
    client = MCPWebSocketClient("ws://localhost:3000/mcp")
    await client.connect()
    
    result = await client.call_tool("search_products", {
        "query": "laptop"
    })
    print(result)

asyncio.run(main())
```

**Server Implementation (websockets library):**
```python
import asyncio
import websockets
import json

connected_clients = set()

async def mcp_handler(websocket, path):
    # Register client
    connected_clients.add(websocket)
    
    try:
        async for message in websocket:
            request = json.loads(message)
            
            # Handle request
            if request['method'] == 'tools/call':
                # Execute tool
                result = await execute_tool(
                    request['params']['name'],
                    request['params']['arguments']
                )
                
                # Send progress notifications
                await websocket.send(json.dumps({
                    "jsonrpc": "2.0",
                    "method": "notifications/progress",
                    "params": {"progress": 0.5}
                }))
                
                # Send response
                response = {
                    "jsonrpc": "2.0",
                    "id": request['id'],
                    "result": result
                }
                await websocket.send(json.dumps(response))
    
    finally:
        connected_clients.remove(websocket)

# Start server
start_server = websockets.serve(mcp_handler, "localhost", 3000)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
```

**Pros:**
- ✅ Real-time bidirectional
- ✅ Server can push notifications
- ✅ Persistent connection
- ✅ Lower latency than HTTP

**Cons:**
- ❌ More complex implementation
- ❌ Connection state management
- ❌ Firewall/proxy issues

---

## 🔒 Security & Authentication {#security}

### Authentication Methods

#### 1. **API Key Authentication**

```json
// Request with API key
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_products",
    "arguments": {...}
  },
  "_auth": {
    "type": "api_key",
    "key": "sk-1234567890abcdef"
  }
}
```

**Server Validation:**
```python
def validate_api_key(request):
    auth = request.get('_auth', {})
    if auth.get('type') != 'api_key':
        raise AuthError("API key required")
    
    key = auth.get('key')
    if not is_valid_key(key):
        raise AuthError("Invalid API key")
    
    return get_user_from_key(key)
```

---

#### 2. **OAuth 2.0**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {...},
  "_auth": {
    "type": "oauth2",
    "access_token": "ya29.a0AfH6SMBx...",
    "token_type": "Bearer"
  }
}
```

---

#### 3. **HTTP Header Authentication (for HTTP transport)**

```python
headers = {
    "Authorization": "Bearer sk-1234567890",
    "Content-Type": "application/json"
}

response = requests.post(
    "https://api.example.com/mcp",
    json=request,
    headers=headers
)
```

---

### Permission System

```json
// Tool definition with permissions
{
  "name": "delete_product",
  "description": "Delete a product from database",
  "inputSchema": {...},
  "permissions": {
    "required": ["products:write", "products:delete"],
    "scope": "admin"
  }
}
```

**Server-side Check:**
```python
@app.tool()
async def delete_product(product_id: int):
    # Check permissions
    user = get_current_user()
    if not user.has_permission("products:delete"):
        raise PermissionError("Insufficient permissions")
    
    # Execute
    db.delete_product(product_id)
    return {"success": True}
```

---

### Rate Limiting

```python
from datetime import datetime, timedelta

rate_limits = {}

def check_rate_limit(user_id, limit=100, window=60):
    now = datetime.now()
    
    if user_id not in rate_limits:
        rate_limits[user_id] = []
    
    # Remove old requests
    rate_limits[user_id] = [
        req_time for req_time in rate_limits[user_id]
        if now - req_time < timedelta(seconds=window)
    ]
    
    # Check limit
    if len(rate_limits[user_id]) >= limit:
        raise RateLimitError(f"Rate limit exceeded: {limit} requests per {window}s")
    
    # Record request
    rate_limits[user_id].append(now)
```

---

## 💻 Real Implementation Examples {#examples}

### Complete MCP Server Example

```python
# ============================================
# complete_mcp_server.py
# Full-featured MCP server for shopping
# ============================================

import asyncio
import json
import sqlite3
from typing import Any, Dict, List
from datetime import datetime

class MCPServer:
    def __init__(self):
        self.tools = {}
        self.resources = {}
        self.db = sqlite3.connect('products.db')
    
    def tool(self, name: str = None, description: str = ""):
        """Decorator to register tools"""
        def decorator(func):
            tool_name = name or func.__name__
            self.tools[tool_name] = {
                "function": func,
                "description": description,
                "schema": self._generate_schema(func)
            }
            return func
        return decorator
    
    def _generate_schema(self, func):
        """Generate JSON schema from function signature"""
        import inspect
        sig = inspect.signature(func)
        
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            param_type = "string"  # Default
            if param.annotation == int:
                param_type = "integer"
            elif param.annotation == float:
                param_type = "number"
            elif param.annotation == bool:
                param_type = "boolean"
            
            properties[param_name] = {"type": param_type}
            
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    async def handle_request(self, request: Dict) -> Dict:
        """Handle incoming JSON-RPC request"""
        
        # Validate JSON-RPC
        if request.get('jsonrpc') != '2.0':
            return self._error_response(
                request.get('id'),
                -32600,
                "Invalid Request"
            )
        
        method = request.get('method')
        request_id = request.get('id')
        
        # Route to method handler
        if method == 'tools/list':
            return await self._handle_tools_list(request_id)
        elif method == 'tools/call':
            return await self._handle_tools_call(request_id, request.get('params', {}))
        elif method == 'resources/list':
            return await self._handle_resources_list(request_id)
        else:
            return self._error_response(
                request_id,
                -32601,
                f"Method not found: {method}"
            )
    
    async def _handle_tools_list(self, request_id):
        """Return list of available tools"""
        tools_list = []
        
        for name, tool in self.tools.items():
            tools_list.append({
                "name": name,
                "description": tool["description"],
                "inputSchema": tool["schema"]
            })
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools_list}
        }
    
    async def _handle_tools_call(self, request_id, params):
        """Execute a tool"""
        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        
        if tool_name not in self.tools:
            return self._error_response(
                request_id,
                -32601,
                f"Tool not found: {tool_name}"
            )
        
        try:
            # Execute tool function
            tool_func = self.tools[tool_name]["function"]
            result = await tool_func(self, **arguments)
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {"type": "text", "text": str(result)}
                    ],
                    "isError": False
                }
            }
        
        except Exception as e:
            return self._error_response(
                request_id,
                -32603,
                f"Tool execution error: {str(e)}"
            )
    
    async def _handle_resources_list(self, request_id):
        """Return list of available resources"""
        resources_list = [
            {
                "uri": "db://products/schema",
                "name": "Database Schema",
                "mimeType": "application/json"
            }
        ]
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"resources": resources_list}
        }
    
    def _error_response(self, request_id, code, message):
        """Generate error response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
    
    async def run_stdio(self):
        """Run server over stdio"""
        import sys
        
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                
                request = json.loads(line)
                response = await self.handle_request(request)
                
                print(json.dumps(response), flush=True)
            
            except Exception as e:
                error_response = self._error_response(
                    None,
                    -32700,
                    f"Parse error: {str(e)}"
                )
                print(json.dumps(error_response), flush=True)

# ============================================
# Register Tools
# ============================================

server = MCPServer()

@server.tool(
    name="search_products",
    description="Search for products in the database"
)
async def search_products(self, query: str, max_price: float = None):
    """Search products by query and optional price filter"""
    
    sql = "SELECT title, price, rating FROM products WHERE title LIKE ?"
    params = [f'%{query}%']
    
    if max_price is not None:
        sql += " AND price <= ?"
        params.append(max_price)
    
    sql += " ORDER BY rating DESC LIMIT 5"
    
    results = self.db.execute(sql, params).fetchall()
    
    if not results:
        return "No products found matching your criteria."
    
    output = []
    for title, price, rating in results:
        output.append(f"• {title}: ${price:.2f} (Rating: {rating}/5)")
    
    return "\n".join(output)

@server.tool(
    name="get_product_stats",
    description="Get statistics about products in database"
)
async def get_product_stats(self):
    """Get overall statistics"""
    
    stats = {}
    
    # Total products
    cursor = self.db.execute("SELECT COUNT(*) FROM products")
    stats['total_products'] = cursor.fetchone()[0]
    
    # Average price
    cursor = self.db.execute("SELECT AVG(price) FROM products")
    stats['average_price'] = round(cursor.fetchone()[0], 2)
    
    # Total categories
    cursor = self.db.execute("SELECT COUNT(DISTINCT category) FROM products")
    stats['total_categories'] = cursor.fetchone()[0]
    
    return json.dumps(stats, indent=2)

# ============================================
# Run Server
# ============================================

if __name__ == "__main__":
    asyncio.run(server.run_stdio())
```

---

### Complete MCP Client Example

```python
# ============================================
# complete_mcp_client.py
# Full-featured MCP client
# ============================================

import json
import subprocess
from typing import Dict, Any, List

class MCPClient:
    def __init__(self, server_command: List[str]):
        self.server_command = server_command
        self.process = None
        self.request_id = 0
        self.tools_cache = None
    
    def connect(self):
        """Start MCP server process"""
        self.process = subprocess.Popen(
            self.server_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
    
    def disconnect(self):
        """Stop MCP server process"""
        if self.process:
            self.process.terminate()
            self.process.wait()
    
    def _send_request(self, method: str, params: Dict = None) -> Dict:
        """Send JSON-RPC request to server"""
        self.request_id += 1
        
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method
        }
        
        if params:
            request["params"] = params
        
        # Send request
        self.process.stdin.write(json.dumps(request) + '\n')
        self.process.stdin.flush()
        
        # Read response
        response_line = self.process.stdout.readline()
        response = json.loads(response_line)
        
        # Check for errors
        if 'error' in response:
            raise MCPError(
                response['error']['code'],
                response['error']['message']
            )
        
        return response['result']
    
    def list_tools(self) -> List[Dict]:
        """Get list of available tools"""
        if self.tools_cache is None:
            result = self._send_request('tools/list')
            self.tools_cache = result['tools']
        return self.tools_cache
    
    def call_tool(self, name: str, arguments: Dict = None) -> Any:
        """Call a tool on the server"""
        params = {
            "name": name,
            "arguments": arguments or {}
        }
        
        result = self._send_request('tools/call', params)
        
        # Extract text content
        if 'content' in result and len(result['content']) > 0:
            return result['content'][0]['text']
        
        return result
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

class MCPError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f"MCP Error {code}: {message}")

# ============================================
# Usage Example
# ============================================

if __name__ == "__main__":
    # Connect to MCP server
    with MCPClient(['python', 'complete_mcp_server.py']) as client:
        
        # List available tools
        print("Available tools:")
        tools = client.list_tools()
        for tool in tools:
            print(f"  • {tool['name']}: {tool['description']}")
        
        print("\n" + "="*60 + "\n")
        
        # Search for products
        print("Searching for laptops under $2000:")
        result = client.call_tool('search_products', {
            'query': 'laptop',
            'max_price': 2000
        })
        print(result)
        
        print("\n" + "="*60 + "\n")
        
        # Get statistics
        print("Product statistics:")
        stats = client.call_tool('get_product_stats')
        print(stats)
```

---

## 🎯 Summary

### Key Takeaways

1. **Architecture**: Three-layer system (Client, Protocol, Server)
2. **Protocol**: JSON-RPC 2.0 based, simple request/response
3. **Transport**: Multiple options (stdio, HTTP, WebSocket)
4. **LLM Communication**: LLM decides tools → MCP executes → LLM formats results
5. **Security**: Authentication, permissions, rate limiting

### MCP vs Custom Integration

| Aspect | Custom Integration | MCP |
|--------|-------------------|-----|
| **Development Time** | High (unique each time) | Low (standardized) |
| **Compatibility** | Single AI | Multiple AIs |
| **Maintenance** | Complex | Simple |
| **Scalability** | Limited | High |
| **Security** | Custom implementation | Built-in patterns |

MCP provides a **standardized, secure, and scalable** way to extend AI capabilities!
