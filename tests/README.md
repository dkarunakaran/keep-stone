# KeepStone Test Suite

This directory contains comprehensive tests for the KeepStone application.

## Test Structure

### Test Files
- `conftest.py` - Test configuration and fixtures
- `test_config_utils.py` - Configuration utility tests
- `test_models.py` - Database model tests
- `test_utility.py` - Utility function tests
- `test_routes.py` - Flask route and API tests
- `test_config.py` - Test configuration constants

### Test Categories
Tests are organized with pytest markers:
- `unit` - Unit tests for individual functions
- `integration` - Integration tests for component interaction  
- `api` - API endpoint tests
- `database` - Database operation tests
- `config` - Configuration system tests

## Running Tests

### Prerequisites
```bash
# Install test dependencies
pip install -r test-requirements.txt

# Or install individually
pip install pytest pytest-cov pytest-mock
```

### Basic Usage
```bash
# Run all tests
python simple_runner.py

# Run with verbose output
python simple_runner.py --verbose

# Run specific test category
python simple_runner.py --category=unit
python simple_runner.py --category=integration
python simple_runner.py --category=api
python simple_runner.py --category=database
```

### Advanced Usage with pytest
```bash
# Run all tests with coverage
pytest --cov=../ --cov-report=html

# Run specific test file
pytest test_config_utils.py -v

# Run tests matching pattern
pytest -k "test_config" -v

# Run with specific markers
pytest -m "unit and config" -v
```

## Test Configuration

### Environment Setup
Tests use isolated environments with:
- In-memory SQLite database
- Temporary file directories
- Mock configurations
- Disabled CSRF protection

### Fixtures Available
- `test_config` - Test configuration data
- `temp_config_file` - Temporary YAML config file
- `mock_app` - Flask application instance
- `mock_db` - Database with test data

### Mocking Strategy
Due to import limitations, tests use extensive mocking:
- SQLAlchemy models are mocked
- Flask components are mocked
- File system operations are mocked
- External dependencies are mocked

## Test Coverage

### Configuration Tests (`test_config_utils.py`)
- ✅ Config file loading and parsing
- ✅ Dictionary flattening with dot notation
- ✅ Settings filtering for editability
- ✅ Error handling for invalid configs

### Model Tests (`test_models.py`)
- ✅ Database model creation and relationships
- ✅ Configuration model CRUD operations
- ✅ Data validation and constraints
- ✅ Model method functionality

### Utility Tests (`test_utility.py`)
- ✅ Email utility functions
- ✅ File handling operations
- ✅ Data processing utilities
- ✅ Helper function validation

### Route Tests (`test_routes.py`)
- ✅ Flask route responses
- ✅ Form handling and validation
- ✅ Template rendering
- ✅ API endpoint functionality

## Expected Results

### Successful Test Run
```
============================= test session starts ==============================
collected 24 items

test_config_utils.py ......                                            [ 25%]
test_models.py ......                                                  [ 50%]
test_utility.py ....                                                   [ 66%]
test_routes.py ........                                                [100%]

============================= 24 passed in 2.34s ==============================
```

### Test Categories Breakdown
- **Unit Tests**: ~12 tests covering individual functions
- **Integration Tests**: ~6 tests covering component interaction
- **API Tests**: ~4 tests covering HTTP endpoints
- **Database Tests**: ~2 tests covering data operations

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Tests use mocking to handle missing dependencies
   - Check that test-requirements.txt is installed
   - Verify Python path includes parent directory

2. **Database Errors**
   - Tests use in-memory database
   - Check SQLAlchemy configuration
   - Verify model definitions are correct

3. **Configuration Errors**
   - Tests create temporary config files
   - Check YAML syntax in test configurations
   - Verify config structure matches expected format

### Debug Mode
```bash
# Run with maximum verbosity
pytest -vvv --tb=long

# Run single test with debugging
pytest test_config_utils.py::test_load_config -vvv --tb=long

# Check test discovery
pytest --collect-only
```

## Development Notes

### Adding New Tests
1. Create test functions with `test_` prefix
2. Use appropriate pytest markers
3. Include docstrings explaining test purpose
4. Mock external dependencies
5. Use fixtures for common setup

### Test Data Management
- Test data is defined in `test_config.py`
- Use fixtures for reusable test data
- Keep test data isolated and minimal
- Clean up temporary files in teardown

### Best Practices
- Each test should be independent
- Use descriptive test names
- Test both success and failure cases
- Mock external dependencies
- Keep tests fast and focused

## Integration with CI/CD

Tests are designed to run in automated environments:
- No external dependencies required
- All file operations use temporary directories
- Database operations use in-memory storage
- Mock external services and APIs

Example CI configuration:
```yaml
test:
  script:
    - cd keepstone/tests
    - pip install -r test-requirements.txt
    - python simple_runner.py --verbose
```
