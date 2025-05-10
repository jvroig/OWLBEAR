# actions/complex.py
import os
import yaml
import logging
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger("workflow-engine.complex")

def load_complex_action(action_name: str) -> Optional[Dict[str, Any]]:
    """
    Load a complex action definition from a YAML file.
    
    Args:
        action_name: The name of the complex action to load
        
    Returns:
        dict: The complex action definition, or None if not found
    """
    # Get the actions/complex directory
    complex_dir = os.path.join(os.path.dirname(__file__), 'complex')
    
    # Try with both .yml and .yaml extensions
    for extension in ['.yml', '.yaml']:
        action_path = os.path.join(complex_dir, f"{action_name}{extension}")
        if os.path.exists(action_path):
            try:
                with open(action_path, 'r') as file:
                    return yaml.safe_load(file)
            except Exception as e:
                logger.error(f"Failed to load complex action '{action_name}': {str(e)}")
                return None
    
    logger.error(f"Complex action '{action_name}' not found in {complex_dir}")
    return None

def expand_complex_action(complex_action: Dict[str, Any], action_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Expand a complex action into its constituent basic actions.
    
    Args:
        complex_action: The complex action definition loaded from YAML
        action_data: The action data from the workflow YAML
        
    Returns:
        list: A list of expanded basic actions
    """
    if 'ACTIONS' not in complex_action:
        logger.error("Invalid complex action: Missing 'ACTIONS' section")
        return []
    
    # Extract common properties
    expert = action_data.get('expert')
    data = action_data.get('data', {})
    output = action_data.get('output')
    
    # Create variable substitution map
    variables = {
        'expert': expert,
        **data  # Unpack all data variables
    }
    
    # Process each action in the complex action
    expanded_actions = []
    for action in complex_action['ACTIONS']:
        # Make a deep copy of the action to avoid modifying the original
        action_copy = yaml.safe_load(yaml.dump(action))
        
        # Perform variable substitution on the entire action
        action_copy = _substitute_variables(action_copy, variables)
        
        # Add to expanded actions
        expanded_actions.append(action_copy)
    
    # If this is the last action and it's a PROMPT and output is specified,
    # update its output to match the complex action's output
    if output and expanded_actions and 'PROMPT' in expanded_actions[-1]:
        last_action_type = list(expanded_actions[-1].keys())[0]
        if last_action_type == 'PROMPT':
            # Store the original output for linking
            original_output = expanded_actions[-1]['PROMPT'].get('output')
            
            if original_output:
                # Link the original output with the complex action output
                # This approach maintains the chain of outputs inside the complex action
                expanded_actions[-1]['PROMPT']['output'] = output
                
                logger.info(f"Linked final output '{original_output}' to complex action output '{output}'")
    
    return expanded_actions

def _substitute_variables(obj: Any, variables: Dict[str, Any]) -> Any:
    """
    Recursively substitute variables in strings within an object.
    
    Args:
        obj: The object to process (can be a dict, list, or scalar)
        variables: Dictionary of variable names to values
        
    Returns:
        The object with variables substituted
    """
    if isinstance(obj, dict):
        return {k: _substitute_variables(v, variables) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_variables(item, variables) for item in obj]
    elif isinstance(obj, str):
        # Replace {{variable}} with its value
        def replace_var(match):
            var_name = match.group(1).strip()
            if var_name in variables:
                return str(variables[var_name])
            else:
                logger.warning(f"Undefined variable in complex action: {var_name}")
                return f"{{{{UNDEFINED:{var_name}}}}}"  # Keep the syntax but mark as undefined
            
        pattern = r"\{\{([^}]+)\}\}"
        return re.sub(pattern, replace_var, obj)
    else:
        # Return other types unchanged
        return obj
