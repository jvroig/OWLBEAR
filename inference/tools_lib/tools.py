def tools_to_string(tools_dict):
    """
    Convert the tools dictionary to a formatted string representation.
    
    Args:
        tools_dict (dict): Dictionary containing tool definitions.
        
    Returns:
        str: Formatted string describing all tools.
    """
    result = ""
    
    # Iterate through all tool categories
    for category, category_tools in tools_dict.items():
        # Iterate through each tool in the category
        for tool_name, tool_info in category_tools.items():
            # Add tool name and description
            result += f"-{tool_name}: {tool_info['description']}\n"
            
            # Add parameters
            result += "    Parameters:\n"
            if not tool_info['parameters']:
                result += "    None. This tool does not need a parameter.\n"
            else:
                for param in tool_info['parameters']:
                    required = "(required, " if param.get("required", True) else "(optional, "
                    result += f"    - {param['name']} {required}{param['type']}): {param['description']}\n"
            
            # Add return value
            result += f"    Returns: {tool_info['returns']}\n\n"
    
    return result


def get_tools_dict():
    """
    Define and return a dictionary of all available tools.
    
    Returns:
        dict: Dictionary containing all tool definitions organized by category.
    """
    tools = {
        "filesystem_tools": {
            "get_cwd": {
                "description": "Get the current working directory",
                "parameters": [],
                "returns": "String - information about the current working directory"
            },
            "read_file": {
                "description": "Read a file in the filesystem",
                "parameters": [
                    {"name": "path", "required": True, "type": "string", "description": "path and filename of the file to read"}
                ],
                "returns": "String - the contents of the file specified in `path`"
            },
            "write_file": {
                "description": "Write content to a file in the filesystem",
                "parameters": [
                    {"name": "path", "required": True, "type": "string", "description": "path and filename of the file to write"},
                    {"name": "content", "required": True, "type": "string", "description": "the content to write to the file"}
                ],
                "returns": "String - confirmation message indicating success or failure"
            },
            "create_directory": {
                "description": "Create a new directory in the filesystem",
                "parameters": [
                    {"name": "path", "required": True, "type": "string", "description": "path of the directory to create"}
                ],
                "returns": "String - confirmation message indicating success or failure"
            },
            "list_directory": {
                "description": "List the contents of a directory in the filesystem",
                "parameters": [
                    {"name": "path", "required": False, "type": "string", "description": "path of the directory to list. If not provided, lists the current working directory."}
                ],
                "returns": "String - a list of files and directories in the specified path"
            }
        },
        
        "git_tools": {
            "git_clone": {
                "description": "Clone a git repository using HTTPS",
                "parameters": [
                    {"name": "repo_url", "required": True, "type": "string", "description": "The HTTPS URL of the repository to clone"},
                    {"name": "target_path", "required": False, "type": "string", "description": "The path where to clone the repository"}
                ],
                "returns": "String - confirmation message indicating success or failure"
            },
            "git_commit": {
                "description": "Stage all changes and create a commit",
                "parameters": [
                    {"name": "message", "required": True, "type": "string", "description": "The commit message"},
                    {"name": "path", "required": False, "type": "string", "description": "The path to the git repository (defaults to current directory)"}
                ],
                "returns": "String - confirmation message indicating success or failure"
            },
            "git_restore": {
                "description": "Restore the repository or specific files to a previous state",
                "parameters": [
                    {"name": "commit_hash", "required": False, "type": "string", "description": "The commit hash to restore to. If not provided, unstages all changes"},
                    {"name": "path", "required": False, "type": "string", "description": "The path to the git repository (defaults to current directory)"},
                    {"name": "files", "required": False, "type": "list", "description": "List of specific files to restore. If not provided, restores everything"}
                ],
                "returns": "String - confirmation message indicating success or failure"
            },
            "git_push": {
                "description": "Push commits to a remote repository",
                "parameters": [
                    {"name": "remote", "required": False, "type": "string", "description": "The remote name (defaults to 'origin')"},
                    {"name": "branch", "required": False, "type": "string", "description": "The branch name to push to (defaults to 'main')"},
                    {"name": "path", "required": False, "type": "string", "description": "The path to the git repository (defaults to current directory)"}
                ],
                "returns": "String - confirmation message indicating success or failure"
            },
            "git_log": {
                "description": "Get the commit history of the repository",
                "parameters": [
                    {"name": "path", "required": False, "type": "string", "description": "The path to the git repository (defaults to current directory)"},
                    {"name": "max_count", "required": False, "type": "integer", "description": "Maximum number of commits to return"},
                    {"name": "since", "required": False, "type": "string", "description": "Get commits since this date (e.g., \"2024-01-01\" or \"1 week ago\")"}
                ],
                "returns": "String - JSON formatted commit history with hash, author, date, and message for each commit"
            },
            "git_show": {
                "description": "Get detailed information about a specific commit",
                "parameters": [
                    {"name": "commit_hash", "required": True, "type": "string", "description": "The hash of the commit to inspect"},
                    {"name": "path", "required": False, "type": "string", "description": "The path to the git repository (defaults to current directory)"}
                ],
                "returns": "String - JSON formatted commit details including metadata and changed files"
            },
            "git_status": {
                "description": "Get the current status of the repository",
                "parameters": [
                    {"name": "path", "required": False, "type": "string", "description": "The path to the git repository (defaults to current directory)"}
                ],
                "returns": "String - JSON formatted repository status including staged, unstaged, and untracked changes"
            },
            "git_diff": {
                "description": "Get the differences between commits, staged changes, or working directory",
                "parameters": [
                    {"name": "path", "required": False, "type": "string", "description": "The path to the git repository (defaults to current directory)"},
                    {"name": "commit1", "required": False, "type": "string", "description": "First commit hash for comparison"},
                    {"name": "commit2", "required": False, "type": "string", "description": "Second commit hash for comparison"},
                    {"name": "staged", "required": False, "type": "boolean", "description": "If True, show staged changes (ignored if commits are specified)"},
                    {"name": "file_path", "required": False, "type": "string", "description": "Path to specific file to diff"}
                ],
                "returns": "String - JSON formatted diff information including: Summary (files changed, total additions/deletions) and Detailed changes per file with hunks showing exact line modifications"
            }
        },
        
        "web_tools": {
            "brave_web_search": {
                "description": "Search the web using Brave Search API. The responses here only contain summaries. Use fetch_web_page to get the full contents of interesting search results.",
                "parameters": [
                    {"name": "query", "required": True, "type": "string", "description": "the search query to submit to Brave"},
                    {"name": "count", "required": False, "type": "integer", "description": "the number of results to return, defaults to 10"}
                ],
                "returns": "Object - a JSON object containing search results or error information from the Brave Search API"
            },
            "fetch_web_page": {
                "description": "Fetch content from a specified URL. This is a good tool to use after doing a brave_web_search, in order to get more details from interesting search results.",
                "parameters": [
                    {"name": "url", "required": True, "type": "string", "description": "the URL to fetch content from"},
                    {"name": "headers", "required": False, "type": "dictionary", "description": "custom headers to include in the request, defaults to a standard User-Agent"},
                    {"name": "timeout", "required": False, "type": "integer", "description": "request timeout in seconds, defaults to 30"},
                    {"name": "clean", "required": False, "type": "boolean", "description": "whether to extract only the main content, defaults to True"}
                ],
                "returns": "String - the cleaned web page content as text, or an error object if the request fails"
            }
        },
        
        "python_tools": {
            "python_execute_file": {
                "description": "Execute a Python file and return its output",
                "parameters": [
                    {"name": "file_path", "required": True, "type": "string", "description": "Path to the Python file to execute"}
                ],
                "returns": "String - The output of the execution or an error message if execution fails"
            },
            "python_check_syntax": {
                "description": "Check the syntax of Python code",
                "parameters": [
                    {"name": "code", "required": False, "type": "string", "description": "Python code to check"},
                    {"name": "file_path", "required": False, "type": "string", "description": "Path to a Python file to check"}
                ],
                "returns": "String - Result of the syntax check"
            },
            "python_execute_code": {
                "description": "Execute arbitrary Python code and return its output",
                "parameters": [
                    {"name": "code", "required": True, "type": "string", "description": "Python code to execute"}
                ],
                "returns": "String - The output of the execution or an error message if execution fails"
            }
        }
    }
    
    return tools


