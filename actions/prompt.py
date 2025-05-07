# actions/prompt.py
import logging
import time
from typing import Dict, Any, Callable
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import event system
from events import (
    emitter,
    EVENT_STEP_END,
    EVENT_EXPERT_START,
    EVENT_EXPERT_END,
    EVENT_ERROR
)

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
        
        # Call the expert - now returning dict with history and final_answer
        # Emit expert start event
        emitter.emit_sync(EVENT_EXPERT_START, expert_id=expert)
        
        try:
            # Call the expert
            response_data = call_agent(expert, full_prompt)
            
            # Emit expert end event
            emitter.emit_sync(EVENT_EXPERT_END, 
                            expert_id=expert, 
                            success=True, 
                            output_length=len(response_data.get('final_answer', '')))
            
            # Save the output with the new structure
            output_data = {
                'history': response_data['history'],
                'final_answer': response_data['final_answer'],
                'timestamp': time.time(),
                'expert': expert,
                'action_type': 'PROMPT',
                'inputs': resolved_inputs
            }
            save_output(output_name, output_data)
        except Exception as e:
            # Emit expert end event with error
            emitter.emit_sync(EVENT_EXPERT_END, expert_id=expert, success=False, error=str(e))
            raise
        
        logger.info(f"Step {step_number}: PROMPT action completed successfully")
        
        # Emit step end event
        emitter.emit_sync(EVENT_STEP_END, 
                        step_index=step_number-1, 
                        action_type='PROMPT', 
                        expert_id=expert,
                        description=action.get('description'),
                        success=True)
        
        return True
    except Exception as e:
        logger.error(f"Step {context['step_number']}: Error in PROMPT action: {str(e)}")
        
        # Emit error event
        emitter.emit_sync(EVENT_ERROR, f"Error in PROMPT action (step {context['step_number']}): {str(e)}")
        
        # Emit step end event with failure
        emitter.emit_sync(EVENT_STEP_END, 
                        step_index=context['step_number']-1, 
                        action_type='PROMPT', 
                        expert_id=expert if 'expert' in locals() else 'unknown',
                        description=action.get('description') if 'action' in locals() else None,
                        success=False,
                        error=str(e))
        
        return False