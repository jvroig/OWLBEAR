# OWLBEAR Testing Framework

This directory contains tests and test data for the OWLBEAR project.

## Directory Structure

- `sample_complex_actions/`: Contains sample complex action templates for testing
- `sample_workflows/`: Contains sample workflows for testing
  - `sequences/`: Sample workflow sequences
  - `strings/`: Sample string files
- `test_scripts/`: Contains Python test scripts
- `run_tests.py`: Main test runner script

## Running Tests

To run all tests:

```bash
python3 tests/run_tests.py
```

To run a specific test:

```bash
python3 tests/run_tests.py --test test_complex_actions
```

## Test Data

The `sample_complex_actions` and `sample_workflows` directories contain test data that's separate from the actual project data. This ensures tests won't be affected by changes to the actual workflow files and complex action templates.

## Adding New Tests

To add a new test:

1. Create a new test script in the `test_scripts` directory
2. Add any necessary test data to the appropriate directories
3. Make sure your test script returns 0 on success and non-zero on failure

## Test Scripts

Current test scripts:

- `test_complex_action_loading.py`: Tests loading complex action templates
- `test_complex_actions.py`: Tests expanding complex actions and their integration in workflows
- `test_workflow_validator.py`: Tests the workflow validator with various workflow configurations
- `test_owlbear_engine.py`: Tests the main OWLBEAR engine (workflow loading, expansion, and execution)

## Notes

- Tests should be independent and not rely on state from other tests
- Tests should clean up after themselves (e.g., remove any created files)
- Tests should provide clear output to help diagnose failures
