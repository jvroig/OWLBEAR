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
        
        # Create a timestamp or use the provided output directory
        if output_dir:
            self.output_dir = output_dir
        else:
            # Get workflow name from file path
            workflow_name = os.path.basename(workflow_path).split('.')[0]
            timestamp = time.strftime("%Y-%m-%d-%H-%M")
            self.output_dir = os.path.join("outputs", f"{workflow_name}_{timestamp}")
            
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"Output directory: {self.output_dir}")
        
    def add_error(self, message: str) -> None:
        """Add a validation error."""
        self.validation_errors.append(message)
        logger.error(f"Validation error: {message}")
        
    def add_warning(self, message: str) -> None:
        """Add a validation warning."""
        self.validation_warnings.append(message)
        logger.warning(f"Validation warning: {message}")
    
    def _process_variables(self, strings_data, variables):
        """Process string variables, replacing {{variable}} references with their values.
        
        Args:
            strings_data (dict): Dictionary of string variables
            variables (dict): Dictionary of variable values
            
        Returns:
            dict: Processed string variables with variables substituted
        """
        # Function to replace {{var}} with its value
        def replace_variables(text, vars_dict):
            if not isinstance(text, str):
                return text
                
            def replace_match(match):
                var_name = match.group(1).strip()
                if var_name in vars_dict:
                    return str(vars_dict[var_name])
                else:
                    self.add_warning(f"Undefined variable in template: {var_name}")
                    return f"{{{{UNDEFINED:{var_name}}}}}"  # Keep the syntax but mark as undefined
            
            pattern = r"\{\{([^}]+)\}\}"
            return re.sub(pattern, replace_match, text)
        
        # Process each string in the dictionary
        processed_strings = {}
        for key, value in strings_data.items():
            processed_strings[key] = replace_variables(value, variables)
            
        return processed_strings
    
    def load_workflow(self) -> bool:
        """Load and validate the workflow YAML file.
        
        Returns:
            bool: True if the workflow was loaded successfully, False otherwise
        """
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
                    
                    # Handle different structures of strings files
                    if 'STRINGS' in strings_data:
                        # If the file has a top-level STRINGS structure, use its contents
                        nested_strings = strings_data['STRINGS']
                        
                        # Extract variables if present in nested structure
                        variables = {}
                        if 'VARIABLES' in nested_strings:
                            variables = nested_strings.pop('VARIABLES')
                        elif 'VARIABLES' in strings_data:
                            # Sometimes VARIABLES might be at the top level
                            variables = strings_data.pop('VARIABLES')
                            
                        logger.info(f"Loaded {len(variables)} variables from {self.strings_path}")
                        # Store variables for use in string resolution
                        self.variables.update(variables)
                        
                        # Process strings from the nested structure
                        self.string_vars = self._process_variables(nested_strings, variables)
                    else:
                        # Standard structure with variables at top level
                        # Extract variables if present
                        variables = {}
                        if 'VARIABLES' in strings_data:
                            variables = strings_data.pop('VARIABLES')
                            logger.info(f"Loaded {len(variables)} variables from {self.strings_path}")
                            # Store variables for use in string resolution
                            self.variables.update(variables)
                        
                        # Process string variables with variable substitution
                        self.string_vars = self._process_variables(strings_data, variables)
                    logger.info(f"Loaded {len(self.string_vars)} strings from {self.strings_path}")
                except Exception as e:
                    logger.error(f"Failed to load strings file {self.strings_path}: {str(e)}")
                    self.add_error(f"Failed to load strings file: {str(e)}")
                    return False
            else:
                # Fall back to STRINGS section in workflow file
                if 'STRINGS' not in self.workflow:
                    logger.warning("No STRINGS section found in workflow and no strings file provided")
                    self.string_vars = {}
                else:
                    strings_data = self.workflow.pop('STRINGS')
                    # Extract variables if present
                    variables = {}
                    if 'VARIABLES' in strings_data:
                        variables = strings_data.pop('VARIABLES')
                        logger.info(f"Loaded {len(variables)} variables from workflow STRINGS section")
                        # Store variables for use in string resolution
                        self.variables.update(variables)
                    
                    # Process string variables with variable substitution
                    self.string_vars = self._process_variables(strings_data, variables)
            
            # Basic workflow validation
            if 'ACTIONS' not in self.workflow or not self.workflow['ACTIONS']:
                self.add_error("No ACTIONS section found in workflow or ACTIONS is empty")
                return False
            
            logger.info(f"Loaded workflow with {len(self.workflow['ACTIONS'])} actions")
            return True
        except Exception as e:
            logger.error(f"Failed to load workflow: {str(e)}")
            self.add_error(f"Failed to load workflow: {str(e)}")
            return False
    
    def validate_string_references(self) -> None:
        """Validate all string references in the workflow."""
        if not self.workflow or 'ACTIONS' not in self.workflow:
            return
            
        # Find all string references in the workflow
        string_refs = set()
        for action in self.workflow['ACTIONS']:
            action_type = list(action.keys())[0]
            action_data = action[action_type]
            
            # Check for string references in inputs
            if 'inputs' in action_data:
                for input_item in action_data['inputs']:
                    if isinstance(input_item, str) and input_item.startswith('STR_'):
                        # Skip STR_USER_INPUT as it's a special case filled at runtime
                        if input_item != 'STR_USER_INPUT':
                            string_refs.add(input_item)
        
        # Validate that all referenced strings exist
        for ref in string_refs:
            if ref not in self.string_vars:
                self.add_error(f"Missing string definition: '{ref}' is referenced in workflow but not defined in STRINGS section or strings file")
    
    def validate_action_structure(self) -> None:
        """Validate the structure of each action in the workflow."""
        if not self.workflow or 'ACTIONS' not in self.workflow:
            return
            
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
                    
            elif action_type == 'DECIDE':
                if 'inputs' not in action_data or not action_data['inputs']:
                    self.add_warning(f"Action {i+1} (DECIDE) has empty or missing 'inputs'")
                
                # Track all action IDs for validation
                action_ids = set()
                for j, act in enumerate(self.workflow['ACTIONS']):
                    act_type = list(act.keys())[0]
                    act_data = act[act_type]
                    if 'id' in act_data:
                        action_ids.add(act_data['id'])
                
                # Validate loopback and loopback_target fields
                has_loopback = 'loopback' in action_data
                has_loopback_target = 'loopback_target' in action_data
                
                if not has_loopback and not has_loopback_target:
                    self.add_error(f"Action {i+1} (DECIDE) is missing both 'loopback' and 'loopback_target' fields - one is required")
                
                if has_loopback and has_loopback_target:
                    self.add_warning(f"Action {i+1} (DECIDE) has both 'loopback' and 'loopback_target' defined - only one should be used")
                
                # Validate numeric loopback
                if has_loopback:
                    if not isinstance(action_data['loopback'], int):
                        self.add_error(f"Action {i+1} (DECIDE) has invalid 'loopback' value: {action_data['loopback']} (must be an integer)")
                    elif action_data['loopback'] < 1 or action_data['loopback'] > len(self.workflow['ACTIONS']):
                        self.add_error(f"Action {i+1} (DECIDE) has out-of-range 'loopback' value: {action_data['loopback']} (must be between 1 and {len(self.workflow['ACTIONS'])})")
                
                # Validate string loopback_target
                if has_loopback_target:
                    target = action_data['loopback_target']
                    if not isinstance(target, str):
                        self.add_error(f"Action {i+1} (DECIDE) has invalid 'loopback_target' value: {target} (must be a string ID)")
                    elif target not in action_ids:
                        self.add_error(f"Action {i+1} (DECIDE) has unknown 'loopback_target' ID: '{target}' (must reference an existing action ID)")
            else:
                self.add_warning(f"Action {i+1} has unknown type: {action_type}")
    
    def validate_output_references(self) -> None:
        """Validate references to outputs from previous steps."""
        if not self.workflow or 'ACTIONS' not in self.workflow:
            return
            
        # Track output names
        outputs = set()
        
        for i, action in enumerate(self.workflow['ACTIONS']):
            action_type = list(action.keys())[0]
            action_data = action[action_type]
            
            # Add this action's output to the set
            if 'output' in action_data:
                outputs.add(action_data['output'])
            
            # Check for references to outputs in inputs
            if 'inputs' in action_data:
                for input_item in action_data['inputs']:
                    if isinstance(input_item, str) and not input_item.startswith('STR_'):
                        # Check if this might be an output reference
                        
                        # Skip obvious literal strings - checking for various patterns that indicate a literal string
                        if any([
                            '"' in input_item,     # Contains double quotes
                            "'" in input_item,     # Contains single quotes
                            " " in input_item,     # Contains spaces
                            "?" in input_item,     # Contains questions
                            "." in input_item,     # Contains periods
                            "," in input_item,     # Contains commas
                            input_item.startswith("Please"),  # Common instruction start
                            input_item.startswith("Write"),   # Common instruction start
                            input_item.startswith("Create"),  # Common instruction start
                            len(input_item) > 30   # Long strings are likely literals
                        ]):
                            continue
                            
                        # Valid output reference
                        if input_item in outputs:
                            continue
                        
                        # Check if it's a file reference
                        if input_item.endswith('.yaml') or input_item.endswith('.yml'):
                            continue
                            
                        # This might be an output reference, but not found in outputs
                        self.add_warning(f"Action {i+1} ({action_type}) input '{input_item}' might be intended as an output reference but no matching output was found")
    
    def validate_loops(self) -> None:
        """Check for potential infinite loops and unreachable steps."""
        if not self.workflow or 'ACTIONS' not in self.workflow:
            return
            
        # Build a directed graph of the workflow
        graph = defaultdict(list)
        decide_steps = {}
        
        # Create a map of action IDs to step indices
        action_id_map = {}
        for i, action in enumerate(self.workflow['ACTIONS']):
            action_type = list(action.keys())[0]
            action_data = action[action_type]
            if 'id' in action_data:
                action_id_map[action_data['id']] = i
        
        for i, action in enumerate(self.workflow['ACTIONS']):
            action_type = list(action.keys())[0]
            action_data = action[action_type]
            
            # Every step can go to the next step
            if i < len(self.workflow['ACTIONS']) - 1:
                graph[i].append(i + 1)
            
            # DECIDE steps can also loop back
            if action_type == 'DECIDE':
                # Check numeric loopback
                if 'loopback' in action_data:
                    loopback = action_data['loopback']
                    if isinstance(loopback, int) and 1 <= loopback <= len(self.workflow['ACTIONS']):
                        # Convert to 0-indexed
                        loopback_idx = loopback - 1
                        graph[i].append(loopback_idx)
                        decide_steps[i] = loopback_idx
                
                # Check ID-based loopback_target
                if 'loopback_target' in action_data:
                    target_id = action_data['loopback_target']
                    if isinstance(target_id, str) and target_id in action_id_map:
                        target_idx = action_id_map[target_id]
                        graph[i].append(target_idx)
                        decide_steps[i] = target_idx
        
        # Check for unreachable steps
        reachable = set([0])  # First step is always reachable
        visited = set()
        
        def dfs(node):
            if node in visited:
                return
            visited.add(node)
            reachable.add(node)
            for neighbor in graph[node]:
                dfs(neighbor)
        
        dfs(0)
        
        for i in range(len(self.workflow['ACTIONS'])):
            if i not in reachable:
                self.add_warning(f"Step {i+1} appears to be unreachable in the workflow")
        
        # Check for potential infinite loops
        # This is a simplified check - we only warn about direct self-loops
        for step, loopback in decide_steps.items():
            if step == loopback:
                self.add_warning(f"Step {step+1} (DECIDE) loops back to itself, may cause infinite loop")
    
    def resolve_string_references(self, expanded_workflow: Dict) -> Dict:
        """Resolve all string references in the expanded workflow.
        
        Args:
            expanded_workflow: Workflow with actions to process
            
        Returns:
            Dict: Workflow with string references resolved
        """
        # Deep copy the workflow to avoid modifying the original
        # We'll manually rebuild the workflow instead of a deep copy
        resolved_workflow = {'ACTIONS': []}
        
        # Add comments about original and expanded values
        def add_comment(expanded_actions, i, item_name, original, expanded):
            if original != expanded:
                expanded_actions[i]['__comments__'] = expanded_actions[i].get('__comments__', {})
                expanded_actions[i]['__comments__'][item_name] = f"Original: {original}"
        
        # Process each action
        for action in expanded_workflow['ACTIONS']:
            action_type = list(action.keys())[0]
            action_data = action[action_type]
            
            # Create a new action with the same structure
            new_action = {action_type: {}}
            for key, value in action_data.items():
                if key == 'inputs':
                    # Resolve string references in inputs
                    new_inputs = []
                    for input_item in value:
                        original = input_item
                        if isinstance(input_item, str):
                            # Special handling for STR_USER_INPUT - keep as is since it's filled at runtime
                            if input_item == 'STR_USER_INPUT':
                                # Leave as is
                                pass
                            elif input_item.startswith('STR_') and input_item in self.string_vars:
                                # Replace string reference with its value
                                input_item = self.string_vars[input_item]
                            elif '{{' in input_item and '}}' in input_item:
                                # Apply variable substitution to inline strings
                                temp_dict = {'temp_var': input_item}
                                processed = self._process_variables(temp_dict, self.variables)
                                input_item = processed['temp_var']
                        
                        new_inputs.append(input_item)
                        # Add a comment if the input was expanded
                        if original != input_item and isinstance(original, str) and original.startswith('STR_'):
                            new_action['__comments__'] = new_action.get('__comments__', {})
                            input_idx = len(new_inputs) - 1
                            new_action['__comments__'][f"input_{input_idx}"] = f"Original: {original}"
                    
                    new_action[action_type]['inputs'] = new_inputs
                else:
                    # Copy other fields as is
                    new_action[action_type][key] = value
            
            resolved_workflow['ACTIONS'].append(new_action)
        
        return resolved_workflow
    
    def generate_expanded_workflow(self) -> Dict:
        """Generate an expanded version of the workflow with all strings and variables resolved.
        
        Returns:
            Dict: Expanded workflow with strings resolved
        """
        # Create a copy of the workflow with string values expanded
        expanded_workflow = {'ACTIONS': []}
        
        for action in self.workflow['ACTIONS']:
            # Copy the action structure
            expanded_action = {}
            for action_type, action_data in action.items():
                expanded_action[action_type] = action_data.copy()
            
            expanded_workflow['ACTIONS'].append(expanded_action)
        
        # Resolve all string references
        expanded_workflow = self.resolve_string_references(expanded_workflow)
        
        # Add metadata
        expanded_workflow['__metadata__'] = {
            'original_workflow': self.workflow_path,
            'generated_at': time.strftime("%Y-%m-%d %H:%M:%S"),
            'validation_status': 'success' if not self.validation_errors else 'error',
            'error_count': len(self.validation_errors),
            'warning_count': len(self.validation_warnings)
        }
        
        # Add validation results
        if self.validation_errors:
            expanded_workflow['__validation_errors__'] = self.validation_errors
        
        if self.validation_warnings:
            expanded_workflow['__validation_warnings__'] = self.validation_warnings
        
        # Add original string variables for reference
        expanded_workflow['__original_strings__'] = self.string_vars
        
        # Add note about STR_USER_INPUT
        expanded_workflow['__special_notes__'] = [
            "STR_USER_INPUT is a special variable that will be filled at runtime with user input from the command line."
        ]
        
        return expanded_workflow
    
    def save_expanded_workflow(self, expanded_workflow: Dict) -> str:
        """Save the expanded workflow to a YAML file.
        
        Args:
            expanded_workflow: Expanded workflow with strings resolved
            
        Returns:
            str: Path to the saved file
        """
        # Create a more descriptive filename
        workflow_name = os.path.basename(self.workflow_path).split('.')[0]
        output_path = os.path.join(self.output_dir, f"{workflow_name}_validated.yaml")
        
        try:
            # Custom string representer to use literal style for multi-line strings
            def represent_str_literal(dumper, data):
                if '\n' in data:
                    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
                return dumper.represent_scalar('tag:yaml.org,2002:str', data)
            
            # Custom dict representer for pretty formatting comments
            def represent_dict(dumper, data):
                if '__comments__' in data:
                    # Handle comments specially
                    comments = data.pop('__comments__')
                    node = dumper.represent_mapping('tag:yaml.org,2002:map', data.items())
                    # Add comments back for future reference
                    data['__comments__'] = comments
                    return node
                return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())
            
            # Add the custom representers
            yaml.add_representer(str, represent_str_literal)
            yaml.add_representer(dict, represent_dict)
            
            with open(output_path, 'w') as file:
                yaml.dump(expanded_workflow, file, default_flow_style=False, allow_unicode=True, width=float("inf"))
            
            logger.info(f"Saved expanded workflow to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to save expanded workflow: {str(e)}")
            self.add_error(f"Failed to save expanded workflow: {str(e)}")
            return ""
    
    def validate(self) -> Tuple[bool, str]:
        """Validate the workflow and generate an expanded version.
        
        Returns:
            Tuple[bool, str]: (success, output_path)
        """
        # Load the workflow
        if not self.load_workflow():
            return False, ""
        
        # Perform validation checks
        self.validate_string_references()
        self.validate_action_structure()
        self.validate_output_references()
        self.validate_loops()
        
        # Generate the expanded workflow
        expanded_workflow = self.generate_expanded_workflow()
        
        # Save the expanded workflow
        output_path = self.save_expanded_workflow(expanded_workflow)
        
        # Return success if there are no errors
        success = len(self.validation_errors) == 0
        
        # Print summary
        if self.validation_errors:
            logger.error(f"Validation failed with {len(self.validation_errors)} errors and {len(self.validation_warnings)} warnings")
            for error in self.validation_errors:
                logger.error(f"  Error: {error}")
        
        if self.validation_warnings:
            logger.warning(f"Validation completed with {len(self.validation_warnings)} warnings")
            for warning in self.validation_warnings:
                logger.warning(f"  Warning: {warning}")
        
        if success:
            logger.info("Validation completed successfully")
        
        return success, output_path

