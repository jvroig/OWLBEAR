# inference/inference.py
import os
import json
import time
import yaml
import logging
import sys
import os
from . import tools_lib

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import event system
from events import (
    emitter,
    EVENT_TOOL_CALL_START,
    EVENT_TOOL_CALL_END,
    EVENT_ERROR
)

from http import HTTPStatus
from openai import OpenAI
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("workflow-engine.inference")

from dotenv import load_dotenv
load_dotenv()

# GLOBAL ENDPOINT SETTINGS
# These are used for experts that don't define their own.
# Load from endpoint_config.yaml
config_path = os.path.join(os.path.dirname(__file__), '..', 'endpoint_config.yaml')

with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Get values from config
# Get the first endpoint from the list if it exists, otherwise use the top-level config
if "Endpoints" in config and isinstance(config["Endpoints"], list) and len(config["Endpoints"]) > 0:
    first_endpoint = config["Endpoints"][0]
    api_key_env_name = first_endpoint.get('ApiKey')
    base_url = first_endpoint.get('Host')
    model = first_endpoint.get('Model')
else:
    logger.error("Improperly configured endpoint_config.yaml!")
    exit()

def call_agent(expert: str, prompt: str) -> dict:
    """
    Call an LLM expert with the given prompt.
    
    Args:
        expert: The identifier of the expert to call
        prompt: The full prompt text to send to the expert
        
    Returns:
        dict: Dictionary containing history (full conversation) and final_answer
    """
    logger.info(f"Calling expert: {expert} with prompt length: {len(prompt)}")
    
    expert_data = get_expert(expert)
    messages = format_messages(expert_data, prompt)

    # Get the streaming generator
    response_generator = inference_loop(expert_data, messages)
    
    # Process the streaming response
    conversation_history = []
    
    # Add initial user query - with role first
    conversation_history.append({
        "role": "user",
        "message": prompt
    })
    
    current_assistant_content = ""
    
    for chunk in response_generator:
        try:
            # Parse the JSON chunk
            chunk_data = json.loads(chunk.strip())
            
            # If it's an assistant content chunk, accumulate it
            if chunk_data.get('role') == 'assistant' and chunk_data.get('type') == 'chunk':
                current_assistant_content += chunk_data.get('content', '')
                
            # If it's a completion signal, add the accumulated assistant content to history
            if chunk_data.get('role') == 'assistant' and chunk_data.get('type') == 'done':
                if current_assistant_content:
                    conversation_history.append({
                        "role": "assistant",
                        "message": current_assistant_content
                    })
                    current_assistant_content = ""
                    
            # Handle tool calls
            if chunk_data.get('role') == 'tool_call':
                conversation_history.append({
                    "role": "tool",
                    "message": chunk_data.get('content', '')
                })
                logger.info(f"Tool call result: {chunk_data.get('content')}")
                
        except json.JSONDecodeError:
            logger.error(f"Failed to parse chunk: {chunk}")
    
    # The final_answer is the last assistant message in the history
    final_answer = ""
    for entry in reversed(conversation_history):
        if entry["role"] == "assistant":
            final_answer = entry["message"]
            break
            
    logger.info(f"FULL HISTORY: {conversation_history}")
    logger.info(f"FINAL ANSWER: {final_answer}")
    
    return {
        "history": conversation_history,
        "final_answer": final_answer
    }



