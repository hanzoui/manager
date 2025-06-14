# ComfyUI-Manager Tests

This directory contains unit tests for ComfyUI-Manager components.

## Running Tests

### Using the Virtual Environment

```bash
# From the project root
/path/to/comfyui/.venv/bin/python -m pytest tests/ -v
```

### Using the Test Runner

```bash
# Run all tests
python run_tests.py

# Run specific tests
python run_tests.py -k test_task_queue

# Run with coverage
python run_tests.py --cov
```

## Test Structure

### test_task_queue.py

Comprehensive tests for the TaskQueue functionality including:

- **Basic Operations**: Initialization, adding/removing tasks, state management
- **Batch Tracking**: Automatic batch creation, history saving, finalization
- **Thread Safety**: Concurrent access, worker lifecycle management
- **Integration Testing**: Full task processing workflow
- **Edge Cases**: Empty queues, invalid data, exception handling

**Key Features Tested:**
- ✅ Task queueing with Pydantic model validation
- ✅ Batch history tracking and persistence
- ✅ Thread-safe concurrent operations
- ✅ Worker thread lifecycle management
- ✅ WebSocket message tracking
- ✅ State snapshots and transitions

### MockTaskQueue

The tests use a `MockTaskQueue` class that:
- Isolates testing from global state and external dependencies
- Provides dependency injection for mocking external services
- Maintains the same API as the real TaskQueue
- Supports both synchronous and asynchronous testing patterns

## Test Categories

- **Unit Tests**: Individual method testing with mocked dependencies
- **Integration Tests**: Full workflow testing with real threading
- **Concurrency Tests**: Multi-threaded access verification
- **Edge Case Tests**: Error conditions and boundary cases

## Dependencies

Tests require:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pydantic` - Data model validation

Install with: `pip install -e ".[dev]"`

## Design Notes

### Handling Singleton Pattern

The real TaskQueue uses a singleton pattern which makes testing challenging. The MockTaskQueue avoids this by:
- Not setting global instance variables
- Creating fresh instances per test
- Providing controlled dependency injection

### Thread Management

Tests handle threading complexities by:
- Using controlled mock workers for predictable behavior
- Providing synchronization primitives for timing-sensitive tests
- Testing both successful workflows and exception scenarios

### Heapq Compatibility

The original TaskQueue uses `heapq` with Pydantic models, which don't support comparison by default. Tests solve this by wrapping items in comparable tuples with priority values, maintaining FIFO order while enabling heap operations.