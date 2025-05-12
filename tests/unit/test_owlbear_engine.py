"""
Unit tests for the main OWLBEAR engine.
"""
import pytest
import os
import yaml
import time
from unittest.mock import patch, MagicMock
from owlbear import WorkflowEngine

def test_engine_initialization(test_files_path):
    """Test that the workflow engine initializes correctly."""
    # Get the path to a sample workflow
    workflow_path = test_files_path("sample_workflows/sequences/test_complex.yml")
    
    # Create an engine
    engine = WorkflowEngine(workflow_path)
    
    # Test the engine was initialized correctly
    assert engine.workflow_path == workflow_path
    assert engine.workflow is None  # It should not load the workflow automatically
    assert isinstance(engine.string_vars, dict)
    assert isinstance(engine.output_vars, dict)
    assert engine.current_step == 0
    assert os.path.exists(engine.output_dir), "Output directory should be created during initialization"

def test_engine_load_workflow(test_files_path):
    """Test that the workflow engine can load a workflow."""
    # Get the path to a sample workflow
    workflow_path = test_files_path("sample_workflows/sequences/test_complex.yml")
    
    # Create an engine and load the workflow
    engine = WorkflowEngine(workflow_path)
    result = engine.load_workflow()
    
    # Test the result
    assert result is True
    assert engine.workflow is not None
    assert 'ACTIONS' in engine.workflow
    assert len(engine.workflow['ACTIONS']) > 0

def test_engine_load_strings(test_files_path):
    """Test that the workflow engine can load string variables."""
    # Get the paths to the sample workflow and strings
    workflow_path = test_files_path("sample_workflows/sequences/test_comparative.yml")
    strings_path = test_files_path("sample_workflows/strings/test_strings.yaml")
    
    # Create an engine with the strings path
    engine = WorkflowEngine(workflow_path, strings_path=strings_path)
    
    # Load the workflow and strings
    result = engine.load_workflow()
    assert result is True
    
    # Test that strings were loaded
    assert len(engine.string_vars) > 0
    assert "STR_delimiter" in engine.string_vars

def test_engine_expand_complex_actions(test_files_path):
    """Test that the workflow engine expands complex actions."""
    # Get the path to a sample workflow with complex actions
    workflow_path = test_files_path("sample_workflows/sequences/test_complex.yml")
    complex_actions_path = test_files_path("sample_complex_actions")
    
    # Create an engine and load the workflow
    engine = WorkflowEngine(workflow_path, complex_actions_path=complex_actions_path)
    result = engine.load_workflow()
    assert result is True
    
    # Test that complex actions were expanded
    complex_actions = [action for action in engine.workflow['ACTIONS'] if 'COMPLEX' in action]
    assert len(complex_actions) == 0, "All complex actions should be expanded"

def test_engine_validate_workflow(test_files_path, temp_output_dir):
    """Test that the workflow engine validates a workflow."""
    # Get the path to a sample workflow
    workflow_path = test_files_path("sample_workflows/sequences/test_complex.yml")
    complex_actions_path = test_files_path("sample_complex_actions")
    
    # Create an engine
    engine = WorkflowEngine(workflow_path, complex_actions_path=complex_actions_path)
    
    # Validate the workflow
    success, output_path = engine.validate_workflow()
    
    # Test the result
    assert success is True
    assert os.path.exists(output_path), "Expanded workflow file should be created"

def test_engine_resolve_input(test_files_path):
    """Test that the workflow engine resolves inputs correctly."""
    # Get the path to a sample workflow
    workflow_path = test_files_path("sample_workflows/sequences/test_complex.yml")
    
    # Create an engine and load the workflow
    engine = WorkflowEngine(workflow_path)
    engine.load_workflow()
    
    # Set up string variables and output variables
    engine.string_vars = {
        "STR_test": "This is a test string",
        "STR_USER_INPUT": "User input"
    }
    engine.output_vars = {
        "previous_output": {
            "final_answer": "Previous output content"
        }
    }
    engine.variables = {
        "name": "John",
        "company": "Acme"
    }
    
    # Test resolving a string variable
    result = engine.resolve_input("STR_test")
    assert result == "This is a test string"
    
    # Test resolving an output variable
    result = engine.resolve_input("previous_output")
    assert result == "Previous output content"
    
    # Test resolving a literal string
    result = engine.resolve_input("Just a literal string")
    assert result == "Just a literal string"
    
    # Test resolving a literal string with variables
    result = engine.resolve_input("Hello {{name}}, welcome to {{company}}!")
    assert result == "Hello John, welcome to Acme!"

