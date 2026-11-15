import asyncio
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables from .env file
load_dotenv()

# Initialize MCP server
mcp = FastMCP("terminal-controller", log_level="ERROR")

# List to store command history
command_history = []

# Maximum history size
MAX_HISTORY_SIZE = 50

# Load safe directories from .env, resolving them to absolute real paths
raw_safe_dirs = os.getenv("TERMINAL_SAFE_DIRS", "")
SAFE_DIRS = [os.path.realpath(d.strip()) for d in raw_safe_dirs.split(",") if d.strip()]

# Navigate into a safe dir if not in one
cwd = os.path.realpath(os.getcwd())
safe_superset = {os.path.realpath(d) for d in SAFE_DIRS}
if cwd not in safe_superset and os.path.exists(SAFE_DIRS[0]):
    try:
        os.chdir(SAFE_DIRS[0])
    except Exception:
        pass

def is_safe_path(path: str) -> bool:
    """
    Verify if a given path falls within the allowed SAFE_DIRS.
    Prevents path traversal attacks (e.g., ../../etc/passwd).
    """
    if not SAFE_DIRS:
        return False

    try:
        target_path = os.path.realpath(path)
        for safe_dir in SAFE_DIRS:
            if os.path.commonpath([safe_dir, target_path]) == safe_dir:
                return True
        return False
    except Exception:
        return False

async def run_command(cmd: str, timeout: int = 30) -> Dict:
    """
    Execute command and return results

    Args:
        cmd: Command to execute
        timeout: Command timeout in seconds

    Returns:
        Dictionary containing command execution results
    """
    start_time = datetime.now()

    try:
        if platform.system() == "Windows":
            # Windows fallback (no bwrap)
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )
        else:
            # Check if bubblewrap is installed
            has_bwrap = shutil.which("bwrap") is not None

            conda_sh = os.path.expanduser("~/miniforge3/etc/profile.d/conda.sh")
            inner_cmd = f"source {conda_sh} && {cmd}" if os.path.exists(conda_sh) else cmd

            if has_bwrap:
                # Construct the Bubblewrap sandbox arguments
                bwrap_args = [
                    "bwrap",
                    # Mount system dependencies strictly as Read-Only
                    "--ro-bind", "/usr", "/usr",
                    "--ro-bind", "/etc", "/etc",
                    # Provide standard Linux directories
                    "--dir", "/tmp",
                    "--dir", "/var",
                    "--proc", "/proc",
                    "--dev", "/dev",
                    # FHS symlinks for commands to resolve (e.g., /bin/bash -> /usr/bin/bash)
                    "--symlink", "usr/lib", "/lib",
                    "--symlink", "usr/lib64", "/lib64",
                    "--symlink", "usr/bin", "/bin",
                    "--symlink", "usr/sbin", "/sbin",
                    # Unshare namespaces for isolation (network remains shared by default)
                    "--unshare-pid",
                    "--unshare-uts",
                    "--unshare-ipc"
                ]

                # Mount miniforge read-only so conda commands still work inside the sandbox
                miniforge_path = os.path.expanduser("~/miniforge3")
                if os.path.exists(miniforge_path):
                    bwrap_args.extend(["--ro-bind", miniforge_path, miniforge_path])

                # Bind the SAFE_DIRS as Read-Write
                for safe_dir in SAFE_DIRS:
                    if os.path.exists(safe_dir):
                        bwrap_args.extend(["--bind", safe_dir, safe_dir])

                # Set working directory inside the sandbox
                cwd = os.getcwd()
                if is_safe_path(cwd):
                    bwrap_args.extend(["--chdir", cwd])
                elif SAFE_DIRS and os.path.exists(SAFE_DIRS[0]):
                    # Fallback to the first safe directory if outside
                    bwrap_args.extend(["--chdir", SAFE_DIRS[0]])

                # Append the command to execute via bash
                bwrap_args.extend(["--", "/bin/bash", "-c", inner_cmd])

                # Convert the argument list back into a safely escaped shell string
                wrapped_cmd = " ".join(shlex.quote(arg) for arg in bwrap_args)
            else:
                # Fallback if bwrap is missing
                print("WARNING: 'bwrap' not found. Executing without sandbox.", file=sys.stderr)
                wrapped_cmd = inner_cmd

            process = await asyncio.create_subprocess_shell(
                wrapped_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True,
                executable="/bin/bash"
            )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
            stdout = stdout.decode('utf-8', errors='replace')
            stderr = stderr.decode('utf-8', errors='replace')
            return_code = process.returncode
        except asyncio.TimeoutError:
            try:
                process.kill()
            except:
                pass
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "return_code": -1,
                "duration": str(datetime.now() - start_time),
                "command": cmd
            }

        duration = datetime.now() - start_time
        result = {
            "success": return_code == 0,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": return_code,
            "duration": str(duration),
            "command": cmd
        }

        command_history.append({
            "timestamp": datetime.now().isoformat(),
            "command": cmd,
            "success": return_code == 0
        })

        if len(command_history) > MAX_HISTORY_SIZE:
            command_history.pop(0)

        return result

    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Error executing command: {str(e)}",
            "return_code": -1,
            "duration": str(datetime.now() - start_time),
            "command": cmd
        }

