"""
Performance tests for OWLBEAR.
"""
import pytest
import time
import os
import yaml
from unittest.mock import patch
from owlbear import WorkflowEngine
from workflow_validator import WorkflowValidator
from tests.utils.test_helpers import (
    create_sample_workflow,
    create_sample_prompt_action,
    create_sample_decide_action,
    create_sample_complex_action,
    temp_workflow_file,
    create_mock_expert_response
)

@pytest.mark.performance
@patch('owlbear.call_agent')
def test_workflow_loading_performance(mock_call_agent, test_files_path, temp_output_dir):
    """Test performance of workflow loading and variable expansion."""
    # Set up mock response for any agent calls
    mock_call_agent.return_value = create_mock_expert_response("Test response")
    
    # Create a workflow with many actions and string variables
    actions = []
    
    # Manually create the actions to avoid the STR_var_{i} issue
    for i in range(50):  # Create 50 actions
        var_name = f"STR_var_{i}"  # Create actual variable name with i as a number
        actions.append(create_sample_prompt_action(
            action_id=f"step_{i}",
            inputs=[f"Input for step {i}", var_name],  # Use the actual variable name
            output=f"output_{i}"
        ))
    
    # Create string variables dictionary
    strings = {
        "VARIABLES": {
            "name": "Test Name",
            "company": "Test Company",
            "product": "OWLBEAR"
        }
    }
    
    # Add 50 string variables with template substitution
    for i in range(50):
        var_name = f"STR_var_{i}"  # Create actual variable name with i as a number
        strings[var_name] = f"String variable {{{{name}}}} for step {i} at {{{{company}}}} working on {{{{product}}}}"
    
    workflow = {
        "STRINGS": strings,
        "ACTIONS": actions
    }
    
    # Create a temp workflow file
    workflow_path = os.path.join(temp_output_dir, "perf_test_workflow.yml")
    with open(workflow_path, 'w') as f:
        yaml.dump(workflow, f)
    
    # Measure time to load and validate workflow
    start_time = time.time()
    
    engine = WorkflowEngine(workflow_path, skip_validation=True)  # Skip validation to test just loading
    load_result = engine.load_workflow()
    
    load_time = time.time() - start_time
    
    # Assertions
    assert load_result is True
    
    # Performance threshold
    assert load_time < 2.0, f"Workflow loading took too long: {load_time} seconds"
    print(f"Workflow loading took {load_time:.4f} seconds")

@pytest.mark.performance
@patch('owlbear.call_agent')
def test_complex_action_expansion_performance(mock_call_agent, test_files_path, temp_output_dir, monkeypatch):
    """Test performance of complex action expansion."""
    # Set up mock response
    mock_call_agent.return_value = create_mock_expert_response("Test response")
    
    # Create polished_output.yml in the sample_complex_actions directory first
    test_complex_action = {
        "ACTIONS": [
            {
                "PROMPT": {
                    "id": "polished_action_1",
                    "expert": "{{expert}}",
                    "inputs": [
                        "Creating polished output for {{instruction}}",
                        "Additional info: {{another_data}}",
                        "Extra context: {{and_another}}"
                    ],
                    "output": "step1_output"
                }
            },
            {
                "PROMPT": {
                    "id": "polished_action_2",
                    "expert": "{{expert}}",
                    "inputs": [
                        "Reviewing draft for {{instruction}}",
                        "step1_output"
                    ],
                    "output": "step2_output"
                }
            },
            {
                "PROMPT": {
                    "id": "polished_action_3",
                    "expert": "{{expert}}",
                    "inputs": [
                        "Finalizing output for {{instruction}}",
                        "step1_output",
                        "step2_output"
                    ],
                    "output": "{{output}}"
                }
            }
        ]
    }
    
    # Save the test complex action to the sample_complex_actions directory
    complex_action_dir = os.path.join(test_files_path("sample_complex_actions"))
    os.makedirs(complex_action_dir, exist_ok=True)
    complex_action_path = os.path.join(complex_action_dir, "polished_output.yml")
    with open(complex_action_path, 'w') as f:
        yaml.dump(test_complex_action, f)
    
    # Create a workflow with many complex actions
    actions = []
    for i in range(10):  # 10 complex actions, each will expand to 3 basic actions
        actions.append(create_sample_complex_action(
            action_name="polished_output",
            expert="CEO",
            data={
                "instruction": f"Instruction for complex action {i}",
                "another_data": f"Additional data for complex action {i}",
                "and_another": f"More data for complex action {i}"
            },
            output=f"complex_output_{i}"
        ))
    
    workflow = create_sample_workflow(actions)
    
    # Create a temp workflow file
    workflow_path = os.path.join(temp_output_dir, "perf_complex_test.yml")
    with open(workflow_path, 'w') as f:
        yaml.dump(workflow, f)
    
    # Measure time to load and expand workflow
    start_time = time.time()
    
    engine = WorkflowEngine(workflow_path, skip_validation=True)
    load_result = engine.load_workflow()
    
    expansion_time = time.time() - start_time
    
    # Assertions
    assert load_result is True
    # Each complex action expands to 3 basic actions, so 10 complex → 30 basic
    assert len(engine.workflow['ACTIONS']) > len(actions), "Complex actions should be expanded"
    
    # Performance threshold
    assert expansion_time < 1.0, f"Complex action expansion took too long: {expansion_time} seconds"
    print(f"Complex action expansion took {expansion_time:.4f} seconds")
    
    # Clean up
    if os.path.exists(workflow_path):
        os.remove(workflow_path)

