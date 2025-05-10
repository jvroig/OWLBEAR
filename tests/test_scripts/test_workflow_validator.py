#!/usr/bin/env python3
# test_workflow_validator.py - Test script for workflow validator

import os
import sys
import yaml

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from workflow_validator import validate_workflow

def get_test_file_path(relative_path):
    """Helper to get a path relative to the tests directory"""
    test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(test_dir, relative_path)

def main():
    """Test the workflow validator with various workflows."""
    # Sample workflows to test
    test_workflows = [
        # Simple workflow test
        {
            "name": "Simple workflow test",
            "workflow": get_test_file_path("sample_workflows/sequences/test_complex.yml"),
            "strings": None
        },
        # Workflow with variables test
        {
            "name": "Complex workflow with variables test",
            "workflow": get_test_file_path("sample_workflows/sequences/test_comparative.yml"),
            "strings": get_test_file_path("sample_workflows/strings/test_strings.yaml")
        }
    ]
    
    # Create a test output directory
    test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(test_dir, "outputs/validator_test")
    os.makedirs(output_dir, exist_ok=True)
    
    # Run validation tests
    success_count = 0
    failure_count = 0
    
    for i, test in enumerate(test_workflows):
        print(f"\n--- Test {i+1}: {test['name']} ---")
        print(f"Workflow: {test['workflow']}")
        if test['strings']:
            print(f"Strings: {test['strings']}")
        
        # Create test-specific output directory
        test_output_dir = os.path.join(output_dir, f"test_{i+1}")
        os.makedirs(test_output_dir, exist_ok=True)
        
        # Run validation
        success, output_path = validate_workflow(
            test['workflow'], 
            test['strings'], 
            test_output_dir
        )
        
        if success:
            print(f"✅ Validation successful: {output_path}")
            # For brevity in test output, only print a short confirmation
            print("  Expanded workflow generated successfully.")
            success_count += 1
        else:
            print(f"❌ Validation failed!")
            failure_count += 1
    
    print("\nTest Summary:")
    print(f"Total tests: {len(test_workflows)}")
    print(f"Successes: {success_count}")
    print(f"Failures: {failure_count}")
    
    return failure_count == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
