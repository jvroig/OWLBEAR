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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("workflow-engine")

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
        
        while self.current_step < len(actions):
            action = actions[self.current_step]
            logger.info(f"Executing step {self.current_step + 1}/{len(actions)}")
            
            # Determine action type and execute
            action_type = list(action.keys())[0]
            action_details = action[action_type]
            
            # Create context to pass to action handlers
            context = {
                'step_number': self.current_step + 1,
                'resolve_input': self.resolve_input,
                'save_output': self.save_output,
                'call_agent': call_agent,
                'output_vars': self.output_vars
            }
            
            if action_type == 'PROMPT':
                success = execute_prompt_action(action_details, context)
                if not success:
                    return False
                self.current_step += 1
                
            elif action_type == 'DECIDE':
                loop_limit = action_details.get('loop_limit', 10)
                loop_count = 0
                
                while loop_count < loop_limit:
                    success, next_step = execute_decide_action(action_details, context)
                    if not success:
                        return False
                    
                    if next_step is None:
                        # Decision was TRUE, move to next step
                        self.current_step += 1
                        break
                    else:
                        # Decision was FALSE, loop back
                        loop_count += 1
                        logger.info(f"Looping back to step {next_step + 1} (attempt {loop_count}/{loop_limit})")
                        if loop_count >= loop_limit:
                            logger.error(f"Loop limit reached for DECIDE action at step {self.current_step + 1}")
                            return False
                        self.current_step = next_step
            
            else:
                logger.error(f"Unknown action type: {action_type} at step {self.current_step + 1}")
                return False
        
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