@pytest.mark.performance
@patch('owlbear.call_agent')
def test_large_workflow_execution_performance(mock_call_agent, test_files_path, temp_output_dir):
    """Test performance of executing a large workflow."""
    # Set up mock response - make it fast
    mock_call_agent.return_value = create_mock_expert_response("Test response")
    
    # Create a workflow with many actions
    actions = []
    for i in range(20):  # Create 20 actions
        actions.append(create_sample_prompt_action(
            action_id=f"step_{i}",
            output=f"output_{i}"
        ))
    
    workflow = create_sample_workflow(actions)
    
    with temp_workflow_file(workflow) as workflow_path:
        # Measure time to execute the workflow
        start_time = time.time()
        
        engine = WorkflowEngine(workflow_path, skip_validation=True)
        engine.load_workflow()
        result = engine.run()
        
        execution_time = time.time() - start_time
        
        # Assertions
        assert result is True
        assert len(engine.output_vars) == 20, "All actions should produce outputs"
        
        # Performance threshold - adjust based on actual execution time on your system
        assert execution_time < 5.0, f"Large workflow execution took too long: {execution_time} seconds"
        print(f"Large workflow execution took {execution_time:.4f} seconds")

@pytest.mark.performance
def test_workflow_validator_performance(test_files_path, temp_output_dir):
    """Test performance of the workflow validator with a complex workflow."""
    # Create a complex workflow with many variable substitutions
    actions = []
    
    # First, create some initial actions to ensure step_i-1 always exists
    actions.append(create_sample_prompt_action(
        action_id="step_0", 
        inputs=["Initial input", "STR_common_var"],
        output="output_0"
    ))
    
    # Now add the remaining actions
    for i in range(1, 30):  # Create 29 more actions, starting from i=1
        if i % 5 == 0:  # Every 5th action is a DECIDE action
            actions.append(create_sample_decide_action(
                action_id=f"decide_{i}",
                inputs=[f"Evaluate output_{i-1}", f"output_{i-1}"],
                loopback_target=f"step_{i-1}",  # This will always exist now
                output=f"decision_{i}"
            ))
        else:
            actions.append(create_sample_prompt_action(
                action_id=f"step_{i}",
                inputs=[f"Input for step {i}", "STR_common_var"],
                output=f"output_{i}"
            ))
    
    # Create string variables with nested templates
    strings = {
        "VARIABLES": {
            "name": "Test Name",
            "company": "Test Company",
            "nested": "{{name}} at {{company}}",
            "double_nested": "{{nested}} working on OWLBEAR"
        },
        "STR_common_var": "This is a {{double_nested}} project"
    }
    
    workflow = {
        "STRINGS": strings,
        "ACTIONS": actions
    }
    
    # Create a temp workflow file with a consistent path
    workflow_path = os.path.join(temp_output_dir, "perf_validator_test.yml")
    with open(workflow_path, 'w') as f:
        yaml.dump(workflow, f)
    
    try:
        # Measure time to validate the workflow
        start_time = time.time()
        
        validator = WorkflowValidator(workflow_path, output_dir=temp_output_dir)
        success, _ = validator.validate()
        
        validation_time = time.time() - start_time
        
        # Assertions
        assert success is True, "Workflow validation should succeed"
        
        # Performance threshold
        assert validation_time < 1.0, f"Workflow validation took too long: {validation_time} seconds"
        print(f"Workflow validation took {validation_time:.4f} seconds")
    finally:
        # Clean up
        if os.path.exists(workflow_path):
            os.remove(workflow_path)

@pytest.mark.performance
def test_memory_usage_large_workflow(test_files_path, temp_output_dir):
    """Test memory usage with a large workflow."""
    try:
        import psutil
    except ImportError:
        pytest.skip("psutil module not installed, skipping memory usage test")
    
    import os
    import sys
    
    # Create a large workflow
    actions = []
    for i in range(100):  # Create 100 actions
        actions.append(create_sample_prompt_action(
            action_id=f"step_{i}",
            inputs=[f"This is a long input string for step {i}. " * 10],  # Longer input
            output=f"output_{i}"
        ))
    
    workflow = create_sample_workflow(actions)
    
    # Create a temp workflow file
    workflow_path = os.path.join(temp_output_dir, "memory_test_workflow.yml")
    with open(workflow_path, 'w') as f:
        yaml.dump(workflow, f)
    
    # Measure memory usage before
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss
    
    # Load the workflow (skip validation to focus on memory used by workflow loading)
    engine = WorkflowEngine(workflow_path, skip_validation=True)
    engine.load_workflow()
    
    # Measure memory usage after
    mem_after = process.memory_info().rss
    
    # Calculate the difference in MB
    memory_used = (mem_after - mem_before) / (1024 * 1024)
    
    # Log the memory usage
    print(f"Memory used for large workflow: {memory_used:.2f} MB")
    
    # Set a reasonable threshold based on your system
    assert memory_used < 100, f"Memory usage too high: {memory_used:.2f} MB"
