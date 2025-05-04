import os
import yaml
import logging
import glob
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

logger = logging.getLogger("owlbear-web-ui.execution-service")

class ExecutionService:
    """Service for managing OWLBEAR workflow execution history."""
    
    def __init__(self):
        self.outputs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "outputs")
        
    async def list_executions(self) -> List[Dict[str, Any]]:
        """
        List recent workflow executions.
        
        Returns:
            List[Dict[str, Any]]: List of execution summary information
        """
        executions = []
        
        # List all directories in the outputs directory
        if os.path.exists(self.outputs_dir):
            for dirname in sorted(os.listdir(self.outputs_dir), reverse=True):
                # Output directories have the format: workflow_name_timestamp
                # We use this to extract workflow ID and execution time
                dir_path = os.path.join(self.outputs_dir, dirname)
                
                if not os.path.isdir(dir_path):
                    continue
                    
                try:
                    # Parse the directory name
                    workflow_id, execution_time = self._parse_output_dir_name(dirname)
                    if not workflow_id or not execution_time:
                        continue
                    
                    # Create a unique execution ID
                    execution_id = dirname
                    
                    # Determine execution status
                    status, error = self._determine_execution_status(dir_path)
                    
                    # Get current step
                    current_step = self._determine_current_step(dir_path)
                    
                    # Create the execution summary
                    execution_summary = {
                        "id": execution_id,
                        "workflow_id": workflow_id,
                        "status": status,
                        "started_at": execution_time,
                        "current_step": current_step,
                        "error": error
                    }
                    
                    if status in ["completed", "failed", "cancelled"]:
                        # Check if we have a completion time
                        log_path = os.path.join(dir_path, "workflow_execution.log")
                        if os.path.exists(log_path):
                            try:
                                with open(log_path, 'r') as file:
                                    log_content = file.read()
                                    
                                    # Find the last timestamp in the log
                                    timestamp_matches = re.findall(r'\[(.*?)\]', log_content)
                                    if timestamp_matches:
                                        last_timestamp = timestamp_matches[-1]
                                        try:
                                            execution_summary["completed_at"] = datetime.strptime(
                                                last_timestamp, 
                                                "%Y-%m-%d %H:%M:%S"
                                            )
                                        except ValueError:
                                            pass
                            except Exception as e:
                                logger.error(f"Error parsing log for {dirname}: {str(e)}")
                    
                    executions.append(execution_summary)
                    
                except Exception as e:
                    logger.error(f"Error processing execution directory {dirname}: {str(e)}")
        
        return executions
    
    async def get_execution_details(self, execution_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific execution.
        
        Args:
            execution_id (str): ID of the execution
            
        Returns:
            Dict[str, Any]: Detailed execution information
            
        Raises:
            FileNotFoundError: If the execution is not found
        """
        # The execution_id is the output directory name
        dir_path = os.path.join(self.outputs_dir, execution_id)
        
        if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
            raise FileNotFoundError(f"Execution {execution_id} not found")
        
        try:
            # Parse the directory name
            workflow_id, execution_time = self._parse_output_dir_name(execution_id)
            if not workflow_id or not execution_time:
                raise ValueError(f"Invalid execution directory name: {execution_id}")
            
            # Determine execution status
            status, error = self._determine_execution_status(dir_path)
            
            # Extract steps from output files
            steps = await self._extract_execution_steps(dir_path)
            
            # Extract tool calls if any
            tool_calls = await self._extract_tool_calls(dir_path)
            
            # Extract logs
            logs = await self._extract_execution_logs(dir_path)
            
            # Get current step
            current_step = self._determine_current_step(dir_path)
            
            # Create the execution detail
            execution_detail = {
                "id": execution_id,
                "workflow_id": workflow_id,
                "status": status,
                "started_at": execution_time,
                "current_step": current_step,
                "error": error,
                "steps": steps,
                "tool_calls": tool_calls,
                "logs": logs
            }
            
            if status in ["completed", "failed", "cancelled"]:
                # Check if we have a completion time
                log_path = os.path.join(dir_path, "workflow_execution.log")
                if os.path.exists(log_path):
                    try:
                        with open(log_path, 'r') as file:
                            log_content = file.read()
                            
                            # Find the last timestamp in the log
                            timestamp_matches = re.findall(r'\[(.*?)\]', log_content)
                            if timestamp_matches:
                                last_timestamp = timestamp_matches[-1]
                                try:
                                    execution_detail["completed_at"] = datetime.strptime(
                                        last_timestamp, 
                                        "%Y-%m-%d %H:%M:%S"
                                    )
                                except ValueError:
                                    pass
                    except Exception as e:
                        logger.error(f"Error parsing log for {execution_id}: {str(e)}")
            
            return execution_detail
            
        except Exception as e:
            logger.error(f"Error getting execution details for {execution_id}: {str(e)}")
            raise
    
    def _parse_output_dir_name(self, dirname: str) -> tuple:
        """
        Parse an output directory name into workflow ID and execution time.
        
        Args:
            dirname (str): Name of the output directory
            
        Returns:
            tuple: (workflow_id, execution_time) or (None, None) if parsing fails
        """
        # Output directories have the format: workflow_name_YYYY-MM-DD-HH-MM
        try:
            # Split by the last underscore to separate workflow name and timestamp
            parts = dirname.split('_')
            
            # The timestamp should be the last part and contain dashes
            if '-' not in parts[-1]:
                return None, None
                
            # Extract timestamp (everything after the last underscore)
            timestamp_str = parts[-1]
            
            # Extract workflow ID (everything before the last underscore)
            workflow_id = '_'.join(parts[:-1])
            
            # Parse the timestamp
            try:
                execution_time = datetime.strptime(timestamp_str, "%Y-%m-%d-%H-%M")
                return workflow_id, execution_time
            except ValueError:
                return None, None
                
        except Exception:
            return None, None
    
    def _determine_execution_status(self, dir_path: str) -> tuple:
        """
        Determine the status of an execution based on its output directory.
        
        Args:
            dir_path (str): Path to the execution output directory
            
        Returns:
            tuple: (status, error) where status is one of: running, completed, failed, cancelled
        """
        # Check the workflow execution log for completion or failure
        log_path = os.path.join(dir_path, "workflow_execution.log")
        
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r') as file:
                    log_content = file.read()
                    
                    # Check for completion
                    if "WORKFLOW COMPLETED SUCCESSFULLY" in log_content:
                        return "completed", None
                    
                    # Check for failure
                    if "Workflow failed!" in log_content:
                        # Try to extract error message
                        error_match = re.search(r"Error.*?: (.*?)$", log_content, re.MULTILINE)
                        if error_match:
                            return "failed", error_match.group(1)
                        return "failed", "Unknown error"
                    
                    # Check for cancellation
                    if "Workflow execution cancelled" in log_content:
                        return "cancelled", "Execution was cancelled"
            except Exception as e:
                logger.error(f"Error reading log file {log_path}: {str(e)}")
        
        # If we couldn't determine status, assume running
        return "running", None
    
    def _determine_current_step(self, dir_path: str) -> Optional[int]:
        """
        Determine the current step of an execution.
        
        Args:
            dir_path (str): Path to the execution output directory
            
        Returns:
            Optional[int]: Current step index (0-based) or None if undetermined
        """
        # Check the workflow execution log
        log_path = os.path.join(dir_path, "workflow_execution.log")
        
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r') as file:
                    log_content = file.read()
                    
                    # Look for step execution entries
                    step_matches = re.findall(r"EXECUTING: Step (\d+)", log_content)
                    if step_matches:
                        # Get the last executed step
                        last_step = int(step_matches[-1]) - 1  # Convert to 0-based
                        return last_step
            except Exception as e:
                logger.error(f"Error reading log file {log_path}: {str(e)}")
        
        return None
    
    async def _extract_execution_steps(self, dir_path: str) -> List[Dict[str, Any]]:
        """
        Extract step information from an execution directory.
        
        Args:
            dir_path (str): Path to the execution output directory
            
        Returns:
            List[Dict[str, Any]]: List of step information
        """
        steps = []
        
        # Find all YAML files in the directory (each represents a step output)
        yaml_files = glob.glob(os.path.join(dir_path, "*.yaml"))
        
        for file_path in yaml_files:
            try:
                # Skip validator files
                if "validated" in os.path.basename(file_path):
                    continue
                
                with open(file_path, 'r') as file:
                    data = yaml.safe_load(file)
                
                if not isinstance(data, dict):
                    continue
                
                # Extract step information
                action_type = data.get('action_type')
                if not action_type:
                    continue
                
                # Determine step index based on execution order
                # This is a simplification - in a real implementation we'd track the actual order
                step_index = len(steps)
                
                step = {
                    "step_index": step_index,
                    "action_type": action_type,
                    "expert_id": data.get('expert', 'Unknown'),
                    "inputs": data.get('inputs', []),
                    "output_name": os.path.splitext(os.path.basename(file_path))[0],
                    "timestamp": datetime.fromtimestamp(data.get('timestamp', 0)),
                    "status": "completed",
                    "result": data.get('final_answer', data.get('content', None))
                }
                
                steps.append(step)
                
            except Exception as e:
                logger.error(f"Error processing step file {file_path}: {str(e)}")
        
        # Sort steps by timestamp
        steps.sort(key=lambda s: s["timestamp"])
        
        # Update step indices based on sorted order
        for i, step in enumerate(steps):
            step["step_index"] = i
        
        return steps
    
    async def _extract_tool_calls(self, dir_path: str) -> List[Dict[str, Any]]:
        """
        Extract tool call information from an execution directory.
        
        Args:
            dir_path (str): Path to the execution output directory
            
        Returns:
            List[Dict[str, Any]]: List of tool call information
        """
        tool_calls = []
        
        # In a real implementation, we'd extract tool calls from logs or special files
        # For now, this is a placeholder
        
        return tool_calls
    
    async def _extract_execution_logs(self, dir_path: str) -> List[str]:
        """
        Extract log entries from an execution directory.
        
        Args:
            dir_path (str): Path to the execution output directory
            
        Returns:
            List[str]: List of log entries
        """
        logs = []
        
        # Check the workflow execution log
        log_path = os.path.join(dir_path, "workflow_execution.log")
        
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r') as file:
                    # Read the log line by line
                    for line in file:
                        logs.append(line.strip())
            except Exception as e:
                logger.error(f"Error reading log file {log_path}: {str(e)}")
        
        return logs
