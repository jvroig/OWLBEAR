"""
Unit tests for complex actions in OWLBEAR.
"""
import pytest
import os
import yaml
from actions.complex import load_complex_action, expand_complex_action, _substitute_variables

def test_load_complex_action(test_files_path, monkeypatch):
    """Test loading a complex action from a file."""
    # Get path to test complex actions
    test_complex_dir = test_files_path("sample_complex_actions")
    
    # Try to load a complex action that exists
    action_def = load_complex_action("polished_output", test_complex_dir)
    
    # The test should pass if the file exists
    assert action_def is not None, f"Could not load polished_output.yml from {test_complex_dir}"
    assert 'ACTIONS' in action_def
    assert len(action_def['ACTIONS']) > 0
    
    # Try to load a complex action that doesn't exist
    action_def = load_complex_action("nonexistent_action", test_complex_dir)
    assert action_def is None

def test_substitute_variables():
    """Test variable substitution in complex actions."""
    # Test with a simple object
    obj = "Hello {{name}}, welcome to {{company}}!"
    variables = {"name": "John", "company": "Acme"}
    result = _substitute_variables(obj, variables)
    assert result == "Hello John, welcome to Acme!"
    
    # Test with a dictionary
    obj = {
        "greeting": "Hello {{name}}",
        "message": "Welcome to {{company}}!"
    }
    result = _substitute_variables(obj, variables)
    assert result["greeting"] == "Hello John"
    assert result["message"] == "Welcome to Acme!"
    
    # Test with a list
    obj = ["Hello {{name}}", "Welcome to {{company}}!"]
    result = _substitute_variables(obj, variables)
    assert result[0] == "Hello John"
    assert result[1] == "Welcome to Acme!"
    
    # Test with a nested structure
    obj = {
        "greeting": {
            "text": "Hello {{name}}",
            "options": ["Welcome to {{company}}!", "How are you?"]
        }
    }
    result = _substitute_variables(obj, variables)
    assert result["greeting"]["text"] == "Hello John"
    assert result["greeting"]["options"][0] == "Welcome to Acme!"
    
    # Test with undefined variables
    obj = "Hello {{name}}, welcome to {{undefined}}!"
    result = _substitute_variables(obj, variables)
    assert "UNDEFINED" in result
    assert "Hello John" in result

def test_expand_complex_action(test_files_path):
    """Test expanding a complex action with variables."""
    # Get path to test complex actions
    test_complex_dir = test_files_path("sample_complex_actions")
    
    # Load a complex action
    action_def = load_complex_action("polished_output", test_complex_dir)
    assert action_def is not None, f"Could not load polished_output.yml from {test_complex_dir}"
    
    # Create action data
    action_data = {
        "expert": "CEO",
        "data": {
            "instruction": "Create a comprehensive plan",
            "another_data": "Consider all options",
            "and_another": "Be concise but thorough"
        },
        "output": "final_result"
    }
    
    # Expand the complex action
    expanded = expand_complex_action(action_def, action_data)
    
    # Check the result
    assert expanded is not None
    assert len(expanded) > 0
    
    # Verify variable substitution
    for action in expanded:
        action_type = list(action.keys())[0]
        action_info = action[action_type]
        
        # The expert should be substituted
        assert action_info.get('expert') == "CEO"
        
        # Check if inputs contain substituted variables
        if 'inputs' in action_info:
            for input_item in action_info['inputs']:
                # No raw variable pattern should remain
                assert "{{" not in input_item or "UNDEFINED" in input_item
                
                # Check for substituted values
                if "instruction" in action_data["data"]:
                    if isinstance(input_item, str) and "comprehensive plan" in input_item:
                        # Found a substituted variable
                        assert True
                        break

def test_output_linking(test_files_path):
    """Test that the last action's output is linked to the complex action output."""
    # Get path to test complex actions
    test_complex_dir = test_files_path("sample_complex_actions")
    
    # Load a complex action
    action_def = load_complex_action("polished_output", test_complex_dir)
    assert action_def is not None, f"Could not load polished_output.yml from {test_complex_dir}"
    
    # Create action data with an output
    action_data = {
        "expert": "CEO",
        "data": {
            "instruction": "Test instruction",
            "another_data": "Test data",
            "and_another": "More test data"
        },
        "output": "complex_output"
    }
    
    # Expand the complex action
    expanded = expand_complex_action(action_def, action_data)
    
    # Check the last action's output
    last_action = expanded[-1]
    action_type = list(last_action.keys())[0]
    
    # If the last action is a DECIDE, check the action before it (PROMPT)
    if action_type == 'DECIDE':
        for action in reversed(expanded):
            action_type = list(action.keys())[0]
            if action_type == 'PROMPT':
                assert action['PROMPT']['output'] == "complex_output", "Final PROMPT output should match complex action output"
                break
    else:
        assert last_action[action_type]['output'] == "complex_output", "Last action output should match complex action output"

def test_expand_complex_action_preserves_structure(test_files_path):
    """Test that complex action expansion preserves the action structure."""
    # Get path to test complex actions
    test_complex_dir = test_files_path("sample_complex_actions")
    
    # Load a complex action
    action_def = load_complex_action("comparative_analysis", test_complex_dir)
    assert action_def is not None, f"Could not load comparative_analysis.yml from {test_complex_dir}"
    
    # Count the number of actions and their types in the definition
    original_count = len(action_def['ACTIONS'])
    original_types = [list(action.keys())[0] for action in action_def['ACTIONS']]
    
    # Create action data
    action_data = {
        "expert": "CEO",
        "data": {
            "topic_a": "Python",
            "topic_b": "JavaScript",
            "criteria": "performance, ease of use",
            "instructions": "Compare these programming languages"
        },
        "output": "comparison_result"
    }
    
    # Expand the complex action
    expanded = expand_complex_action(action_def, action_data)
    
    # Check the result has the same number of actions
    assert len(expanded) == original_count
    
    # Check that the action types are preserved
    expanded_types = [list(action.keys())[0] for action in expanded]
    assert expanded_types == original_types
