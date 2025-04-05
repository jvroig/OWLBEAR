# actions/prompt.py
import logging
import time
from typing import Dict, Any, Callable

logger = logging.getLogger("workflow-engine.prompt")

def execute_prompt_action(action: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """
    Execute a PROMPT action.
    
    Args:
        action: The action configuration from the workflow YAML
        context: Execution context containing helper functions and state
        
    Returns:
        bool: True if execution was successful, False otherwise
    """
    try:
        expert = action.get('expert')
        inputs = action.get('inputs', [])
        output_name = action.get('output')
        step_number = context['step_number']
        resolve_input = context['resolve_input']
        save_output = context['save_output']
        call_agent = context['call_agent']
        
        if not expert or not output_name:
            logger.error(f"Step {step_number}: Missing expert or output in PROMPT action")
            return False
        
        # Resolve and concatenate all inputs
        resolved_inputs = [resolve_input(input_item) for input_item in inputs]
        full_prompt = "\n".join(resolved_inputs)
        
        # Call the expert
        response = call_agent(expert, full_prompt)
        
        # Save the output
        output_data = {
            'content': response,
            'timestamp': time.time(),
            'expert': expert,
            'action_type': 'PROMPT',
            'inputs': resolved_inputs
        }
        save_output(output_name, output_data)
        
        logger.info(f"Step {step_number}: PROMPT action completed successfully")
        return True
    except Exception as e:
        logger.error(f"Step {context['step_number']}: Error in PROMPT action: {str(e)}")
        return False