# Dagger Testing Example

A minimal example demonstrating how to run Python unit tests and end-to-end tests using Dagger.

## Project Structure

```
dagger-testing-example/
├── dagger.json              # Dagger configuration
├── dagger_module/           # Dagger module (instead of .dagger)
│   └── src/
│       └── dagger_testing/
│           ├── __init__.py
│           └── main.py      # Dagger functions
├── pyproject.toml           # Python project config
├── src/                     # Application code
│   ├── __init__.py
│   └── hello_world.py       # FastAPI application
└── tests/                   # Test suites
    ├── __init__.py
    ├── e2e/                 # End-to-end tests
    │   ├── __init__.py
    │   └── test_api_integration.py
    └── unit/                # Unit tests
        ├── __init__.py
        └── test_hello_world.py
```

## Prerequisites

- Python 3.11+
- Dagger CLI installed ([installation guide](https://docs.dagger.io/install))

## Setup

1. Clone or copy this example directory
2. Navigate to the project directory:
   ```bash
   cd dagger-testing-example
   ```

## Running Tests with Dagger

### Run Unit Tests

```bash
dagger call unit-tests --source .
```

This will:
- Build a Python container with test dependencies
- Run pytest on the `tests/unit` directory
- Return the test results

### Run End-to-End Tests

```bash
dagger call e-2-e-tests --source .
```

Note: Dagger converts function names with underscores to kebab-case.

This will:
- Start the FastAPI service in a container
- Run tests that make real HTTP requests to the service
- Return the test results

### Run All Tests

```bash
dagger call all-tests --source .
```

This runs both unit and e2e tests sequentially.

## Running Tests Locally (without Dagger)

If you want to run tests locally:

```bash
# Install dependencies
pip install -e ".[test]"

# Run unit tests
pytest tests/unit -v

# Run the FastAPI app (in one terminal)
python -m src.hello_world

# Run e2e tests (in another terminal)
API_BASE_URL=http://localhost:8000 pytest tests/e2e -v
```

## How It Works

### Dagger Module (`dagger_module/src/dagger_testing/main.py`)

The Dagger module defines functions that:
- Build isolated test environments
- Install dependencies
- Run tests in containers
- Start services for e2e testing

### Test Organization

- **Unit Tests**: Test individual functions and endpoints using FastAPI's TestClient
- **E2E Tests**: Test the full service by making real HTTP requests

### Key Benefits

1. **Consistency**: Tests run in the same environment every time
2. **Isolation**: No local environment pollution
3. **Caching**: Dependencies are cached between runs
4. **CI/CD Ready**: Same commands work locally and in pipelines

## Extending This Example

To adapt this for your own project:

1. Replace `src/hello_world.py` with your application
2. Update the service startup command in `dagger_module/src/dagger_testing/main.py`
3. Add your tests to the appropriate directories
4. Update dependencies in `pyproject.toml`

## Important Notes

### Dagger Module Configuration

The Dagger module requires:
1. A `pyproject.toml` in the `dagger_module/` directory with the correct entry point
2. The class name must match what's configured in the entry point
3. The SDK is automatically downloaded when running `dagger develop`

### Known Issues

- E2E tests may take longer to run as they start a real service
- The type checker may show warnings about Dagger imports (these can be ignored)

## Troubleshooting

### Import Errors

Make sure your Python code is in the `src/` directory and tests import from there:
```python
from src.your_module import your_function
```

### Dagger Not Found

Ensure Dagger is installed and the daemon is running:
```bash
dagger version
```

### Tests Not Found

Ensure test files follow the naming convention:
- `test_*.py` or `*_test.py`
- Test functions start with `test_`