def truncate_terminal_output(text: str, max_lines: int = 300) -> str:
    """
    Generic safeguard for terminal commands. Keeps the first 150 lines and
    last 150 lines if the output exceeds max_lines to prevent LLM memory overflow.
    """
    if not text:
        return text

    lines = text.split('\n')
    if len(lines) <= max_lines:
        return text

    omitted = len(lines) - max_lines
    keep_start = 150
    keep_end = 150

    header = lines[:keep_start]
    footer = lines[-keep_end:]

    truncation_msg = (
        f"\n\n... [SYSTEM WARNING: Terminal output truncated. {omitted} lines omitted to prevent memory overflow. "
        f"For large outputs, redirect to a file (e.g., 'command > output.txt') and use 'cat' or 'grep' to read specific parts.] ...\n\n"
    )

    return "\n".join(header) + truncation_msg + "\n".join(footer)

@mcp.tool()
async def get_safe_directories() -> str:
    """
    Get the list of directories that the agent is allowed to access.
    Use this if you receive a security error and need to know where you can safely navigate.
    """
    if not SAFE_DIRS:
        return "No safe directories are currently configured."

    output = "You have full read/write/execute access to the following directories (and their subdirectories):\n"
    for d in SAFE_DIRS:
        output += f"- {d}\n"
    return output

@mcp.tool()
async def execute_command(command: str, timeout: int = 30) -> str:
    """
    Execute terminal command and return results

    Args:
        command: Command line command to execute
        timeout: Command timeout in seconds, default is 30 seconds

    Returns:
        Output of the command execution
    """
    if not is_safe_path(os.getcwd()):
        return "Security Error: Current working directory is outside allowed safe zones. Cannot execute commands here."
    # Check for dangerous commands (can add more security checks)
    dangerous_commands = ["rm -rf /", "mkfs"]
    if any(dc in command.lower() for dc in dangerous_commands):
        return "For security reasons, this command is not allowed."

    result = await run_command(command, timeout)

    safe_stdout = truncate_terminal_output(result["stdout"]) if result["stdout"] else ""
    safe_stderr = truncate_terminal_output(result["stderr"]) if result["stderr"] else ""

    if result["success"]:
        output = f"Command executed successfully (duration: {result['duration']})\n\n"
        output += f"Output:\n{safe_stdout}\n" if safe_stdout else "Command had no output.\n"
        if safe_stderr: output += f"\nWarnings/Info:\n{safe_stderr}"
        return output
    else:
        output = f"Command execution failed (duration: {result['duration']})\n"
        if safe_stdout: output += f"\nOutput:\n{safe_stdout}\n"
        if safe_stderr: output += f"\nError:\n{safe_stderr}"
        output += f"\nReturn code: {result['return_code']}"
        return output

