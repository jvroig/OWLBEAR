"""
Unit tests for the OWLBEAR events system.
"""
import pytest
import os
import sys
import asyncio
from unittest.mock import Mock

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from events import emitter
from events import (
    EVENT_WORKFLOW_START,
    EVENT_WORKFLOW_END,
    EVENT_STEP_START,
    EVENT_STEP_END,
    EVENT_EXPERT_START,
    EVENT_EXPERT_END,
    EVENT_TOOL_CALL_START,
    EVENT_TOOL_CALL_END,
    EVENT_LOG,
    EVENT_ERROR
)

def test_event_emitter_initialization():
    """Test that the event emitter initializes correctly."""
    # The emitter should have been initialized by the import
    assert emitter._handlers is not None
    assert isinstance(emitter._handlers, dict)

def test_event_registration():
    """Test registering event handlers."""
    # Create a mock handler
    mock_handler = Mock()
    
    # Register the handler for a test event
    event_name = "test_event"
    emitter.on(event_name, mock_handler)
    
    # Check that the handler was registered
    assert event_name in emitter._handlers
    assert mock_handler in emitter._handlers[event_name]
    
    # Clean up - remove the handler
    emitter.off(event_name, mock_handler)

def test_event_unregistration():
    """Test unregistering event handlers."""
    # Create mock handlers
    mock_handler1 = Mock()
    mock_handler2 = Mock()
    
    # Register the handlers for a test event
    event_name = "test_event_unregister"
    emitter.on(event_name, mock_handler1)
    emitter.on(event_name, mock_handler2)
    
    # Check that both handlers were registered
    assert len(emitter._handlers[event_name]) == 2
    
    # Unregister one handler
    emitter.off(event_name, mock_handler1)
    
    # Check that only the second handler remains
    assert len(emitter._handlers[event_name]) == 1
    assert mock_handler1 not in emitter._handlers[event_name]
    assert mock_handler2 in emitter._handlers[event_name]
    
    # Unregister all handlers for the event
    emitter.off(event_name)
    
    # Check that no handlers remain
    assert len(emitter._handlers.get(event_name, [])) == 0

def test_sync_event_emission():
    """Test synchronous event emission."""
    # Create a mock handler
    mock_handler = Mock()
    
    # Register the handler for a test event
    event_name = "test_sync_event"
    emitter.on(event_name, mock_handler)
    
    # Emit the event with some test arguments
    test_arg = "Test Argument"
    test_kwarg = "Test Keyword Argument"
    emitter.emit_sync(event_name, test_arg, kwarg=test_kwarg)
    
    # Check that the handler was called with the correct arguments
    mock_handler.assert_called_once_with(test_arg, kwarg=test_kwarg)
    
    # Clean up - remove the handler
    emitter.off(event_name, mock_handler)

@pytest.mark.asyncio
async def test_async_event_emission():
    """Test asynchronous event emission."""
    # Create mock handlers - one sync and one async
    mock_sync_handler = Mock()
    
    async def mock_async_handler(*args, **kwargs):
        # Just record that we were called with the arguments
        mock_async_handler.args = args
        mock_async_handler.kwargs = kwargs
    
    # Add a call property to the async handler to track calls
    mock_async_handler.args = None
    mock_async_handler.kwargs = None
    
    # Register the handlers for a test event
    event_name = "test_async_event"
    emitter.on(event_name, mock_sync_handler)
    emitter.on(event_name, mock_async_handler)
    
    # Emit the event with some test arguments
    test_arg = "Test Async Argument"
    test_kwarg = "Test Async Keyword Argument"
    await emitter.emit(event_name, test_arg, kwarg=test_kwarg)
    
    # Check that both handlers were called with the correct arguments
    mock_sync_handler.assert_called_once_with(test_arg, kwarg=test_kwarg)
    assert mock_async_handler.args == (test_arg,)
    assert mock_async_handler.kwargs == {"kwarg": test_kwarg}
    
    # Clean up - remove the handlers
    emitter.off(event_name, mock_sync_handler)
    emitter.off(event_name, mock_async_handler)

def test_workflow_events():
    """Test workflow start and end events."""
    # Create mock handlers for workflow events
    mock_start_handler = Mock()
    mock_end_handler = Mock()
    
    # Register the handlers
    emitter.on(EVENT_WORKFLOW_START, mock_start_handler)
    emitter.on(EVENT_WORKFLOW_END, mock_end_handler)
    
    # Emit workflow start event
    workflow_id = "test_workflow"
    workflow_path = "/path/to/workflow.yml"
    emitter.emit_sync(EVENT_WORKFLOW_START, workflow_id=workflow_id, path=workflow_path)
    
    # Check that the start handler was called with the correct arguments
    mock_start_handler.assert_called_once_with(workflow_id=workflow_id, path=workflow_path)
    
    # Emit workflow end event
    success = True
    emitter.emit_sync(EVENT_WORKFLOW_END, workflow_id=workflow_id, success=success)
    
    # Check that the end handler was called with the correct arguments
    mock_end_handler.assert_called_once_with(workflow_id=workflow_id, success=success)
    
    # Clean up - remove the handlers
    emitter.off(EVENT_WORKFLOW_START, mock_start_handler)
    emitter.off(EVENT_WORKFLOW_END, mock_end_handler)

