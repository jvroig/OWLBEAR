import os
import yaml
import asyncio
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys
import re

# Add the parent directory to the path to be able to import OWLBEAR modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import OWLBEAR modules
from owlbear import WorkflowEngine

from .event_service import EventService
from .expert_service import ExpertService

logger = logging.getLogger("owlbear-web-ui.workflow-service")

class WorkflowService:
    """Service for managing OWLBEAR workflows."""
    
    def __init__(self):
        self.workflows_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "workflows", "sequences")
        self.strings_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "workflows", "strings")
        self.running_workflows = {}  # Dictionary to track running workflow tasks
        self.event_service = EventService()
        self.expert_service = ExpertService()
        
    async def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List all available workflows.
        
        Returns:
            List[Dict[str, Any]]: List of workflow summary information
        """
        workflows = []
        
        # List all YAML files in the workflows directory
        for filename in os.listdir(self.workflows_dir):
            if filename.endswith(('.yml', '.yaml')):
                workflow_id = os.path.splitext(filename)[0]
                
                try:
                    # Load the workflow file to extract metadata
                    with open(os.path.join(self.workflows_dir, filename), 'r') as file:
                        workflow_data = yaml.safe_load(file)
                    
                    # Extract workflow information
                    name = self._extract_workflow_name(workflow_id, workflow_data)
                    description = self._extract_workflow_description(workflow_data)
                    expert_count = self._count_unique_experts(workflow_data)
                    action_count = len(workflow_data.get('ACTIONS', []))
                    
                    workflows.append({
                        "id": workflow_id,
                        "name": name,
                        "description": description,
                        "expert_count": expert_count,
                        "action_count": action_count
                    })
                except Exception as e:
                    logger.error(f"Error loading workflow {filename}: {str(e)}")
        
        return workflows
    
    async def get_workflow_details(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific workflow.
        
        Args:
            workflow_id (str): ID of the workflow
            
        Returns:
            Dict[str, Any]: Detailed workflow information
            
        Raises:
            FileNotFoundError: If the workflow is not found
        """
        # Construct the file path
        file_path = os.path.join(self.workflows_dir, f"{workflow_id}.yml")
        if not os.path.exists(file_path):
            file_path = os.path.join(self.workflows_dir, f"{workflow_id}.yaml")
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Workflow {workflow_id} not found")
        
        # Load the workflow file
        with open(file_path, 'r') as file:
            workflow_data = yaml.safe_load(file)
        
        # Extract basic information
        name = self._extract_workflow_name(workflow_id, workflow_data)
        description = self._extract_workflow_description(workflow_data)
        action_count = len(workflow_data.get('ACTIONS', []))
        
        # Extract expert information
        expert_ids = self._extract_expert_ids(workflow_data)
        experts = []
        
        for expert_id in expert_ids:
            try:
                expert = await self.expert_service.get_expert_details(expert_id)
                # Simplify for the response
                experts.append({
                    "id": expert["id"],
                    "name": expert["name"],
                    "description": expert["description"],
                    "tools": expert.get("tools", [])
                })
            except FileNotFoundError:
                # Expert not found, but we still include it with minimal info
                experts.append({
                    "id": expert_id,
                    "name": expert_id,
                    "description": f"Expert {expert_id}",
                    "tools": []
                })
        
        # Extract parameters
        parameters = self._extract_parameters(workflow_data)
        
        # Check for decision points and tool usage
        has_decision_points = any(
            list(action.keys())[0] == "DECIDE" 
            for action in workflow_data.get('ACTIONS', [])
        )
        
        has_tools = any(
            expert.get("tools", []) for expert in experts
        )
        
        return {
            "id": workflow_id,
            "name": name,
            "description": description,
            "expert_count": len(experts),
            "action_count": action_count,
            "experts": experts,
            "parameters": parameters,
            "has_decision_points": has_decision_points,
            "has_tools": has_tools
        }
    
    async def execute_workflow(self, workflow_id: str, parameters: Dict[str, Any]) -> str:
        """
        Execute a workflow with the provided parameters.
        
        Args:
            workflow_id (str): ID of the workflow to execute
            parameters (Dict[str, Any]): Parameters for the workflow
            
        Returns:
            str: Execution ID for tracking
            
        Raises:
            FileNotFoundError: If the workflow is not found
            ValueError: If required parameters are missing
        """
        # Validate that the workflow exists
        file_path = os.path.join(self.workflows_dir, f"{workflow_id}.yml")
        if not os.path.exists(file_path):
            file_path = os.path.join(self.workflows_dir, f"{workflow_id}.yaml")
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Workflow {workflow_id} not found")
        
        # Load the workflow to validate parameters
        with open(file_path, 'r') as file:
            workflow_data = yaml.safe_load(file)
        
        # Extract required parameters
        required_params = [
            param["name"] for param in self._extract_parameters(workflow_data)
            if param["required"] and not param.get("default_value")
        ]
        
        # Validate required parameters
        missing_params = [param for param in required_params if param not in parameters]
        if missing_params:
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
        
        # Generate a unique execution ID
        execution_id = str(uuid.uuid4())
        
        # Create a user_input string from the parameters
        user_input = self._build_user_input_from_parameters(parameters)
        
        # Determine if there's a strings file to use
        strings_path = self._find_strings_file(workflow_id)
        
        # Start the workflow execution as a background task
        task = asyncio.create_task(
            self._execute_workflow_task(
                execution_id, 
                workflow_id, 
                file_path, 
                user_input, 
                strings_path, 
                parameters
            )
        )
        
        # Store the task for potential cancellation
        self.running_workflows[execution_id] = {
            "task": task,
            "workflow_id": workflow_id,
            "started_at": datetime.now(),
            "parameters": parameters,
            "status": "running"
        }
        
        # Return the execution ID
        return execution_id
    
    async def cancel_workflow(self, workflow_id: str, execution_id: str) -> bool:
        """
        Cancel a running workflow execution.
        
        Args:
            workflow_id (str): ID of the workflow
            execution_id (str): ID of the execution to cancel
            
        Returns:
            bool: True if successfully cancelled, False otherwise
            
        Raises:
            ValueError: If the execution is not found
        """
        if execution_id not in self.running_workflows:
            raise ValueError(f"Execution {execution_id} not found")
        
        workflow_info = self.running_workflows[execution_id]
        if workflow_info["workflow_id"] != workflow_id:
            raise ValueError(f"Execution {execution_id} is not for workflow {workflow_id}")
        
        if workflow_info["status"] != "running":
            raise ValueError(f"Execution {execution_id} is not running (status: {workflow_info['status']})")
        
        try:
            # Cancel the task
            task = workflow_info["task"]
            task.cancel()
            
            # Wait for the task to be cancelled
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Update status
            workflow_info["status"] = "cancelled"
            
            # Emit an event for the cancellation
            await self.event_service.emit_execution_status(
                execution_id, 
                "cancelled",
                error="Execution was cancelled by user"
            )
            
            return True
        except Exception as e:
            logger.error(f"Error cancelling workflow execution {execution_id}: {str(e)}")
            return False
    
    async def _execute_workflow_task(
        self, 
        execution_id: str, 
        workflow_id: str, 
        file_path: str, 
        user_input: str, 
        strings_path: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Background task for workflow execution.
        
        Args:
            execution_id (str): Unique ID for this execution
            workflow_id (str): ID of the workflow being executed
            file_path (str): Path to the workflow file
            user_input (str): User input string for the workflow
            strings_path (Optional[str]): Path to strings file if applicable
            parameters (Optional[Dict[str, Any]]): Parameters provided for execution
        """
        try:
            # Emit initial status
            await self.event_service.emit_execution_status(
                execution_id, 
                "running",
                steps=[]
            )
            
            # Create a custom logger that will emit events
            event_logger = EventLogger(execution_id, self.event_service)
            
            # Initialize the workflow engine with our custom event handlers
            engine = WorkflowEngine(
                file_path,
                user_input,
                strings_path,
                skip_validation=False,
                event_logger=event_logger
            )
            
            # Run the workflow
            success = await self._run_workflow_with_events(engine, execution_id)
            
            # Update status based on result
            final_status = "completed" if success else "failed"
            error = None if success else "Workflow execution failed"
            
            # Update the running workflow status
            if execution_id in self.running_workflows:
                self.running_workflows[execution_id]["status"] = final_status
            
            # Emit final status
            await self.event_service.emit_execution_status(
                execution_id, 
                final_status,
                error=error
            )
            
        except asyncio.CancelledError:
            # Task was cancelled, don't need to do anything here as cancel_workflow handles status updates
            raise
            
        except Exception as e:
            logger.error(f"Error executing workflow {workflow_id}: {str(e)}")
            
            # Update the running workflow status
            if execution_id in self.running_workflows:
                self.running_workflows[execution_id]["status"] = "failed"
            
            # Emit error status
            await self.event_service.emit_execution_status(
                execution_id, 
                "failed",
                error=str(e)
            )
            
        finally:
            # Clean up resources
            pass
    
    async def _run_workflow_with_events(self, engine, execution_id):
        """
        Run the workflow and handle events.
        
        This is a placeholder for the actual implementation, which would need to:
        1. Patch the OWLBEAR code to emit events
        2. Connect those events to our event service
        3. Run the workflow and monitor its progress
        
        Args:
            engine: The workflow engine instance
            execution_id: ID of this execution
            
        Returns:
            bool: True if execution was successful, False otherwise
        """
        # In a real implementation, we'd hook into OWLBEAR's execution flow
        # For now, we'll just simulate it with a basic run
        try:
            # For now, just use the synchronous implementation with a wrapper
            return await asyncio.to_thread(engine.run)
        except Exception as e:
            logger.error(f"Workflow execution error: {str(e)}")
            return False
    
    def _extract_workflow_name(self, workflow_id: str, workflow_data: Dict[str, Any]) -> str:
        """
        Extract a display name for the workflow.
        
        Args:
            workflow_id (str): ID of the workflow
            workflow_data (Dict[str, Any]): Workflow YAML data
            
        Returns:
            str: Display name for the workflow
        """
        # Check for a NAME field in the workflow
        if 'NAME' in workflow_data:
            return workflow_data['NAME']
        
        # Otherwise, convert the ID to a readable name
        return workflow_id.replace('_', ' ').title()
    
    def _extract_workflow_description(self, workflow_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract a description for the workflow.
        
        Args:
            workflow_data (Dict[str, Any]): Workflow YAML data
            
        Returns:
            Optional[str]: Description if available, None otherwise
        """
        # Check for a DESCRIPTION field
        if 'DESCRIPTION' in workflow_data:
            return workflow_data['DESCRIPTION']
        
        # Check for a description in STRINGS
        if 'STRINGS' in workflow_data and 'STR_intro_prompt' in workflow_data['STRINGS']:
            # Use the intro prompt as a description
            desc = workflow_data['STRINGS']['STR_intro_prompt']
            # Truncate if too long
            if len(desc) > 200:
                return desc[:197] + "..."
            return desc
        
        return None
    
    def _count_unique_experts(self, workflow_data: Dict[str, Any]) -> int:
        """
        Count the number of unique experts used in a workflow.
        
        Args:
            workflow_data (Dict[str, Any]): Workflow YAML data
            
        Returns:
            int: Number of unique experts
        """
        experts = set()
        
        # Extract experts from each action
        for action in workflow_data.get('ACTIONS', []):
            for action_type, action_data in action.items():
                if 'expert' in action_data:
                    experts.add(action_data['expert'])
        
        return len(experts)
    
    def _extract_expert_ids(self, workflow_data: Dict[str, Any]) -> List[str]:
        """
        Extract all unique expert IDs used in a workflow.
        
        Args:
            workflow_data (Dict[str, Any]): Workflow YAML data
            
        Returns:
            List[str]: List of unique expert IDs
        """
        experts = set()
        
        # Extract experts from each action
        for action in workflow_data.get('ACTIONS', []):
            for action_type, action_data in action.items():
                if 'expert' in action_data:
                    experts.add(action_data['expert'])
        
        return list(experts)
    
    def _extract_parameters(self, workflow_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract required parameters for a workflow.
        
        Args:
            workflow_data (Dict[str, Any]): Workflow YAML data
            
        Returns:
            List[Dict[str, Any]]: List of parameter information
        """
        parameters = []
        
        # Check for explicit PARAMETERS section
        if 'PARAMETERS' in workflow_data:
            for param_name, param_data in workflow_data['PARAMETERS'].items():
                parameters.append({
                    "name": param_name,
                    "description": param_data.get('description', f"Parameter {param_name}"),
                    "required": param_data.get('required', True),
                    "default_value": param_data.get('default')
                })
        
        # Check for string variables that need substitution
        if 'STRINGS' in workflow_data:
            strings_data = workflow_data['STRINGS']
            
            # Check for variables section
            if 'VARIABLES' in strings_data:
                for var_name, var_default in strings_data['VARIABLES'].items():
                    # Skip if already defined in PARAMETERS
                    if any(param["name"] == var_name for param in parameters):
                        continue
                    
                    parameters.append({
                        "name": var_name,
                        "description": f"Variable {var_name}",
                        "required": True,
                        "default_value": var_default
                    })
            
            # Check for template variables in string values
            template_vars = set()
            for key, value in strings_data.items():
                if key == 'VARIABLES':
                    continue
                    
                if isinstance(value, str):
                    # Extract variables from {{var}} pattern
                    var_matches = re.findall(r'\{\{([^}]+)\}\}', value)
                    for var_name in var_matches:
                        var_name = var_name.strip()
                        template_vars.add(var_name)
            
            # Add template variables not already covered
            for var_name in template_vars:
                # Skip if already defined
                if any(param["name"] == var_name for param in parameters):
                    continue
                
                parameters.append({
                    "name": var_name,
                    "description": f"Template variable {var_name}",
                    "required": True,
                    "default_value": None
                })
        
        # Add STR_USER_INPUT as a special parameter if workflow seems to use it
        uses_user_input = False
        
        # Check if any action has a direct reference to STR_USER_INPUT
        for action in workflow_data.get('ACTIONS', []):
            for action_type, action_data in action.items():
                if 'inputs' in action_data:
                    if 'STR_USER_INPUT' in action_data['inputs']:
                        uses_user_input = True
                        break
        
        if uses_user_input and not any(param["name"] == "STR_USER_INPUT" for param in parameters):
            parameters.append({
                "name": "STR_USER_INPUT",
                "description": "Primary user input for the workflow",
                "required": True,
                "default_value": None
            })
        
        return parameters
    
    def _build_user_input_from_parameters(self, parameters: Dict[str, Any]) -> str:
        """
        Build a user input string from parameters.
        
        Args:
            parameters (Dict[str, Any]): Parameters for workflow execution
            
        Returns:
            str: User input string
        """
        # If STR_USER_INPUT is provided directly, use that
        if 'STR_USER_INPUT' in parameters:
            return str(parameters['STR_USER_INPUT'])
        
        # Otherwise, construct a simple string from the parameters
        parts = []
        for key, value in parameters.items():
            parts.append(f"{key}: {value}")
        
        return "\n".join(parts)
    
    def _find_strings_file(self, workflow_id: str) -> Optional[str]:
        """
        Find a strings file for a workflow.
        
        Args:
            workflow_id (str): ID of the workflow
            
        Returns:
            Optional[str]: Path to strings file if found, None otherwise
        """
        # Check for workflow-specific strings file
        for ext in ['.yml', '.yaml']:
            strings_path = os.path.join(self.strings_dir, f"{workflow_id}{ext}")
            if os.path.exists(strings_path):
                return strings_path
        
        # Check for a strings file referenced in the workflow
        file_path = os.path.join(self.workflows_dir, f"{workflow_id}.yml")
        if not os.path.exists(file_path):
            file_path = os.path.join(self.workflows_dir, f"{workflow_id}.yaml")
            if not os.path.exists(file_path):
                return None
        
        try:
            with open(file_path, 'r') as file:
                workflow_data = yaml.safe_load(file)
                
            # Check for a strings file reference
            if 'STRINGS_FILE' in workflow_data:
                strings_path = os.path.join(self.strings_dir, workflow_data['STRINGS_FILE'])
                if os.path.exists(strings_path):
                    return strings_path
        except Exception as e:
            logger.error(f"Error checking for strings file: {str(e)}")
        
        return None


class EventLogger:
    """Custom logger that emits events for the web UI."""
    
    def __init__(self, execution_id: str, event_service: 'EventService'):
        self.execution_id = execution_id
        self.event_service = event_service
        
    async def log_debug(self, message: str):
        """
        Log a debug message and emit an event.
        
        Args:
            message (str): Debug message
        """
        # Let the logging system handle it normally
        logger.debug(message)
        
        # Emit an event for the UI
        await self.event_service.emit_log(self.execution_id, message)
    
    async def log_step_update(self, step_index: int, action_type: str, expert_id: str, status: str, **kwargs):
        """
        Log a step update and emit an event.
        
        Args:
            step_index (int): Index of the step (0-based)
            action_type (str): Type of action
            expert_id (str): ID of the expert
            status (str): Status of the step
            **kwargs: Additional data
        """
        # Emit an event for the UI
        await self.event_service.emit_step_update(
            self.execution_id,
            step_index,
            action_type,
            expert_id,
            status,
            **kwargs
        )
    
    async def log_tool_call(self, expert_id: str, tool_name: str, parameters: Dict[str, Any], result: str):
        """
        Log a tool call and emit an event.
        
        Args:
            expert_id (str): ID of the expert making the call
            tool_name (str): Name of the tool
            parameters (Dict[str, Any]): Parameters for the tool call
            result (str): Result of the tool call
        """
        # Emit an event for the UI
        await self.event_service.emit_tool_call(
            self.execution_id,
            expert_id,
            tool_name,
            parameters,
            result
        )
