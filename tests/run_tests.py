#!/usr/bin/env python3
"""
OWLBEAR Test Runner

This script runs all tests for the OWLBEAR project.
"""
import os
import sys
import subprocess
import logging
import glob
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test-runner")

def run_test(test_script_path):
    """Run a single test script and return True if successful"""
    logger.info(f"Running test: {os.path.basename(test_script_path)}")
    result = subprocess.run([sys.executable, test_script_path], capture_output=True, text=True)
    
    # Log the output
    if result.stdout:
        logger.info(f"Test output:\n{result.stdout}")
    if result.stderr:
        logger.error(f"Test errors:\n{result.stderr}")
    
    if result.returncode == 0:
        logger.info(f"Test passed: {os.path.basename(test_script_path)}")
        return True
    else:
        logger.error(f"Test failed: {os.path.basename(test_script_path)}")
        return False

def run_all_tests():
    """Run all test scripts in the test_scripts directory"""
    # Get the test scripts directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_scripts_dir = os.path.join(current_dir, "test_scripts")
    
    # Find all Python files in the test_scripts directory
    test_files = glob.glob(os.path.join(test_scripts_dir, "*.py"))
    
    if not test_files:
        logger.error("No test scripts found!")
        return False
    
    logger.info(f"Found {len(test_files)} test scripts")
    
    # Run each test
    success_count = 0
    failure_count = 0
    
    for test_file in test_files:
        if run_test(test_file):
            success_count += 1
        else:
            failure_count += 1
    
    # Print summary
    logger.info("=" * 50)
    logger.info(f"Test Summary: {success_count} passed, {failure_count} failed")
    logger.info("=" * 50)
    
    return failure_count == 0

def run_specific_test(test_name):
    """Run a specific test by name"""
    # Get the test scripts directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_scripts_dir = os.path.join(current_dir, "test_scripts")
    
    # Build the path to the test script
    if not test_name.endswith(".py"):
        test_name += ".py"
    
    test_path = os.path.join(test_scripts_dir, test_name)
    
    if not os.path.exists(test_path):
        logger.error(f"Test script not found: {test_name}")
        return False
    
    return run_test(test_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OWLBEAR Test Runner")
    parser.add_argument("--test", help="Run a specific test by name (e.g., test_complex_actions)")
    
    args = parser.parse_args()
    
    if args.test:
        success = run_specific_test(args.test)
    else:
        success = run_all_tests()
    
    sys.exit(0 if success else 1)
