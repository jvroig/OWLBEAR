# actions/decide.py
import logging
import time
from typing import Dict, Any, Callable, Tuple, Optional

logger = logging.getLogger("workflow-engine.decide")

def execute_decide_action(action: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, Optional[int]]:
    """
    Execute a DECIDE action.
    
    Args:
        action: The action configuration from the workflow YAML
        context: Execution context containing helper functions and state
        
    Returns:
        tuple: (success, next_step) where next_step is None to continue or an index to loop back to
    """
    try:
        expert = action.get('expert')
        inputs = action.get('inputs', [])
        output_name = action.get('output')
        loopback = action.get('loopback')
        step_number = context['step_number']
        resolve_input = context['resolve_input']
        save_output = context['save_output']
        call_agent = context['call_agent']
        
        if not expert or not output_name or loopback is None:
            logger.error(f"Step {step_number}: Missing required fields in DECIDE action")
            return False, None
        
        # Resolve and concatenate all inputs
        resolved_inputs = [resolve_input(input_item) for input_item in inputs]
        full_prompt = "\n".join(resolved_inputs)
        
        # Add explicit instructions for the decision
        decision_prompt = f"{full_prompt}\n\nBased on the above, please respond with only TRUE or FALSE."
        
        # Call the expert
        response = call_agent(expert, decision_prompt)
        
        # Parse the response (in a real implementation, ensure the model returns TRUE/FALSE)
        decision = 'TRUE' in response.upper()
        
        # Save the output
        output_data = {
            'content': response,
            'decision': decision,
            'timestamp': time.time(),
            'expert': expert,
            'action_type': 'DECIDE',
            'inputs': resolved_inputs
        }
        save_output(output_name, output_data)
        
        logger.info(f"Step {step_number}: DECIDE action completed with decision: {decision}")
        
        # Determine next step
        if decision:
            return True, None  # Continue to next step
        else:
            return True, loopback - 1  # Loop back (adjust for 0-indexing)
    except Exception as e:
        logger.error(f"Step {context['step_number']}: Error in DECIDE action: {str(e)}")
        return False, None