@mcp.tool()
async def get_command_history(count: int = 10) -> str:
    """
    Get recent command execution history

    Args:
        count: Number of recent commands to return

    Returns:
        Formatted command history record
    """
    if not command_history:
        return "No command execution history."

    count = min(count, len(command_history))
    recent_commands = command_history[-count:]

    output = f"Recent {count} command history:\n\n"

    for i, cmd in enumerate(recent_commands):
        status = "✓" if cmd["success"] else "✗"
        output += f"{i+1}. [{status}] {cmd['timestamp']}: {cmd['command']}\n"

    return output

@mcp.tool()
async def get_current_directory() -> str:
    """
    Get current working directory

    Returns:
        Path of current working directory
    """
    return os.getcwd()

# @mcp.tool()
# async def change_directory(path: str) -> str:
#     """
#     Change current working directory

#     Args:
#         path: Directory path to switch to

#     Returns:
#         Operation result information
#     """
#     if not is_safe_path(path):
#         return f"Security Error: Access to '{path}' is denied. Directory is outside of SAFE_DIRS."
#     try:
#         os.chdir(path)
#         return f"Switched to directory: {os.getcwd()}"
#     except FileNotFoundError:
#         return f"Error: Directory '{path}' does not exist"
#     except PermissionError:
#         return f"Error: No permission to access directory '{path}'"
#     except Exception as e:
#         return f"Error changing directory: {str(e)}"

@mcp.tool()
async def list_directory(path: Optional[str] = None) -> str:
    """
    List files and subdirectories in the specified directory

    Args:
        path: Directory path to list contents, default is current directory

    Returns:
        List of directory contents
    """
    if path is None:
        path = os.getcwd()
    if not is_safe_path(path):
        return f"Security Error: Access to '{path}' is denied. Directory is outside of SAFE_DIRS."
    try:
        items = os.listdir(path)

        dirs = []
        files = []

        for item in items:
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                dirs.append(f"📁 {item}/")
            else:
                files.append(f"📄 {item}")

        # Sort directories and files
        dirs.sort()
        files.sort()

        if not dirs and not files:
            return f"Directory '{path}' is empty"

        output = f"Contents of directory '{path}':\n\n"

        if dirs:
            output += "Directories:\n"
            output += "\n".join(dirs) + "\n\n"

        if files:
            output += "Files:\n"
            output += "\n".join(files)

        return output

    except FileNotFoundError:
        return f"Error: Directory '{path}' does not exist"
    except PermissionError:
        return f"Error: No permission to access directory '{path}'"
    except Exception as e:
        return f"Error listing directory contents: {str(e)}"

@mcp.tool()
async def write_file(path: str, content: str, mode: str = "overwrite") -> str:
    """
    Write content to a file

    Args:
        path: Path to the file
        content: Content to write (string or JSON object)
        mode: Write mode ('overwrite' or 'append')

    Returns:
        Operation result information
    """
    if not is_safe_path(path):
        return f"Security Error: Access to '{path}' is denied. File is outside of SAFE_DIRS."
    try:
        # Handle different content types
        if not isinstance(content, str):
            try:
                # Advanced JSON serialization with better handling of complex objects
                content = json.dumps(content,
                    indent=4,
                    sort_keys=False,
                    ensure_ascii=False,
                    default=lambda obj: str(obj) if hasattr(obj, '__dict__') else repr(obj))
            except Exception as e:
                # Try a more aggressive approach if standard serialization fails
                try:
                    # Convert object to dictionary first if it has __dict__
                    if hasattr(content, '__dict__'):
                        content = json.dumps(content.__dict__,
                            indent=4,
                            sort_keys=False,
                            ensure_ascii=False)
                    else:
                        # Last resort: convert to string representation
                        content = str(content)
                except Exception as inner_e:
                    return f"Error: Unable to convert complex object to writable string: {str(e)}, then tried alternative method and got: {str(inner_e)}"

        # Choose file mode based on the specified writing mode
        file_mode = "w" if mode.lower() == "overwrite" else "a"

        # Ensure content ends with a newline if it doesn't already
        if content and not content.endswith('\n'):
            content += '\n'

        # Ensure directory exists
        directory = os.path.dirname(os.path.abspath(path))
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        with open(path, file_mode, encoding="utf-8") as file:
            file.write(content)

        # Verify the write operation was successful
        if os.path.exists(path):
            file_size = os.path.getsize(path)
            return f"Successfully wrote {file_size} bytes to '{path}' in {mode} mode."
        else:
            return f"Write operation completed, but unable to verify file exists at '{path}'."

    except FileNotFoundError:
        return f"Error: The directory in path '{path}' does not exist and could not be created."
    except PermissionError:
        return f"Error: No permission to write to file '{path}'."
    except Exception as e:
        return f"Error writing to file: {str(e)}"

