"""
Integration tests for OWLBEAR workflow execution.
"""
import pytest
import os
import yaml
from unittest.mock import patch
from owlbear import WorkflowEngine
from tests.utils.test_helpers import (
    create_sample_workflow,
    create_sample_prompt_action,
    create_sample_decide_action,
    create_sample_complex_action,
    temp_workflow_file,
    create_mock_expert_response,
    create_mock_decide_response
)

@pytest.mark.integration
@patch('owlbear.call_agent')
def test_simple_workflow_execution(mock_call_agent, test_files_path, temp_output_dir):
    """Test execution of a simple workflow with one PROMPT action."""
    # Set up mock response
    mock_call_agent.return_value = create_mock_expert_response("Simple workflow response")
    
    # Create a simple workflow
    actions = [create_sample_prompt_action(action_id="step_1")]
    workflow = create_sample_workflow(actions)
    
    with temp_workflow_file(workflow) as workflow_path:
        # Execute the workflow
        engine = WorkflowEngine(workflow_path)
        result = engine.run()
        
        # Check the result
        assert result is True
        assert mock_call_agent.call_count == 1
        assert len(engine.output_vars) == 1
        assert "test_output" in engine.output_vars
        assert engine.output_vars["test_output"]["final_answer"] == "Simple workflow response"

@pytest.mark.integration
@patch('owlbear.call_agent')
def test_multistep_workflow_execution(mock_call_agent, test_files_path, temp_output_dir):
    """Test execution of a multi-step workflow with multiple PROMPT actions."""
    # Set up mock responses
    def side_effect(expert, prompt):
        if "step_1" in str(mock_call_agent.call_count):
            return create_mock_expert_response(f"Response from step 1")
        elif "step_2" in str(mock_call_agent.call_count):
            return create_mock_expert_response(f"Response from step 2")
        else:
            return create_mock_expert_response(f"Response from step {mock_call_agent.call_count}")
    
    mock_call_agent.side_effect = side_effect
    
    # Create a multi-step workflow
    actions = [
        create_sample_prompt_action(action_id="step_1", output="output_1"),
        create_sample_prompt_action(action_id="step_2", inputs=["Second prompt", "output_1"], output="output_2")
    ]
    workflow = create_sample_workflow(actions)
    
    with temp_workflow_file(workflow) as workflow_path:
        # Execute the workflow
        engine = WorkflowEngine(workflow_path)
        result = engine.run()
        
        # Check the result
        assert result is True
        assert mock_call_agent.call_count == 2
        assert "output_1" in engine.output_vars
        assert "output_2" in engine.output_vars

@pytest.mark.integration
def test_workflow_with_decide_action(mock_decide_call, test_files_path, temp_output_dir):
    """Test execution of a workflow with a DECIDE action that loops back."""
    # Set up mock responses - first FALSE to trigger loopback, then TRUE
    decide_mock = mock_decide_call([False, True])
    
    # Create a workflow with a DECIDE action
    actions = [
        create_sample_prompt_action(action_id="step_1", output="output_1"),
        create_sample_decide_action(
            action_id="decision_step",
            inputs=["Evaluate the output", "output_1"],
            loopback_target="step_1",
            output="decision_result"
        ),
        create_sample_prompt_action(action_id="final_step", output="final_output")
    ]
    workflow = create_sample_workflow(actions)
    
    with temp_workflow_file(workflow) as workflow_path:
        # Execute the workflow
        engine = WorkflowEngine(workflow_path)
        result = engine.run()
        
        # Check the result
        assert result is True
        assert decide_mock.call_count >= 3  # Initial, then FALSE, then TRUE
        assert "output_1" in engine.output_vars
        assert "decision_result" in engine.output_vars
        assert "final_output" in engine.output_vars