def format_expanded_workflow_summary(validator_path: str) -> str:
    """Format a human-readable summary of the expanded workflow.
    
    Args:
        validator_path: Path to the validator.yaml file
        
    Returns:
        str: Formatted summary for display
    """
    try:
        with open(validator_path, 'r') as file:
            expanded = yaml.safe_load(file)
            
        summary = ["====== WORKFLOW VALIDATION SUMMARY ======\n"]
        
        # Add metadata
        if '__metadata__' in expanded:
            meta = expanded['__metadata__']
            summary.append(f"Original workflow: {meta.get('original_workflow')}")
            summary.append(f"Generated at: {meta.get('generated_at')}")
            summary.append(f"Status: {meta.get('validation_status').upper()}")
            summary.append(f"Errors: {meta.get('error_count', 0)}")
            summary.append(f"Warnings: {meta.get('warning_count', 0)}\n")
        
        # Add validation errors
        if '__validation_errors__' in expanded and expanded['__validation_errors__']:
            summary.append("⚠️  ERRORS:")
            for error in expanded['__validation_errors__']:
                summary.append(f"  • {error}")
            summary.append("")
        
        # Add validation warnings
        if '__validation_warnings__' in expanded and expanded['__validation_warnings__']:
            summary.append("⚠️  WARNINGS:")
            for warning in expanded['__validation_warnings__']:
                summary.append(f"  • {warning}")
            summary.append("")
            
        # Add special notes
        if '__special_notes__' in expanded and expanded['__special_notes__']:
            summary.append("ℹ️  SPECIAL NOTES:")
            for note in expanded['__special_notes__']:
                summary.append(f"  • {note}")
            summary.append("")
        
        # Summarize actions
        if 'ACTIONS' in expanded:
            summary.append(f"📋 ACTIONS SUMMARY ({len(expanded['ACTIONS'])} steps):")
            for i, action in enumerate(expanded['ACTIONS']):
                action_type = list(action.keys())[0]
                if action_type == '__comments__':
                    continue
                    
                action_data = action[action_type]
                summary.append(f"  Step {i+1}: {action_type}")
                
                # Show expanded inputs
                if 'inputs' in action_data:
                    for j, input_item in enumerate(action_data['inputs']):
                        # Check for comments to show original values
                        original = None
                        if '__comments__' in action and f"input_{j}" in action['__comments__']:
                            original = action['__comments__'][f"input_{j}"]
                        
                        # Truncate long input items for display
                        display_item = input_item
                        if isinstance(display_item, str) and len(display_item) > 60:
                            display_item = display_item[:57] + "..."
                        
                        if original:
                            summary.append(f"    Input {j+1}: {display_item}")
                            summary.append(f"      {original}")
                        else:
                            summary.append(f"    Input {j+1}: {display_item}")
                
                # Show loopback targets for DECIDE actions
                if action_type == 'DECIDE' and 'loopback' in action_data:
                    summary.append(f"    Loopback target: Step {action_data['loopback']}")
                    
                summary.append("")
                
        summary.append("====== END VALIDATION SUMMARY ======")
        return "\n".join(summary)
    except Exception as e:
        return f"Error creating summary: {str(e)}"