@mcp.tool()
async def read_file(path: str, start_row: int = None, end_row: int = None, as_json: bool = False) -> str:
    """
    Read content from a file with optional row selection

    Args:
        path: Path to the file
        start_row: Starting row to read from (0-based, optional)
        end_row: Ending row to read to (0-based, inclusive, optional)
        as_json: If True, attempt to parse file content as JSON (optional)

    Returns:
        File content or selected lines, optionally parsed as JSON
    """
    if not is_safe_path(path):
        return f"Security Error: Access to '{path}' is denied. File is outside of SAFE_DIRS."
    try:
        if not os.path.exists(path):
            return f"Error: File '{path}' does not exist."

        if not os.path.isfile(path):
            return f"Error: '{path}' is not a file."

        # Check file size before reading to prevent memory issues
        file_size = os.path.getsize(path)
        if file_size > 10 * 1024 * 1024:  # 10 MB limit
            return f"Warning: File is very large ({file_size/1024/1024:.2f} MB). Consider using row selection."

        with open(path, 'r', encoding='utf-8', errors='replace') as file:
            lines = file.readlines()

        # If row selection is specified
        if start_row is not None:
            if start_row < 0:
                return "Error: start_row must be non-negative."

            # If only start_row is specified, read just that single row
            if end_row is None:
                if start_row >= len(lines):
                    return f"Error: start_row {start_row} is out of range (file has {len(lines)} lines)."
                content = f"Line {start_row}: {lines[start_row]}"
            else:
                # Both start_row and end_row are specified
                if end_row < start_row:
                    return "Error: end_row must be greater than or equal to start_row."

                if end_row >= len(lines):
                    end_row = len(lines) - 1

                selected_lines = lines[start_row:end_row+1]
                content = ""
                for i, line in enumerate(selected_lines):
                    content += f"Line {start_row + i}: {line}" if not line.endswith('\n') else f"Line {start_row + i}: {line}"
        else:
            # If no row selection, return the entire file
            content = "".join(lines)

        # If as_json is True, try to parse the content as JSON
        if as_json:
            try:
                # If we're showing line numbers, we cannot parse as JSON
                if start_row is not None:
                    return "Error: Cannot parse as JSON when displaying line numbers. Use as_json without row selection."

                # Try to parse the content as JSON
                parsed_json = json.loads(content)
                # Return pretty-printed JSON for better readability
                return json.dumps(parsed_json, indent=4, sort_keys=False, ensure_ascii=False)
            except json.JSONDecodeError as e:
                return f"Error: File content is not valid JSON. {str(e)}\n\nRaw content:\n{content}"

        return content

    except PermissionError:
        return f"Error: No permission to read file '{path}'."
    except Exception as e:
        return f"Error reading file: {str(e)}"

