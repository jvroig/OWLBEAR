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
        engine = WorkflowEngine(workflow_path)
        
        # Load the workflow
        result = engine.load_workflow()
        self.assertTrue(result, "Failed to load workflow")
        
        # Count actions before expansion
        actions_before = len(engine.workflow['ACTIONS'])
        
        # Get the number of COMPLEX actions
        complex_actions = sum(1 for action in engine.workflow['ACTIONS'] if 'COMPLEX' in action)
        self.assertGreater(complex_actions, 0, "No COMPLEX actions found in test workflow")
        
        # Call the expansion method directly
        engine._expand_complex_actions()
        
        # Verify that expansion occurred
        actions_after = len(engine.workflow['ACTIONS'])
        self.assertGreater(actions_after, actions_before, 
                          "Complex action expansion did not increase the number of actions")
        
        # Verify that no COMPLEX actions remain
        remaining_complex = sum(1 for action in engine.workflow['ACTIONS'] if 'COMPLEX' in action)
        self.assertEqual(remaining_complex, 0, "Some COMPLEX actions were not expanded")

    @patch('owlbear.call_agent')
    def test_workflow_execution(self, mock_call_agent):
        """Test workflow execution with mocked expert calls"""
        # Setup mock to return a simple response
        mock_response = {
            'history': [
                {'role': 'user', 'content': 'Test prompt'},
                {'role': 'assistant', 'content': 'Test response'}
            ],
            'final_answer': 'Test response'
        }
        mock_call_agent.return_value = mock_response
        
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

if __name__ == "__main__":
    unittest.main()
