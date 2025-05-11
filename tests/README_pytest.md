# OWLBEAR Pytest Testing Framework

This directory contains the pytest-based testing framework for the OWLBEAR project.

## Framework Structure

- `unit/`: Unit tests for individual components
- `integration/`: Integration tests for system interactions
- `utils/`: Testing utilities and helpers
- `conftest.py`: pytest configuration and fixtures
- `run_pytest.py`: Script to run pytest tests

## Running Tests

### Using pytest directly

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_workflow_validator.py

# Run specific test function
pytest tests/unit/test_workflow_validator.py::test_workflow_validator_initializes

# Run tests with specific markers
pytest -m unit
pytest -m integration

# Run tests with coverage reporting
pytest --cov=owlbear
```

### Using the run_pytest.py script

```bash
# Run all tests
python tests/run_pytest.py

# Run specific test
python tests/run_pytest.py --test unit/test_workflow_validator.py

# Run tests with coverage
python tests/run_pytest.py --coverage

# Run tests with specific markers
python tests/run_pytest.py --markers integration

# Stop after first failure (with details)
python tests/run_pytest.py --xvs
```

## Test Categories

Tests are organized using pytest markers:

- `unit`: Tests for individual components in isolation
- `integration`: Tests for interactions between components
- `performance`: Tests that measure performance metrics
- `regression`: Tests that prevent previously fixed bugs from returning

## Adding New Tests

1. **Unit Tests**: Add new tests to `tests/unit/` with filename pattern `test_*.py`
2. **Integration Tests**: Add to `tests/integration/` with filename pattern `test_*.py`
3. **Test Naming**: Test functions should start with `test_`
4. **Markers**: Use appropriate markers for your tests: `@pytest.mark.unit`, `@pytest.mark.integration`, etc.

## Test Fixtures

Common test fixtures are defined in `conftest.py`:

- `test_files_path`: Helper to resolve paths relative to the tests directory
- `temp_output_dir`: Creates and cleans up a temporary output directory
- `mock_expert_call`: Mocks expert calls with configurable responses
- `mock_decide_call`: Mocks DECIDE action calls with configurable decision sequences
- `sample_workflow_factory`: Creates sample workflows for testing

## Helper Functions

The `tests/utils/test_helpers.py` module provides helper functions:

- `temp_workflow_file`: Context manager for creating temporary workflow files
- `create_sample_prompt_action`: Creates sample PROMPT actions
- `create_sample_decide_action`: Creates sample DECIDE actions
- `create_sample_complex_action`: Creates sample COMPLEX actions
- `create_sample_workflow`: Creates sample workflows
- `create_mock_expert_response`: Creates mock expert responses
- `create_mock_decide_response`: Creates mock DECIDE responses

## Best Practices

1. **Isolation**: Tests should be independent and not rely on state from other tests
2. **Mocking**: Use mocks for external dependencies (like expert calls)
3. **Fixtures**: Use fixtures for common setup and teardown
4. **Assertions**: Make specific assertions that clearly indicate what's being tested
5. **Documentation**: Document the purpose of each test and what it's verifying
6. **Cleanup**: Tests should clean up after themselves (temp files, directories, etc.)
