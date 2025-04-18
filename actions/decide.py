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
        
        # Detailed logging for debugging
        logger.info(f"DECIDE ACTION - Step {step_number}: Starting with loopback={loopback} (1-indexed)")
        
        if not expert or not output_name or loopback is None:
            logger.error(f"Step {step_number}: Missing required fields in DECIDE action")
            return False, None
        
        # Resolve and concatenate all inputs
        resolved_inputs = [resolve_input(input_item) for input_item in inputs]
        full_prompt = "\n".join(resolved_inputs)
        
        # Add explicit instructions for the decision
        decision_prompt = f"{full_prompt}\n\nBased on the above, please respond with only TRUE or FALSE."
        
        # Call the expert
        logger.info(f"Step {step_number}: Calling expert '{expert}' for DECIDE action")
        response = call_agent(expert, decision_prompt)
        
        # Parse the response (in a real implementation, ensure the model returns TRUE/FALSE)
        decision = 'TRUE' in response.upper()
        logger.info(f"Step {step_number}: Received decision: {decision} from response: '{response.strip()}'")
        
        # Save the output
        output_data = {
            'content': response,
            'decision': decision,
            'timestamp': time.time(),
            'expert': expert,
            'action_type': 'DECIDE',
            'inputs': resolved_inputs,
            'loopback_value': loopback,
            'loopback_adjusted': loopback - 1,
            'current_step': step_number
        }
        save_output(output_name, output_data)
        
        logger.info(f"Step {step_number}: DECIDE action completed with decision: {decision}")
        
        # Determine next step with detailed logging
        if decision:
            logger.info(f"Step {step_number}: Decision is TRUE - Continuing to next step")
            return True, None  # Continue to next step
        else:
            # Fix: return the correct 0-indexed step number
            # YAML files use 1-indexed steps, so we subtract 1 to convert to 0-indexed
            loopback_value = loopback - 1  # Convert to 0-indexed
            
            # Extra detail for debugging
            logger.info(f"=== DECISION LOOPBACK DETAILS ===")
            logger.info(f"Current step (1-indexed): {step_number}")
            logger.info(f"Current step (0-indexed): {step_number - 1}")
            logger.info(f"Loopback value in YAML (1-indexed): {loopback}")
            logger.info(f"Adjusted loopback (0-indexed): {loopback_value}")
            logger.info(f"=== END DECISION LOOPBACK DETAILS ===")
            
            logger.info(f"Step {step_number}: Decision is FALSE - Looping back to step {loopback} (1-indexed) / {loopback_value} (0-indexed)")
            return True, loopback_value  # Loop back (adjusted for 0-indexing)
    except Exception as e:
        logger.error(f"Step {context['step_number']}: Error in DECIDE action: {str(e)}")
        return False, None