def list_tools(ignore=''):
    """
    Get a formatted string description of all available tools.
    
    Returns:
        str: Formatted string describing all tools.
    """
    tools_dict = get_tools_dict()
    return tools_to_string(tools_dict)


def get_tools_format():
    """
    Get the format to use when making tool calls.
    
    Returns:
        str: Instructions for how to format tool calls.
    """
    tools_format = """

When you want to use a tool, make a tool call (no explanations) using this exact format:

```
[[qwen-tool-start]]
{
    "name": "tool_name",
    "input": {
        "param1": "value1",
        "param2": "value2"
    }
}
[[qwen-tool-end]]
```

Note that the triple backticks (```) are part of the format!

Example 1:
************************
User: What is your current working directory?
Qwen-Max:
```
[[qwen-tool-start]]
{
    "name": "get_cwd",
    "input": ""
}
[[qwen-tool-end]]
```
**********************


Example 2:
************************
User: List the files in your current working directory.
Qwen-Max:
```
[[qwen-tool-start]]
{
    "name": "list_directory",
    "input": {
        "path": "."
    }
}
[[qwen-tool-end]]
```
**********************

Example 3:
************************
User: Can you check the syntax of my Python code?
Qwen-Max:
```
[[qwen-tool-start]]
{
    "name": "python_check_syntax",
    "input": {
        "code": "print('Hello world'"
    }
}
[[qwen-tool-end]]
```
**********************

Immediately end your response after calling a tool and the final triple backticks.

After receiving the results of a tool call, do not parrot everything back to the user.
Instead, just briefly summarize the results in 1-2 sentences.

"""
    return tools_format