# 🔌 Provider API Reference — Sample Requests & Responses

> Reference cho Codex khi implement `pio_lab/providers/adapters/*.py` (M3-M4).
>
> **Tất cả response đã được normalize** thông qua adapter để Provider Router work đồng nhất.
> Đây là format **RAW** từ provider — adapter của bạn có nhiệm vụ convert sang format chuẩn.

---

## 📐 Normalized Response Format (output của adapter)

Mỗi provider adapter PHẢI return dict theo format này (định nghĩa ở `pio_lab/providers/adapters/base_provider.py`):

```python
{
    "content": [                    # list of content blocks
        {"type": "text", "text": "..."},
        {"type": "tool_use", "id": "...", "name": "...", "input": {...}},
    ],
    "stop_reason": "end_turn" | "tool_use" | "max_tokens" | "error",
    "usage": {
        "input_tokens": 150,
        "output_tokens": 230,
    },
    "model": "claude-sonnet-4-6",
    "provider": "claude",
    "raw": <original_response_object>,  # giữ nguyên để debug
}
```

**Tại sao normalize:** Mỗi provider có schema khác nhau. Worker code chỉ làm việc với normalized format → swap provider không phá worker.

---

## 🟣 1. Anthropic Claude

### Request format

```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=api_key)

response = await client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    system="Bạn là Worker chuyên frontend...",
    messages=[
        {"role": "user", "content": "Viết React component login form"},
    ],
    tools=[
        {
            "name": "file_write",
            "description": "Write content to a file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        }
    ],
)
```

### Raw response (text only)

```python
Message(
    id='msg_01XYZ...',
    type='message',
    role='assistant',
    content=[
        TextBlock(type='text', text='Đây là component login form...')
    ],
    model='claude-sonnet-4-6',
    stop_reason='end_turn',
    stop_sequence=None,
    usage=Usage(input_tokens=125, output_tokens=342)
)
```

### Raw response (tool use)

```python
Message(
    content=[
        TextBlock(type='text', text='Tôi sẽ viết file LoginForm.tsx'),
        ToolUseBlock(
            type='tool_use',
            id='toolu_01ABC',
            name='file_write',
            input={'path': 'src/LoginForm.tsx', 'content': 'export default function...'}
        )
    ],
    stop_reason='tool_use',
    usage=Usage(input_tokens=200, output_tokens=450)
)
```

### Multi-turn với tool result

```python
messages=[
    {"role": "user", "content": "Viết LoginForm.tsx"},
    {"role": "assistant", "content": [
        {"type": "text", "text": "Tôi sẽ viết..."},
        {"type": "tool_use", "id": "toolu_01ABC", "name": "file_write", "input": {...}},
    ]},
    {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "toolu_01ABC", "content": "File written: src/LoginForm.tsx"},
    ]},
]
```

### Errors

```python
# Quota exhausted
anthropic.RateLimitError(
    message='rate_limit_error: Number of request tokens has exceeded...',
    status_code=429,
)

# Invalid key
anthropic.AuthenticationError(
    message='invalid x-api-key',
    status_code=401,
)

# Model overloaded
anthropic.APIStatusError(
    status_code=529,
    message='Overloaded',
)
```

### Adapter implementation hint

```python
async def complete(self, account, model, messages, tools=None, **kwargs):
    api_key = os.environ[account.env_key]
    client = AsyncAnthropic(api_key=api_key, timeout=60.0)

    # Extract system from messages if present
    system = kwargs.get("system", "")
    user_msgs = [m for m in messages if m["role"] != "system"]

    # Convert tools to Claude format if needed
    claude_tools = self._convert_tools(tools) if tools else []

    try:
        response = await client.messages.create(
            model=model,
            max_tokens=kwargs.get("max_tokens", 4096),
            system=system,
            messages=user_msgs,
            tools=claude_tools,
        )
    except anthropic.RateLimitError as e:
        raise QuotaExceededError(provider="claude", account=account.id) from e

    # Normalize content
    content = []
    for block in response.content:
        if block.type == "text":
            content.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            content.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })

    return {
        "content": content,
        "stop_reason": response.stop_reason,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
        "model": model,
        "provider": "claude",
        "raw": response,
    }
```

---

## 🟢 2. OpenAI Codex / GPT

### Request format

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=api_key)

