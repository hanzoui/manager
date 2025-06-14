"""
Tests for TaskQueue functionality.

This module tests the core TaskQueue operations including:
- Task queueing and processing
- Batch tracking
- Thread lifecycle management
- State management
- WebSocket message delivery
"""

import asyncio
import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Any, Dict, Optional

import pytest

from comfyui_manager.data_models import (
    QueueTaskItem,
    TaskExecutionStatus,
    TaskStateMessage,
    InstallPackParams,
    ManagerDatabaseSource,
    ManagerChannel,
)


class MockTaskQueue:
    """
    A testable version of TaskQueue that allows for dependency injection
    and isolated testing without global state.
    """
    
    def __init__(self, history_dir: Optional[Path] = None):
        # Don't set the global instance for testing
        self.mutex = threading.RLock()
        self.not_empty = threading.Condition(self.mutex)
        self.current_index = 0
        self.pending_tasks = []
        self.running_tasks = {}
        self.history_tasks = {}
        self.task_counter = 0
        self.batch_id = None
        self.batch_start_time = None
        self.batch_state_before = None
        self._worker_task = None
        self._history_dir = history_dir
        
        # Mock external dependencies
        self.mock_core = MagicMock()
        self.mock_prompt_server = MagicMock()
        
    def is_processing(self) -> bool:
        """Check if the queue is currently processing tasks"""
        return (
            self._worker_task is not None 
            and self._worker_task.is_alive()
        )
    
    def start_worker(self, mock_task_worker=None) -> bool:
        """Start the task worker. Can inject a mock worker for testing."""
        if self._worker_task is not None and self._worker_task.is_alive():
            return False  # Already running
        
        if mock_task_worker:
            self._worker_task = threading.Thread(target=mock_task_worker)
        else:
            # Use a simple test worker that processes one task then stops
            self._worker_task = threading.Thread(target=self._test_worker)
        self._worker_task.start()
        return True
    
    def _test_worker(self):
        """Simple test worker that processes tasks without external dependencies"""
        while True:
            task = self.get(timeout=1.0)  # Short timeout for tests
            if task is None:
                if self.total_count() == 0:
                    break
                continue
                
            item, task_index = task
            
            # Simulate task processing
            self.running_tasks[task_index] = item
            
            # Simulate work
            time.sleep(0.1)
            
            # Mark as completed
            status = TaskExecutionStatus(
                status_str="success",
                completed=True,
                messages=["Test task completed"]
            )
            
            self.mark_done(task_index, item, status, "Test result")
            
            # Clean up
            if task_index in self.running_tasks:
                del self.running_tasks[task_index]
    
    def get_current_state(self) -> TaskStateMessage:
        """Get current queue state with mocked dependencies"""
        return TaskStateMessage(
            history=self.get_history(),
            running_queue=self.get_current_queue()[0],
            pending_queue=self.get_current_queue()[1],
            installed_packs={}  # Mocked empty
        )
    
    def send_queue_state_update(self, msg: str, update, client_id: Optional[str] = None):
        """Mock implementation that tracks calls instead of sending WebSocket messages"""
        if not hasattr(self, '_sent_updates'):
            self._sent_updates = []
        self._sent_updates.append({
            'msg': msg,
            'update': update,
            'client_id': client_id
        })
    
    # Copy the essential methods from the real TaskQueue
    def put(self, item) -> None:
        """Add a task to the queue. Item can be a dict or QueueTaskItem model."""
        with self.mutex:
            # Start a new batch if this is the first task after queue was empty
            if (
                self.batch_id is None
                and len(self.pending_tasks) == 0
                and len(self.running_tasks) == 0
            ):
                self._start_new_batch()

            # Convert to Pydantic model if it's a dict
            if isinstance(item, dict):
                item = QueueTaskItem(**item)

            import heapq
            # Wrap in tuple with priority to make it comparable
            # Use task_counter as priority to maintain FIFO order
            priority_item = (self.task_counter, item)
            heapq.heappush(self.pending_tasks, priority_item)
            self.task_counter += 1
            self.not_empty.notify()

    def _start_new_batch(self) -> None:
        """Start a new batch session for tracking operations."""
        self.batch_id = (
            f"test_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )
        self.batch_start_time = datetime.now().isoformat()
        self.batch_state_before = {"test": "state"}  # Simplified for testing

    def get(self, timeout: Optional[float] = None):
        """Get next task from queue"""
        with self.not_empty:
            while len(self.pending_tasks) == 0:
                self.not_empty.wait(timeout=timeout)
                if timeout is not None and len(self.pending_tasks) == 0:
                    return None
            import heapq
            priority_item = heapq.heappop(self.pending_tasks)
            task_index, item = priority_item  # Unwrap the tuple
            return item, task_index

    def total_count(self) -> int:
        """Get total number of tasks (pending + running)"""
        return len(self.pending_tasks) + len(self.running_tasks)
    
    def done_count(self) -> int:
        """Get number of completed tasks"""
        return len(self.history_tasks)
    
    def get_current_queue(self):
        """Get current running and pending queues"""
        running = list(self.running_tasks.values())
        # Extract items from the priority tuples
        pending = [item for priority, item in self.pending_tasks]
        return running, pending
    
    def get_history(self):
        """Get task history"""
        return self.history_tasks
    
    def mark_done(self, task_index: int, item: QueueTaskItem, status: TaskExecutionStatus, result: str):
        """Mark a task as completed"""
        from comfyui_manager.data_models import TaskHistoryItem
        
        history_item = TaskHistoryItem(
            ui_id=item.ui_id,
            client_id=item.client_id,
            kind=item.kind.value if hasattr(item.kind, 'value') else str(item.kind),
            timestamp=datetime.now().isoformat(),
            result=result,
            status=status
        )
        
        self.history_tasks[item.ui_id] = history_item
    
    def finalize(self):
        """Finalize batch (simplified for testing)"""
        if self._history_dir and self.batch_id:
            batch_file = self._history_dir / f"{self.batch_id}.json"
            batch_record = {
                "batch_id": self.batch_id,
                "start_time": self.batch_start_time,
                "state_before": self.batch_state_before,
                "operations": []  # Simplified
            }
            with open(batch_file, 'w') as f:
                json.dump(batch_record, f, indent=2)


class TestTaskQueue:
    """Test suite for TaskQueue functionality"""
    
    @pytest.fixture
    def task_queue(self, tmp_path):
        """Create a clean TaskQueue instance for each test"""
        return MockTaskQueue(history_dir=tmp_path)
    
    @pytest.fixture
    def sample_task(self):
        """Create a sample task for testing"""
        return QueueTaskItem(
            ui_id=str(uuid.uuid4()),
            client_id="test_client",
            kind="install",
            params=InstallPackParams(
                id="test-node",
                version="1.0.0",
                selected_version="1.0.0",
                mode=ManagerDatabaseSource.cache,
                channel=ManagerChannel.dev
            )
        )
    
    def test_task_queue_initialization(self, task_queue):
        """Test TaskQueue initializes with correct default state"""
        assert task_queue.total_count() == 0
        assert task_queue.done_count() == 0
        assert not task_queue.is_processing()
        assert task_queue.batch_id is None
        assert len(task_queue.pending_tasks) == 0
        assert len(task_queue.running_tasks) == 0
        assert len(task_queue.history_tasks) == 0
    
    def test_put_task_starts_batch(self, task_queue, sample_task):
        """Test that adding first task starts a new batch"""
        assert task_queue.batch_id is None
        
        task_queue.put(sample_task)
        
        assert task_queue.batch_id is not None
        assert task_queue.batch_id.startswith("test_batch_")
        assert task_queue.batch_start_time is not None
        assert task_queue.total_count() == 1
    
    def test_put_multiple_tasks(self, task_queue, sample_task):
        """Test adding multiple tasks to queue"""
        task_queue.put(sample_task)
        
        # Create second task
        task2 = QueueTaskItem(
            ui_id=str(uuid.uuid4()),
            client_id="test_client_2", 
            kind="install",
            params=sample_task.params
        )
        task_queue.put(task2)
        
        assert task_queue.total_count() == 2
        assert len(task_queue.pending_tasks) == 2
    
    def test_put_task_with_dict(self, task_queue):
        """Test adding task as dictionary gets converted to QueueTaskItem"""
        task_dict = {
            "ui_id": str(uuid.uuid4()),
            "client_id": "test_client",
            "kind": "install",
            "params": {
                "id": "test-node",
                "version": "1.0.0",
                "selected_version": "1.0.0",
                "mode": "cache",
                "channel": "dev"
            }
        }
        
        task_queue.put(task_dict)
        
        assert task_queue.total_count() == 1
        # Verify it was converted to QueueTaskItem
        item, _ = task_queue.get(timeout=0.1)
        assert isinstance(item, QueueTaskItem)
        assert item.ui_id == task_dict["ui_id"]
    
    def test_get_task_from_queue(self, task_queue, sample_task):
        """Test retrieving task from queue"""
        task_queue.put(sample_task)
        
        item, task_index = task_queue.get(timeout=0.1)
        
        assert item == sample_task
        assert isinstance(task_index, int)
        assert task_queue.total_count() == 0  # Should be removed from pending
    
    def test_get_task_timeout(self, task_queue):
        """Test get with timeout on empty queue returns None"""
        result = task_queue.get(timeout=0.1)
        assert result is None
    
    def test_start_stop_worker(self, task_queue):
        """Test worker thread lifecycle"""
        assert not task_queue.is_processing()
        
        # Mock worker that stops immediately
        stop_event = threading.Event()
        def mock_worker():
            stop_event.wait(0.1)  # Brief delay then stop
        
        started = task_queue.start_worker(mock_worker)
        assert started is True
        assert task_queue.is_processing()
        
        # Try to start again - should return False
        started_again = task_queue.start_worker(mock_worker)
        assert started_again is False
        
        # Wait for worker to finish
        stop_event.set()
        task_queue._worker_task.join(timeout=1.0)
        assert not task_queue.is_processing()
    
    def test_task_processing_integration(self, task_queue, sample_task):
        """Test full task processing workflow"""
        # Add task to queue
        task_queue.put(sample_task)
        assert task_queue.total_count() == 1
        
        # Start worker
        started = task_queue.start_worker()
        assert started is True
        
        # Wait for processing to complete
        for _ in range(50):  # Max 5 seconds
            if task_queue.done_count() > 0:
                break
            time.sleep(0.1)
        
        # Verify task was processed
        assert task_queue.done_count() == 1
        assert task_queue.total_count() == 0
        assert sample_task.ui_id in task_queue.history_tasks
        
        # Stop worker
        task_queue._worker_task.join(timeout=1.0)
    
    def test_get_current_state(self, task_queue, sample_task):
        """Test getting current queue state"""
        task_queue.put(sample_task)
        
        state = task_queue.get_current_state()
        
        assert isinstance(state, TaskStateMessage)
        assert len(state.pending_queue) == 1
        assert len(state.running_queue) == 0
        assert state.pending_queue[0] == sample_task
    
    def test_batch_finalization(self, task_queue, tmp_path):
        """Test batch history is saved correctly"""
        task_queue.put(QueueTaskItem(
            ui_id=str(uuid.uuid4()),
            client_id="test_client",
            kind="install", 
            params=InstallPackParams(
                id="test-node",
                version="1.0.0",
                selected_version="1.0.0",
                mode=ManagerDatabaseSource.cache,
                channel=ManagerChannel.dev
            )
        ))
        
        batch_id = task_queue.batch_id
        task_queue.finalize()
        
        # Check batch file was created
        batch_file = tmp_path / f"{batch_id}.json"
        assert batch_file.exists()
        
        # Verify content
        with open(batch_file) as f:
            batch_data = json.load(f)
        
        assert batch_data["batch_id"] == batch_id
        assert "start_time" in batch_data
        assert "state_before" in batch_data
    
    def test_concurrent_access(self, task_queue):
        """Test thread-safe concurrent access to queue"""
        num_tasks = 10
        added_tasks = []
        
        def add_tasks():
            for i in range(num_tasks):
                task = QueueTaskItem(
                    ui_id=f"task_{i}",
                    client_id=f"client_{i}",
                    kind="install",
                    params=InstallPackParams(
                        id=f"node_{i}",
                        version="1.0.0",
                        selected_version="1.0.0", 
                        mode=ManagerDatabaseSource.cache,
                        channel=ManagerChannel.dev
                    )
                )
                task_queue.put(task)
                added_tasks.append(task)
        
        # Start multiple threads adding tasks
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=add_tasks)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all tasks were added
        assert task_queue.total_count() == num_tasks * 3
        assert len(added_tasks) == num_tasks * 3
    
    @pytest.mark.asyncio
    async def test_queue_state_updates_tracking(self, task_queue, sample_task):
        """Test that queue state updates are tracked properly"""
        # Mock the update tracking
        task_queue.send_queue_state_update("test-message", {"test": "data"}, "client1")
        
        # Verify update was tracked
        assert hasattr(task_queue, '_sent_updates')
        assert len(task_queue._sent_updates) == 1
        
        update = task_queue._sent_updates[0]
        assert update['msg'] == "test-message"
        assert update['update'] == {"test": "data"}
        assert update['client_id'] == "client1"


class TestTaskQueueEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def task_queue(self):
        return MockTaskQueue()
    
    def test_empty_queue_operations(self, task_queue):
        """Test operations on empty queue"""
        assert task_queue.total_count() == 0
        assert task_queue.done_count() == 0
        
        # Getting from empty queue should timeout
        result = task_queue.get(timeout=0.1)
        assert result is None
        
        # State should be empty
        state = task_queue.get_current_state()
        assert len(state.pending_queue) == 0
        assert len(state.running_queue) == 0
    
    def test_invalid_task_data(self, task_queue):
        """Test handling of invalid task data"""
        # This should raise ValidationError due to missing required fields
        with pytest.raises(Exception):  # ValidationError from Pydantic
            task_queue.put({
                "ui_id": "test",
                # Missing required fields
            })
    
    def test_worker_cleanup_on_exception(self, task_queue):
        """Test worker cleanup when worker function raises exception"""
        exception_raised = threading.Event()
        
        def failing_worker():
            exception_raised.set()
            raise RuntimeError("Test exception")
        
        started = task_queue.start_worker(failing_worker)
        assert started is True
        
        # Wait for exception to be raised
        exception_raised.wait(timeout=1.0)
        
        # Worker should eventually stop
        task_queue._worker_task.join(timeout=1.0)
        assert not task_queue.is_processing()


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__])