def inference_loop(expert_data, messages):
    # Get global variables or override with expert-specific values if provided
    current_api_key = expert_data.get("Endpoint", {}).get("ApiKey") or api_key_env_name
    current_base_url = expert_data.get("Endpoint", {}).get("Host") or base_url
    current_model = expert_data.get("Endpoint", {}).get("Model") or model

    logger.info(f"Endpoint to try: {current_base_url}")
    logger.info(f"Model to use: {current_model}")

    # Debugging (optional)
    api_key = os.getenv(current_api_key)
    if not api_key:
        raise EnvironmentError(f"Environment variable '{current_api_key}' not set.")

    while True:
        client = OpenAI(
            api_key=api_key,
            base_url=current_base_url
        )
        response = client.chat.completions.create(
            model=current_model,
            messages=messages,
            stream=True
        )
 

        assistant_response = ""

        # Iterate through the streaming response
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                # Get the text chunk
                content = chunk.choices[0].delta.content
                
                # Accumulate the full response
                assistant_response += content
                
                # Stream the chunk to the frontend
                yield json.dumps({'role': 'assistant', 'content': content, 'type': 'chunk'}) + "\n"

        # After streaming is complete, add the full response to messages
        messages.append({"role": "assistant", "content": assistant_response})

        # Send a completion signal
        yield json.dumps({'role': 'assistant', 'content': '', 'type': 'done'}) + "\n"


        occurrences = assistant_response.count("[[qwen-tool-start]]")
        if occurrences > 1:
            #Multiple tool calls are not allowed
            ToolErrorMsg="Tool Call Error: Multiple tool calls found. Please only use one tool at a time."
            yield json.dumps({'role': 'tool_call', 'content': ToolErrorMsg}) + "\n"

            messages.append({"role": "user", "content": ToolErrorMsg})
            print(ToolErrorMsg)
        elif occurrences == 1:
            tool_call_data = None
            try:
                tool_call_data = parse_tool_call(assistant_response)
            except:
                print(f"No valid tool call found")
                tool_message = f"Tool result: No valid tool call found. Please make sure tool request is valid JSON, and escape necessary characters. Try again with better-formatted JSON"
                messages.append({"role": "user", "content": tool_message})
                yield json.dumps({'role': 'tool_call', 'content': tool_message}) + "\n"

            if tool_call_data:
                # Stream the tool call message back to the frontend
                # yield json.dumps({'role': 'tool_call', 'content': f"Tool call: {tool_call_data}"}) + "\n"

                # Execute the tool with the provided parameters
                tool_name = tool_call_data["name"]
                tool_input = tool_call_data.get("input", {})
                print(f"Executing tool: {tool_name} with input: {tool_input}")
                
                # Emit tool call start event
                expert_id = expert_data.get("ExpertID", "unknown")
                emitter.emit_sync(EVENT_TOOL_CALL_START, 
                                 expert_id=expert_id,
                                 tool_name=tool_name,
                                 parameters=tool_input)
                
                try:
                    # Execute the tool
                    tool_result = execute_tool(tool_name, tool_input)
                    
                    # Emit tool call end event
                    emitter.emit_sync(EVENT_TOOL_CALL_END,
                                     expert_id=expert_id,
                                     tool_name=tool_name,
                                     parameters=tool_input,
                                     result=tool_result,
                                     success=True)
                except Exception as e:
                    # Emit tool call end event with error
                    error_msg = f"Error executing tool '{tool_name}': {str(e)}"
                    emitter.emit_sync(EVENT_TOOL_CALL_END,
                                     expert_id=expert_id,
                                     tool_name=tool_name,
                                     parameters=tool_input,
                                     result=error_msg,
                                     success=False,
                                     error=str(e))
                    
                    # Re-raise the exception
                    raise

                # Add the tool result as a "user" message in the conversation
                tool_message = f"Tool result: ```{tool_result}```"
                messages.append({"role": "user", "content": tool_message})
                print(f"Tool executed. Result: {tool_result}")

                # Stream the tool result back to the frontend
                yield json.dumps({'role': 'tool_call', 'content': tool_message}) + "\n"

        else:
            # If no tool call, terminate the loop
            break

def format_messages(expert_data, prompt):

    #FIXME: list_tools can be affected by "available_tools" list in experts config
    #   in order to limit the tools for particular experts
    available_tools = expert_data.get("ToolsAvailable", None)

    tools_available = tools_lib.list_tools(available_tools)
    if tools_available == "":
        system_prompt = expert_data["SystemPrompt"]
    else:
        tools_format = tools_lib.get_tools_format()
        print(tools_available)
        print(tools_format)
        system_prompt = f"""
You have the following tools available:
{tools_available}

{tools_format}

"""
        system_prompt = expert_data["SystemPrompt"] + system_prompt


    messages = []
    system_message = {"role": "system", "content": system_prompt}
    messages.insert(0, system_message)
    messages.insert(1,{"role": "user", "content": prompt} )

    logger.info(f"Messages sent: {messages}")
    return messages

