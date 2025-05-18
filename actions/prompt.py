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
        
        # Handle append-history functionality
        append_history = action.get('append-history', False)
        append_history_type = action.get('append-history-type', 'LATEST')
        step_id = action.get('id')
        
        logger.info(f"Step {step_number}: append-history={append_history}, type={append_history_type}, output={output_name}, id={step_id}")
        
        if append_history and output_name:
            # Access necessary data from context
            output_history = context.get('output_history', {})
            output_vars = context.get('output_vars', {})
            output_dir = context.get('output_dir', '')
            
            logger.info(f"Step {step_number}: output_dir is '{output_dir}'")
            if not output_dir:
                logger.warning(f"Step {step_number}: No output_dir provided in context")
                
            logger.info(f"Step {step_number}: output_history keys: {list(output_history.keys())}")
            if output_name in output_history:
                logger.info(f"Step {step_number}: output_history[{output_name}] = {output_history[output_name]}")
            
            # 1. Add previous output history based on type
            if output_name in output_history and len(output_history[output_name]) >= 1:
                if append_history_type == 'LATEST':
                    # Only include the most recent previous output
                    try:
                        prev_name = output_history[output_name][-1] 
                        prev_path = os.path.join(output_dir, f"{prev_name}.yaml")
                        logger.info(f"Step {step_number}: Looking for previous output at {prev_path}")
                        
                        if os.path.exists(prev_path):
                            with open(prev_path, 'r') as file:
                                import yaml
                                prev_data = yaml.safe_load(file)
                                if 'final_answer' in prev_data:
                                    prev_content = prev_data.get('final_answer', '')
                                    resolved_inputs.append(f"===== YOUR PREVIOUS OUTPUT =====\n{prev_content}")
                                    logger.info(f"Step {step_number}: Including previous output (LATEST) for {output_name}")
                                else:
                                    logger.warning(f"Previous output file {prev_path} has no final_answer field")
                        else:
                            logger.warning(f"Previous output file {prev_path} does not exist")
                    except Exception as e:
                        logger.warning(f"Failed to read previous output file: {str(e)}")
                        logger.exception(e)  # Log the full stack trace
                        
                elif append_history_type == 'ALL' and len(output_history[output_name]) > 1:
                    # Include all previous outputs
                    history_text = "===== PREVIOUS OUTPUTS =====\n"
                    history_count = 0
                    
                    for i, hist_name in enumerate(output_history[output_name][:-1]):  # Skip the most recent one
                        try:
                            hist_path = os.path.join(output_dir, f"{hist_name}.yaml")
                            with open(hist_path, 'r') as file:
                                import yaml
                                hist_data = yaml.safe_load(file)
                                if 'final_answer' in hist_data:
                                    hist_content = hist_data.get('final_answer', '')
                                    history_text += f"--- Output {i+1} ---\n{hist_content}\n"
                                    history_count += 1
                                else:
                                    logger.warning(f"Historical file {hist_path} has no final_answer field")
                        except Exception as e:
                            logger.warning(f"Failed to read history file {hist_path}: {str(e)}")
                    
                    if history_count > 0:  # Only add if we actually found some history
                        resolved_inputs.append(history_text)
                        logger.info(f"Step {step_number}: Including {history_count} previous outputs (ALL) for {output_name}")
            
            # 2. Add feedback if available - after history
            feedback_cache = context.get('feedback_cache', {})
            logger.info(f"Step {step_number}: feedback_cache keys: {list(feedback_cache.keys())}")
            
            if step_id and step_id in feedback_cache:
                feedback = feedback_cache.get(step_id, '')
                if feedback:
                    resolved_inputs.append(f"===== FEEDBACK =====\n{feedback}")
                    logger.info(f"Step {step_number}: Including feedback for step ID '{step_id}'")
                    logger.info(f"Step {step_number}: Feedback content (first 50 chars): {feedback[:50]}...")
        
        # Concatenate all inputs into full prompt
        full_prompt = "\n\n".join(resolved_inputs)
        
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