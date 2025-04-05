# inference/inference.py
import os
import json
import time
import yaml
import logging

from http import HTTPStatus
from openai import OpenAI
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("workflow-engine.inference")

# Load API Key
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('DASHSCOPE_API_KEY')
base_url = 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1'


def call_agent(expert: str, prompt: str) -> str:
    """
    Call an LLM expert with the given prompt.
    
    Args:
        expert: The identifier of the expert to call
        prompt: The full prompt text to send to the expert
        
    Returns:
        str: The response from the expert
    """
    logger.info(f"Calling expert: {expert} with prompt length: {len(prompt)}")
    
    expert_data = get_expert(expert)
    messages = format_messages(expert_data, prompt)

    response = inference_loop(expert_data, messages)
    logger.info(f"RESPONSE: {response}")
    return response


def inference_loop(expert_data, messages):
    while True:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        response = client.chat.completions.create(
            model="qwen2.5-32b-instruct",
            messages=messages,
            stream=False
        )
        print(f"Sent for inference: {messages}")
        return response.choices[0].message.content
    
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
                    expert_data["system_prompt"] = data.get("SystemPrompt")
                    logger.info(f"Found expert '{expert}' in {yaml_file.name}")
                    return expert_data
                    
        except Exception as e:
            logger.error(f"Error reading {yaml_file}: {str(e)}")
    
    logger.warning(f"Expert '{expert}' not found, using default system prompt")
    return expert_data
    
def format_messages(expert_data, prompt):

    messages = [
        {
            "role": "system",
            "content": expert_data["system_prompt"]
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    return messages