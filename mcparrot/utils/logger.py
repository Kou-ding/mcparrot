import logging
import sys

# ! Note: On other files do:
# from utils.logger import my_logger 
# to load the logger variable created here

# Configure logging
my_logger = logging.getLogger("MCPClient")
my_logger.setLevel(logging.DEBUG)

# File handler with DEBUG level
file_handler = logging.FileHandler("instance/logs/mcp_client.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
my_logger.addHandler(file_handler)

# Console handler with INFO level
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
my_logger.addHandler(console_handler)
