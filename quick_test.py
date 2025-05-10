#!/usr/bin/env python3
import yaml
import os
import logging
from actions.complex import load_complex_action, expand_complex_action

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("quick-test")

def test_complex_action_loading():
    """Test loading the complex action from YAML"""
    action_name = "polished_output"
    complex_def = load_complex_action(action_name)
    
    if complex_def:
        logger.info(f"Successfully loaded complex action: {action_name}")
        logger.info(f"Complex action YAML structure:")
        print(yaml.dump(complex_def, default_flow_style=False))
        return True
    else:
        logger.error(f"Failed to load complex action: {action_name}")
        return False

if __name__ == "__main__":
    if test_complex_action_loading():
        print("\nTest successful!")
        exit(0)
    else:
        print("\nTest failed!")
        exit(1)
