import subprocess

# To silence all terminal logging
# import sys
# import os
# sys.stderr = open(os.devnull, "w")

from fastmcp import FastMCP
import os
from datetime import datetime

# Initialize the MCP Server
mcp = FastMCP("Gobuster MCP Server")

root_dir=os.getcwd()
output_dir=f"{root_dir}/instance/gobuster"

def run_gobuster_command(args: list[str], output_file: str, timeout: int) -> str:
    """
    Helper function to execute gobuster and capture output.
    """
    # We add --no-color to prevent ANSI escape codes from confusing the LLM
    cmd = ["gobuster"] + args + ["--no-color"]
    
    try:
        # Run the command and capture output
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )

        if not os.path.exists(output_file):
            return "Gobuster finished, but no output file was created."
            
        with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        # Filter out empty lines
        findings = [l for l in lines if l.strip()]
            
        # Include total count so the LLM knows the full scope
        summary = f"Gobuster scan complete. Found {len(findings)} results. Full output saved to: {output_file}\n\n"
        
        if len(findings) > 500:
            summary += "[SYSTEM NOTE: Showing first 500 of " + str(len(findings)) + " results to save memory. Use terminal to 'grep' the output file for more.]\n"
            summary += "".join(findings[:500])
        else:
            summary += "".join(findings)
            
        return summary if summary.strip() else f"Gobuster scan complete. No findings. Full log at {output_file}"
        
    except subprocess.TimeoutExpired:
        return f"Error: Scan timed out after {timeout} seconds."
    except FileNotFoundError:
        return "Error: 'gobuster' command not found. Please ensure it is installed."

@mcp.tool()
def inspect_wordlist(file_path: str, num_lines: int = 50) -> str:
    """
    [UTILITY] Reads the first N lines of a wordlist file to verify its contents 
    and format before running a long scan. This prevents starting a massive 
    scan with a hallucinated file path or the wrong wordlist.
    
    Args:
        file_path: Absolute path to the wordlist file.
        num_lines: Number of lines to read (default 50).
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at '{file_path}'"
        
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [f.readline().strip() for _ in range(num_lines) if f.readable()]
            
        total_size = os.path.getsize(file_path)
        return f"File size: {total_size / (1024*1024):.2f} MB\nFirst {len(lines)} lines:\n" + "\n".join(lines)
    except Exception as e:
        return f"Error reading file: {str(e)}"

@mcp.tool()
def scan_directories(
    target_url: str, 
    wordlist_path: str, 
    extensions: str = "", 
    exclude_length: str = "",
    threads: int = 10, 
    timeout: int = 300
) -> str:
    f"""
    Brute-force directories and files on a web server.
    
    Args:
        target_url: The target URL (e.g., http://10.10.10.10)
        wordlist_path: The absolute path to the wordlist file (e.g., {root_dir}/wordlists/dirb/common.txt)
        extensions: Optional comma-separated extensions to look for (e.g., 'php,html,txt')
        exclude_length: Exclude specific response lengths (e.g., '9903' or '203-206'). Crucial for bypassing custom 404 pages that return a 200 status code.
        threads: Number of concurrent threads (default: 10)
        timeout: Maximum seconds to run the scan (default: 300)
    """
    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"gobuster_{timestamp}.txt"
    filepath = os.path.join(output_dir, filename)
    
    args = [
        "dir", 
        "-u", target_url, 
        "-w", wordlist_path, 
        "-t", str(threads), 
        "-o", filepath
    ]

    if exclude_length:
        args.extend(["--exclude-length", exclude_length])

    if extensions:
        args.extend(["-x", extensions])
        
    return run_gobuster_command(args, filepath, timeout)

@mcp.tool()
def scan_vhost(
    target_url: str, 
    domain: str, 
    wordlist_path: str, 
    timeout: int = 300
) -> str:
    """
    Perform virtual host (vhost) brute-forcing.
    
    Args:
        target_url: The target IP or URL.
        domain: The base domain to append vhosts to (e.g., 'example.com').
        wordlist_path: The absolute path to the wordlist file.
        timeout: Maximum seconds to run the scan.
    """

    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"gobuster_{timestamp}.txt"
    filepath = os.path.join(output_dir, filename)

    args = ["vhost", "-u", target_url, "--domain", domain, "-w", wordlist_path, "-o", filepath]
    return run_gobuster_command(args, filepath, timeout)

@mcp.tool()
def scan_dns(
    domain: str, 
    wordlist_path: str, 
    timeout: int = 300
) -> str:
    """
    Perform DNS subdomain brute-forcing.
    
    Args:
        domain: The target domain (e.g., 'example.com').
        wordlist_path: The absolute path to the wordlist file.
        timeout: Maximum seconds to run the scan.
    """
    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"gobuster_{timestamp}.txt"
    filepath = os.path.join(output_dir, filename)

    args = ["dns", "--domain", domain, "-w", wordlist_path, "-o", filepath]
    return run_gobuster_command(args, filepath, timeout)

@mcp.tool()
def scan_fuzz(
    target_url_pattern: str,
    wordlist_path: str,
    threads: int = 10,
    timeout: int = 300
) -> str:
    f"""
    Perform custom fuzzing using the 'FUZZ' keyword in the URL.
    Useful for finding hidden API parameters, user IDs, or specific file paths.
    
    Args:
        target_url_pattern: The URL containing the word 'FUZZ' to be replaced (e.g., 'http://target.com/api/FUZZ' or 'http://target.com/?id=FUZZ').
        wordlist_path: e.g. '{root_dir}/wordlists/seclists/Fuzzing'.
        threads: Concurrent threads (default: 10).
        timeout: Max seconds to run (default: 300).
    """
    if "FUZZ" not in target_url_pattern:
        return "Error: The target_url_pattern must contain the exact string 'FUZZ'."
    
    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"gobuster_{timestamp}.txt"
    filepath = os.path.join(output_dir, filename)

    args = ["fuzz", "-u", target_url_pattern, "-w", wordlist_path, "-t", str(threads), "-o", filepath]
    return run_gobuster_command(args, filepath, timeout)

if __name__ == "__main__":
    # Start the server over standard I/O (stdio)
    mcp.run()