@mcp.tool()
async def insert_file_content(path: str, content: str, row: int = None, rows: list = None) -> str:
    """
    Insert content at specific row(s) in a file

    Args:
        path: Path to the file
        content: Content to insert (string or JSON object)
        row: Row number to insert at (0-based, optional)
        rows: List of row numbers to insert at (0-based, optional)

    Returns:
        Operation result information
    """
    if not is_safe_path(path):
        return f"Security Error: Access to '{path}' is denied. File is outside of SAFE_DIRS."
    try:
        # Handle different content types
        if not isinstance(content, str):
            try:
                content = json.dumps(content, indent=4, sort_keys=False, ensure_ascii=False, default=str)
            except Exception as e:
                return f"Error: Unable to convert content to JSON string: {str(e)}"

        # Ensure content ends with a newline if it doesn't already
        if content and not content.endswith('\n'):
            content += '\n'

        # Create file if it doesn't exist
        directory = os.path.dirname(os.path.abspath(path))
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as file:
                pass

        with open(path, 'r', encoding='utf-8', errors='replace') as file:
            lines = file.readlines()

        # Ensure all existing lines end with newlines
        for i in range(len(lines)):
            if lines[i] and not lines[i].endswith('\n'):
                lines[i] += '\n'

        # Prepare lines for insertion
        content_lines = content.splitlines(True)  # Keep line endings

        # Handle inserting at specific rows
        if rows is not None:
            if not isinstance(rows, list):
                return "Error: 'rows' parameter must be a list of integers."

            # Sort rows in descending order to avoid changing indices during insertion
            rows = sorted(rows, reverse=True)

            for r in rows:
                if not isinstance(r, int) or r < 0:
                    return "Error: Row numbers must be non-negative integers."

                if r > len(lines):
                    # If row is beyond the file, append necessary empty lines
                    lines.extend(['\n'] * (r - len(lines)))
                    lines.extend(content_lines)
                else:
                    # Insert content at each specified row
                    for line in reversed(content_lines):
                        lines.insert(r, line)

            # Write back to the file
            with open(path, 'w', encoding='utf-8') as file:
                file.writelines(lines)

            return f"Successfully inserted content at rows {rows} in '{path}'."

        # Handle inserting at a single row
        elif row is not None:
            if not isinstance(row, int) or row < 0:
                return "Error: Row number must be a non-negative integer."

            if row > len(lines):
                # If row is beyond the file, append necessary empty lines
                lines.extend(['\n'] * (row - len(lines)))
                lines.extend(content_lines)
            else:
                # Insert content at the specified row
                for line in reversed(content_lines):
                    lines.insert(row, line)

            # Write back to the file
            with open(path, 'w', encoding='utf-8') as file:
                file.writelines(lines)

            return f"Successfully inserted content at row {row} in '{path}'."

        # If neither row nor rows specified, append to the end
        else:
            with open(path, 'a', encoding='utf-8') as file:
                file.write(content)
            return f"Successfully appended content to '{path}'."

    except PermissionError:
        return f"Error: No permission to modify file '{path}'."
    except Exception as e:
        return f"Error inserting content: {str(e)}"