def validate_workflow(workflow_path: str, strings_path: Optional[str] = None, output_dir: Optional[str] = None) -> Tuple[bool, str]:
    """Helper function to validate a workflow.
    
    Args:
        workflow_path: Path to the workflow YAML file
        strings_path: Optional path to a separate YAML file containing string variables
        output_dir: Optional output directory for the validated workflow
        
    Returns:
        Tuple[bool, str]: (success, output_path)
    """
    validator = WorkflowValidator(workflow_path, strings_path, output_dir)
    success, output_path = validator.validate()
    
    # Display summary if validation was successful
    if success and output_path:
        summary = format_expanded_workflow_summary(output_path)
        logger.info("\n" + summary)
    
    return success, output_path

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='OWLBEAR Workflow Validator - Expand and validate workflow YAML files')
    parser.add_argument('workflow', help='Path to the workflow YAML file')
    parser.add_argument('--strings', '-s', help='Path to a separate YAML file containing string variables')
    parser.add_argument('--output-dir', '-o', help='Output directory for the validated workflow (defaults to timestamped directory in outputs/)')
    
    args = parser.parse_args()
    
    success, output_path = validate_workflow(args.workflow, args.strings, args.output_dir)
    
    if success:
        print(f"Validation successful! Expanded workflow saved to: {output_path}")
        # Print a human-readable summary
        summary = format_expanded_workflow_summary(output_path)
        print("\n" + summary)
        sys.exit(0)
    else:
        print("Validation failed! See log for details.")
        sys.exit(1)
