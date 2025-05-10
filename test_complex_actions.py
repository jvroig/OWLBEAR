#!/usr/bin/env python3
# test_complex_actions.py
import yaml
import os
import logging
from actions.complex import load_complex_action, expand_complex_action

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test-complex-actions")

def test_complex_action_expansion():
    """Test loading and expanding a complex action."""
    
    # 1. Load the complex action definition
    complex_action_name = "polished_output"
    complex_def = load_complex_action(complex_action_name)
    
    if not complex_def:
        logger.error(f"Failed to load complex action: {complex_action_name}")
        return False
    
    logger.info(f"Successfully loaded complex action: {complex_action_name}")
    
    # 2. Define action data similar to what would be in a workflow
    action_data = {
        "action": "polished_output",
        "expert": "CEO",
        "data": {
            "instruction": "Create a comprehensive response plan to the data breach",
            "another_data": "Consider legal, ethical, and public relations implications",
            "and_another": "The plan should be actionable and clear"
        },
        "output": "polished_response_plan"
    }
    
    # 3. Expand the complex action
    expanded_actions = expand_complex_action(complex_def, action_data)
    
    if not expanded_actions:
        logger.error("Failed to expand complex action")
        return False
    
    logger.info(f"Successfully expanded complex action into {len(expanded_actions)} basic actions")
    
    # 4. Print the expanded actions for inspection
    print("\nExpanded actions:")
    print("=" * 50)
    for i, action in enumerate(expanded_actions):
        print(f"\nAction {i+1}:")
        print(yaml.dump(action, default_flow_style=False))
    
    return True

def test_complex_action_in_workflow():
    """Test how a complex action would be expanded within a workflow."""
    
    # 1. Load a sample workflow
    workflow_path = "workflows/sequences/test_complex.yml"
    try:
        with open(workflow_path, 'r') as file:
            workflow = yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Failed to load workflow {workflow_path}: {str(e)}")
        return False
    
    # 2. Find complex actions in the workflow
    complex_actions = []
    for i, action in enumerate(workflow['ACTIONS']):
        if 'COMPLEX' in action:
            complex_actions.append((i, action['COMPLEX']))
    
    if not complex_actions:
        logger.error(f"No complex actions found in workflow {workflow_path}")
        return False
    
    logger.info(f"Found {len(complex_actions)} complex actions in workflow {workflow_path}")
    
    # 3. Expand each complex action
    expanded_workflow = {'ACTIONS': []}
    for i, action in enumerate(workflow['ACTIONS']):
        if 'COMPLEX' in action:
            # This is a complex action, expand it
            complex_data = action['COMPLEX']
            action_name = complex_data.get('action')
            
            # Load the complex action definition
            complex_def = load_complex_action(action_name)
            if not complex_def:
                logger.error(f"Failed to load complex action '{action_name}'")
                continue
                
            # Expand the complex action
            expanded = expand_complex_action(complex_def, complex_data)
            
            if not expanded:
                logger.error(f"Failed to expand complex action '{action_name}'")
                continue
                
            # Add the expanded actions
            expanded_workflow['ACTIONS'].extend(expanded)
            logger.info(f"Complex action '{action_name}' expanded into {len(expanded)} basic actions")
        else:
            # Not a complex action, keep as-is
            expanded_workflow['ACTIONS'].append(action)
    
    # 4. Print the expanded workflow for inspection
    print("\nExpanded workflow:")
    print("=" * 50)
    print(yaml.dump(expanded_workflow, default_flow_style=False))
    
    return True

if __name__ == "__main__":
    print("\n=== Testing Complex Action Expansion ===")
    if not test_complex_action_expansion():
        print("Complex action expansion test failed!")
    
    print("\n=== Testing Complex Action in Workflow ===")
    if not test_complex_action_in_workflow():
        print("Complex action in workflow test failed!")
