import os
import sys
import ast
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr

def python_execute_file(file_path):
    """
    Execute a Python file and return its output.
    
    Args:
        file_path (str): Path to the Python file to execute.
        
    Returns:
        str: The output of the execution or an error message if execution fails.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found: {file_path}"
    
    if not file_path.endswith('.py'):
        return f"Error: File does not have a .py extension: {file_path}"
    
    try:
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            # Execute the file
            with open(file_path, 'r') as f:
                code = f.read()
            
            # Create a namespace for execution
            namespace = {'__file__': file_path}
            
            # Execute the code
            exec(code, namespace)
        
        # Get the captured output
        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()
        
        # Prepare the result
        result = ""
        if stdout_output:
            result += f"Standard Output:\n{stdout_output}\n"
        if stderr_output:
            result += f"Standard Error:\n{stderr_output}\n"
        
        if not result:
            result = "File executed successfully with no output."
            
        return result
        
    except Exception as e:
        tb = traceback.format_exc()
        return f"Error executing file: {e}\n\nTraceback:\n{tb}"


def python_check_syntax(code=None, file_path=None):
    """
    Check the syntax of Python code.
    
    Args:
        code (str, optional): Python code to check.
        file_path (str, optional): Path to a Python file to check.
        
    Returns:
        str: Result of the syntax check.
    """
    if code is None and file_path is None:
        return "Error: Either code or file_path must be provided."
    
    if file_path is not None:
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"
        
        try:
            with open(file_path, 'r') as f:
                code = f.read()
        except Exception as e:
            return f"Error reading file: {e}"
    
    try:
        ast.parse(code)
        return "Syntax check passed. No syntax errors found."
    except SyntaxError as e:
        line_no = e.lineno
        col_no = e.offset
        line = code.split('\n')[line_no - 1] if line_no <= len(code.split('\n')) else "Line not available"
        error_message = str(e)
        
        result = f"Syntax error at line {line_no}, column {col_no}:\n"
        result += f"{line}\n"
        result += f"{' ' * (col_no - 1)}^\n" if col_no else "\n"
        result += f"Error message: {error_message}"
        
        return result
    except Exception as e:
        return f"Error checking syntax: {e}"


def python_execute_code(code):
    """
    Execute arbitrary Python code and return its output.
    
    Args:
        code (str): Python code to execute.
        
    Returns:
        str: The output of the execution or an error message if execution fails.
    """
    if not code:
        return "Error: No code provided."
    
    try:
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            # Create a namespace for execution
            namespace = {}
            
            # Execute the code
            exec(code, namespace)
        
        # Get the captured output
        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()
        
        # Prepare the result
        result = ""
        if stdout_output:
            result += f"Standard Output:\n{stdout_output}\n"
        if stderr_output:
            result += f"Standard Error:\n{stderr_output}\n"
        
        if not result:
            result = "Code executed successfully with no output."
            
        return result
        
    except Exception as e:
        tb = traceback.format_exc()
        return f"Error executing code: {e}\n\nTraceback:\n{tb}"