#!/usr/bin/env python3
"""
OWLBEAR Pytest Runner

This script runs tests for the OWLBEAR project using pytest.
"""
import os
import sys
import pytest
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("pytest-runner")

def run_tests(test_path=None, markers=None, verbose=True, xvs=False, coverage=False):
    """
    Run tests using pytest.
    
    Args:
        test_path: Specific test path to run (module, directory, or test function)
        markers: Test markers to include (e.g., 'unit', 'integration')
        verbose: Whether to use verbose output
        xvs: Whether to stop after first failure (-xvs option)
        coverage: Whether to collect coverage information
        
    Returns:
        int: pytest exit code (0 for success, non-zero for failure)
    """
    # Determine the test directory
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Build pytest arguments
    pytest_args = []
    
    # Add verbosity
    if verbose:
        pytest_args.append("-v")
    
    # Add stop-after-first-failure
    if xvs:
        pytest_args.extend(["-x", "--showlocals"])
    
    # Add coverage
    if coverage:
        pytest_args.extend(["--cov=owlbear", "--cov-report=term", "--cov-report=html"])
    
    # Add markers
    if markers:
        marker_arg = f"-m {markers}"
        pytest_args.append(marker_arg)
    
    # Add specific test path or use default
    if test_path:
        # Check if it's a relative path within the tests directory
        if not os.path.isabs(test_path) and not test_path.startswith("test_"):
            full_path = os.path.join(test_dir, test_path)
            if os.path.exists(full_path):
                pytest_args.append(full_path)
            else:
                logger.error(f"Test path not found: {full_path}")
                return 1
        else:
            pytest_args.append(test_path)
    else:
        # Run all tests in the tests directory
        pytest_args.append(test_dir)
    
    # Log the pytest command
    logger.info(f"Running pytest with arguments: {' '.join(pytest_args)}")
    
    # Run pytest
    return pytest.main(pytest_args)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OWLBEAR Pytest Runner")
    parser.add_argument("--test", "-t", help="Run a specific test (module, directory, or test function)")
    parser.add_argument("--markers", "-m", help="Run tests with specific markers (e.g., 'unit', 'integration')")
    parser.add_argument("--quiet", "-q", action="store_true", help="Disable verbose output")
    parser.add_argument("--xvs", "-x", action="store_true", help="Stop after first failure (-xvs option)")
    parser.add_argument("--coverage", "-c", action="store_true", help="Collect coverage information")
    
    args = parser.parse_args()
    
    # Run tests with specified options
    exit_code = run_tests(
        test_path=args.test,
        markers=args.markers,
        verbose=not args.quiet,
        xvs=args.xvs,
        coverage=args.coverage
    )
    
    # Exit with the pytest exit code
    sys.exit(exit_code)