@mcp.tool()
async def delete_file_content(path: str, row: int = None, rows: list = None, substring: str = None) -> str:
    """
    Delete content at specific row(s) from a file

    Args:
        path: Path to the file
        row: Row number to delete (0-based, optional)
        rows: List of row numbers to delete (0-based, optional)
        substring: If provided, only delete this substring within the specified row(s), not the entire row (optional)

    Returns:
        Operation result information
    """
    if not is_safe_path(path):
        return f"Security Error: Access to '{path}' is denied. File is outside of SAFE_DIRS."

    try:
        if not os.path.exists(path):
            return f"Error: File '{path}' does not exist."

        if not os.path.isfile(path):
            return f"Error: '{path}' is not a file."

        with open(path, 'r', encoding='utf-8', errors='replace') as file:
            lines = file.readlines()

        total_lines = len(lines)
        deleted_rows = []
        modified_rows = []

        # Handle substring deletion (doesn't delete entire rows)
        if substring is not None:
            # For multiple rows
            if rows is not None:
                if not isinstance(rows, list):
                    return "Error: 'rows' parameter must be a list of integers."

                for r in rows:
                    if not isinstance(r, int) or r < 0:
                        return "Error: Row numbers must be non-negative integers."

                    if r < total_lines and substring in lines[r]:
                        original_line = lines[r]
                        lines[r] = lines[r].replace(substring, '')
                        # Ensure line ends with newline if original did
                        if original_line.endswith('\n') and not lines[r].endswith('\n'):
                            lines[r] += '\n'
                        modified_rows.append(r)

            # For single row
            elif row is not None:
                if not isinstance(row, int) or row < 0:
                    return "Error: Row number must be a non-negative integer."

                if row >= total_lines:
                    return f"Error: Row {row} is out of range (file has {total_lines} lines)."

                if substring in lines[row]:
                    original_line = lines[row]
                    lines[row] = lines[row].replace(substring, '')
                    # Ensure line ends with newline if original did
                    if original_line.endswith('\n') and not lines[row].endswith('\n'):
                        lines[row] += '\n'
                    modified_rows.append(row)

            # For entire file
            else:
                for i in range(len(lines)):
                    if substring in lines[i]:
                        original_line = lines[i]
                        lines[i] = lines[i].replace(substring, '')
                        # Ensure line ends with newline if original did
                        if original_line.endswith('\n') and not lines[i].endswith('\n'):
                            lines[i] += '\n'
                        modified_rows.append(i)

            # Write back to the file
            with open(path, 'w', encoding='utf-8') as file:
                file.writelines(lines)

            if not modified_rows:
                return f"No occurrences of '{substring}' found in the specified rows."
            return f"Successfully removed '{substring}' from {len(modified_rows)} rows ({modified_rows}) in '{path}'."

        # Handle deleting multiple rows
        elif rows is not None:
            if not isinstance(rows, list):
                return "Error: 'rows' parameter must be a list of integers."

            # Sort rows in descending order to avoid changing indices during deletion
            rows = sorted(rows, reverse=True)

            for r in rows:
                if not isinstance(r, int) or r < 0:
                    return "Error: Row numbers must be non-negative integers."

                if r < total_lines:
                    lines.pop(r)
                    deleted_rows.append(r)

            # Write back to the file
            with open(path, 'w', encoding='utf-8') as file:
                file.writelines(lines)

            if not deleted_rows:
                return f"No rows were within range to delete (file has {total_lines} lines)."
            return f"Successfully deleted {len(deleted_rows)} rows ({deleted_rows}) from '{path}'."

        # Handle deleting a single row
        elif row is not None:
            if not isinstance(row, int) or row < 0:
                return "Error: Row number must be a non-negative integer."

            if row >= total_lines:
                return f"Error: Row {row} is out of range (file has {total_lines} lines)."

            # Delete the specified row
            lines.pop(row)

            # Write back to the file
            with open(path, 'w', encoding='utf-8') as file:
                file.writelines(lines)

            return f"Successfully deleted row {row} from '{path}'."

        # If neither row nor rows specified, clear the file
        else:
            with open(path, 'w', encoding='utf-8') as file:
                pass
            return f"Successfully cleared all content from '{path}'."

    except PermissionError:
        return f"Error: No permission to modify file '{path}'."
    except Exception as e:
        return f"Error deleting content: {str(e)}"