response = await client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "Bạn là backend worker..."},
        {"role": "user", "content": "Viết FastAPI endpoint POST /users"},
    ],
    tools=[
        {
            "type": "function",
            "function": {
                "name": "file_write",
                "description": "Write content to a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
        }
    ],
)
```

### Raw response (text)

```python
ChatCompletion(
    id='chatcmpl-9XYZ',
    object='chat.completion',
    model='gpt-4o-2024-05-13',
    choices=[
        Choice(
            index=0,
            message=ChatCompletionMessage(
                role='assistant',
                content='Đây là FastAPI endpoint:\n\n```python\n@router.post("/users")...```',
                tool_calls=None,
            ),
            finish_reason='stop',
        )
    ],
    usage=CompletionUsage(prompt_tokens=87, completion_tokens=212, total_tokens=299),
)
```

### Raw response (tool call)

```python
ChatCompletionMessage(
    role='assistant',
    content=None,                          # often None when calling tool
    tool_calls=[
        ChatCompletionMessageToolCall(
            id='call_abc123',
            type='function',
            function=Function(
                name='file_write',
                arguments='{"path": "users.py", "content": "@router.post..."}'  # JSON string!
            )
        )
    ],
    finish_reason='tool_calls',
)
```

### Multi-turn với tool result

```python
messages=[
    {"role": "user", "content": "Viết file users.py"},
    {"role": "assistant", "content": None, "tool_calls": [
        {"id": "call_abc", "type": "function", "function": {"name": "file_write", "arguments": "{...}"}}
    ]},
    {"role": "tool", "tool_call_id": "call_abc", "content": "Written successfully"},
]
```

### Errors

```python
# Quota
openai.RateLimitError(
    status_code=429,
    body={'error': {'message': 'You exceeded your current quota...', 'type': 'insufficient_quota'}}
)

# Invalid key
openai.AuthenticationError(
    status_code=401,
    body={'error': {'message': 'Incorrect API key provided...'}}
)
```

### Khác biệt quan trọng vs Claude

- `tool_calls` thay vì `tool_use` blocks
- `arguments` là **JSON string**, không phải dict — phải `json.loads()` trong adapter
- Role `tool` cho tool result (không phải `user`)
- `system` message là role trong messages list (Claude tách riêng)

---

## 🔵 3. Google Gemini

### Request format

```python
import google.generativeai as genai

genai.configure(api_key=api_key)

model = genai.GenerativeModel(
    model_name="gemini-2.0-pro",
    system_instruction="Bạn là content writer...",
)

response = await model.generate_content_async(
    "Viết blog post 500 từ về adaptive optics",
    tools=[
        genai.protos.Tool(
            function_declarations=[
                genai.protos.FunctionDeclaration(
                    name="file_write",
                    description="Write content to a file",
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            "path": genai.protos.Schema(type=genai.protos.Type.STRING),
                            "content": genai.protos.Schema(type=genai.protos.Type.STRING),
                        },
                        required=["path", "content"],
                    ),
                )
            ]
        )
    ],
)
```

### Raw response (text)

```python
GenerateContentResponse(
    candidates=[
        Candidate(
            content=Content(
                parts=[
                    Part(text='Adaptive optics là kỹ thuật...')
                ],
                role='model',
            ),
            finish_reason=FinishReason.STOP,
        )
    ],
    usage_metadata=UsageMetadata(
        prompt_token_count=12,
        candidates_token_count=487,
        total_token_count=499,
    ),
)

# Convenience accessor
response.text  # → "Adaptive optics là kỹ thuật..."
```

### Raw response (function call)

```python
Part(
    function_call=FunctionCall(
        name='file_write',
        args={
            'path': 'blog/adaptive_optics.md',
            'content': '# Adaptive Optics\n\n...',
        }
    )
)
```

### Multi-turn

```python
chat = model.start_chat(history=[])
response1 = await chat.send_message_async("Viết blog post")
response2 = await chat.send_message_async(
    genai.protos.Content(
        parts=[genai.protos.Part(function_response=genai.protos.FunctionResponse(
            name='file_write',
            response={'result': 'success'},
        ))],
        role='function',
    )
)
```

### Errors

```python
google.api_core.exceptions.ResourceExhausted(
    "429 Quota exceeded for quota metric..."
)
google.api_core.exceptions.PermissionDenied(
    "403 API key not valid..."
)
```

### Khác biệt quan trọng

- Schema dùng protobuf objects (verbose hơn)
- `args` là dict (không phải JSON string như OpenAI)
- Role: `user` / `model` / `function` (không phải `assistant`/`tool`)
- Token count field tên khác: `prompt_token_count` thay vì `input_tokens`

---

## 🔷 4. DeepSeek

### Request format (OpenAI-compatible API)

```python
from openai import AsyncOpenAI

