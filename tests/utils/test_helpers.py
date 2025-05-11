"""
Helper utilities for OWLBEAR tests.
"""
import os
import yaml
import tempfile
import contextlib
from typing import Dict, Any, List, Optional

@contextlib.contextmanager
def temp_workflow_file(workflow_data: Dict[str, Any]):
    """
    Create a temporary workflow file for testing.
    
    Args:
        workflow_data: The workflow data to write to the file
        
    Yields:
        str: Path to the temporary workflow file
    """
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.yml', delete=False) as f:
        # Write workflow data to the file
        yaml.dump(workflow_data, f)
        temp_path = f.name
    
    try:
        # Yield the path to the caller
        yield temp_path
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

def create_sample_prompt_action(expert: str = "CEO", 
                               inputs: List[str] = None, 
                               output: str = "test_output",
                               action_id: Optional[str] = None):
    """
    Create a sample PROMPT action for testing.
    
    Args:
        expert: The expert to use
        inputs: List of input items
        output: The output variable name
        action_id: Optional ID for the action
        
    Returns:
        dict: A PROMPT action dictionary
    """
    if inputs is None:
        inputs = ["Test prompt"]
        
    action = {
        "PROMPT": {
            "expert": expert,
            "inputs": inputs,
            "output": output
        }
    }
    
    if action_id:
        action["PROMPT"]["id"] = action_id
        
    return action

def create_sample_decide_action(expert: str = "CEO", 
                               inputs: List[str] = None, 
                               output: str = "decision_output",
                               loopback_target: str = "step1",
                               loop_limit: int = 3,
                               action_id: Optional[str] = None):
    """
    Create a sample DECIDE action for testing.
    
    Args:
        expert: The expert to use
        inputs: List of input items
        output: The output variable name
        loopback_target: The target action ID to loop back to
        loop_limit: The maximum number of loops
        action_id: Optional ID for the action
        
    Returns:
        dict: A DECIDE action dictionary
    """
    if inputs is None:
        inputs = ["Decide if this meets requirements", "TRUE or FALSE"]
        
    action = {
        "DECIDE": {
            "expert": expert,
            "inputs": inputs,
            "output": output,
            "loopback_target": loopback_target,
            "loop_limit": loop_limit
        }
    }
    
    if action_id:
        action["DECIDE"]["id"] = action_id
        
    return action

def create_sample_complex_action(action_name: str = "polished_output",
                                expert: str = "CEO",
                                data: Dict[str, str] = None,
                                output: str = "complex_output"):
    """
    Create a sample COMPLEX action for testing.
    
    Args:
        action_name: The name of the complex action template
        expert: The expert to use
        data: Dictionary of variables for the complex action
        output: The output variable name
        
    Returns:
        dict: A COMPLEX action dictionary
    """
    if data is None:
        data = {
            "instruction": "Test instruction",
            "another_data": "Test data",
            "and_another": "More test data"
        }
        
    return {
        "COMPLEX": {
            "action": action_name,
            "expert": expert,
            "data": data,
            "output": output
        }
    }

def create_sample_workflow(actions: List[Dict[str, Any]] = None,
                          strings: Dict[str, str] = None):
    """
    Create a sample workflow for testing.
    
    Args:
        actions: List of actions for the workflow
        strings: Dictionary of string variables
        
    Returns:
        dict: A complete workflow dictionary
    """
    if actions is None:
        # Create a default workflow with one prompt action
        actions = [create_sample_prompt_action()]
        
    if strings is None:
        strings = {
            "STR_test": "This is a test string"
        }
        
    return {
        "STRINGS": strings,
        "ACTIONS": actions
    }

def create_mock_expert_response(content: str = "Mock response",
                              history: List[Dict[str, str]] = None):
    """
    Create a mock expert response for testing.
    
    Args:
        content: The content of the response
        history: The conversation history
        
    Returns:
        dict: An expert response dictionary
    """
    if history is None:
        history = [
            {"role": "user", "content": "Test prompt"},
            {"role": "assistant", "content": content}
        ]
        
    return {
        "history": history,
        "final_answer": content
    }

def create_mock_decide_response(decision: bool,
                              explanation: str = "Test explanation"):
    """
    Create a mock DECIDE action response for testing.
    
    Args:
        decision: The decision (True/False)
        explanation: The explanation for the decision
        
    Returns:
        dict: A DECIDE response dictionary
    """
    content = f'{{"explanation": "{explanation}", "decision": {str(decision).lower()}}}'
    
    return {
        "history": [
            {"role": "user", "content": "Test decide prompt"},
            {"role": "assistant", "content": content}
        ],
        "final_answer": content
    }
