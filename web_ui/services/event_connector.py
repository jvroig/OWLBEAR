"""
Event connector for integrating OWLBEAR events with the web UI.

This module connects the OWLBEAR event system to the web UI event service,
forwarding events to the appropriate WebSocket connections.
"""
import logging
import asyncio
from typing import Dict, Any, Optional
import sys
import os
import uuid
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import OWLBEAR event system
from events import (
    emitter,
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

# Import web UI event service
from .event_service import EventService

logger = logging.getLogger("owlbear-web-ui.event-connector")

class EventConnector:
    """
    Connects OWLBEAR events to the web UI event service.
    """
    
    def __init__(self, event_service: EventService):
        """
        Initialize the event connector.
        
        Args:
            event_service (EventService): Web UI event service
        """
        self.event_service = event_service
        self.execution_mappings: Dict[str, str] = {}  # Map workflow_id to execution_id
        self.current_executions: Dict[str, Dict[str, Any]] = {}  # Track execution state
        
    def connect(self):
        """Connect to OWLBEAR event system"""
        # Register event handlers
        emitter.on(EVENT_WORKFLOW_START, self.handle_workflow_start)
        emitter.on(EVENT_WORKFLOW_END, self.handle_workflow_end)
        emitter.on(EVENT_STEP_START, self.handle_step_start)
        emitter.on(EVENT_STEP_END, self.handle_step_end)
        emitter.on(EVENT_EXPERT_START, self.handle_expert_start)
        emitter.on(EVENT_EXPERT_END, self.handle_expert_end)
        emitter.on(EVENT_TOOL_CALL_START, self.handle_tool_call_start)
        emitter.on(EVENT_TOOL_CALL_END, self.handle_tool_call_end)
        emitter.on(EVENT_LOG, self.handle_log)
        emitter.on(EVENT_ERROR, self.handle_error)
        
        logger.info("Connected to OWLBEAR event system")
    
    def disconnect(self):
        """Disconnect from OWLBEAR event system"""
        # Remove event handlers
        emitter.off(EVENT_WORKFLOW_START)
        emitter.off(EVENT_WORKFLOW_END)
        emitter.off(EVENT_STEP_START)
        emitter.off(EVENT_STEP_END)
        emitter.off(EVENT_EXPERT_START)
        emitter.off(EVENT_EXPERT_END)
        emitter.off(EVENT_TOOL_CALL_START)
        emitter.off(EVENT_TOOL_CALL_END)
        emitter.off(EVENT_LOG)
        emitter.off(EVENT_ERROR)
        
        logger.info("Disconnected from OWLBEAR event system")
    
    def register_execution(self, workflow_id: str, execution_id: str):
        """
        Register a new execution with the connector.
        
        Args:
            workflow_id (str): ID of the workflow
            execution_id (str): ID of the execution
        """
        self.execution_mappings[workflow_id] = execution_id
        self.current_executions[execution_id] = {
            "workflow_id": workflow_id,
            "status": "running",
            "started_at": datetime.now(),
            "steps": [],
            "experts": {},
            "tool_calls": []
        }
        
        logger.info(f"Registered execution: {execution_id} for workflow: {workflow_id}")
    
    def get_execution_id(self, workflow_id: str) -> Optional[str]:
        """
        Get the execution ID for a workflow.
        
        Args:
            workflow_id (str): ID of the workflow
            
        Returns:
            Optional[str]: Execution ID if found, None otherwise
        """
        return self.execution_mappings.get(workflow_id)
    
    async def handle_workflow_start(self, workflow_id: str, **kwargs):
        """
        Handle workflow start event.
        
        Args:
            workflow_id (str): ID of the workflow
            **kwargs: Additional data
        """
        # Generate execution ID if not already registered
        execution_id = self.get_execution_id(workflow_id)
        if not execution_id:
            execution_id = str(uuid.uuid4())
            self.register_execution(workflow_id, execution_id)
        
        # Create execution data
        execution_data = {
            "workflow_id": workflow_id,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            **kwargs
        }
        
        # Emit execution status event
        await self.event_service.emit_execution_status(execution_id, "running", **execution_data)
        
        # Log the event
        log_message = f"Workflow started: {workflow_id}"
        await self.event_service.emit_log(execution_id, log_message)
        
        logger.info(f"Emitted workflow start event for execution: {execution_id}")
    
    async def handle_workflow_end(self, workflow_id: str, success: bool, **kwargs):
        """
        Handle workflow end event.
        
        Args:
            workflow_id (str): ID of the workflow
            success (bool): Whether the workflow completed successfully
            **kwargs: Additional data
        """
        # Get execution ID
        execution_id = self.get_execution_id(workflow_id)
        if not execution_id:
            logger.warning(f"No execution found for workflow: {workflow_id}")
            return
        
        # Update execution data
        status = "completed" if success else "failed"
        error = kwargs.get("error")
        
        # Emit execution status event
        await self.event_service.emit_execution_status(
            execution_id, 
            status, 
            completed_at=datetime.now().isoformat(),
            error=error,
            **kwargs
        )
        
        # Log the event
        log_message = f"Workflow {status}: {workflow_id}"
        if error:
            log_message += f" - Error: {error}"
        await self.event_service.emit_log(execution_id, log_message)
        
        # Update current execution
        if execution_id in self.current_executions:
            self.current_executions[execution_id]["status"] = status
            self.current_executions[execution_id]["completed_at"] = datetime.now()
            if error:
                self.current_executions[execution_id]["error"] = error
        
        logger.info(f"Emitted workflow end event for execution: {execution_id}")
        
        # Clean up after a delay to ensure all clients receive the final status
        asyncio.create_task(self._delayed_cleanup(execution_id))
    
    async def _delayed_cleanup(self, execution_id: str, delay: int = 60):
        """
        Clean up execution data after a delay.
        
        Args:
            execution_id (str): ID of the execution
            delay (int): Delay in seconds before cleanup
        """
        await asyncio.sleep(delay)
        
        # Remove from mappings and current executions
        workflow_id = None
        for wf_id, exec_id in list(self.execution_mappings.items()):
            if exec_id == execution_id:
                workflow_id = wf_id
                break
        
        if workflow_id:
            del self.execution_mappings[workflow_id]
        
        if execution_id in self.current_executions:
            del self.current_executions[execution_id]
        
        # Clean up event history
        await self.event_service.clean_up_execution(execution_id)
        
        logger.info(f"Cleaned up execution: {execution_id}")
    
    async def handle_step_start(self, step_index: int, action_type: str, expert_id: str, **kwargs):
        """
        Handle step start event.
        
        Args:
            step_index (int): Index of the step
            action_type (str): Type of action
            expert_id (str): ID of the expert
            **kwargs: Additional data
        """
        # Find the current execution by checking running executions
        execution_id = None
        for exec_id, exec_data in self.current_executions.items():
            if exec_data["status"] == "running":
                execution_id = exec_id
                break
        
        if not execution_id:
            logger.warning(f"No running execution found for step: {step_index}")
            return
        
        # Update current execution
        self.current_executions[execution_id]["current_step"] = step_index
        
        # Track step in execution
        step_data = {
            "step_index": step_index,
            "action_type": action_type,
            "expert_id": expert_id,
            "status": "running",
            "started_at": datetime.now(),
            **kwargs
        }
        
        # Add to steps list
        self.current_executions[execution_id]["steps"].append(step_data)
        
        # Emit step update event
        await self.event_service.emit_step_update(
            execution_id,
            step_index,
            action_type,
            expert_id,
            "running",
            **kwargs
        )
        
        # Log the event
        log_message = f"Step {step_index + 1} started: {action_type} with expert {expert_id}"
        await self.event_service.emit_log(execution_id, log_message)
        
        logger.info(f"Emitted step start event for execution: {execution_id}, step: {step_index}")
    
    async def handle_step_end(self, step_index: int, action_type: str, expert_id: str, success: bool, **kwargs):
        """
        Handle step end event.
        
        Args:
            step_index (int): Index of the step
            action_type (str): Type of action
            expert_id (str): ID of the expert
            success (bool): Whether the step completed successfully
            **kwargs: Additional data
        """
        # Find the current execution by checking current step
        execution_id = None
        for exec_id, exec_data in self.current_executions.items():
            if exec_data.get("current_step") == step_index:
                execution_id = exec_id
                break
        
        if not execution_id:
            logger.warning(f"No execution found for step: {step_index}")
            return
        
        # Update step in current execution
        for step in self.current_executions[execution_id]["steps"]:
            if step["step_index"] == step_index:
                step["status"] = "completed" if success else "failed"
                step["completed_at"] = datetime.now()
                if not success and "error" in kwargs:
                    step["error"] = kwargs["error"]
                break
        
        # Emit step update event
        status = "completed" if success else "failed"
        await self.event_service.emit_step_update(
            execution_id,
            step_index,
            action_type,
            expert_id,
            status,
            **kwargs
        )
        
        # Log the event
        log_message = f"Step {step_index + 1} {status}: {action_type} with expert {expert_id}"
        if not success and "error" in kwargs:
            log_message += f" - Error: {kwargs['error']}"
        await self.event_service.emit_log(execution_id, log_message)
        
        logger.info(f"Emitted step end event for execution: {execution_id}, step: {step_index}")
    
    async def handle_expert_start(self, expert_id: str, **kwargs):
        """
        Handle expert start event.
        
        Args:
            expert_id (str): ID of the expert
            **kwargs: Additional data
        """
        # Find the current execution
        execution_id = None
        for exec_id, exec_data in self.current_executions.items():
            if exec_data["status"] == "running":
                execution_id = exec_id
                break
        
        if not execution_id:
            logger.warning(f"No running execution found for expert: {expert_id}")
            return
        
        # Update experts in current execution
        self.current_executions[execution_id]["experts"][expert_id] = {
            "status": "running",
            "started_at": datetime.now(),
            **kwargs
        }
        
        # Log the event
        log_message = f"Expert {expert_id} activated"
        await self.event_service.emit_log(execution_id, log_message)
        
        # No specific event for expert start in the UI yet
        logger.info(f"Handled expert start event for execution: {execution_id}, expert: {expert_id}")
    
    async def handle_expert_end(self, expert_id: str, success: bool, **kwargs):
        """
        Handle expert end event.
        
        Args:
            expert_id (str): ID of the expert
            success (bool): Whether the expert completed successfully
            **kwargs: Additional data
        """
        # Find the current execution with this expert
        execution_id = None
        for exec_id, exec_data in self.current_executions.items():
            if expert_id in exec_data.get("experts", {}):
                execution_id = exec_id
                break
        
        if not execution_id:
            logger.warning(f"No execution found for expert: {expert_id}")
            return
        
        # Update expert in current execution
        if expert_id in self.current_executions[execution_id]["experts"]:
            self.current_executions[execution_id]["experts"][expert_id]["status"] = "completed" if success else "failed"
            self.current_executions[execution_id]["experts"][expert_id]["completed_at"] = datetime.now()
            if not success and "error" in kwargs:
                self.current_executions[execution_id]["experts"][expert_id]["error"] = kwargs["error"]
        
        # Log the event
        status = "completed" if success else "failed"
        log_message = f"Expert {expert_id} {status}"
        if not success and "error" in kwargs:
            log_message += f" - Error: {kwargs['error']}"
        await self.event_service.emit_log(execution_id, log_message)
        
        # No specific event for expert end in the UI yet
        logger.info(f"Handled expert end event for execution: {execution_id}, expert: {expert_id}")
    
    async def handle_tool_call_start(self, expert_id: str, tool_name: str, parameters: Dict[str, Any], **kwargs):
        """
        Handle tool call start event.
        
        Args:
            expert_id (str): ID of the expert making the call
            tool_name (str): Name of the tool being called
            parameters (Dict[str, Any]): Parameters passed to the tool
            **kwargs: Additional data
        """
        # Find the current execution with this expert
        execution_id = None
        for exec_id, exec_data in self.current_executions.items():
            if expert_id in exec_data.get("experts", {}):
                execution_id = exec_id
                break
        
        if not execution_id:
            # Fall back to any running execution
            for exec_id, exec_data in self.current_executions.items():
                if exec_data["status"] == "running":
                    execution_id = exec_id
                    break
        
        if not execution_id:
            logger.warning(f"No execution found for tool call by expert: {expert_id}")
            return
        
        # Add tool call to current execution
        tool_call_data = {
            "expert_id": expert_id,
            "tool_name": tool_name,
            "parameters": parameters,
            "status": "running",
            "started_at": datetime.now(),
            **kwargs
        }
        
        self.current_executions[execution_id]["tool_calls"].append(tool_call_data)
        
        # Log the event
        param_str = str(parameters)
        if len(param_str) > 100:
            param_str = param_str[:97] + "..."
            
        log_message = f"Expert {expert_id} calling tool: {tool_name} with parameters: {param_str}"
        await self.event_service.emit_log(execution_id, log_message)
        
        # Emit tool call event without result
        await self.event_service.emit_tool_call(
            execution_id,
            expert_id,
            tool_name,
            parameters
        )
        
        logger.info(f"Emitted tool call start event for execution: {execution_id}, expert: {expert_id}, tool: {tool_name}")
    
    async def handle_tool_call_end(self, expert_id: str, tool_name: str, parameters: Dict[str, Any], result: str, success: bool, **kwargs):
        """
        Handle tool call end event.
        
        Args:
            expert_id (str): ID of the expert making the call
            tool_name (str): Name of the tool being called
            parameters (Dict[str, Any]): Parameters passed to the tool
            result (str): Result of the tool call
            success (bool): Whether the tool call completed successfully
            **kwargs: Additional data
        """
        # Find the current execution with this expert
        execution_id = None
        for exec_id, exec_data in self.current_executions.items():
            if expert_id in exec_data.get("experts", {}):
                execution_id = exec_id
                break
        
        if not execution_id:
            # Fall back to any running execution
            for exec_id, exec_data in self.current_executions.items():
                if exec_data["status"] == "running":
                    execution_id = exec_id
                    break
        
        if not execution_id:
            logger.warning(f"No execution found for tool call by expert: {expert_id}")
            return
        
        # Update tool call in current execution
        for tool_call in self.current_executions[execution_id]["tool_calls"]:
            if (tool_call["expert_id"] == expert_id and 
                tool_call["tool_name"] == tool_name and
                tool_call["status"] == "running"):
                
                tool_call["status"] = "completed" if success else "failed"
                tool_call["completed_at"] = datetime.now()
                tool_call["result"] = result
                if not success and "error" in kwargs:
                    tool_call["error"] = kwargs["error"]
                break
        
        # Log the event
        status = "completed" if success else "failed"
        
        result_str = str(result)
        if len(result_str) > 100:
            result_str = result_str[:97] + "..."
            
        log_message = f"Tool call {status}: {tool_name} by expert {expert_id} with result: {result_str}"
        if not success and "error" in kwargs:
            log_message += f" - Error: {kwargs['error']}"
        await self.event_service.emit_log(execution_id, log_message)
        
        # Emit tool call event with result
        await self.event_service.emit_tool_call(
            execution_id,
            expert_id,
            tool_name,
            parameters,
            result
        )
        
        logger.info(f"Emitted tool call end event for execution: {execution_id}, expert: {expert_id}, tool: {tool_name}")
    
    async def handle_log(self, message: str, level: str = "INFO", **kwargs):
        """
        Handle log event.
        
        Args:
            message (str): Log message
            level (str): Log level
            **kwargs: Additional data
        """
        # Determine which execution this log belongs to
        execution_id = None
        
        # Check if execution_id is explicitly provided
        if "execution_id" in kwargs:
            execution_id = kwargs["execution_id"]
        else:
            # Find any running execution
            for exec_id, exec_data in self.current_executions.items():
                if exec_data["status"] == "running":
                    execution_id = exec_id
                    break
        
        if not execution_id:
            # If we can't determine the execution, just log it locally
            logger.info(f"Unattributed log message: {message}")
            return
        
        # Format the message based on log level
        formatted_message = f"[{level}] {message}"
        
        # Emit log event
        await self.event_service.emit_log(execution_id, formatted_message)
        
        logger.info(f"Emitted log event for execution: {execution_id}")
    
    async def handle_error(self, message: str, **kwargs):
        """
        Handle error event.
        
        Args:
            message (str): Error message
            **kwargs: Additional data
        """
        # Determine which execution this error belongs to
        execution_id = None
        
        # Check if execution_id is explicitly provided
        if "execution_id" in kwargs:
            execution_id = kwargs["execution_id"]
        else:
            # Find any running execution
            for exec_id, exec_data in self.current_executions.items():
                if exec_data["status"] == "running":
                    execution_id = exec_id
                    break
        
        if not execution_id:
            # If we can't determine the execution, just log it locally
            logger.error(f"Unattributed error message: {message}")
            return
        
        # Format the message
        formatted_message = f"ERROR: {message}"
        
        # Emit log event
        await self.event_service.emit_log(execution_id, formatted_message)
        
        # Emit error event
        await self.event_service.emit_event(execution_id, "error", {"message": message})
        
        logger.info(f"Emitted error event for execution: {execution_id}")
