# OpenAI Tool Use API Emulator

This project provides a Flask-based server that emulates OpenAI's function calling/tool use API functionality through prompt engineering and code generation. It allows you to use language models that don't natively support tool use with the OpenAI tool use interface. Compatible with reasoning-focused models like QwQ and R1, as well as any general purpose model with coding ability but lacks native function calling abilities.

## Features

- 🔄 Drop-in replacement for OpenAI's chat completions API with tool use
- 🛠️ Supports multiple tool definitions using OpenAI's function schema
- 🔒 Safe code execution in isolated environments
- 📝 Automatic Pydantic model generation for parameter validation
- 🔍 Code extraction and validation
- 📊 Request/response logging
- 📡 Streaming support

## Installation

```bash
# Clone the repository
git clone [repository-url]

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Set the following environment variables:
```bash
DEEPSEEK_API_KEY=your_api_key_here  # If using DeepSeek
```

## Usage

1. Start the server:
```bash
python app.py
```

The server accepts the following command line arguments:
```bash
--api-key     API key for authentication (default: "lol")
--base-url    Base URL for the API (default: "http://0.0.0.0:4000/v1")
--port        Port to run the server on (default: 8001)
```

2. Make requests to the API endpoint:
```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:8001/v1",
    api_key="any_string"  # Not used but required
)

# Define your tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name"
                    }
                },
                "required": ["location"]
            }
        }
    }
]

# Make a request
response = client.chat.completions.create(
    model="any-model",  # Model name is passed through
    messages=[
        {"role": "user", "content": "What's the weather in London?"}
    ],
    tools=tools
)
```

## How It Works

1. **Request Processing**
   - Validates incoming requests against OpenAI's API schema
   - Processes and combines tool messages with user messages

2. **Code Generation**
   - Generates Pydantic models from tool definitions
   - Creates function stubs for each tool
   - Formats code with proper imports and structure

3. **Prompt Engineering**
   - Enhances system prompts with tool information
   - Guides the LLM to output valid Python code

4. **Code Execution**
   - Extracts code snippets from LLM responses
   - Validates tool calls against defined tools
   - Executes code in isolated Jupyter notebook environment

5. **Response Formatting**
   - Formats responses to match OpenAI's API structure
   - Supports both streaming and non-streaming responses

## Why Code-Based Tool Calling?

Recent research ([Executable Code Actions](https://huggingface.co/papers/2402.01030), [LLM Agents](https://huggingface.co/papers/2411.01747)) has demonstrated that having LLMs express tool calls through code patterns rather than JSON format leads to better performance. This project leverages Python code patterns with Pydantic type definitions and literal value assignments for tool calling, rather than the traditional JSON-based approach.

The key insight is that LLMs are better at working with code patterns they've seen in their training data:

- **Natural Pattern Recognition:** LLMs have seen countless examples of Python variable assignments and function calls in their training data
- **Type Safety:** Pydantic type definitions provide clear structure while staying in familiar Python syntax
- **Value Assignment:** Using Python's literal value assignment is more natural for LLMs than JSON key-value pairs
- **Static Analysis:** The code output can be parsed and validated using standard Python tooling

This approach solves a fundamental issue in the current tool use ecosystem. The traditional flow involves:
1. Writing Python functions with decorators
2. Serializing these to JSON schemas for the API
3. Having the LLM generate JSON
4. Converting JSON function calls into Python code for execution

Instead, we maintain code as the primary interface throughout the pipeline. While we still handle JSON for API compatibility, the LLM itself works purely with Python code patterns, eliminating unnecessary transformations and leveraging the model's training data more effectively.

This approach leverages the LLM's training on code patterns while maintaining a controlled, analyzable structure for tool use.
## API Compatibility Benefits

By maintaining compatibility with OpenAI's tool use API format, this project seamlessly integrates with existing AI tooling:

- **Drop-in Replacement:** Switch models without changing your application code
- **Tool Reusability:** Use tools built for OpenAI's API with any supported model
- **Type Safety:** Full Pydantic validation and type checking throughout the pipeline
- **Framework Support:** Works with major AI development frameworks

The project enables sophisticated agentic use cases through integration with popular AI development tools:

- **LangGraph:** Build complex multi-agent workflows and DAG-based reasoning chains
- **PydanticAI:** Agent framework by the Pydantic team for building production-grade AI applications with type safety and dependency injection
- **LangChain:** Compose modular AI applications with standardized components
- **Instructor:** Structure and validate LLM outputs with Pydantic schemas

The project integrates with popular AI development tools like LangChain for composable applications, LangGraph for multi-agent workflows, and Pydantic for type-safe development - enabling you to build sophisticated AI applications while maintaining compatibility with the broader ecosystem.

This compatibility layer allows you to leverage the growing ecosystem of AI tools while using your preferred language model.

## Security Considerations

WARNING: Current implementation has security limitations:

- Code execution in Jupyter notebooks still allows file I/O operations
- Import restrictions can be bypassed through certain Python features
- No memory/CPU usage limits on code execution
- No network access restrictions
- Temporary files may persist if cleanup fails
- Request logs could expose sensitive data

Use caution when deploying in production environments. Additional security measures recommended:

- Run in containerized environment with strict resource limits
- Implement proper authentication and rate limiting
- Add comprehensive input validation
- Consider alternatives to direct code execution

## Limitations

- Relies on LLM's ability to generate valid Python code
- Tool execution is synchronous
- Limited error recovery options
- May require more prompt engineering for complex tools

## License

[License to come]

## Acknowledgments

- OpenAI for the original API design
- Pydantic for data validation
- Flask for the web framework