#!/usr/bin/env python3
# test_validator.py - Test script for workflow validator

import os
import sys
from workflow_validator import validate_workflow, format_expanded_workflow_summary

def main():
    """Test the workflow validator with various workflows."""
    # Sample workflows to test
    test_workflows = [
        # Simple workflow
        {
            "name": "Simple workflow test",
            "workflow": "workflows/sequences/helloworld.yml",
            "strings": None
        },
        # Workflow with external strings
        {
            "name": "External strings test",
            "workflow": "workflows/sequences/flow_external_strings.yml",
            "strings": "workflows/strings/strings_sample.yaml"
        },
        # Workflow with variables
        {
            "name": "Variables test",
            "workflow": "workflows/sequences/variables_demo.yml",
            "strings": "workflows/strings/variables_example.yaml"
        },
        # Workflow with deliberate validation errors
        {
            "name": "Validation errors test",
            "workflow": "workflows/sequences/validation_test.yml",
            "strings": None
        }
    ]
    
    # Create a test output directory
    output_dir = "outputs/validator_test"
    os.makedirs(output_dir, exist_ok=True)
    
    # Run validation tests
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
        else:
            print(f"❌ Validation failed!")
    
    print("\nAll tests completed.")

if __name__ == "__main__":
    main()