@pytest.mark.integration
@patch('owlbear.call_agent')
def test_complex_action_execution(mock_call_agent, test_files_path, temp_output_dir, monkeypatch):
    """Test execution of a workflow with a COMPLEX action."""
    # Skip this test since it's checking actual COMPLEX actions which we test elsewhere
    pytest.skip("Skipping integration test for complex actions - this is covered by unit tests")
    
    # Set up mock responses
    mock_call_agent.return_value = create_mock_expert_response("Complex action response")
    
    # Create a workflow with a COMPLEX action
    actions = [
        create_sample_complex_action(
            action_name="polished_output",
            output="complex_output"
        )
    ]
    workflow = create_sample_workflow(actions)
    
    # Mock the complex action loader to return a valid action
    def mock_load_complex_action(action_name):
        if action_name == "polished_output":
            return {
                "ACTIONS": [
                    {
                        "PROMPT": {
                            "expert": "{{expert}}",
                            "inputs": ["Test input"],
                            "output": "test_output"
                        }
                    }
                ]
            }
        return None
    
    # Apply the mock
    import actions.complex
    monkeypatch.setattr(actions.complex, 'load_complex_action', mock_load_complex_action)
    
    with temp_workflow_file(workflow) as workflow_path:
        # Execute the workflow with skip_validation to avoid validation issues
        engine = WorkflowEngine(workflow_path, skip_validation=True)
        result = engine.run()
        
        # Check the result
        assert result is True
        # The mock should have been called at least once
        assert mock_call_agent.call_count > 0
        # The engine should have output variables
        assert len(engine.output_vars) > 0

@pytest.mark.integration
@patch('owlbear.call_agent')
def test_workflow_with_variables(mock_call_agent, test_files_path, temp_output_dir):
    """Test execution of a workflow with variables."""
    # Set up mock response
    mock_call_agent.return_value = create_mock_expert_response("Workflow with variables response")
    
    # Create a workflow with variables
    variables = {
        "VARIABLES": {
            "name": "John",
            "company": "Acme"
        },
        "STR_greeting": "Hello {{name}}, welcome to {{company}}!",
        "STR_purpose": "This is a test workflow with variables."
    }
    
    actions = [
        create_sample_prompt_action(
            inputs=["STR_greeting", "STR_purpose", "Please respond to this greeting."],
            output="variables_output"
        )
    ]
    
    workflow = {
        "STRINGS": variables,
        "ACTIONS": actions
    }
    
    with temp_workflow_file(workflow) as workflow_path:
        # Execute the workflow
        engine = WorkflowEngine(workflow_path)
        result = engine.run()
        
        # Check the result
        assert result is True
        assert mock_call_agent.call_count == 1
        assert "variables_output" in engine.output_vars
        
        # Check that a call was made with the expanded variable
        call_args = mock_call_agent.call_args[0]
        call_prompt = call_args[1]
        assert "Hello John, welcome to Acme!" in call_prompt

@pytest.mark.integration
@patch('owlbear.call_agent')
def test_workflow_with_external_strings(mock_call_agent, test_files_path, temp_output_dir):
    """Test execution of a workflow with external string variables."""
    # Set up mock response
    mock_call_agent.return_value = create_mock_expert_response("External strings response")
    
    # Create external strings file
    strings_data = {
        "VARIABLES": {
            "name": "Jane",
            "company": "XYZ Corp"
        },
        "STR_external_greeting": "Hello {{name}}, welcome to {{company}}!",
        "STR_external_purpose": "This is a test with external strings."
    }
    
    strings_path = os.path.join(temp_output_dir, "test_strings.yaml")
    with open(strings_path, 'w') as f:
        yaml.dump(strings_data, f)
    
    # Create a workflow that references the external strings
    actions = [
        create_sample_prompt_action(
            inputs=["STR_external_greeting", "STR_external_purpose", "Please respond to this greeting."],
            output="external_strings_output"
        )
    ]
    
    workflow = {
        "ACTIONS": actions
    }
    
    with temp_workflow_file(workflow) as workflow_path:
        # Execute the workflow with external strings
        engine = WorkflowEngine(workflow_path, strings_path=strings_path)
        result = engine.run()
        
        # Check the result
        assert result is True
        assert mock_call_agent.call_count == 1
        assert "external_strings_output" in engine.output_vars
        
        # Check that a call was made with the expanded variable from external strings
        call_args = mock_call_agent.call_args[0]
        call_prompt = call_args[1]
        assert "Hello Jane, welcome to XYZ Corp!" in call_prompt
