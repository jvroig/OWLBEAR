#!/usr/bin/env python3
"""
Test script for owlbear.py - Tests the main workflow engine
"""
import os
import sys
import yaml
import logging
import unittest
from unittest.mock import patch, MagicMock

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import the WorkflowEngine class from owlbear.py
from owlbear import WorkflowEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test-owlbear-engine")

def get_test_file_path(relative_path):
    """Helper to get a path relative to the tests directory"""
    test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(test_dir, relative_path)

class TestOwlbearEngine(unittest.TestCase):
    """Unit tests for the OWLBEAR engine"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Note: We don't need to create an output directory as WorkflowEngine
        # creates it automatically based on the workflow name and timestamp
        pass
    
    def test_load_workflow(self):
        """Test loading a workflow with complex actions"""
        # Create a workflow engine instance with a test workflow
        workflow_path = get_test_file_path("sample_workflows/sequences/test_complex.yml")
        engine = WorkflowEngine(workflow_path)
        
        # Test loading the workflow
        result = engine.load_workflow()
        self.assertTrue(result, "Failed to load workflow")
        
        # Verify that ACTIONS were loaded
        self.assertIn('ACTIONS', engine.workflow, "ACTIONS section not found in loaded workflow")
        self.assertGreater(len(engine.workflow['ACTIONS']), 0, "No actions found in loaded workflow")

    def test_complex_action_expansion(self):
        """Test expansion of complex actions in the workflow"""
        # Create a workflow engine instance with a test workflow
        workflow_path = get_test_file_path("sample_workflows/sequences/test_complex.yml")
        
        # Just as a debug check, ensure file exists
        self.assertTrue(os.path.exists(workflow_path), f"Test workflow file not found: {workflow_path}")
        
        # Print workflow content for debugging
        with open(workflow_path, 'r') as f:
            workflow_content = f.read()
            # Verify COMPLEX is actually in the file
            self.assertIn("COMPLEX:", workflow_content, "COMPLEX action not found in workflow file")
        
        # Create a new version for testing expansion directly
        with open(workflow_path, 'r') as f:
            original_workflow = yaml.safe_load(f)
            
        # Verify the original workflow has COMPLEX actions
        complex_actions_original = sum(1 for action in original_workflow['ACTIONS'] if 'COMPLEX' in action)
        self.assertGreater(complex_actions_original, 0, "No COMPLEX actions found in original workflow")
        
        # Now use the engine to load and expand
        engine = WorkflowEngine(workflow_path)
        result = engine.load_workflow()
        self.assertTrue(result, "Failed to load workflow")
        
        # ACTIONS should be expanded by now since expansion happens in load_workflow()
        # Verify that no COMPLEX actions remain in the loaded workflow
        remaining_complex = sum(1 for action in engine.workflow['ACTIONS'] if 'COMPLEX' in action)
        self.assertEqual(remaining_complex, 0, "Complex actions were not automatically expanded during loading")
        
        # Verify the number of actions increased after expansion
        self.assertGreater(len(engine.workflow['ACTIONS']), len(original_workflow['ACTIONS']), 
                         "Complex action expansion did not increase the number of actions")

    @patch('owlbear.call_agent')
    def test_workflow_execution(self, mock_call_agent):
        """Test workflow execution with mocked expert calls"""
        # Setup a dynamic mock that returns different responses based on the context
        def mock_call_agent_func(expert, prompt):
            # For PROMPT actions, return a simple response
            default_response = {
                'history': [
                    {'role': 'user', 'content': prompt},
                    {'role': 'assistant', 'content': 'Test response for prompt: ' + prompt[:30] + '...'}
                ],
                'final_answer': 'Test response for prompt: ' + prompt[:30] + '...'
            }
            
            # For DECIDE actions, return a structured response with a decision
            if 'TRUE' in prompt or 'true' in prompt:
                decide_response = {
                    'history': [
                        {'role': 'user', 'content': prompt},
                        {'role': 'assistant', 'content': '{"explanation": "This is a test explanation", "decision": true}'}
                    ],
                    'final_answer': '{"explanation": "This is a test explanation", "decision": true}'
                }
                return decide_response
                
            return default_response
            
        # Use the dynamic mock
        mock_call_agent.side_effect = mock_call_agent_func
        
        # Create a workflow engine instance with a simplified test workflow
        workflow_path = get_test_file_path("sample_workflows/sequences/test_complex.yml")
        engine = WorkflowEngine(workflow_path, skip_validation=True)
        
        # Run the workflow
        result = engine.run()
        
        # Verify that the workflow ran successfully
        self.assertTrue(result, "Workflow execution failed")
        
        # Verify that the mock was called at least once
        mock_call_agent.assert_called()
        
        # Check if output directory was created (should be in WorkflowEngine.output_dir)
        self.assertIsNotNone(engine.output_dir, "Output directory was not created")
        self.assertTrue(os.path.exists(engine.output_dir), "Output directory does not exist")
        
        # Check if output files were created
        output_files = os.listdir(engine.output_dir)
        self.assertGreater(len(output_files), 0, "No output files were created")

    @patch('owlbear.call_agent')
    def test_decide_workflow(self, mock_call_agent):
        """Test workflow execution with DECIDE actions"""
        # Track calls to the mock to verify proper decision handling
        call_count = 0
        
        # Setup a dynamic mock that simulates decision-making
        def mock_call_agent_func(expert, prompt):
            nonlocal call_count
            call_count += 1
            
            # For the first DECIDE call, return FALSE to trigger a loop back
            # For the second DECIDE call, return TRUE to allow the workflow to continue
            if 'decide if it meets' in prompt.lower():  # This is specific to our test workflow
                # First time we see a DECIDE, return FALSE (to test loopback)
                if call_count == 2:  # This would be the first DECIDE after initial PROMPT
                    decide_response_false = {
                        'history': [
                            {'role': 'user', 'content': prompt},
                            {'role': 'assistant', 'content': '{"explanation": "Needs improvement", "decision": false}'}
                        ],
                        'final_answer': '{"explanation": "Needs improvement", "decision": false}'
                    }
                    return decide_response_false
                # Second time, return TRUE to let workflow proceed
                else:
                    decide_response_true = {
                        'history': [
                            {'role': 'user', 'content': prompt},
                            {'role': 'assistant', 'content': '{"explanation": "Looks good now", "decision": true}'}
                        ],
                        'final_answer': '{"explanation": "Looks good now", "decision": true}'
                    }
                    return decide_response_true
            
            # Default response for PROMPT actions
            return {
                'history': [
                    {'role': 'user', 'content': prompt},
                    {'role': 'assistant', 'content': f'Response #{call_count}: Test response'}
                ],
                'final_answer': f'Response #{call_count}: Test response'
            }
        
        # Use the dynamic mock
        mock_call_agent.side_effect = mock_call_agent_func
        
        # Create a workflow engine instance with a workflow that includes DECIDE actions
        workflow_path = get_test_file_path("sample_workflows/sequences/test_decide.yml")
        engine = WorkflowEngine(workflow_path, skip_validation=True)
        
        # Run the workflow
        result = engine.run()
        
        # Verify that the workflow ran successfully
        self.assertTrue(result, "Workflow execution failed")
        
        # Verify that the mock was called multiple times (at least 4 times):
        # 1. Initial PROMPT
        # 2. First DECIDE (returns FALSE)
        # 3. PROMPT again (due to loopback)
        # 4. Second DECIDE (returns TRUE)
        # 5. Final PROMPT
        self.assertGreaterEqual(mock_call_agent.call_count, 4, 
                              "The mock should be called at least 4 times for this workflow")
        
        # Check if output files were created for each step
        output_files = os.listdir(engine.output_dir)
        self.assertGreaterEqual(len(output_files), 4, 
                              "Not enough output files were created, suggesting loopback didn't work")

if __name__ == "__main__":
    unittest.main()