# DeepSeek dùng OpenAI SDK với base_url custom
client = AsyncOpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com/v1",
)

response = await client.chat.completions.create(
    model="deepseek-coder",  # hoặc "deepseek-chat"
    messages=[
        {"role": "system", "content": "Bạn là backend worker..."},
        {"role": "user", "content": "Optimize this SQL query: SELECT * FROM users"},
    ],
    tools=[...],  # cùng format OpenAI
)
```

### Response format

**Hoàn toàn giống OpenAI** — tận dụng được code của Codex adapter.

```python
ChatCompletion(
    id='chatcmpl-...',
    model='deepseek-coder',
    choices=[Choice(message=ChatCompletionMessage(...), ...)],
    usage=CompletionUsage(prompt_tokens=..., completion_tokens=...),
)
```

### Models available

- `deepseek-chat` — general purpose
- `deepseek-coder` — code-specialized (recommend cho CODER department)
- `deepseek-reasoner` — chain-of-thought (recommend cho QA department)

### Adapter tip

DeepSeek adapter có thể **kế thừa từ Codex adapter** chỉ override `base_url`:

```python
class DeepSeekProvider(CodexProvider):
    name = "deepseek"

    def _create_client(self, api_key: str) -> AsyncOpenAI:
        return AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1",
            timeout=60.0,
        )
```

---

## 🟠 5. Ollama (Local AI qua Tailscale)

### Request format

```python
from ollama import AsyncClient

# OLLAMA_HOST trong .env trỏ tới Tailscale IP
client = AsyncClient(host=os.environ["OLLAMA_HOST"])  # vd: http://100.64.10.5:11434

response = await client.chat(
    model="qwen2.5-coder:32b",  # hoặc "gpt-oss-20b", "llama3.1:70b"
    messages=[
        {"role": "system", "content": "Bạn là backend worker..."},
        {"role": "user", "content": "Viết FastAPI endpoint"},
    ],
    tools=[
        {
            "type": "function",
            "function": {
                "name": "file_write",
                "description": "...",
                "parameters": {...},
            }
        }
    ],
    options={
        "temperature": 0.7,
        "num_ctx": 8192,
    },
)
```

### Raw response (text)

```python
{
    'model': 'qwen2.5-coder:32b',
    'created_at': '2026-05-04T08:30:00Z',
    'message': {
        'role': 'assistant',
        'content': 'Đây là FastAPI endpoint:\n```python\n...```',
    },
    'done_reason': 'stop',
    'done': True,
    'total_duration': 5234567890,    # nanoseconds
    'load_duration': 234567890,
    'prompt_eval_count': 87,         # input tokens
    'prompt_eval_duration': 1234567,
    'eval_count': 245,                # output tokens
    'eval_duration': 4000000000,
}
```

### Raw response (tool call) — only models that support it

```python
{
    'message': {
        'role': 'assistant',
        'content': '',
        'tool_calls': [
            {
                'function': {
                    'name': 'file_write',
                    'arguments': {'path': 'main.py', 'content': '...'},  # đã parse, không phải string!
                }
            }
        ]
    },
    'done_reason': 'stop',
}
```

### Errors

```python
# Connection refused (Ollama not running / Tailscale down)
httpx.ConnectError("All connection attempts failed")

# Model not pulled
ollama.ResponseError("model 'unknown:latest' not found, try pulling it first")