@patch('owlbear.call_agent')
def test_engine_run_simple_workflow(mock_call_agent, test_files_path, sample_workflow_factory):
    """Test running a simple workflow with the engine."""
    # Set up mock response
    mock_call_agent.return_value = {
        'history': [
            {'role': 'user', 'content': 'Test prompt'},
            {'role': 'assistant', 'content': 'Mock response'}
        ],
        'final_answer': 'Mock response'
    }
    
    # Create a simple workflow with one action
    workflow_path = sample_workflow_factory(num_steps=1)
    
    # Create an engine and run the workflow
    engine = WorkflowEngine(workflow_path, skip_validation=True)
    result = engine.run()
    
    # Test the result
    assert result is True
    assert mock_call_agent.called
    assert len(engine.output_vars) == 1
    
    # Check if output files were created
    output_files = os.listdir(engine.output_dir)
    assert len(output_files) >= 1

@patch('owlbear.call_agent')
def test_engine_decide_action_true(mock_call_agent, test_files_path, sample_workflow_factory):
    """Test the DECIDE action that returns TRUE."""
    # Set up mock response for decide
    mock_call_agent.return_value = {
        'history': [
            {'role': 'user', 'content': 'Test prompt'},
            {'role': 'assistant', 'content': '{"explanation": "Test explanation", "decision": true}'}
        ],
        'final_answer': '{"explanation": "Test explanation", "decision": true}'
    }
    
    # Create a workflow with a DECIDE action
    workflow_path = sample_workflow_factory(include_decide=True)
    
    # Create an engine and run the workflow
    engine = WorkflowEngine(workflow_path, skip_validation=True)
    result = engine.run()
    
    # Test the result
    assert result is True
    assert mock_call_agent.called
    
    # With a TRUE decision, we should have output vars for all steps
    assert len(engine.output_vars) >= 2  # At least one for PROMPT and one for DECIDE

def test_engine_decide_action_false_loopback(mock_decide_call, test_files_path, sample_workflow_factory):
    """Test the DECIDE action that returns FALSE and loops back."""
    # Set up mock responses with the first returning FALSE and the second TRUE
    mock = mock_decide_call([False, True])
    
    # Create a workflow with a DECIDE action
    workflow_path = sample_workflow_factory(include_decide=True)
    
    # Create an engine and run the workflow
    engine = WorkflowEngine(workflow_path, skip_validation=True)
    result = engine.run()
    
    # Test the result
    assert result is True
    # The mock should have been called for the DECIDE actions
    # We can't verify exact call count due to mocking approach, but at minimum it should have been called
    assert mock.call_count > 0
    
    # Check if output files were created for each iteration
    output_files = os.listdir(engine.output_dir)
    assert len(output_files) >= 3  # Should have multiple files from loopback

def test_engine_save_output(test_files_path):
    """Test saving outputs with the workflow engine."""
    # Create an engine
    workflow_path = test_files_path("sample_workflows/sequences/test_complex.yml")
    engine = WorkflowEngine(workflow_path)
    
    # Create test output data
    output_data = {
        'history': [
            {'role': 'user', 'content': 'Test prompt'},
            {'role': 'assistant', 'content': 'Test response'}
        ],
        'final_answer': 'Test response',
        'timestamp': time.time(),
        'expert': 'TestExpert',
        'action_type': 'PROMPT',
        'inputs': ['Test input']
    }
    
    # Save the output
    engine.save_output("test_output", output_data)
    
    # Check if the output was saved in memory
    assert "test_output" in engine.output_vars
    assert engine.output_vars["test_output"] == output_data
    
    # Check if output files were created
    test_output_file = os.path.join(engine.output_dir, "test_output.yaml")
    assert os.path.exists(test_output_file)
    
    # Verify the content of the output file
    with open(test_output_file, 'r') as f:
        saved_data = yaml.safe_load(f)
    
    assert saved_data is not None
    assert saved_data.get('final_answer') == 'Test response'
    assert saved_data.get('expert') == 'TestExpert'
