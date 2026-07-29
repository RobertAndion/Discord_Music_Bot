# Testing Guide

## Running Tests

### Run all tests:
```bash
pytest
```

### Run specific test file:
```bash
pytest tests/test_music_cog.py
```

### Run with coverage report:
```bash
pytest --cov=. --cov-report=html
```

### Run only unit tests:
```bash
pytest -m "not integration"
```

### Run only integration tests:
```bash
pytest -m integration
```

## Test Structure

- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test complete workflows and interactions
- **Mock Objects**: Use Discord API and Lavalink mocks for testing

## Coverage Goals

- Target: 80%+ coverage
- Focus on core functionality first
- Priority: Music cog, file processing, error handling

## Adding New Tests

1. Create test file following naming: `test_<module>.py`
2. Use descriptive test names: `test_<functionality>_<condition>`
3. Mock external dependencies (Discord, Lavalink)
4. Test both success and failure cases
5. Add appropriate markers: `@pytest.mark.unit` or `@pytest.mark.integration`
