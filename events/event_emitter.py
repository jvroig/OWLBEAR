"""
Event Emitter for OWLBEAR.

This module provides a simple event emitter system that allows OWLBEAR
components to emit events and register event handlers.
"""
import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Set, Optional, Union
from datetime import datetime

logger = logging.getLogger("workflow-engine.events")

class EventEmitter:
    """
    Simple event emitter that supports synchronous and asynchronous handlers.
    """
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        
    def on(self, event: str, handler: Callable) -> None:
        """
        Register an event handler.
        
        Args:
            event (str): Event name to listen for
            handler (Callable): Function to call when the event is emitted
        """
        if event not in self._handlers:
            self._handlers[event] = []
            
        self._handlers[event].append(handler)
        logger.debug(f"Registered handler for event '{event}'")
        
    def off(self, event: str, handler: Optional[Callable] = None) -> None:
        """
        Remove an event handler.
        
        Args:
            event (str): Event name
            handler (Optional[Callable]): Handler to remove. If None, all handlers for the event are removed.
        """
        if event not in self._handlers:
            return
            
        if handler is None:
            # Remove all handlers for this event
            self._handlers[event] = []
            logger.debug(f"Removed all handlers for event '{event}'")
        else:
            # Remove specific handler
            if handler in self._handlers[event]:
                self._handlers[event].remove(handler)
                logger.debug(f"Removed handler for event '{event}'")
    
    async def emit(self, event: str, *args, **kwargs) -> None:
        """
        Emit an event asynchronously.
        
        Args:
            event (str): Event name
            *args: Arguments to pass to handlers
            **kwargs: Keyword arguments to pass to handlers
        """
        if event not in self._handlers:
            return
            
        for handler in self._handlers[event]:
            try:
                if inspect.iscoroutinefunction(handler):
                    # Async handler
                    await handler(*args, **kwargs)
                else:
                    # Sync handler
                    handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in event handler for '{event}': {str(e)}")
    
    def emit_sync(self, event: str, *args, **kwargs) -> None:
        """
        Emit an event synchronously.
        
        Args:
            event (str): Event name
            *args: Arguments to pass to handlers
            **kwargs: Keyword arguments to pass to handlers
        """
        if event not in self._handlers:
            return
            
        for handler in self._handlers[event]:
            try:
                if inspect.iscoroutinefunction(handler):
                    # Create a new event loop for the async handler
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(handler(*args, **kwargs))
                    loop.close()
                else:
                    # Sync handler
                    handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in event handler for '{event}': {str(e)}")

# Global event emitter instance
emitter = EventEmitter()

# Event types
EVENT_WORKFLOW_START = "workflow_start"
EVENT_WORKFLOW_END = "workflow_end"
EVENT_STEP_START = "step_start"
EVENT_STEP_END = "step_end"
EVENT_EXPERT_START = "expert_start"
EVENT_EXPERT_END = "expert_end"
EVENT_TOOL_CALL_START = "tool_call_start"
EVENT_TOOL_CALL_END = "tool_call_end"
EVENT_LOG = "log"
EVENT_ERROR = "error"

def register_global_handlers():
    """Register default handlers for logging events."""
    emitter.on(EVENT_LOG, lambda message, level="INFO": 
        logger.log(getattr(logging, level), message))
    
    emitter.on(EVENT_ERROR, lambda message: 
        logger.error(message))
    
    emitter.on(EVENT_WORKFLOW_START, lambda workflow_id, **kwargs: 
        logger.info(f"Workflow started: {workflow_id}"))
    
    emitter.on(EVENT_WORKFLOW_END, lambda workflow_id, success, **kwargs: 
        logger.info(f"Workflow ended: {workflow_id} (success: {success})"))
        
    emitter.on(EVENT_STEP_START, lambda step_index, action_type, **kwargs: 
        logger.info(f"Step {step_index} started: {action_type}"))
    
    emitter.on(EVENT_STEP_END, lambda step_index, action_type, success, **kwargs: 
        logger.info(f"Step {step_index} ended: {action_type} (success: {success})"))
        
    emitter.on(EVENT_EXPERT_START, lambda expert_id, **kwargs: 
        logger.info(f"Expert started: {expert_id}"))
    
    emitter.on(EVENT_EXPERT_END, lambda expert_id, **kwargs: 
        logger.info(f"Expert ended: {expert_id}"))
        
    emitter.on(EVENT_TOOL_CALL_START, lambda expert_id, tool_name, **kwargs: 
        logger.info(f"Tool call started: {expert_id} -> {tool_name}"))
    
    emitter.on(EVENT_TOOL_CALL_END, lambda expert_id, tool_name, result, **kwargs: 
        logger.info(f"Tool call ended: {expert_id} -> {tool_name}"))

# Initialize with default handlers
register_global_handlers()