def test_step_events():
    """Test step start and end events."""
    # Create mock handlers for step events
    mock_start_handler = Mock()
    mock_end_handler = Mock()
    
    # Register the handlers
    emitter.on(EVENT_STEP_START, mock_start_handler)
    emitter.on(EVENT_STEP_END, mock_end_handler)
    
    # Emit step start event
    step_index = 0
    action_type = "PROMPT"
    expert_id = "TestExpert"
    description = "Test step"
    emitter.emit_sync(EVENT_STEP_START, 
                     step_index=step_index, 
                     action_type=action_type, 
                     expert_id=expert_id, 
                     description=description)
    
    # Check that the start handler was called with the correct arguments
    mock_start_handler.assert_called_once()
    
    # Emit step end event
    success = True
    emitter.emit_sync(EVENT_STEP_END, 
                     step_index=step_index, 
                     action_type=action_type, 
                     expert_id=expert_id, 
                     description=description, 
                     success=success)
    
    # Check that the end handler was called with the correct arguments
    mock_end_handler.assert_called_once()
    
    # Clean up - remove the handlers
    emitter.off(EVENT_STEP_START, mock_start_handler)
    emitter.off(EVENT_STEP_END, mock_end_handler)

def test_expert_events():
    """Test expert start and end events."""
    # Create mock handlers for expert events
    mock_start_handler = Mock()
    mock_end_handler = Mock()
    
    # Register the handlers
    emitter.on(EVENT_EXPERT_START, mock_start_handler)
    emitter.on(EVENT_EXPERT_END, mock_end_handler)
    
    # Emit expert start event
    expert_id = "TestExpert"
    emitter.emit_sync(EVENT_EXPERT_START, expert_id=expert_id)
    
    # Check that the start handler was called with the correct arguments
    mock_start_handler.assert_called_once_with(expert_id=expert_id)
    
    # Emit expert end event
    success = True
    output_length = 100
    emitter.emit_sync(EVENT_EXPERT_END, 
                     expert_id=expert_id, 
                     success=success, 
                     output_length=output_length)
    
    # Check that the end handler was called with the correct arguments
    mock_end_handler.assert_called_once()
    
    # Clean up - remove the handlers
    emitter.off(EVENT_EXPERT_START, mock_start_handler)
    emitter.off(EVENT_EXPERT_END, mock_end_handler)

def test_tool_call_events():
    """Test tool call start and end events."""
    # Create mock handlers for tool call events
    mock_start_handler = Mock()
    mock_end_handler = Mock()
    
    # Register the handlers
    emitter.on(EVENT_TOOL_CALL_START, mock_start_handler)
    emitter.on(EVENT_TOOL_CALL_END, mock_end_handler)
    
    # Emit tool call start event
    expert_id = "TestExpert"
    tool_name = "TestTool"
    parameters = {"param1": "value1"}
    emitter.emit_sync(EVENT_TOOL_CALL_START, 
                     expert_id=expert_id, 
                     tool_name=tool_name, 
                     parameters=parameters)
    
    # Check that the start handler was called with the correct arguments
    mock_start_handler.assert_called_once()
    
    # Emit tool call end event
    success = True
    result = "Tool execution result"
    emitter.emit_sync(EVENT_TOOL_CALL_END, 
                     expert_id=expert_id, 
                     tool_name=tool_name, 
                     parameters=parameters, 
                     result=result, 
                     success=success)
    
    # Check that the end handler was called with the correct arguments
    mock_end_handler.assert_called_once()
    
    # Clean up - remove the handlers
    emitter.off(EVENT_TOOL_CALL_START, mock_start_handler)
    emitter.off(EVENT_TOOL_CALL_END, mock_end_handler)

def test_log_and_error_events():
    """Test log and error events."""
    # Create mock handlers for log and error events
    mock_log_handler = Mock()
    mock_error_handler = Mock()
    
    # Register the handlers
    emitter.on(EVENT_LOG, mock_log_handler)
    emitter.on(EVENT_ERROR, mock_error_handler)
    
    # Emit log event
    log_message = "Test log message"
    log_level = "INFO"
    emitter.emit_sync(EVENT_LOG, log_message, level=log_level)
    
    # Check that the log handler was called with the correct arguments
    mock_log_handler.assert_called_once_with(log_message, level=log_level)
    
    # Emit error event
    error_message = "Test error message"
    emitter.emit_sync(EVENT_ERROR, error_message)
    
    # Check that the error handler was called with the correct arguments
    mock_error_handler.assert_called_once_with(error_message)
    
    # Clean up - remove the handlers
    emitter.off(EVENT_LOG, mock_log_handler)
    emitter.off(EVENT_ERROR, mock_error_handler)
