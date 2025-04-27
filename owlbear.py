# workflow_engine.py
import yaml
import os
import time
from typing import Dict, List, Any, Union, Optional
import logging
import importlib
import sys

# Import actions
from actions.prompt import execute_prompt_action
from actions.decide import execute_decide_action
from inference import call_agent

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("workflow-engine")

from dotenv import load_dotenv
load_dotenv()


class WorkflowEngine:
    def __init__(self, workflow_path: str, user_input: Optional[str] = None):
        """Initialize the workflow engine with a YAML workflow definition file."""
        self.workflow_path = workflow_path
        self.workflow = None
        self.string_vars = {}
        self.output_vars = {}
        self.current_step = 0
        self.user_input = user_input

        # Get workflow name from file path
        workflow_name = os.path.basename(workflow_path).split('.')[0]
        
        # Create timestamped output directory
        timestamp = time.strftime("%Y-%m-%d-%H-%M")
        self.output_dir = os.path.join("outputs", f"{workflow_name}_{timestamp}")
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"Created output directory: {self.output_dir}")
        
        # Create a debug log file to track workflow execution
        self.debug_log_path = os.path.join(self.output_dir, "workflow_execution.log")
        with open(self.debug_log_path, 'w') as f:
            f.write(f"Workflow Execution Log: {workflow_name} - {timestamp}\n")
            f.write("=" * 80 + "\n\n")
        logger.info(f"Created debug log file: {self.debug_log_path}")
        
    def log_debug(self, message: str):
        """Write a debug message to the workflow execution log file."""
        with open(self.debug_log_path, 'a') as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
        logger.debug(message)
        
    def get_step_type(self, step_index: int) -> str:
        """Get the action type for a given step (0-indexed)"""
        if not self.workflow or 'ACTIONS' not in self.workflow:
            return "UNKNOWN"
            
        actions = self.workflow['ACTIONS']
        if step_index < 0 or step_index >= len(actions):
            return f"INVALID_STEP({step_index})"
            
        action = actions[step_index]
        return list(action.keys())[0]

    def load_workflow(self) -> bool:
        """Load and validate the workflow YAML file."""
        try:
            with open(self.workflow_path, 'r') as file:
                self.workflow = yaml.safe_load(file)
            
            # Basic validation
            if 'STRINGS' not in self.workflow:
                logger.warning("No STRINGS section found in workflow")
                self.string_vars = {}
            else:
                self.string_vars = self.workflow['STRINGS']
            
            if 'ACTIONS' not in self.workflow or not self.workflow['ACTIONS']:
                logger.error("No ACTIONS section found in workflow or ACTIONS is empty")
                return False

            if self.user_input:
                self.string_vars["STR_USER_INPUT"] = self.user_input
            # Otherwise, ensure it exists with empty string if not defined
            elif "STR_USER_INPUT" not in self.string_vars:
                self.string_vars["STR_USER_INPUT"] = ""

            logger.info(f"Loaded workflow with {len(self.workflow['ACTIONS'])} actions")
            return True
        except Exception as e:
            logger.error(f"Failed to load workflow: {str(e)}")
            return False
    
    def resolve_input(self, input_item: str) -> str:
        """Resolve a string input, which could be a variable reference or literal."""
        if input_item in self.string_vars:
            return self.string_vars[input_item]
        elif input_item in self.output_vars:
            # If this is an output reference, get just the content (not metadata)
            return self.output_vars[input_item].get('content')
        else:
            # Check if this is a file reference that needs path updating
            if input_item.endswith('.yaml') and not os.path.exists(input_item):
                # Try looking in the output directory
                output_path = os.path.join(self.output_dir, input_item)
                if os.path.exists(output_path):
                    try:
                        with open(output_path, 'r') as file:
                            data = yaml.safe_load(file)
                            return data.get('content', '')
                    except Exception as e:
                        logger.error(f"Failed to read yaml file {output_path}: {str(e)}")
            
            return input_item
    
    def save_output(self, name: str, data: Dict[str, Any]) -> None:
        """Save action output to a YAML file and to memory."""
        # Store in memory
        self.output_vars[name] = data
        
        # Save to file
        output_path = os.path.join(self.output_dir, f"{name}.yaml")
        try:
            # Set up a custom string representer to always use literal style
            def represent_str_literal(dumper, data):
                if '\n' in data:
                    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
                return dumper.represent_scalar('tag:yaml.org,2002:str', data)     
                       
            # Add the custom representer
            yaml.add_representer(str, represent_str_literal)
            
            with open(output_path, 'w') as file:
                yaml.dump(data, file, default_flow_style=False, allow_unicode=True, width=float("inf"))
            
            logger.info(f"Saved output to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save output to {output_path}: {str(e)}")


    def run(self) -> bool:
        """Run the entire workflow."""
        if not self.workflow:
            if not self.load_workflow():
                return False
        
        actions = self.workflow['ACTIONS']
        self.current_step = 0
        
        # Log workflow starting
        self.log_debug(f"WORKFLOW STARTING WITH {len(actions)} ACTIONS")
        self.log_debug("Workflow steps structure:")
        for i, action in enumerate(actions):
            action_type = list(action.keys())[0]
            if action_type == 'DECIDE':
                loopback = action[action_type].get('loopback')
                self.log_debug(f"  Step {i+1}: {action_type} (loopback: {loopback}, loopback-1: {loopback-1})")
            else:
                self.log_debug(f"  Step {i+1}: {action_type}")
        self.log_debug("="*50)
        
        exec_count = {}
        
        while self.current_step < len(actions):
            action = actions[self.current_step]
            # Track how many times each step is executed
            exec_count[self.current_step] = exec_count.get(self.current_step, 0) + 1
            
            # Determine action type and execute
            action_type = list(action.keys())[0]
            action_details = action[action_type]
            
            # Log execution with detailed information
            self.log_debug(f"EXECUTING: Step {self.current_step+1} ({action_type}) - Execution #{exec_count[self.current_step]}")
            logger.info(f"Executing step {self.current_step + 1}/{len(actions)}")
            
            # Create context to pass to action handlers
            context = {
                'step_number': self.current_step + 1,
                'resolve_input': self.resolve_input,
                'save_output': self.save_output,
                'call_agent': call_agent,
                'output_vars': self.output_vars
            }
            
            if action_type == 'PROMPT':
                self.log_debug(f"Starting PROMPT action (step {self.current_step+1})")
                success = execute_prompt_action(action_details, context)
                if not success:
                    self.log_debug(f"PROMPT action failed at step {self.current_step+1}")
                    return False
                self.log_debug(f"PROMPT action succeeded at step {self.current_step+1}")
                self.log_debug(f"Moving from step {self.current_step+1} to step {self.current_step+2}")
                self.current_step += 1
                
            elif action_type == 'DECIDE':
                loop_limit = action_details.get('loop_limit', 10)
                loop_count = 0
                loopback = action_details.get('loopback')
                
                self.log_debug(f"Starting DECIDE action (step {self.current_step+1}) with loopback={loopback} (1-indexed)")
                
                while loop_count < loop_limit:
                    self.log_debug(f"DECIDE evaluation #{loop_count+1} at step {self.current_step+1}")
                    success, next_step = execute_decide_action(action_details, context)
                    if not success:
                        self.log_debug(f"DECIDE action failed at step {self.current_step+1}")
                        return False
                    
                    if next_step is None:
                        # Decision was TRUE, move to next step
                        self.log_debug(f"DECIDE result: TRUE - Moving from step {self.current_step+1} to step {self.current_step+2}")
                        self.current_step += 1
                        break
                    else:
                        # Decision was FALSE, loop back
                        loop_count += 1
                        self.log_debug(f"DECIDE result: FALSE - Looping back from step {self.current_step+1} to step {next_step+1} (0-indexed: {next_step})")
                        self.log_debug(f"Loop attempt {loop_count}/{loop_limit}")
                        
                        logger.info(f"Looping back to step {next_step + 1} (attempt {loop_count}/{loop_limit})")
                        if loop_count >= loop_limit:
                            self.log_debug(f"Loop limit reached for DECIDE action at step {self.current_step + 1}")
                            logger.error(f"Loop limit reached for DECIDE action at step {self.current_step + 1}")
                            return False
                            
                        # BUGFIX: The problem occurs when a DECIDE action loops back to an earlier step,
                        # especially when multiple DECIDE actions are chained.
                        # 
                        # For clarity and debugging, we're going to add explicit verification that the
                        # loopback value is valid and properly 0-indexed when we apply it:
                        
                        if next_step < 0 or next_step >= len(actions):
                            error_msg = f"INVALID LOOPBACK: {next_step} is outside workflow range (0-{len(actions)-1})"
                            self.log_debug(error_msg)
                            logger.error(error_msg)
                            return False
                           
                        # Log detailed information about the loopback process
                        self.log_debug(f"LOOPBACK TRACE:")
                        from_type = self.get_step_type(self.current_step)
                        to_type = self.get_step_type(next_step)
                        self.log_debug(f"  From: Step {self.current_step+1} ({from_type}, 0-indexed: {self.current_step})")
                        self.log_debug(f"  To: Step {next_step+1} ({to_type}, 0-indexed: {next_step})")
                        self.log_debug(f"  Loopback defined in YAML: {action_details.get('loopback')}")
                        self.log_debug(f"  Adjusted in decide.py: {action_details.get('loopback')-1}")
                        
                        # This verification log will help identify incorrect loopback targets
                        expected_loopback = action_details.get('loopback') - 1
                        if next_step != expected_loopback:
                            self.log_debug(f"WARNING: LOOPBACK MISMATCH - Expected {expected_loopback} but got {next_step}")
                        
                        # Reset the current step to the loopback target
                        self.log_debug(f"Setting current_step from {self.current_step} to {next_step} (0-indexed) which is step {next_step+1} in workflow")
                        logger.debug(f"Setting current_step to {next_step} (0-indexed) which is step {next_step+1} in the workflow")
                        self.current_step = next_step
                        
                        # FIX: Break out of the DECIDE loop when looping back to allow proper re-evaluation of the action type
                        # This is the key fix for the workflow orchestration bug
                        self.log_debug(f"BUGFIX: Breaking out of DECIDE loop to re-evaluate action at step {next_step+1}")
                        break
            
            else:
                self.log_debug(f"Unknown action type: {action_type} at step {self.current_step + 1}")
                logger.error(f"Unknown action type: {action_type} at step {self.current_step + 1}")
                return False
            
            # Add a visual separator in the log
            self.log_debug("-"*50)
        
        self.log_debug("WORKFLOW COMPLETED SUCCESSFULLY")
        self.log_debug("Execution summary:")
        for step, count in sorted(exec_count.items()):
            action_type = list(actions[step].keys())[0]
            self.log_debug(f"  Step {step+1} ({action_type}): Executed {count} times")
            
        logger.info("Workflow completed successfully")
        
        logger.info("Workflow completed successfully")
        return True


def run_workflow(workflow_path: str) -> bool:
    """Helper function to run a workflow from a file path."""
    engine = WorkflowEngine(workflow_path)
    return engine.run()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python owlbear.py <workflow_yaml_path> [user_prompt]")
        sys.exit(1)
    
    workflow_path = sys.argv[1]
    user_input = sys.argv[2] if len(sys.argv) > 2 else None
    
    engine = WorkflowEngine(workflow_path, user_input)
    success = engine.run()
    
    if success:
        print("Workflow completed successfully!")
        sys.exit(0)
    else:
        print("Workflow failed!")
        sys.exit(1)