# Out of memory (model too large)
ollama.ResponseError("CUDA out of memory")
```

### Khác biệt CRITICAL

1. **Tool calling support phụ thuộc model:**
   - `qwen2.5-coder:32b` ✓ tốt
   - `llama3.1:70b` ✓ tốt
   - `gpt-oss-20b` ⚠️ partial (có thể không return tool_calls đúng format)
   - **Strategy:** test với simple tool trước, fallback sang prompt-based parsing nếu cần

2. **Token count field khác:**
   - `prompt_eval_count` (Ollama) = `prompt_tokens` (OpenAI) = `input_tokens` (Claude)
   - `eval_count` (Ollama) = `completion_tokens` = `output_tokens`

3. **Latency:** lần gọi đầu tiên rất chậm (load model vào RAM/VRAM). Đặt timeout 90s+ cho first request.

4. **Streaming:** mặc định nếu set `stream=True`, return generator. Phase 1 dùng `stream=False`.

### Adapter implementation hint

```python
class OllamaProvider(BaseProvider):
    name = "ollama"

    def __init__(self) -> None:
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    async def complete(self, account, model, messages, tools=None, **kwargs):
        from ollama import AsyncClient

        client = AsyncClient(host=self.host, timeout=90.0)

        try:
            response = await client.chat(
                model=model,
                messages=messages,
                tools=tools or [],
                options={"temperature": kwargs.get("temperature", 0.7)},
            )
        except httpx.ConnectError as e:
            raise ProviderUnavailableError("Ollama unreachable via Tailscale") from e

        # Normalize content
        message = response["message"]
        content = []
        if message.get("content"):
            content.append({"type": "text", "text": message["content"]})
        for tc in message.get("tool_calls", []) or []:
            content.append({
                "type": "tool_use",
                "id": f"ollama_tc_{uuid.uuid4().hex[:8]}",  # Ollama không tự gen ID
                "name": tc["function"]["name"],
                "input": tc["function"]["arguments"],
            })

        return {
            "content": content,
            "stop_reason": response.get("done_reason", "stop"),
            "usage": {
                "input_tokens": response.get("prompt_eval_count", 0),
                "output_tokens": response.get("eval_count", 0),
            },
            "model": model,
            "provider": "ollama",
            "raw": response,
        }
```

---

## 📊 Comparison Cheat Sheet

| Field | Claude | OpenAI/Codex/DeepSeek | Gemini | Ollama |
|---|---|---|---|---|
| SDK | `anthropic` | `openai` | `google-generativeai` | `ollama` |
| System prompt | Top-level `system=` | Role `system` in messages | `system_instruction=` | Role `system` in messages |
| Tool format | `input_schema` (JSON Schema) | `function.parameters` | protobuf Schema | OpenAI-like |
| Tool result | `{"type":"tool_result","tool_use_id":"...","content":"..."}` | `{"role":"tool","tool_call_id":"...","content":"..."}` | `function_response` Part | OpenAI-like |
| Tool call ID | `id` in tool_use block | `id` in tool_call | (no ID, must gen) | (no ID, must gen) |
| Tool args | dict | **JSON string** (parse it!) | dict | dict |
| Input tokens field | `usage.input_tokens` | `usage.prompt_tokens` | `usage_metadata.prompt_token_count` | `prompt_eval_count` |
| Quota error | `RateLimitError` | `RateLimitError` | `ResourceExhausted` | (no quota — local) |
| Streaming default | `False` | `False` | `False` | `False` |

---

## 🧪 Quick Smoke Test khi implement xong adapter

Tạo `scripts/smoke_provider.py`:

```python
"""Smoke test: gọi 1 simple message qua mỗi provider."""
import asyncio
from pio_lab.providers.router import ProviderRouter

async def main():
    router = ProviderRouter()
    router.load()

    test_messages = [{"role": "user", "content": "Say 'Pio_lab works!' and nothing else."}]

    for routing_key in [
        "chief_of_staff",
        "coder.frontend",
        "coder.backend",
        "research.optics",
        "media.content",
        "qa.qa_reviewer",
    ]:
        try:
            response = await router.call(routing_key, test_messages)
            text = response["content"][0]["text"]
            print(f"✓ {routing_key:30s} → {text[:60]}")
        except Exception as e:
            print(f"✗ {routing_key:30s} → ERROR: {e}")

asyncio.run(main())
```

Run: `python scripts/smoke_provider.py`

Tất cả routing key phải work với ít nhất 1 provider trong fallback chain.

---

## 🔗 Documentation Links

- Anthropic: https://docs.anthropic.com/en/api/messages
- OpenAI: https://platform.openai.com/docs/api-reference/chat
- Google Gemini: https://ai.google.dev/gemini-api/docs
- DeepSeek: https://api-docs.deepseek.com
- Ollama: https://github.com/ollama/ollama/blob/main/docs/api.md
- Ollama Python: https://github.com/ollama/ollama-python

---

*Update khi có provider mới hoặc API thay đổi.*
