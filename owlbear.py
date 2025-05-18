# workflow_engine.py
import yaml
import os
import time
from typing import Dict, List, Any, Union, Optional, Tuple
import logging
import importlib
import sys
import asyncio

# Import event system
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

# Import the workflow validator
from workflow_validator import validate_workflow

# Import actions
from actions.prompt import execute_prompt_action
from actions.decide import execute_decide_action
from actions.complex import load_complex_action, expand_complex_action
from inference import call_agent

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("workflow-engine")

from dotenv import load_dotenv
load_dotenv()


class WorkflowEngine:
    def __init__(self, workflow_path: str, user_input: Optional[str] = None, strings_path: Optional[str] = None, 
                 skip_validation: bool = False, event_logger: Optional[Any] = None,
                 actions_path: Optional[str] = None, complex_actions_path: Optional[str] = None):
        """Initialize the workflow engine with a YAML workflow definition file.
        
        Args:
            workflow_path: Path to the workflow YAML file
            user_input: Optional user input to be stored as STR_USER_INPUT
            strings_path: Optional path to a separate YAML file containing string variables
            skip_validation: Whether to skip validation
            event_logger: Optional event logger for external integrations
            actions_path: Optional custom path for actions (default: "actions")
            complex_actions_path: Optional custom path for complex actions (default: "actions/complex")
        """
        self.workflow_path = workflow_path
        self.strings_path = strings_path
        self.workflow = None
        self.string_vars = {}
        self.output_vars = {}
        self.current_step = 0
        self.user_input = user_input
        self.variables = {}  # Store variables for template substitution
        self.skip_validation = skip_validation
        self.validated = False
        
        # Store paths for actions and complex actions with defaults
        self.actions_path = actions_path  # Default to None, standard path used in methods
        self.complex_actions_path = complex_actions_path  # Default to None, standard path used in methods
        
        # New attributes for enhanced DECIDE functionality
        self.execution_counts = {}  # Track execution counts for each output variable
        self.output_history = {}    # Track output history for each variable
        self.feedback_cache = {}    # Cache for feedback from DECIDE actions

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
        
        # Path to store validator output
        self.validator_path = ""
        
        # Event logger for external event handling
        self.event_logger = event_logger
        
    def log_debug(self, message: str):
        """Write a debug message to the workflow execution log file."""
        with open(self.debug_log_path, 'a') as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
        logger.debug(message)
        
        # Emit log event
        emitter.emit_sync(EVENT_LOG, message, level="DEBUG")
        
        # Forward to event logger if available
        if self.event_logger and hasattr(self.event_logger, 'log_debug'):
            if asyncio.iscoroutinefunction(self.event_logger.log_debug):
                # Create a new event loop for async methods
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.event_logger.log_debug(message))
                loop.close()
            else:
                self.event_logger.log_debug(message)
        
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
            # Load workflow file
            with open(self.workflow_path, 'r') as file:
                self.workflow = yaml.safe_load(file)
            
            # Load strings from separate file if provided
            if self.strings_path:
                logger.info(f"Loading strings from separate file: {self.strings_path}")
                try:
                    with open(self.strings_path, 'r') as file:
                        strings_data = yaml.safe_load(file)
                    
                    # Extract variables if present
                    variables = {}
                    if 'VARIABLES' in strings_data:
                        variables = strings_data.pop('VARIABLES')
                        logger.info(f"Loaded {len(variables)} variables from {self.strings_path}")
                        # Store variables for use in resolve_input
                        self.variables.update(variables)
                    
                    # Process string variables with variable substitution
                    self.string_vars = self._process_variables(strings_data, variables)
                    logger.info(f"Loaded {len(self.string_vars)} strings from {self.strings_path}")
                except Exception as e:
                    logger.error(f"Failed to load strings file {self.strings_path}: {str(e)}")
                    return False
            else:
                # Fall back to STRINGS section in workflow file
                if 'STRINGS' not in self.workflow:
                    logger.warning("No STRINGS section found in workflow and no strings file provided")
                    self.string_vars = {}
                else:
                    strings_data = self.workflow['STRINGS']
                    # Extract variables if present
                    variables = {}
                    if 'VARIABLES' in strings_data:
                        variables = strings_data.pop('VARIABLES')
                        logger.info(f"Loaded {len(variables)} variables from workflow STRINGS section")
                        # Store variables for use in resolve_input
                        self.variables.update(variables)
                    
                    # Process string variables with variable substitution
                    self.string_vars = self._process_variables(strings_data, variables)
                    # Remove STRINGS section from workflow to maintain clean separation
                    del self.workflow['STRINGS']
            
            # Basic workflow validation
            if 'ACTIONS' not in self.workflow or not self.workflow['ACTIONS']:
                logger.error("No ACTIONS section found in workflow or ACTIONS is empty")
                return False

            # Expand complex actions
            self._expand_complex_actions()

            # Always ensure STR_USER_INPUT exists
            if self.user_input:
                self.string_vars["STR_USER_INPUT"] = self.user_input
            elif "STR_USER_INPUT" not in self.string_vars:
                self.string_vars["STR_USER_INPUT"] = ""

            # Validate that all required strings exist
            required_strings = self._extract_required_strings()
            missing_strings = [s for s in required_strings if s not in self.string_vars]
            if missing_strings:
                logger.error(f"Missing required strings in workflow: {', '.join(missing_strings)}")
                logger.error(f"Available strings: {', '.join(self.string_vars.keys())}")
                return False

            logger.info(f"Loaded workflow with {len(self.workflow['ACTIONS'])} actions")
            return True
        except Exception as e:
            logger.error(f"Failed to load workflow: {str(e)}")
            return False
            
    def _expand_complex_actions(self) -> None:
        """
        Expand all COMPLEX actions in the workflow to their basic components.
        This modifies the self.workflow['ACTIONS'] list in place.
        """
        if 'ACTIONS' not in self.workflow:
            return
            
        expanded_actions = []
        for action in self.workflow['ACTIONS']:
            # Check if this is a COMPLEX action
            if 'COMPLEX' in action:
                complex_data = action['COMPLEX']
                action_name = complex_data.get('action')
                
                logger.info(f"Expanding complex action: {action_name}")
                
                # Load the complex action definition, using custom path if provided
                complex_action_def = load_complex_action(action_name, self.complex_actions_path)
                if not complex_action_def:
                    logger.error(f"Failed to load complex action '{action_name}'")
                    # Keep the original action as a placeholder (will fail validation)
                    expanded_actions.append(action)
                    continue
                    
                # Expand the complex action
                expanded = expand_complex_action(complex_action_def, complex_data)
                
                if not expanded:
                    logger.error(f"Failed to expand complex action '{action_name}'")
                    # Keep the original action as a placeholder (will fail validation)
                    expanded_actions.append(action)
                    continue
                    
                # Add the expanded actions
                expanded_actions.extend(expanded)
                logger.info(f"Complex action '{action_name}' expanded into {len(expanded)} basic actions")
            else:
                # Not a complex action, keep as-is
                expanded_actions.append(action)
                
        # Replace the actions with the expanded version
        self.workflow['ACTIONS'] = expanded_actions
        logger.info(f"Workflow now has {len(expanded_actions)} actions after expansion")
            
    def _extract_required_strings(self) -> List[str]:
        """Extract all string variable references from the workflow that need to be resolved.
        
        Returns:
            List of string variable names that are referenced in the workflow
        """
        required_strings = set()
        
        if not self.workflow or 'ACTIONS' not in self.workflow:
            return list(required_strings)
            
        # Iterate through all actions to find string references
        for action in self.workflow['ACTIONS']:
            action_type = list(action.keys())[0]
            action_data = action[action_type]
            
            # Handle string references in inputs
            if 'inputs' in action_data:
                for input_item in action_data['inputs']:
                    # Check if this is a potential string reference
                    if isinstance(input_item, str) and input_item.startswith('STR_'):
                        required_strings.add(input_item)
        
        # Always include STR_USER_INPUT as a special case
        if 'STR_USER_INPUT' not in required_strings:
            required_strings.add('STR_USER_INPUT')
            
        logger.info(f"Found {len(required_strings)} required strings in workflow: {', '.join(required_strings)}")
        return list(required_strings)
    
    def _process_variables(self, strings_data, variables):
        """Process string variables, replacing {{variable}} references with their values.
        
        Args:
            strings_data (dict): Dictionary of string variables
            variables (dict): Dictionary of variable values
            
        Returns:
            dict: Processed string variables with variables substituted
        """
        import re
        
        # Function to replace {{var}} with its value
        def replace_variables(text, vars_dict):
            if not isinstance(text, str):
                return text
                
            def replace_match(match):
                var_name = match.group(1).strip()
                if var_name in vars_dict:
                    return str(vars_dict[var_name])
                else:
                    logger.warning(f"Undefined variable in template: {var_name}")
                    return f"{{{{UNDEFINED:{var_name}}}}}"  # Keep the syntax but mark as undefined
            
            pattern = r"\{\{([^}]+)\}\}"
            return re.sub(pattern, replace_match, text)
        
        # Process each string in the dictionary
        processed_strings = {}
        for key, value in strings_data.items():
            processed_strings[key] = replace_variables(value, variables)
            
        return processed_strings
    
    def resolve_input(self, input_item: str) -> str:
        """Resolve a string input, which could be a variable reference or literal.
        
        If it's a string variable reference (STR_*), return the value.
        If it's an output reference, return the appropriate field.
        If it's a literal string containing {{var}} patterns, substitute variables.
        Otherwise, return the input unchanged.
        """
        self.log_debug(f"RESOLVE INPUT CALLED WITH: {input_item}")

        # First check if this is a string variable reference
        if input_item in self.string_vars:
            return self.string_vars[input_item]
        elif input_item in self.output_vars:
            # Check if this is a reference to an output that has append-history flag
            current_action = self.workflow['ACTIONS'][self.current_step] if self.workflow and 'ACTIONS' in self.workflow else None
            
            if current_action:
                action_type = list(current_action.keys())[0]  # Get the action type (e.g., PROMPT, DECIDE)
                action_config = current_action[action_type]
                
                # Check for append-history flag
                append_history = action_config.get('append-history', False)
                append_history_type = action_config.get('append-history-type', 'LATEST')
                
                # Handle history appending if enabled
                if append_history and input_item in self.output_history:
                    history = self.output_history[input_item]
                    
                    # Check if the current step is targeted by a DECIDE action (has feedback)
                    step_id = action_config.get('id')
                    has_feedback = (step_id and step_id in self.feedback_cache) or self.current_step in self.feedback_cache
                    
                    # Build the output with history
                    result = ""
                    
                    # Include the output (final_answer only)
                    output_var = self.output_vars[input_item]
                    if 'final_answer' in output_var:
                        result = output_var.get('final_answer')
                    else:
                        logger.warning(f"Output variable {input_item} has no final_answer field")
                        result = ""
                    
                    # Then, append history based on type
                    if append_history_type == 'ALL' and len(history) > 1:
                        result += "\n\n===== PREVIOUS OUTPUTS =====\n"
                        for i, hist_name in enumerate(history[:-1]):  # Skip the most recent one (already included)
                            try:
                                hist_path = os.path.join(self.output_dir, f"{hist_name}.yaml")
                                with open(hist_path, 'r') as file:
                                    hist_data = yaml.safe_load(file)
                                    if 'final_answer' in hist_data:
                                        hist_content = hist_data.get('final_answer', '')
                                        result += f"\n--- Output {i+1} ---\n{hist_content}\n"
                                    else:
                                        logger.warning(f"Historical file {hist_path} has no final_answer field")
                            except Exception as e:
                                self.log_debug(f"Failed to read history file {hist_path}: {str(e)}")
                    
                    elif append_history_type == 'LATEST' and len(history) > 1:
                        # Only include the most recent previous output
                        try:
                            prev_name = history[-2]  # Second-to-last item (latest previous)
                            prev_path = os.path.join(self.output_dir, f"{prev_name}.yaml")
                            with open(prev_path, 'r') as file:
                                prev_data = yaml.safe_load(file)
                                if 'final_answer' in prev_data:
                                    prev_content = prev_data.get('final_answer', '')
                                    result += f"\n\n===== YOUR PREVIOUS OUTPUT =====\n{prev_content}\n"
                                else:
                                    logger.warning(f"Previous output file {prev_path} has no final_answer field")
                        except Exception as e:
                            self.log_debug(f"Failed to read previous output file: {str(e)}")
                    
                    # Add feedback if available
                    if has_feedback:
                        feedback = self.feedback_cache.get(step_id, self.feedback_cache.get(self.current_step, ''))
                        if feedback:
                            result += f"\n\n===== FEEDBACK =====\n{feedback}\n"
                    
                    return result
            
            # Fall back to normal output resolution if history appending not enabled
            output_var = self.output_vars[input_item]
            if 'final_answer' in output_var:
                return output_var.get('final_answer')
            else:
                logger.warning(f"Output variable {input_item} has no final_answer field")
                return ""
        else:
            # Check if this is a file reference that needs path updating
            if input_item.endswith('.yaml') and not os.path.exists(input_item):
                # Try looking in the output directory
                output_path = os.path.join(self.output_dir, input_item)
                if os.path.exists(output_path):
                    try:
                        with open(output_path, 'r') as file:
                            data = yaml.safe_load(file)
                            # Only use final_answer, no more content fallback
                            if 'final_answer' in data:
                                return data.get('final_answer', '')
                            else:
                                logger.warning(f"YAML file {output_path} has no final_answer field")
                                return ""
                    except Exception as e:
                        logger.error(f"Failed to read yaml file {output_path}: {str(e)}")
            
            # If it's a literal string, check for variable patterns
            if isinstance(input_item, str) and '{{' in input_item and '}}' in input_item:
                # Apply variable substitution to inline strings
                logger.info(f"Applying variable substitution to inline string: {input_item}")
                temp_dict = {'temp_var': input_item}
                processed = self._process_variables(temp_dict, self.variables)
                result = processed['temp_var']
                if result != input_item:
                    logger.info(f"Variable substitution result: {result}")
                return result
            
            # Otherwise, return as is
            return input_item
    
    def save_output(self, name: str, data: Dict[str, Any]) -> None:
        """Save action output to a YAML file and to memory with version tracking."""
        # Store in memory
        self.output_vars[name] = data
        
        # Track output history - increment execution count
        self.execution_counts[name] = self.execution_counts.get(name, 0) + 1
        current_count = self.execution_counts[name]
        
        # Create versioned filename
        versioned_name = f"{name}_{current_count:04d}"
        
        # Store in history tracker
        if name not in self.output_history:
            self.output_history[name] = []
        self.output_history[name].append(versioned_name)
        
        # If this is a DECIDE action with an explanation, cache the feedback
        if data.get('action_type') == 'DECIDE' and 'explanation' in data:
            # For string ID loopback
            loopback_target = data.get('loopback_target')
            if loopback_target is not None:
                self.feedback_cache[loopback_target] = data['explanation']
        
        # Save both the regular and versioned output files
        self._save_output_to_file(os.path.join(self.output_dir, f"{name}.yaml"), data)
        self._save_output_to_file(os.path.join(self.output_dir, f"{versioned_name}.yaml"), data)
        
        self.log_debug(f"Saved output '{name}' (version {current_count}) to files")
    
    def _save_output_to_file(self, output_path: str, data: Dict[str, Any]) -> None:
        """Helper method to save output data to a YAML file."""
        try:
            # Set up a custom string representer to always use literal style
            def represent_str_literal(dumper, data):
                if '\n' in data:
                    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
                return dumper.represent_scalar('tag:yaml.org,2002:str', data)
            
            # Custom dictionary representer for history items to preserve field order
            def represent_dict_preserve_order(dumper, data):
                if 'history' in data and isinstance(data['history'], list):
                    # Ensure role comes before content in each history item
                    for item in data['history']:
                        if 'role' in item and 'content' in item:
                            # Reorder the keys to ensure role is first
                            ordered_item = {}
                            ordered_item['role'] = item['role']
                            ordered_item['content'] = item['content']
                            # Replace the original item with the ordered one
                            item.clear()
                            item.update(ordered_item)
                            
                return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())
                       
            # Add the custom representers
            yaml.add_representer(str, represent_str_literal)
            yaml.add_representer(dict, represent_dict_preserve_order)
            
            with open(output_path, 'w') as file:
                yaml.dump(data, file, default_flow_style=False, allow_unicode=True, width=float("inf"))
            
            logger.info(f"Saved output to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save output to {output_path}: {str(e)}")


    def validate_workflow(self) -> Tuple[bool, str]:
        """Validate the workflow before execution.
        
        Returns:
            Tuple[bool, str]: (success, validator_output_path)
        """
        if self.validated:
            return True, self.validator_path
            
        if self.skip_validation:
            logger.info("Skipping workflow validation due to skip_validation flag")
            self.validated = True
            return True, ""
            
        logger.info("Validating workflow before execution")
        success, output_path = validate_workflow(
            self.workflow_path, 
            self.strings_path, 
            self.output_dir,
            self.complex_actions_path
        )
        
        self.validated = True
        self.validator_path = output_path
        
        if success:
            self.log_debug(f"Workflow validation successful. Expanded workflow saved to: {output_path}")
            logger.info(f"Workflow validation successful. Expanded workflow saved to: {output_path}")
            # Print a reminder about the validated workflow file
            workflow_name = os.path.basename(self.workflow_path).split('.')[0]
            validated_file = f"{workflow_name}_validated.yaml"
            logger.info(f"You can review the expanded workflow in: {os.path.join(self.output_dir, validated_file)}")
        else:
            self.log_debug("Workflow validation failed! See validator output for details.")
            logger.error("Workflow validation failed! See validator output for details.")
            
        return success, output_path
    
    def run(self) -> bool:
        """Run the entire workflow."""
        if not self.workflow:
            if not self.load_workflow():
                return False
                
        # Validate the workflow before execution
        if not self.validated and not self.skip_validation:
            success, _ = self.validate_workflow()
            if not success:
                logger.error("Workflow validation failed. Aborting execution.")
                emitter.emit_sync(EVENT_ERROR, "Workflow validation failed. Aborting execution.")
                return False
        
        actions = self.workflow['ACTIONS']
        self.current_step = 0
        
        # Create a map of action IDs to step indices for id-based loopback
        action_id_map = {}
        for i, action in enumerate(actions):
            action_type = list(action.keys())[0]
            action_data = action[action_type]
            if 'id' in action_data:
                action_id = action_data['id']
                action_id_map[action_id] = i
                self.log_debug(f"Mapped action ID '{action_id}' to step index {i} (step {i+1})")
        
        # Emit workflow start event
        workflow_id = os.path.basename(self.workflow_path).split('.')[0]
        emitter.emit_sync(EVENT_WORKFLOW_START, workflow_id=workflow_id, path=self.workflow_path)
        
        # Log workflow starting
        self.log_debug(f"WORKFLOW STARTING WITH {len(actions)} ACTIONS")
        self.log_debug("Workflow steps structure:")
        for i, action in enumerate(actions):
            action_type = list(action.keys())[0]
            if action_type == 'DECIDE':
                loopback = action[action_type].get('loopback')
                loopback_target = action[action_type].get('loopback_target')
                if loopback is not None:
                    self.log_debug(f"  Step {i+1}: {action_type} (loopback: {loopback}, loopback-1: {loopback-1})")
                elif loopback_target is not None:
                    self.log_debug(f"  Step {i+1}: {action_type} (loopback_target: {loopback_target})")
                else:
                    self.log_debug(f"  Step {i+1}: {action_type} (no loopback defined)")
            else:
                self.log_debug(f"  Step {i+1}: {action_type}")
        self.log_debug("="*50)
        
        exec_count = {}
        
        # NEW: Dictionary to track DECIDE loop counts across loop iterations
        decide_loop_counts = {}
        
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
            
            # Emit step start event
            expert_id = action_details.get('expert', 'unknown')
            # Include the description field if it exists in the action_details
            description = action_details.get('description', None)
            emitter.emit_sync(EVENT_STEP_START, 
                step_index=self.current_step, 
                action_type=action_type, 
                expert_id=expert_id,
                description=description,
                execution_count=exec_count[self.current_step])
            
            # Create context to pass to action handlers
            context = {
                'step_number': self.current_step + 1,
                'resolve_input': self.resolve_input,
                'save_output': self.save_output,
                'call_agent': call_agent,
                'output_vars': self.output_vars,
                'feedback_cache': self.feedback_cache
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
                # Get the unique identifier for this specific DECIDE action and its loopback target
                loopback_target = action_details.get('loopback_target')
                decide_id = f"{self.current_step}_{loopback_target}"
                
                # Initialize loop counter for this DECIDE action if not already tracking
                if decide_id not in decide_loop_counts:
                    decide_loop_counts[decide_id] = 0
                
                # Get the loop limit
                loop_limit = action_details.get('loop_limit', 10)
                
                # Check if we've already hit the loop limit
                if decide_loop_counts[decide_id] >= loop_limit:
                    self.log_debug(f"Loop limit reached for DECIDE action at step {self.current_step + 1} (attempt {decide_loop_counts[decide_id]}/{loop_limit})")
                    logger.error(f"Loop limit reached for DECIDE action at step {self.current_step + 1}")
                    return False
                
                # Execute the DECIDE action
                self.log_debug(f"Starting DECIDE action (step {self.current_step+1}) with loopback_target={loopback_target}")
                self.log_debug(f"DECIDE evaluation attempt #{decide_loop_counts[decide_id] + 1}/{loop_limit}")
                
                success, next_step = execute_decide_action(action_details, context)
                if not success:
                    self.log_debug(f"DECIDE action failed at step {self.current_step+1}")
                    return False
                
                if next_step is None:
                    # Decision was TRUE, move to next step
                    self.log_debug(f"DECIDE result: TRUE - Moving from step {self.current_step+1} to step {self.current_step+2}")
                    self.current_step += 1
                    
                    # Reset the loop counter for this DECIDE action when it passes
                    decide_loop_counts[decide_id] = 0
                else:
                    # Decision was FALSE, loop back using ID-based loopback
                    # Increment the loop counter
                    decide_loop_counts[decide_id] += 1
                    current_loop_count = decide_loop_counts[decide_id]
                    
                    # Handle string ID-based loopback target
                    if next_step in action_id_map:
                        target_step = action_id_map[next_step]
                        self.log_debug(f"DECIDE result: FALSE - Looping back from step {self.current_step+1} to action ID '{next_step}' (step {target_step+1})")
                        self.log_debug(f"Loop attempt {current_loop_count}/{loop_limit}")
                        
                        logger.info(f"Looping back to action ID '{next_step}' (step {target_step+1}) (attempt {current_loop_count}/{loop_limit})")
                        
                        # Log detailed information about the ID-based loopback
                        self.log_debug(f"LOOPBACK TRACE (ID-based):")
                        from_type = self.get_step_type(self.current_step)
                        to_type = self.get_step_type(target_step)
                        self.log_debug(f"  From: Step {self.current_step+1} ({from_type}, 0-indexed: {self.current_step})")
                        self.log_debug(f"  To: Step {target_step+1} ({to_type}, 0-indexed: {target_step})")
                        self.log_debug(f"  Loopback target ID: '{next_step}'")
                        
                        # Reset the current step to the target step
                        self.log_debug(f"Setting current_step from {self.current_step} to {target_step} (0-indexed) which is step {target_step+1} in workflow")
                        logger.debug(f"Setting current_step to {target_step} (0-indexed) which is step {target_step+1} in the workflow")
                        self.current_step = target_step
                    else:
                        error_msg = f"INVALID LOOPBACK TARGET ID: '{next_step}' is not defined in the workflow"
                        self.log_debug(error_msg)
                        logger.error(error_msg)
                        return False
            
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
        
        # Emit workflow end event
        workflow_id = os.path.basename(self.workflow_path).split('.')[0]
        emitter.emit_sync(EVENT_WORKFLOW_END, workflow_id=workflow_id, success=True)
        
        logger.info("Workflow completed successfully")
        return True


def run_workflow(workflow_path: str, user_input: Optional[str] = None, strings_path: Optional[str] = None, 
              skip_validation: bool = False, actions_path: Optional[str] = None, 
              complex_actions_path: Optional[str] = None) -> bool:
    """Helper function to run a workflow from a file path.
    
    Args:
        workflow_path: Path to the workflow YAML file
        user_input: Optional user input to be stored as STR_USER_INPUT
        strings_path: Optional path to a separate YAML file containing string variables
        skip_validation: Whether to skip validation
        actions_path: Optional custom path for actions
        complex_actions_path: Optional custom path for complex actions
        
    Returns:
        bool: True if the workflow was executed successfully, False otherwise
    """
    engine = WorkflowEngine(
        workflow_path, 
        user_input, 
        strings_path, 
        skip_validation,
        actions_path=actions_path,
        complex_actions_path=complex_actions_path
    )
    return engine.run()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='OWLBEAR: Orchestrated Workflow Logic with Bespoke Experts for Agentic Routines')
    parser.add_argument('workflow', help='Path to the workflow YAML file')
    parser.add_argument('--user-input', '-u', help='User input to be stored as STR_USER_INPUT')
    parser.add_argument('--strings', '-s', help='Path to a separate YAML file containing string variables. This allows decoupling string variables from workflow definitions.')
    parser.add_argument('--skip-validation', action='store_true', help='Skip workflow validation before execution')
    parser.add_argument('--validate-only', action='store_true', help='Only validate the workflow without executing it')
    parser.add_argument('--actions-path', help='Custom path for actions directory (default: "actions")')
    parser.add_argument('--complex-actions-path', help='Custom path for complex actions directory (default: "actions/complex")')
    
    args = parser.parse_args()
    
    # Log the parameters
    logger.info(f"Starting workflow: {args.workflow}")
    if args.strings:
        logger.info(f"Using strings file: {args.strings}")
    if args.user_input:
        logger.info(f"With user input: {args.user_input}")
    if args.skip_validation:
        logger.info("Skipping workflow validation")
    if args.validate_only:
        logger.info("Running in validation-only mode")
    if args.actions_path:
        logger.info(f"Using custom actions path: {args.actions_path}")
    if args.complex_actions_path:
        logger.info(f"Using custom complex actions path: {args.complex_actions_path}")
    
    engine = WorkflowEngine(
        args.workflow, 
        args.user_input, 
        args.strings, 
        args.skip_validation,
        actions_path=args.actions_path,
        complex_actions_path=args.complex_actions_path
    )
    
    if args.validate_only:
        # Run validation only
        success, validator_path = engine.validate_workflow()
        if success:
            workflow_name = os.path.basename(args.workflow).split('.')[0]
            validated_file = f"{workflow_name}_validated.yaml"
            output_dir = os.path.dirname(validator_path)
            print(f"\nWorkflow validation successful!")
            print(f"Expanded workflow saved to: {validator_path}")
            print(f"\nUse this command to view the validated workflow:")
            print(f"cat {validator_path}")
        else:
            print("\nWorkflow validation failed! See log for details.")
    else:
        # Run the complete workflow
        success = engine.run()
    
    if success:
        print("Workflow completed successfully!")
        sys.exit(0)
    else:
        print("Workflow failed!")
        sys.exit(1)