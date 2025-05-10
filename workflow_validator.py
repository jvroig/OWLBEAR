#!/usr/bin/env python3
# workflow_validator.py
import yaml
import os
import re
import logging
import time
from typing import Dict, List, Any, Union, Optional, Tuple
from collections import defaultdict
import sys

# Import complex action handling
from actions.complex import load_complex_action, expand_complex_action

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("workflow-validator")

class WorkflowValidator:
    def __init__(self, workflow_path: str, strings_path: Optional[str] = None, output_dir: Optional[str] = None):
        """Initialize the workflow validator.
        
        Args:
            workflow_path: Path to the workflow YAML file
            strings_path: Optional path to a separate YAML file containing string variables
            output_dir: Optional output directory for the validated workflow
        """
        self.workflow_path = workflow_path
        self.strings_path = strings_path
        self.workflow = None
        self.string_vars = {}
        self.variables = {}
        self.validation_errors = []
        self.validation_warnings = []
        self.output_dir = output_dir
        
        # Create output directory if specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
    
    def add_error(self, message: str):
        """Add a validation error message."""
        self.validation_errors.append(message)
        logger.error(f"Validation error: {message}")
    
    def add_warning(self, message: str):
        """Add a validation warning message."""
        self.validation_warnings.append(message)
        logger.warning(f"Validation warning: {message}")
        
    def load_workflow(self) -> bool:
        """Load the workflow from the YAML file."""
        try:
            with open(self.workflow_path, 'r') as file:
                self.workflow = yaml.safe_load(file)
                
            if not self.workflow:
                self.add_error(f"Empty or invalid workflow file: {self.workflow_path}")
                return False
                
            if not isinstance(self.workflow, dict):
                self.add_error(f"Workflow must be a YAML dictionary/object, got: {type(self.workflow)}")
                return False
                
            # Load strings if specified
            if self.strings_path:
                if not self._load_strings():
                    return False
            elif 'STRINGS' in self.workflow:
                self.string_vars = self.workflow.pop('STRINGS', {})
                # Extract variables if present
                if 'VARIABLES' in self.string_vars:
                    self.variables = self.string_vars.pop('VARIABLES', {})
            
            # Check for ACTIONS section
            if 'ACTIONS' not in self.workflow:
                self.add_error("Missing ACTIONS section in workflow")
                return False
                
            logger.info(f"Loaded workflow with {len(self.workflow['ACTIONS'])} actions")
            return True
        except Exception as e:
            self.add_error(f"Failed to load workflow: {str(e)}")
            return False
    
    def _load_strings(self) -> bool:
        """Load string variables from a separate file."""
        try:
            with open(self.strings_path, 'r') as file:
                strings_data = yaml.safe_load(file)
                
            if not strings_data:
                self.add_error(f"Empty or invalid strings file: {self.strings_path}")
                return False
                
            # Extract variables if present
            if 'VARIABLES' in strings_data:
                self.variables = strings_data.pop('VARIABLES', {})
                
            self.string_vars = strings_data
            return True
        except Exception as e:
            self.add_error(f"Failed to load strings file: {str(e)}")
            return False
            
    def _resolve_variables(self, template: str) -> str:
        """Replace variables in a template string."""
        if not isinstance(template, str) or '{{' not in template:
            return template
            
        pattern = r'\{\{([^}]+)\}\}'
        def replace(match):
            var_name = match.group(1).strip()
            if var_name in self.variables:
                return str(self.variables[var_name])
            else:
                self.add_warning(f"Undefined variable: {var_name}")
                return f"{{UNDEFINED:{var_name}}}"
                
        return re.sub(pattern, replace, template)
            
    def validate_action_structure(self):
        """Validate the structure of each action in the workflow."""
        if not self.workflow or 'ACTIONS' not in self.workflow:
            return
            
        # Track all action IDs for validation
        action_ids = set()
        for j, act in enumerate(self.workflow['ACTIONS']):
            if not isinstance(act, dict) or len(act) != 1:
                continue  # Skip invalid actions
            act_type = list(act.keys())[0]
            act_data = act[act_type]
            if 'id' in act_data:
                action_ids.add(act_data['id'])
                
        for i, action in enumerate(self.workflow['ACTIONS']):
            if not isinstance(action, dict) or len(action) != 1:
                self.add_error(f"Action {i+1} has invalid structure: {action}")
                continue
                
            action_type = list(action.keys())[0]
            action_data = action[action_type]
            
            # Validate common action properties
            if 'output' not in action_data:
                self.add_error(f"Action {i+1} ({action_type}) is missing 'output' field")
            
            if 'expert' not in action_data:
                self.add_error(f"Action {i+1} ({action_type}) is missing 'expert' field")
            
            # Validate action-specific structure
            if action_type == 'PROMPT':
                if 'inputs' not in action_data or not action_data['inputs']:
                    self.add_warning(f"Action {i+1} (PROMPT) has empty or missing 'inputs'")
                
                # Check for append-history flag configuration
                if 'append-history' in action_data and action_data['append-history']:
                    if 'append-history-type' in action_data:
                        append_type = action_data['append-history-type']
                        if append_type not in ['ALL', 'LATEST']:
                            self.add_warning(f"Action {i+1} (PROMPT) has invalid 'append-history-type' value: {append_type} (must be 'ALL' or 'LATEST')")
                    
            elif action_type == 'COMPLEX':
                # Validate COMPLEX action structure
                if 'action' not in action_data:
                    self.add_error(f"Action {i+1} (COMPLEX) is missing 'action' field - must specify which complex action to use")
                else:
                    # Check if the complex action exists
                    action_name = action_data.get('action')
                    complex_def = load_complex_action(action_name)
                    if not complex_def:
                        self.add_error(f"Action {i+1} (COMPLEX) references unknown complex action '{action_name}'")
                    
                # Check for expert field
                if 'expert' not in action_data:
                    self.add_error(f"Action {i+1} (COMPLEX) is missing 'expert' field")
                    
                # Check that data field exists if required by the complex action
                if 'data' not in action_data:
                    self.add_warning(f"Action {i+1} (COMPLEX) is missing 'data' field - complex action may require variables")
                
            elif action_type == 'DECIDE':
                if 'inputs' not in action_data or not action_data['inputs']:
                    self.add_warning(f"Action {i+1} (DECIDE) has empty or missing 'inputs'")
                
                # Validate loopback_target field is present
                has_loopback_target = 'loopback_target' in action_data
                
                if not has_loopback_target:
                    self.add_error(f"Action {i+1} (DECIDE) is missing 'loopback_target' field - this is required")
                
                # Show warning if deprecated loopback field is still used
                if 'loopback' in action_data:
                    self.add_error(f"Action {i+1} (DECIDE) uses deprecated 'loopback' field - use 'loopback_target' instead")
                
                # Validate string loopback_target
                if has_loopback_target:
                    target = action_data['loopback_target']
                    if not isinstance(target, str):
                        self.add_error(f"Action {i+1} (DECIDE) has invalid 'loopback_target' value: {target} (must be a string ID)")
                    elif target not in action_ids:
                        self.add_error(f"Action {i+1} (DECIDE) has unknown 'loopback_target' ID: '{target}' (no action with this ID found)")
                
                # Validate loop_limit if present
                if 'loop_limit' in action_data:
                    if not isinstance(action_data['loop_limit'], int):
                        self.add_error(f"Action {i+1} (DECIDE) has invalid 'loop_limit' value: {action_data['loop_limit']} (must be an integer)")
                    elif action_data['loop_limit'] < 1:
                        self.add_error(f"Action {i+1} (DECIDE) has invalid 'loop_limit' value: {action_data['loop_limit']} (must be > 0)")
            else:
                self.add_error(f"Action {i+1} has unknown action type: {action_type}")
    
    def validate_string_references(self):
        """Validate that all string references in the workflow are defined."""
        if not self.workflow or 'ACTIONS' not in self.workflow:
            return
            
        # Build set of all defined string variables
        defined_strings = set(self.string_vars.keys())
        defined_strings.add('STR_USER_INPUT')  # Special case
        
        # Check for undefined string references in each action
        for i, action in enumerate(self.workflow['ACTIONS']):
            if not isinstance(action, dict) or len(action) != 1:
                continue  # Skip invalid actions
                
            action_type = list(action.keys())[0]
            action_data = action[action_type]
            
            # Check inputs for string references
            inputs = action_data.get('inputs', [])
            for j, input_item in enumerate(inputs):
                if isinstance(input_item, str) and input_item.startswith('STR_') and input_item not in defined_strings:
                    self.add_error(f"Action {i+1} ({action_type}) references undefined string variable: {input_item}")
    
    def expand_variables(self):
        """Expand variables in the workflow."""
        if not self.workflow or 'ACTIONS' not in self.workflow:
            return
            
        # Process the workflow to expand variables
        expanded_workflow = {
            'ACTIONS': []
        }
        
        for action in self.workflow['ACTIONS']:
            if not isinstance(action, dict) or len(action) != 1:
                expanded_workflow['ACTIONS'].append(action)
                continue
                
            action_type = list(action.keys())[0]
            action_data = action[action_type]
            
            # Create new action with expanded variables
            expanded_action = {action_type: {}}
            
            for key, value in action_data.items():
                if key == 'inputs':
                    # Expand variables in inputs
                    expanded_inputs = []
                    for input_item in value:
                        if isinstance(input_item, str):
                            if input_item.startswith('STR_') and input_item in self.string_vars:
                                # Reference to a string variable
                                expanded_inputs.append(self._resolve_variables(self.string_vars[input_item]))
                            else:
                                # Regular string, might contain variables
                                expanded_inputs.append(self._resolve_variables(input_item))
                        else:
                            expanded_inputs.append(input_item)
                    expanded_action[action_type]['inputs'] = expanded_inputs
                else:
                    # Copy other fields as-is or expand if they are strings
                    if isinstance(value, str):
                        expanded_action[action_type][key] = self._resolve_variables(value)
                    else:
                        expanded_action[action_type][key] = value
            
            expanded_workflow['ACTIONS'].append(expanded_action)
        
        return expanded_workflow
    
    def validate(self) -> Tuple[bool, str]:
        """Validate the workflow.
        
        Returns:
            tuple: (success, output_path)
        """
        # Clear previous validation results
        self.validation_errors = []
        self.validation_warnings = []
        
        logger.info(f"Output directory: {self.output_dir}")
        
        # Step 1: Load the workflow
        if not self.load_workflow():
            return False, ""
        
        # Step 2: Validate structure of each action
        self.validate_action_structure()
        
        # Step 3: Validate string references
        self.validate_string_references()
        
        # Check for validation errors
        if self.validation_errors:
            logger.error(f"Validation failed with {len(self.validation_errors)} errors:")
            for i, error in enumerate(self.validation_errors):
                logger.error(f"  {i+1}. {error}")
            return False, ""
        
        # Step 4: Expand variables
        expanded_workflow = self.expand_variables()
        
        # Save the expanded workflow if specified
        if self.output_dir:
            # Create a filename for the validated workflow
            workflow_name = os.path.basename(self.workflow_path).split('.')[0]
            validated_path = os.path.join(self.output_dir, f"{workflow_name}_validated.yaml")
            
            try:
                with open(validated_path, 'w') as file:
                    yaml.dump(expanded_workflow, file, default_flow_style=False)
                logger.info(f"Saved validated workflow to: {validated_path}")
                return True, validated_path
            except Exception as e:
                logger.error(f"Failed to save validated workflow: {str(e)}")
                return False, ""
        
        return True, ""


def validate_workflow(workflow_path: str, strings_path: Optional[str] = None, output_dir: Optional[str] = None) -> Tuple[bool, str]:
    """Validate a workflow.
    
    Args:
        workflow_path: Path to the workflow YAML file
        strings_path: Optional path to a separate YAML file containing string variables
        output_dir: Optional output directory for the validated workflow
        
    Returns:
        tuple: (success, output_path)
    """
    validator = WorkflowValidator(workflow_path, strings_path, output_dir)
    return validator.validate()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate a workflow')
    parser.add_argument('workflow', help='Path to the workflow YAML file')
    parser.add_argument('--strings', '-s', help='Path to a separate YAML file containing string variables')
    parser.add_argument('--output-dir', '-o', help='Path to the output directory for the validated workflow')
    
    args = parser.parse_args()
    
    success, output_path = validate_workflow(args.workflow, args.strings, args.output_dir)
    
    if success:
        print(f"Validation successful! Expanded workflow saved to: {output_path}")
        sys.exit(0)
    else:
        print("Validation failed!")
        sys.exit(1)
