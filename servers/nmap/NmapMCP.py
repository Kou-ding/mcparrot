import subprocess

# To silence all terminal logging
# import sys
# import os
# sys.stderr = open(os.devnull, "w")

from fastmcp import FastMCP

# Initialize the MCP Server
mcp = FastMCP("Nmap MCP Server")

def run_nmap_command(args: list[str], timeout: int) -> str:
    """
    Helper function to execute nmap and capture output.
    """
    # We append args to the base nmap command
    cmd = ["nmap"] + args
    
    try:
        # Run the command and capture output
        # Nmap can be slow depending on the target and network, so we respect the timeout
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        
        # Nmap mostly outputs to stdout, but warnings go to stderr
        output = result.stdout
        if result.stderr:
            output += f"\n[NMAP WARNINGS/ERRORS]\n{result.stderr}"
            
        return output.strip() or "No output returned. The scan may have failed or timed out silently."
        
    except subprocess.TimeoutExpired:
        return f"Error: Nmap scan timed out after {timeout} seconds."
    except FileNotFoundError:
        return "Error: 'nmap' command not found. Please ensure it is installed and in your system PATH."
    except Exception as e:
        return f"An unexpected OS-level error occurred: {str(e)}"


@mcp.tool()
def ping_sweep(target: str, timeout: int = 120) -> str:
    """
    Perform a quick ping sweep to discover live hosts on a network or check 
    if a specific IP/domain is online. Does NOT scan ports.
    
    Args:
        target: The target IP, CIDR range (e.g., 192.168.1.0/24), or domain.
        timeout: Maximum seconds to run the scan (default: 120).
    """
    # -sn: Ping scan - disable port scan
    args = ["-sn", target]
    return run_nmap_command(args, timeout)

@mcp.tool()
def tcp_scan(
    target: str, 
    ports: str = "top 100", 
    timeout: int = 600
) -> str:
    """
    Perform a standard TCP port scan with service version detection. 
    By default, only shows OPEN ports to save LLM context tokens.
    
    Args:
        target: The target IP or domain.
        ports: Ports to scan. Use 'top 100', 'top 1000', '1-65535', or specific ports like '80,443,8080'.
        timeout: Maximum seconds to run the scan (default: 600).
    """
    args = []
    
    # Handle port arguments
    if ports.startswith("top "):
        args.extend(["--top-ports", ports.split(" ")[1]])
    else:
        args.extend(["-p", ports])
        
    # -sV: Probe open ports to determine service/version info
    # --open: Only show open (or possibly open) ports to reduce output noise
    # -T4: Aggressive timing to speed up the scan without being overly noisy
    args.extend(["-sV", "--open", "-T4", target])
    
    return run_nmap_command(args, timeout)

@mcp.tool()
def vulnerability_scan(target: str, ports: str = "", timeout: int = 900) -> str:
    """
    Run Nmap's default vulnerability scripts (--script vuln) to check for 
    known CVEs (e.g., Heartbleed, SMBGhost, Log4j). 
    
    Args:
        target: IP or domain.
        ports: Optional specific ports to check (e.g., '443,445'). Leave blank to scan open ports.
        timeout: Max seconds to run.
    """
    args = ["--script", "vuln", "-T4"]
    if ports:
        args.extend(["-p", ports])
    args.append(target)
    return run_nmap_command(args, timeout)

@mcp.tool()
def web_enumeration(target: str, timeout: int = 600) -> str:
    """
    Enumerate web servers. Checks for HTTP headers, page titles, common 
    directories (http-enum), and allowed HTTP methods.
    
    Args:
        target: IP or domain.
        timeout: Max seconds to run.
    """
    scripts = "http-enum,http-headers,http-title,http-methods"
    # Target common web ports
    args = ["--script", scripts, "-p", "80,443,8080,8443,8000", target]
    return run_nmap_command(args, timeout)

@mcp.tool()
def smb_enumeration(target: str, timeout: int = 600) -> str:
    """
    Enumerate SMB/NetBIOS services (Windows file sharing). Extracts OS version, 
    domain name, shared folders, and user lists. Essential for internal pentests.
    
    Args:
        target: IP or domain.
        timeout: Max seconds to run.
    """
    scripts = "smb-enum-shares,smb-enum-users,smb-os-discovery,smb-protocols"
    args = ["--script", scripts, "-p", "139,445", target]
    return run_nmap_command(args, timeout)

@mcp.tool()
def smtp_enumeration(target: str, timeout: int = 300) -> str:
    """
    Enumerate allowed SMTP commands (like VRFY, EXPN) and test for open relays. 
    Useful for internal network mail server testing.
    
    Args:
        target: IP or domain.
        timeout: Max seconds to run.
    """
    scripts = "smtp-commands,smtp-open-relay"
    args = ["--script", scripts, "-p", "25,465,587", target]
    return run_nmap_command(args, timeout)

@mcp.tool()
def ftp_enumeration(target: str, timeout: int = 300) -> str:
    """
    Check for anonymous FTP login access and gather server banners.
    
    Args:
        target: IP or domain.
        timeout: Max seconds to run.
    """
    scripts = "ftp-anon"
    args = ["--script", scripts, "-p", "21", target]
    return run_nmap_command(args, timeout)

@mcp.tool()
def ssl_tls_enumeration(target: str, timeout: int = 300) -> str:
    """
    Extract SSL/TLS certificate details, expiration dates, and supported cipher suites. 
    Useful for identifying weak encryption, mismatched domain names, or expired certs.
    
    Args:
        target: IP or domain.
        timeout: Max seconds to run.
    """
    scripts = "ssl-cert,ssl-enum-ciphers"
    args = ["--script", scripts, "-p", "443,8443,465,993,995", target]
    return run_nmap_command(args, timeout)

@mcp.tool()
def dns_brute_force(target: str, timeout: int = 300) -> str:
    """
    Attempt to discover subdomains by brute-forcing DNS records using Nmap's 
    dns-brute script.
    
    Args:
        target: The base domain (e.g., 'example.com'). Do NOT include 'http://'.
        timeout: Max seconds to run.
    """
    args = ["--script", "dns-brute", target]
    return run_nmap_command(args, timeout)

## Require sudo
# @mcp.tool()
# def udp_scan(
#     target: str, 
#     ports: str = "53,67,68,69,123,135,137,138,139,161,445,500", 
#     timeout: int = 600
# ) -> str:
#     """
#     Perform a UDP port scan. Note: UDP scans are notoriously slow and 
#     often require root/admin privileges to work correctly (using ICMP errors).
    
#     Args:
#         target: The target IP or domain.
#         ports: Comma-separated list of common UDP ports to scan (default: top common UDP ports).
#         timeout: Maximum seconds to run the scan (default: 600).
#     """
#     # -sU: UDP scan
#     # --open: Only show open/filtered ports
#     args = ["-sU", "-p", ports, "--open", "-T4", target]
#     return run_nmap_command(args, timeout)
#
# @mcp.tool()
# def os_detection(target: str, timeout: int = 300) -> str:
#     """
#     Attempt to guess the target's Operating System using TCP/IP fingerprinting.
#     Note: This requires root/administrator privileges on the machine running this server.
    
#     Args:
#         target: The target IP or domain.
#         timeout: Maximum seconds to run the scan (default: 300).
#     """
#     # -O: Enable OS detection
#     # --osscan-limit: Limit OS detection to promising targets to save time
#     args = ["-O", "--osscan-limit", target]
#     return run_nmap_command(args, timeout)


if __name__ == "__main__":
    # Start the server over standard I/O (stdio)
    mcp.run()