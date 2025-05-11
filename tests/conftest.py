"""
OWLBEAR pytest configuration and shared fixtures.
"""
import os
import sys
import shutil
import pytest
import yaml
from unittest.mock import patch

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import components needed for testing
from owlbear import WorkflowEngine
from workflow_validator import WorkflowValidator
from actions.complex import load_complex_action, expand_complex_action

@pytest.fixture
def test_files_path():
    """Fixture to get paths relative to the tests directory."""
    def _get_path(relative_path):
        test_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(test_dir, relative_path)
    return _get_path

@pytest.fixture
def temp_output_dir(test_files_path):
    """Fixture to create and clean up a temporary output directory."""
    output_dir = test_files_path("outputs/pytest_temp")
    
    # Create the directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Return the path for tests to use
    yield output_dir
    
    # Clean up (uncomment to enable cleanup after tests)
    # shutil.rmtree(output_dir)

@pytest.fixture
def complex_action_path():
    """Fixture to get the path to the sample complex actions directory."""
    def _get_complex_action_path(action_name):
        test_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(test_dir, f"sample_complex_actions/{action_name}.yml")
    return _get_complex_action_path

# Add a monkey patch for the complex action loading function
@pytest.fixture(autouse=True)
def patch_complex_action_loader(monkeypatch):
    """
    Monkey patch the load_complex_action function to look in the test directory.
    This is applied to all tests automatically.
    """
    import logging  # Add missing import
    
    def mock_load_complex_action(action_name):
        test_dir = os.path.dirname(os.path.abspath(__file__))
        # Try with both file extensions
        for ext in ['.yml', '.yaml']:
            action_path = os.path.join(test_dir, f"sample_complex_actions/{action_name}{ext}")
            if os.path.exists(action_path):
                try:
                    with open(action_path, 'r') as file:
                        return yaml.safe_load(file)
                except Exception as e:
                    logger = logging.getLogger("workflow-engine.complex")
                    logger.error(f"Failed to load complex action '{action_name}': {str(e)}")
                    return None
        
        # If we get here, the file was not found
        logger = logging.getLogger("workflow-engine.complex")
        logger.error(f"Complex action '{action_name}' not found in {test_dir}/sample_complex_actions")
        return None
    
    # Apply the monkey patch directly to actions.complex module
    import actions.complex
    monkeypatch.setattr(actions.complex, 'load_complex_action', mock_load_complex_action)

@pytest.fixture
def mock_expert_call():
    """Fixture to mock expert calls in workflows."""
    with patch('owlbear.call_agent') as mock:
        # Setup default response behavior
        def default_response(expert, prompt):
            # Convert any non-string prompt to a string to avoid serialization issues
            if not isinstance(prompt, str):
                prompt = str(prompt)
                
            # Create a properly structured response
            return {
                'history': [
                    {'role': 'user', 'content': prompt},
                    {'role': 'assistant', 'content': f'Mock response from {expert}'}
                ],
                'final_answer': f'Mock response from {expert}'
            }
        
        # Set the default side effect
        mock.side_effect = default_response
        
        # Return the mock for customization in tests
        yield mock
        
@pytest.fixture
def mock_decide_call():
    """Fixture to mock DECIDE calls with configurable decisions."""
    # Setup mock to return proper decide responses
    def decide_response_factory(decisions):
        """Create a function that returns decide responses based on a sequence."""
        call_count = 0
        
        def get_response(expert, prompt):
            nonlocal call_count
            # Only increment for DECIDE-like prompts
            if isinstance(prompt, str) and any(term in prompt.lower() for term in ['decide', 'evaluate', 'true', 'false']):
                # Get the decision (True/False) - default to True if we run out
                decision_index = min(call_count, len(decisions)-1)
                decision = decisions[decision_index]
                call_count += 1
                
                # Create a properly formatted response
                content = f'{{"explanation": "Test explanation", "decision": {str(decision).lower()}}}'
                return {
                    'history': [
                        {'role': 'user', 'content': prompt},
                        {'role': 'assistant', 'content': content}
                    ],
                    'final_answer': content
                }
            else:
                # Safety check for non-string prompts (like MagicMock objects)
                if not isinstance(prompt, str):
                    prompt = "Non-string prompt"
                
                # Regular prompt response
                return {
                    'history': [
                        {'role': 'user', 'content': prompt},
                        {'role': 'assistant', 'content': f'Mock response from {expert}'}
                    ],
                    'final_answer': f'Mock response from {expert}'
                }
        
        return get_response
    
    # Use a new patch for each call to avoid shared state
    def setup_decisions(decision_sequence):
        # Ensure we have at least one decision
        if not decision_sequence:
            decision_sequence = [True]
        
        mock = patch('owlbear.call_agent').start()
        mock.side_effect = decide_response_factory(decision_sequence)
        return mock
    
    # Clean up any patches after the test
    yield setup_decisions
    patch.stopall()

@pytest.fixture
def sample_workflow_factory(test_files_path):
    """Fixture to create temporary test workflows."""
    created_files = []
    
    def create_workflow(num_steps=2, include_decide=False, id_based_loopback=True):
        """Create a sample workflow with specified characteristics.
        
        Args:
            num_steps: Number of action steps
            include_decide: Whether to include a DECIDE action
            id_based_loopback: Whether to use ID-based loopback (vs. numeric)
            
        Returns:
            Path to the created workflow file
        """
        actions = []
        
        # Add PROMPT actions
        for i in range(num_steps - (1 if include_decide else 0)):
            actions.append({
                'PROMPT': {
                    'id': f'step_{i}',
                    'expert': 'CEO',
                    'inputs': [f'Test prompt for step {i}'],
                    'output': f'output_{i}'
                }
            })
        
        # Add DECIDE action if requested
        if include_decide:
            decide_action = {
                'DECIDE': {
                    'expert': 'CEO',
                    'inputs': ['Decide if this meets requirements', 'output_0'],
                    'output': 'decision_result'
                }
            }
            
            if id_based_loopback:
                decide_action['DECIDE']['loopback_target'] = 'step_0'
            else:
                # For testing backward compatibility (should fail with updated code)
                decide_action['DECIDE']['loopback'] = 1
                
            decide_action['DECIDE']['loop_limit'] = 3
            actions.append(decide_action)
        
        # Create the workflow object
        workflow = {
            'STRINGS': {
                'STR_test': 'This is a test string'
            },
            'ACTIONS': actions
        }
        
        # Write the workflow to a file
        output_path = test_files_path(f"outputs/pytest_temp/test_workflow_{len(created_files)}.yml")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            yaml.dump(workflow, f)
            
        created_files.append(output_path)
        return output_path
    
    # Return the factory function
    yield create_workflow
    
    # Clean up created files
    for file_path in created_files:
        if os.path.exists(file_path):
            os.remove(file_path)
