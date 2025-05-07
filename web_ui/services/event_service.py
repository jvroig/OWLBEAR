import asyncio
import logging
import json
from typing import Dict, List, Any, Set, Optional
from datetime import datetime
from fastapi import WebSocket

logger = logging.getLogger("owlbear-web-ui.event-service")

class EventService:
    """Service for managing real-time events via WebSockets."""
    
    def __init__(self):
        # Dictionary of active connections, keyed by execution_id
        self.connections: Dict[str, Set[WebSocket]] = {}
        
        # Dictionary of execution event history, for late-joining clients
        self.event_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Maximum events to keep per execution
        self.max_events_per_execution = 1000
        
    async def register_client(self, execution_id: str, websocket: WebSocket):
        """
        Register a new WebSocket client for an execution.
        
        Args:
            execution_id (str): ID of the execution to track
            websocket (WebSocket): Client WebSocket connection
        """
        if execution_id not in self.connections:
            self.connections[execution_id] = set()
            
        self.connections[execution_id].add(websocket)
        logger.info(f"Registered client for execution {execution_id}, total clients: {len(self.connections[execution_id])}")
        
        # Send event history to the new client
        if execution_id in self.event_history:
            for event in self.event_history[execution_id]:
                await websocket.send_json(event)
    
    async def unregister_client(self, execution_id: str, websocket: WebSocket):
        """
        Unregister a WebSocket client from an execution.
        
        Args:
            execution_id (str): ID of the execution
            websocket (WebSocket): Client WebSocket connection
        """
        if execution_id in self.connections:
            if websocket in self.connections[execution_id]:
                self.connections[execution_id].remove(websocket)
                logger.info(f"Unregistered client from execution {execution_id}, remaining clients: {len(self.connections[execution_id])}")
                
            # Clean up if no more clients
            if not self.connections[execution_id]:
                del self.connections[execution_id]
                logger.info(f"No more clients for execution {execution_id}, removed from connections")
    
    async def emit_event(self, execution_id: str, event_type: str, data: Any):
        """
        Emit an event to all clients tracking a specific execution.
        
        Args:
            execution_id (str): ID of the execution
            event_type (str): Type of event
            data (Any): Event data
        """
        # Create the event object
        event = {
            "type": event_type,
            "execution_id": execution_id,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        # Log event for debugging
        logger.info(f"Emitting event: {event_type} for execution: {execution_id}")
        if event_type == 'step_update':
            expert_id = data.get('expert_id', 'unknown')
            step_index = data.get('step_index', -1)
            status = data.get('status', 'unknown')
            description = data.get('description', 'none')
            logger.info(f"Step update details: step={step_index+1}, expert={expert_id}, status={status}, description={description}")
        
        # Store in event history
        if execution_id not in self.event_history:
            self.event_history[execution_id] = []
            
        self.event_history[execution_id].append(event)
        
        # Trim history if needed
        if len(self.event_history[execution_id]) > self.max_events_per_execution:
            self.event_history[execution_id] = self.event_history[execution_id][-self.max_events_per_execution:]
        
        # Log connection status
        if execution_id in self.connections:
            logger.info(f"Broadcasting to {len(self.connections[execution_id])} clients")
        else:
            logger.warning(f"No clients registered for execution: {execution_id}")
            return
        
        # Broadcast to all connected clients
        if execution_id in self.connections:
            disconnected_clients = []
            
            for websocket in self.connections[execution_id]:
                try:
                    await websocket.send_json(event)
                    logger.debug(f"Event sent to client successfully")
                except Exception as e:
                    logger.error(f"Error sending event to client: {str(e)}")
                    disconnected_clients.append(websocket)
            
            # Clean up any disconnected clients
            for websocket in disconnected_clients:
                await self.unregister_client(execution_id, websocket)
    
    async def emit_log(self, execution_id: str, message: str):
        """
        Emit a log message event.
        
        Args:
            execution_id (str): ID of the execution
            message (str): Log message
        """
        await self.emit_event(execution_id, "log", {
            "message": message
        })
    
    async def emit_step_update(
        self, 
        execution_id: str, 
        step_index: int, 
        action_type: str, 
        expert_id: str, 
        status: str, 
        description: str = None,
        **kwargs
    ):
        """
        Emit a step update event.
        
        Args:
            execution_id (str): ID of the execution
            step_index (int): Index of the step (0-based)
            action_type (str): Type of action
            expert_id (str): ID of the expert
            status (str): Status of the step
            description (str, optional): Description of the action (if available)
            **kwargs: Additional data
        """
        data = {
            "step_index": step_index,
            "action_type": action_type,
            "expert_id": expert_id,
            "status": status,
            **kwargs
        }
        
        # Include description if provided
        if description:
            data["description"] = description
        
        await self.emit_event(execution_id, "step_update", data)
    
    async def emit_tool_call(
        self, 
        execution_id: str, 
        expert_id: str, 
        tool_name: str, 
        parameters: Dict[str, Any], 
        result: Optional[str] = None
    ):
        """
        Emit a tool call event.
        
        Args:
            execution_id (str): ID of the execution
            expert_id (str): ID of the expert making the call
            tool_name (str): Name of the tool
            parameters (Dict[str, Any]): Parameters for the tool call
            result (Optional[str]): Result of the tool call, if available
        """
        data = {
            "expert_id": expert_id,
            "tool_name": tool_name,
            "parameters": parameters,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.emit_event(execution_id, "tool_call", data)
    
    async def emit_execution_status(
        self, 
        execution_id: str, 
        status: str, 
        **kwargs
    ):
        """
        Emit an execution status update event.
        
        Args:
            execution_id (str): ID of the execution
            status (str): Status of the execution
            **kwargs: Additional data
        """
        data = {
            "status": status,
            **kwargs
        }
        
        await self.emit_event(execution_id, "execution_status", data)
    
    async def clean_up_execution(self, execution_id: str):
        """
        Clean up resources for a completed execution.
        
        Args:
            execution_id (str): ID of the execution
        """
        # Remove from event history
        if execution_id in self.event_history:
            del self.event_history[execution_id]
            logger.info(f"Cleaned up event history for execution {execution_id}")
