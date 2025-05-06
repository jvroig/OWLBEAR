# actions/decide.py
import logging
import time
from typing import Dict, Any, Callable, Tuple, Optional, Union
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

logger = logging.getLogger("workflow-engine.decide")

def execute_decide_action(action: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, Optional[Union[int, str]]]:
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
        # Support both numeric loopback and string loopback_target
        loopback = action.get('loopback')
        loopback_target = action.get('loopback_target')
        
        step_number = context['step_number']
        resolve_input = context['resolve_input']
        save_output = context['save_output']
        call_agent = context['call_agent']
        
        # Detailed logging for debugging
        logger.info(f"DECIDE ACTION - Step {step_number}: Starting with loopback={loopback} or loopback_target={loopback_target}")
        
        if not expert or not output_name or (loopback is None and loopback_target is None):
            logger.error(f"Step {step_number}: Missing required fields in DECIDE action")
            return False, None
        
        # Resolve and concatenate all inputs
        resolved_inputs = [resolve_input(input_item) for input_item in inputs]
        full_prompt = "\n".join(resolved_inputs)
        
        # Add explicit instructions for structured decision output
        decision_prompt = f"""{full_prompt}

Based on the above, please respond with a structured assessment in the following JSON format:
{{
  "explanation": "Your detailed explanation and reasoning...",
  "decision": true or false
}}

Your explanation should be specific and actionable, highlighting key strengths or areas for improvement."""
        
        # Emit expert start event
        emitter.emit_sync(EVENT_EXPERT_START, expert_id=expert)
        
        # Call the expert - now returning dict with history and final_answer
        logger.info(f"Step {step_number}: Calling expert '{expert}' for DECIDE action")
        try:
            response_data = call_agent(expert, decision_prompt)
            
            # Emit expert end event
            emitter.emit_sync(EVENT_EXPERT_END, 
                            expert_id=expert, 
                            success=True, 
                            output_length=len(response_data.get('final_answer', '')))
        except Exception as e:
            # Emit expert end event with error
            emitter.emit_sync(EVENT_EXPERT_END, expert_id=expert, success=False, error=str(e))
            raise
        
        # Extract explanation and decision from the response
        response = response_data['final_answer']
        explanation, decision = extract_decision_and_explanation(response)
        
        logger.info(f"Step {step_number}: Received decision: {decision}")
        logger.info(f"Step {step_number}: Explanation: {explanation[:100]}..." if len(explanation) > 100 else f"Step {step_number}: Explanation: {explanation}")  # Log first 100 chars
        
        # Save the output with the explanation and decision
        output_data = {
            'history': response_data['history'],
            'final_answer': response_data['final_answer'],
            'decision': decision,
            'explanation': explanation,
            'timestamp': time.time(),
            'expert': expert,
            'action_type': 'DECIDE',
            'inputs': resolved_inputs,
            'loopback_value': loopback,
            'loopback_target': loopback_target,
            'current_step': step_number
        }
        save_output(output_name, output_data)
        
        logger.info(f"Step {step_number}: DECIDE action completed with decision: {decision}")
        
        # Determine next step
        if decision:
            logger.info(f"Step {step_number}: Decision is TRUE - Continuing to next step")
            
            # Emit step end event
            emitter.emit_sync(EVENT_STEP_END, 
                            step_index=step_number-1, 
                            action_type='DECIDE', 
                            expert_id=expert, 
                            success=True,
                            decision=True)
            
            return True, None  # Continue to next step
        else:
            # Determine target step - either by ID or by index
            if loopback_target is not None:
                logger.info(f"Step {step_number}: Decision is FALSE - Looping back to target '{loopback_target}'")
                
                # Emit step end event
                emitter.emit_sync(EVENT_STEP_END, 
                                step_index=step_number-1, 
                                action_type='DECIDE', 
                                expert_id=expert, 
                                success=True,
                                decision=False,
                                loopback_to=loopback_target)
                
                return True, loopback_target
            else:
                # Original numeric loopback (adjusted for 0-indexing)
                loopback_value = loopback - 1  # Convert to 0-indexed
                
                # Extra detail for debugging
                logger.info(f"=== DECISION LOOPBACK DETAILS ===")
                logger.info(f"Current step (1-indexed): {step_number}")
                logger.info(f"Current step (0-indexed): {step_number - 1}")
                logger.info(f"Loopback value in YAML (1-indexed): {loopback}")
                logger.info(f"Adjusted loopback (0-indexed): {loopback_value}")
                logger.info(f"=== END DECISION LOOPBACK DETAILS ===")
                
                logger.info(f"Step {step_number}: Decision is FALSE - Looping back to step {loopback} (1-indexed) / {loopback_value} (0-indexed)")
                
                # Emit step end event
                emitter.emit_sync(EVENT_STEP_END, 
                                step_index=step_number-1, 
                                action_type='DECIDE', 
                                expert_id=expert, 
                                success=True,
                                decision=False,
                                loopback_to=loopback_value)
                
                return True, loopback_value  # Loop back (adjusted for 0-indexing)
    except Exception as e:
        logger.error(f"Step {context['step_number']}: Error in DECIDE action: {str(e)}")
        
        # Emit error event
        emitter.emit_sync(EVENT_ERROR, f"Error in DECIDE action (step {context['step_number']}): {str(e)}")
        
        # Emit step end event with failure
        emitter.emit_sync(EVENT_STEP_END, 
                        step_index=context['step_number']-1, 
                        action_type='DECIDE', 
                        expert_id=expert if 'expert' in locals() else 'unknown', 
                        success=False,
                        error=str(e))
        
        return False, None


def extract_decision_and_explanation(response: str) -> Tuple[str, bool]:
    """
    Extract the decision and explanation from a structured response.
    
    Args:
        response: The response string containing JSON
        
    Returns:
        tuple: (explanation, decision)
    """
    # Default values
    explanation = ""
    decision = False
    
    try:
        # Try to find JSON in the response
        import re
        import json
        
        # Look for JSON pattern
        json_match = re.search(r'(\{.*?\})', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            try:
                # Parse the JSON
                data = json.loads(json_str)
                
                # Extract explanation and decision
                if 'explanation' in data:
                    explanation = data['explanation']
                if 'decision' in data:
                    decision = bool(data['decision'])
            except json.JSONDecodeError:
                # If JSON parsing fails, fall back to simple pattern matching
                logger.warning("Failed to parse JSON in response, falling back to pattern matching")
        
        # If no JSON found or parsing failed, fall back to simple pattern matching
        if not explanation:
            # Look for explanation-like text
            expl_match = re.search(r'explanation[\"\':]?\s*[\"\':]?\s*([^\"\']*)[\"\':]?', response, re.IGNORECASE)
            if expl_match:
                explanation = expl_match.group(1).strip()
            else:
                # Just use the whole response as explanation if no pattern found
                explanation = response.strip()
        
        # If no decision extracted from JSON, check for TRUE/FALSE in the text
        if not decision:
            decision = 'TRUE' in response.upper()
            
    except Exception as e:
        logger.error(f"Error extracting decision and explanation: {str(e)}")
        # Default to FALSE if an error occurs
        decision = False
        
    return explanation, decision