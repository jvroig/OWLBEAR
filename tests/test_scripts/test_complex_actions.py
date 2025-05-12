#!/usr/bin/env python3
# test_complex_actions.py
import yaml
import os
import sys
import logging

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from actions.complex import load_complex_action, expand_complex_action

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test-complex-actions")

def get_test_file_path(relative_path):
    """Helper to get a path relative to the tests directory"""
    test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(test_dir, relative_path)

def test_complex_action_expansion():
    """Test loading and expanding a complex action."""
    
    # 1. Load the complex action definition
    complex_action_path = get_test_file_path("sample_complex_actions/polished_output.yml")
    
    try:
        with open(complex_action_path, 'r') as file:
            complex_def = yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Failed to load complex action from {complex_action_path}: {str(e)}")
        assert False, f"Failed to load complex action: {str(e)}"
    
    # Use assertion instead of if-return
    assert complex_def is not None, "Failed to load complex action: Empty or invalid YAML"
    
    logger.info(f"Successfully loaded complex action from: {complex_action_path}")
    
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
    
    # Use assertion instead of if-return
    assert expanded_actions is not None, "Failed to expand complex action"
    
    logger.info(f"Successfully expanded complex action into {len(expanded_actions)} basic actions")
    
    # 4. Print the expanded actions for inspection
    print("\nExpanded actions:")
    print("=" * 50)
    for i, action in enumerate(expanded_actions):
        print(f"\nAction {i+1}:")
        print(yaml.dump(action, default_flow_style=False))

def test_complex_action_in_workflow():
    """Test how a complex action would be expanded within a workflow."""
    
    # 1. Load a sample workflow
    workflow_path = get_test_file_path("sample_workflows/sequences/test_complex.yml")
    try:
        with open(workflow_path, 'r') as file:
            workflow = yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Failed to load workflow {workflow_path}: {str(e)}")
        assert False, f"Failed to load workflow: {str(e)}"
    
    # 2. Find complex actions in the workflow
    complex_actions = []
    for i, action in enumerate(workflow['ACTIONS']):
        if 'COMPLEX' in action:
            complex_actions.append((i, action['COMPLEX']))
    
    # Use assertion instead of if-return
    assert len(complex_actions) > 0, f"No complex actions found in workflow {workflow_path}"
    
    logger.info(f"Found {len(complex_actions)} complex actions in workflow {workflow_path}")
    
    # 3. Expand each complex action
    expanded_workflow = {'ACTIONS': []}
    for i, action in enumerate(workflow['ACTIONS']):
        if 'COMPLEX' in action:
            # This is a complex action, expand it
            complex_data = action['COMPLEX']
            action_name = complex_data.get('action')
            
            # Load the complex action definition
            # Make sure to look for the polished_output.yml file if action_name is test_polished_output
            if action_name == 'test_polished_output':
                action_name = 'polished_output'
            complex_action_path = get_test_file_path(f"sample_complex_actions/{action_name}.yml")
            try:
                with open(complex_action_path, 'r') as file:
                    complex_def = yaml.safe_load(file)
            except Exception as e:
                logger.error(f"Failed to load complex action '{action_name}': {str(e)}")
                assert False, f"Failed to load complex action '{action_name}': {str(e)}"
                
            # Expand the complex action
            expanded = expand_complex_action(complex_def, complex_data)
            
            # Use assertion instead of if-continue
            assert expanded is not None, f"Failed to expand complex action '{action_name}'"
                
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

if __name__ == "__main__":
    try:
        print("\n=== Testing Complex Action Expansion ===")
        test_complex_action_expansion()
        
        print("\n=== Testing Complex Action in Workflow ===")
        test_complex_action_in_workflow()
        
        print("\nAll tests passed!")
        exit(0)
    except AssertionError as e:
        print(f"\nTest failed: {str(e)}")
        exit(1)
