from flask import Flask, Response, request, jsonify
import json
import logging
import uuid
from openai import OpenAI
from utils.code_generation import get_code, get_fn_names, get_fn_call_example_str, is_valid_tool_call
from utils.code_execution import extract_code, evaluate_python_code
from models.schemas import Message, OpenAIRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('tool_call_code_execution')

# Initialize Flask app and global variables
app = Flask(__name__)
model = "deepseek-reasoner"
system_fingerprint = str(uuid.uuid4())

# Initialize OpenAI client with default values
client = None

def configure_client(api_key: str, base_url: str):
    """Configure the OpenAI client with the provided credentials"""
    global client
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    logger.info(f"Configured OpenAI client with base URL: {base_url}")

# Set default configuration
configure_client("YOUR_API_KEY", "http://0.0.0.0:4000/v1")

@app.route("/chat/completions", methods=["POST"])
def chat():
    """
    Main endpoint that emulates OpenAI's chat completions API with tool use
    
    Process:
    1. Validates and processes incoming request
    2. Reformats tool messages into user messages
    3. Generates code for tool definitions
    4. Creates enhanced system prompt with tool information
    5. Makes API call to underlying LLM
    6. Extracts and executes tool calls from response
    7. Returns formatted response matching OpenAI's API
    """
    # Log incoming requests
    request_data = request.get_json()
    with open('requests.jsonl', 'a') as f:
        json.dump(request_data, f)
        f.write('\n')
    
    chat = OpenAIRequest(**request.get_json())

    # Process and combine tool messages with user messages
    if chat.messages:
        tool_messages = []
        new_messages = []
        
        for message in chat.messages:
            if message.role == "tool":
                tool_messages.append(f"Tool message received - Function: {message.name}, Result: {message.content}")
            else:
                # Combine accumulated tool messages into user message
                if tool_messages:
                    combined_content = "\n".join(tool_messages)
                    if new_messages and new_messages[-1].role == "user":
                        new_messages[-1].content += "\n\n" + combined_content
                    else:
                        new_messages.append(Message(role="user", content=combined_content))
                    tool_messages = []
                
                new_messages.append(message)
        
        # Handle any remaining tool messages
        if tool_messages:
            combined_content = "\n".join(tool_messages)
            new_messages.append(Message(role="user", content=combined_content))
            
        chat.messages = new_messages

    # Generate code for tools and create enhanced system prompt
    code = get_code(chat.tools)
    
    # Create example snippets for tool usage
    dblnl = "\n\nand/or\n\n"
    snippets = [f'```python\n{get_fn_call_example_str(tool["function"])}\n```' for tool in chat.tools]

    # Build system prompt with tool information
    system_prompt_tool_suffix = f"""You have access to the following function and model:

```python
{code}
```

After analyzing the user request that will follow, you can call any of {{{get_fn_names(chat.tools)}}} function with your evaluation. For each function call you decide to make, format your response as a Python code block using triple backticks containing the function call. Be logical and smart about which function call you make. Each function call you make will be executed and the result shown to you in this thread. It is up to you to call the functions in any order to best accomplish the task you've been given. If any function call you want to make necessitates the use of an output of another function, you can call the other function first and only that one. Or you can call many functions to get results in parallel in next message in this thread. The functions you decide to call now will have an impact on the planning and orchestration of the task. Take time to reflect on proper order of function calls and only do the ones that don't have unawaited dependencies.

DO NOT MAKE UP FIELDS NOT DEFINED IN THE MODEL.
DO NOT ASSIGN VARIABLES, DO NOT PRINT, DO NOT DO ANYTHING WITH SIDE EFFECTS. PURE CODE ONLY. SIMPLY CALL THE FUNCTIONS WITH LITTERALS WITHOUT CAPTURING THE OUTPUT. EXAMPLES BELOW.

Function call syntax and output formatting examples:
{dblnl.join(snippets)}

The arguments you call the functions with must be relevant with the provided context."""
    
    try:
        # Prepare messages with enhanced system prompt
        messages = []
        system_message_found = False
        
        # Check if there's a system message and append suffix to it
        for m in chat.messages:
            content = m.content
            if m.role == "system":
                content += f"\n\n{system_prompt_tool_suffix}"
                system_message_found = True
            messages.append({"role": m.role, "content": content})
        
        # If no system message found, create one and insert at beginning
        if not system_message_found:
            messages.insert(0, {
                "role": "system",
                "content": system_prompt_tool_suffix
            })

        # Make API call to underlying LLM
        params = {
            'temperature': chat.temperature,
            'top_p': chat.top_p,
            'presence_penalty': chat.presence_penalty, 
            'frequency_penalty': chat.frequency_penalty,
            'stream': chat.stream,
            'tools': None
        }
        params = {k: v for k, v in params.items() if v is not None}

        response = client.chat.completions.create(
            model=chat.model,
            messages=messages,
            **params
        )

        # Extract and process tool calls from response
        code_snippets = extract_code(response.choices[0].message.content)
        tool_calls = []
        filled_index = 0

        for code_snippet in code_snippets:
            is_valid = is_valid_tool_call(code_snippet[1], chat.tools)

            if is_valid:
                # Generate and execute code for tool call
                code_to_execute = (get_code(chat.tools, return_args=True) +  "\n\n" + code_snippet[1]).strip() + '.model_dump_json()'
                
                # Log code execution for debugging
                logger.debug(f"Code to execute:\n{code_to_execute}")

                # Format tool call in OpenAI's structure
                tool_calls.append({
                    "id": "call_" + uuid.uuid4().hex,
                    "index": filled_index,
                    "type": "function",
                    "function": {
                        "name": is_valid, 
                        "arguments": eval(evaluate_python_code(code_to_execute, authorized_imports=['pydantic', '__future__']))
                    }
                })

                filled_index += 1

        print("messages", messages)

        print("response", response.choices[0].message.content)
        print("---")
        print("tool_calls", tool_calls)

        # Add tool calls to response
        response.choices[0].message.tool_calls = tool_calls

        # Handle streaming vs non-streaming response
        if chat.stream:
            def generate():
                try:
                    for chunk in response:
                        yield f"data: {json.dumps(chunk.model_dump())}\n\n"
                except Exception as e:
                    logger.error(f"Streaming error: {str(e)}")
                    raise
            
            return Response(generate(), mimetype="text/event-stream")
        else:
            return jsonify(response.model_dump())
            
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=False, port=8001) 