@mcp.tool()
async def update_file_content(path: str, content: str, row: int = None, rows: list = None, substring: str = None) -> str:
    """
    Update content at specific row(s) in a file

    Args:
        path: Path to the file
        content: New content to place at the specified row(s)
        row: Row number to update (0-based, optional)
        rows: List of row numbers to update (0-based, optional)
        substring: If provided, only replace this substring within the specified row(s), not the entire row

    Returns:
        Operation result information
    """
    if not is_safe_path(path):
        return f"Security Error: Access to '{path}' is denied. File is outside of SAFE_DIRS."

    try:
        # Handle different content types
        if not isinstance(content, str):
            try:
                content = json.dumps(content, indent=4, sort_keys=False, ensure_ascii=False, default=str)
            except Exception as e:
                return f"Error: Unable to convert content to JSON string: {str(e)}"

        if not os.path.exists(path):
            return f"Error: File '{path}' does not exist."

        if not os.path.isfile(path):
            return f"Error: '{path}' is not a file."

        with open(path, 'r', encoding='utf-8', errors='replace') as file:
            lines = file.readlines()

        total_lines = len(lines)
        updated_rows = []

        # Ensure content ends with a newline if replacing a full line and doesn't already have one
        if substring is None and content and not content.endswith('\n'):
            content += '\n'

        # Prepare lines for update
        content_lines = content.splitlines(True) if substring is None else [content]

        # Handle updating multiple rows
        if rows is not None:
            if not isinstance(rows, list):
                return "Error: 'rows' parameter must be a list of integers."

            for r in rows:
                if not isinstance(r, int) or r < 0:
                    return "Error: Row numbers must be non-negative integers."

                if r < total_lines:
                    # If substring is provided, only replace that part
                    if substring is not None:
                        # Only update if substring exists in the line
                        if substring in lines[r]:
                            original_line = lines[r]
                            lines[r] = lines[r].replace(substring, content)
                            # Ensure line ends with newline if original did
                            if original_line.endswith('\n') and not lines[r].endswith('\n'):
                                lines[r] += '\n'
                            updated_rows.append(r)
                    else:
                        # Otherwise, replace the entire line
                        # If we have multiple content lines, use them in sequence
                        if len(content_lines) > 1:
                            content_index = r % len(content_lines)
                            lines[r] = content_lines[content_index]
                        else:
                            # If we have only one content line, use it for all rows
                            lines[r] = content_lines[0] if content_lines else "\n"
                        updated_rows.append(r)

            # Write back to the file
            with open(path, 'w', encoding='utf-8') as file:
                file.writelines(lines)

            if not updated_rows:
                if substring is not None:
                    return f"No occurrences of substring '{substring}' found in the specified rows (file has {total_lines} lines)."
                else:
                    return f"No rows were within range to update (file has {total_lines} lines)."

            if substring is not None:
                return f"Successfully updated substring in {len(updated_rows)} rows ({updated_rows}) in '{path}'."
            else:
                return f"Successfully updated {len(updated_rows)} rows ({updated_rows}) in '{path}'."

        # Handle updating a single row
        elif row is not None:
            if not isinstance(row, int) or row < 0:
                return "Error: Row number must be a non-negative integer."

            if row >= total_lines:
                return f"Error: Row {row} is out of range (file has {total_lines} lines)."

            # If substring is provided, only replace that part
            if substring is not None:
                # Only update if substring exists in the line
                if substring in lines[row]:
                    original_line = lines[row]
                    lines[row] = lines[row].replace(substring, content)
                    # Ensure line ends with newline if original did
                    if original_line.endswith('\n') and not lines[row].endswith('\n'):
                        lines[row] += '\n'
                else:
                    return f"Substring '{substring}' not found in row {row}."
            else:
                # Otherwise, replace the entire line
                lines[row] = content_lines[0] if content_lines else "\n"

            # Write back to the file
            with open(path, 'w', encoding='utf-8') as file:
                file.writelines(lines)

            if substring is not None:
                return f"Successfully updated substring in row {row} in '{path}'."
            else:
                return f"Successfully updated row {row} in '{path}'."

        # If neither row nor rows specified, update the entire file
        else:
            if substring is not None:
                # Replace substring throughout the file
                updated_count = 0
                for i in range(len(lines)):
                    if substring in lines[i]:
                        original_line = lines[i]
                        lines[i] = lines[i].replace(substring, content)
                        # Ensure line ends with newline if original did
                        if original_line.endswith('\n') and not lines[i].endswith('\n'):
                            lines[i] += '\n'
                        updated_count += 1

                with open(path, 'w', encoding='utf-8') as file:
                    file.writelines(lines)

                if updated_count == 0:
                    return f"Substring '{substring}' not found in any line of '{path}'."
                return f"Successfully updated substring in {updated_count} lines in '{path}'."
            else:
                # Replace entire file content
                with open(path, 'w', encoding='utf-8') as file:
                    file.write(content)
                return f"Successfully updated all content in '{path}'."

    except PermissionError:
        return f"Error: No permission to modify file '{path}'."
    except Exception as e:
        return f"Error updating content: {str(e)}"

def main():
    """
    Entry point function that runs the MCP server.
    """
    print("Starting Terminal Controller MCP Server...", file=sys.stderr)
    mcp.run(transport='stdio')

# Make the module callable
def __call__():
    """
    Make the module callable for uvx.
    This function is called when the module is executed directly.
    """
    print("Terminal Controller MCP Server starting via __call__...", file=sys.stderr)
    mcp.run(transport='stdio')

# Add this for compatibility with uvx
sys.modules[__name__].__call__ = __call__

# Run the server when the script is executed directly
if __name__ == "__main__":
    main()