def parse_tool_call(response):
    """
    Parses the tool call information from an LLM response.
    
    Args:
        response (str): The LLM's response containing the tool call.
        
    Returns:
        dict: A dictionary containing the tool name and input parameters.
              Example: {"name": "tool_name", "input": {"param1": "value1", "param2": "value2"}}
              
    Raises:
        ValueError: If the tool call format is invalid or cannot be parsed.
    """
    # Define markers for the tool call block
    start_marker = "[[qwen-tool-start]]"
    end_marker = "[[qwen-tool-end]]"
    
    try:
        # Extract the JSON block between the markers
        start_index = response.find(start_marker) + len(start_marker)
        end_index = response.find(end_marker)
        
        if start_index == -1 or end_index == -1:
            raise ValueError("Tool call markers not found in the response.")
        
        tool_call_block = response[start_index:end_index].strip()
        
        # Parse the JSON content
        tool_call_data = json.loads(tool_call_block)
        
        # Validate the structure of the tool call
        if "name" not in tool_call_data:
            raise ValueError("Tool call must include a 'name' field.")

        return tool_call_data

    except json.JSONDecodeError as e:
        print(f"Failed to parse tool call JSON: {e}. Please make sure the tool call is valid JSON")
        raise
    
    except ValueError as e:
        print(f"Value Error: {e}.")
        raise

def execute_tool(tool_name, tool_input):
    """
    Executes the specified tool with the given input parameters.

    Args:
        tool_name (str): The name of the tool to execute.
        tool_input (dict): A dictionary containing the input parameters for the tool.

    Returns:
        str: The result of the tool execution.

    Raises:
        ValueError: If the tool_name is invalid or the tool function raises an error.
    """

    # Check if the tool exists
    if hasattr(tools_lib, tool_name):
        tool = getattr(tools_lib, tool_name)
        if callable(tool):
            pass
        else:
            error_msg = f"Unknown tool or uncallable tool: {tool_name}"
            emitter.emit_sync(EVENT_ERROR, error_msg)
            raise ValueError(error_msg)
    else:
        error_msg = f"Unknown tool: {tool_name}"
        emitter.emit_sync(EVENT_ERROR, error_msg)
        raise ValueError(error_msg)

    try:
        # Execute the tool function with the provided input
        if tool_input == "":
            result = tool()
        else:
            result = tool(**tool_input)
        return result
    except Exception as e:
        error_msg = f"Error executing tool '{tool_name}': {e}"
        emitter.emit_sync(EVENT_ERROR, error_msg)
        raise ValueError(error_msg)




def get_expert(expert):
    """
    Get expert data from YAML files in the experts directory.
    
    Args:
        expert: The identifier of the expert to get
        
    Returns:
        dict: The expert data including system prompt
    """
    # Get the project root directory
    root_dir = Path(__file__).parent.parent
    experts_dir = root_dir / "experts"
    expert_data = {}
        
    # Look for expert in all YAML files
    for yaml_file in experts_dir.glob("*.yaml"):
        try:
            with open(yaml_file, 'r') as file:
                data = yaml.safe_load(file)
                
                # Check if this is the expert we're looking for
                # Case-insensitive matching for flexibility
                # logger.info(f"Looking for: {expert.lower().strip()}")
                # logger.info(f"Found: {data.get("ExpertID", "").lower().strip()}")
                if data.get("ExpertID", "").lower().strip() == expert.lower().strip():
                    #expert_data["system_prompt"] = data.get("SystemPrompt")
                    expert_data = data
                    logger.info(f"Found expert '{expert}' in {yaml_file.name}")
                    return expert_data
                    
        except Exception as e:
            logger.error(f"Error reading {yaml_file}: {str(e)}")
    
    logger.warning(f"Expert '{expert}' not found, using default system prompt")
    return expert_data
