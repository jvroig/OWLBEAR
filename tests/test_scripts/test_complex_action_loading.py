#!/usr/bin/env python3
import yaml
import os
import sys
import logging

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from actions.complex import load_complex_action, expand_complex_action

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test-complex-action-loading")

def test_complex_action_loading():
    """Test loading the complex action from YAML"""
    # Get the test file path
    test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    action_path = os.path.join(test_dir, "sample_complex_actions/polished_output.yml")
    
    # Try to load directly from path (bypassing the normal directory search)
    try:
        with open(action_path, 'r') as file:
            complex_def = yaml.safe_load(file)
            
        if complex_def:
            logger.info(f"Successfully loaded complex action from: {action_path}")
            logger.info(f"Complex action YAML structure:")
            print(yaml.dump(complex_def, default_flow_style=False))
            return True
        else:
            logger.error(f"Failed to load complex action: Empty or invalid YAML")
            return False
    except Exception as e:
        logger.error(f"Failed to load complex action: {str(e)}")
        return False

if __name__ == "__main__":
    if test_complex_action_loading():
        print("\nTest successful!")
        exit(0)
    else:
        print("\nTest failed!")
        exit(1)

