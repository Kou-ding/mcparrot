#!/bin/bash

# Exit immediately if any command fails
set -e

# Environment
echo "Setting up the environment..."

# Instance folder
mkdir -p instance
mkdir -p instance/gobuster
mkdir -p instance/hashcat
mkdir -p instance/logs
mkdir -p instance/metasploit
mkdir -p instance/sqlmap

# Hashcat necessary
mkdir -p instance/hashcat/temp
touch instance/hashcat/attack_presets.json
touch instance/hashcat/hashcat_sessions.db
touch instance/hashcat/hashcat_modes.csv

# Sessions
mkdir -p sessions

# Plans
mkdir -p static/plans

# Playground
mkdir -p playground

# .env
touch .env
echo "MODEL='deepseek-v4-pro'
API_KEY=''
BASE_URL='https://api.deepseek.com/anthropic'

MSF_PASSWORD=kali
MSF_SERVER=127.0.0.1
MSF_PORT=55553
MSF_SSL=false
PAYLOAD_SAVE_DIR=$PWD/instance/metasploit

TERMINAL_SAFE_DIRS=$PWD/playground,$PWD/static/plans,$PWD/wordlists,$PWD/instance

HASHCAT_PATH=$PWD/instance/hashcat/temp/
HASHCAT_SESSION_DB=$PWD/instance/hashcat/hashcat_sessions.db
HASHCAT_MODES_CSV=$PWD/instance/hashcat/hashcat_modes.csv
PRESETS_FILE_PATH=$PWD/instance/hashcat/attack_presets.json
HASHCAT_SAFE_DIRS=$PWD/wordlists/,$PWD/instance/hashcat/,$PWD/playground/
HASHCAT_DEFAULT_WORDLISTS=$PWD/wordlists/Passwords/Leaked-Databases/rockyou-75.txt

FASTMCP_LOG_LEVEL='ERROR'
" > .env

echo "Environment Setup Complete!"
echo "Note: Please add your deepseek API key in .env"
sleep 2

echo "Attempting to Install Dependencies..."
sleep 2

# Dependencies
echo "Detecting Linux Distribution..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO_ID=$ID
else
    echo "Error: Cannot detect OS. /etc/os-release not found."
    echo "Manually install the necessary dependencies."
    exit 1
fi

install_deps(){
    case "$DISTRO_ID" in
        arch|cachyos|blackarch|endeavouros|artix|manjaro)
            echo "Detected Arch-based system. Using pacman..."
            sudo pacman -Syu --noconfirm
            sudo pacman -S --noconfirm --needed python nmap gobuster hashcat sqlmap metasploit termshark binwalk bubblewrap uv
            ;;

        kali|parrot)
            echo "Detected Debian-based system. Using apt..."

            sudo apt update
            sudo apt upgrade -y
            sudo apt install -y curl python3 nmap gobuster hashcat sqlmap termshark binwalk bubblewrap metasploit-framework

            if ! command -v uv &> /dev/null; then
                echo "Installing uv..."
                curl -LsSf https://astral.sh/uv/install.sh | sh
                # Avoid restarting the terminal
                export PATH="$HOME/.local/bin:$PATH"
            else
                echo "uv is already installed. Skipping."
            fi
            ;;
        *)
            echo "Error: Unsupported distribution: $DISTRO_ID" >&2
            echo "Manually install the necessary dependencies."
            exit 1
            ;;
    esac
}

install_deps

echo "Dependencies were installed successfully."
