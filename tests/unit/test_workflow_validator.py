"""
Unit tests for the workflow validator.
"""
import pytest
import os
import yaml
from workflow_validator import WorkflowValidator

def test_workflow_validator_initializes(test_files_path, temp_output_dir):
    """Test that the workflow validator initializes correctly."""
    # Get the path to a sample workflow
    workflow_path = test_files_path("sample_workflows/sequences/test_complex.yml")
    
    # Create a validator
    validator = WorkflowValidator(workflow_path, output_dir=temp_output_dir)
    
    # Test the validator was initialized correctly
    assert validator.workflow_path == workflow_path
    assert validator.output_dir == temp_output_dir
    assert validator.workflow is None  # It should not load the workflow automatically
    assert len(validator.validation_errors) == 0
    assert len(validator.validation_warnings) == 0

def test_workflow_validator_loads_workflow(test_files_path):
    """Test that the workflow validator can load a workflow."""
    # Get the path to a sample workflow
    workflow_path = test_files_path("sample_workflows/sequences/test_complex.yml")
    
    # Create a validator and load the workflow
    validator = WorkflowValidator(workflow_path)
    result = validator.load_workflow()
    
    # Test the result
    assert result is True
    assert validator.workflow is not None
    assert 'ACTIONS' in validator.workflow
    assert len(validator.workflow['ACTIONS']) > 0

def test_workflow_validator_loads_strings(test_files_path):
    """Test that the workflow validator can load string variables."""
    # Get the paths to the sample workflow and strings
    workflow_path = test_files_path("sample_workflows/sequences/test_comparative.yml")
    strings_path = test_files_path("sample_workflows/strings/test_strings.yaml")
    
    # Create a validator with the strings path
    validator = WorkflowValidator(workflow_path, strings_path=strings_path)
    
    # Load the workflow and strings
    result = validator.load_workflow()
    assert result is True
    
    # Test that strings were loaded
    assert len(validator.string_vars) > 0
    assert validator.string_vars.get("STR_delimiter") == "*********************************************"

def test_workflow_validator_resolves_variables(test_files_path):
    """Test that the validator resolves variables correctly."""
    # Create a validator
    workflow_path = test_files_path("sample_workflows/sequences/test_complex.yml")
    validator = WorkflowValidator(workflow_path)
    
    # Set up variables
    validator.variables = {
        "name": "John",
        "company": "Acme",
        "nested": "{{name}}'s Company"
    }
    
    # Test basic variable resolution
    template = "Hello {{name}}, welcome to {{company}}!"
    result = validator._resolve_variables(template)
    assert result == "Hello John, welcome to Acme!"
    
    # Test missing variable
    template = "Hello {{missing}}"
    result = validator._resolve_variables(template)
    assert "UNDEFINED" in result
    
    # Test nested variables (should not be resolved in one pass)
    template = "This is {{nested}}"
    result = validator._resolve_variables(template)
    assert result == "This is {{name}}'s Company"

def test_workflow_validator_finds_errors(test_files_path, sample_workflow_factory):
    """Test that the validator finds errors in workflows."""
    # Create an invalid workflow with a DECIDE action using deprecated loopback
    workflow_path = sample_workflow_factory(include_decide=True, id_based_loopback=False)
    
    # Create a validator and validate the workflow
    validator = WorkflowValidator(workflow_path)
    success, _ = validator.validate()
    
    # Should fail due to using deprecated loopback
    assert success is False
    assert len(validator.validation_errors) > 0
    
    # Verify the specific error about deprecated loopback
    found_loopback_error = False
    for error in validator.validation_errors:
        if "deprecated 'loopback'" in error:
            found_loopback_error = True
            break
    
    assert found_loopback_error, "Should have an error about deprecated 'loopback'"

def test_workflow_validator_validates_valid_workflow(test_files_path, sample_workflow_factory, temp_output_dir):
    """Test that the validator successfully validates a valid workflow."""
    # Create a valid workflow
    workflow_path = sample_workflow_factory(include_decide=True, id_based_loopback=True)
    
    # Create a validator and validate the workflow
    validator = WorkflowValidator(workflow_path, output_dir=temp_output_dir)
    success, output_path = validator.validate()
    
    # Should succeed with a valid workflow
    assert success is True
    assert len(validator.validation_errors) == 0
    assert os.path.exists(output_path), "Expanded workflow file should be created"
    
    # Verify that the output contains expanded actions
    with open(output_path, 'r') as f:
        expanded_workflow = yaml.safe_load(f)
    
    assert expanded_workflow is not None
    assert 'ACTIONS' in expanded_workflow
    assert len(expanded_workflow['ACTIONS']) > 0

def test_workflow_validator_expands_variables(test_files_path, temp_output_dir):
    """Test that the validator expands variables in a workflow."""
    # Create a simple workflow with variables instead of trying to use existing ones
    actions = [
        {
            "PROMPT": {
                "expert": "CEO",
                "inputs": [
                    "Compare {{topic_a}} and {{topic_b}} based on {{criteria}}",
                    "Write a report about {{topic_a}}"
                ],
                "output": "variable_test"
            }
        }
    ]
    
    # Create string variables with nested templates
    strings = {
        "VARIABLES": {
            "name": "Test Name",
            "company": "Test Company",
            "topic_a": "Python",
            "topic_b": "JavaScript",
            "criteria": "performance, ease of use"
        },
        "STR_common_var": "This is a {{name}} at {{company}} project"
    }
    
    workflow = {
        "STRINGS": strings,
        "ACTIONS": actions
    }
    
    # Create temporary files
    workflow_path = os.path.join(temp_output_dir, "test_variables.yml")
    with open(workflow_path, 'w') as f:
        yaml.dump(workflow, f)
    
    try:
        # Create a validator and validate the workflow
        validator = WorkflowValidator(workflow_path, output_dir=temp_output_dir)
        validator.load_workflow()
        
        # Before applying variables, ensure they're available
        assert "topic_a" in validator.variables, "Variable 'topic_a' should be available"
        assert "topic_b" in validator.variables, "Variable 'topic_b' should be available"
        assert "criteria" in validator.variables, "Variable 'criteria' should be available"
        
        # Expand the variables in the workflow
        expanded = validator.expand_variables()
        
        # Verify that variables were expanded
        assert expanded is not None, "expand_variables() should return a non-None result"
        assert 'ACTIONS' in expanded, "Expanded workflow should contain ACTIONS section"
        
        # Look for expanded variables in at least one action
        found_expanded = False
        expanded_patterns = ["Python", "JavaScript", "performance, ease of use"]
        
        for action in expanded['ACTIONS']:
            action_type = list(action.keys())[0]
            action_data = action[action_type]
            
            if 'inputs' in action_data:
                for input_item in action_data['inputs']:
                    if isinstance(input_item, str):
                        # Check if any expanded variable is in the input string
                        if any(pattern in input_item for pattern in expanded_patterns):
                            found_expanded = True
                            break
            
            if found_expanded:
                break
        
        assert found_expanded, "Variables should be expanded in the workflow"
    finally:
        # Clean up
        if os.path.exists(workflow_path):
            os.remove(workflow_path)
