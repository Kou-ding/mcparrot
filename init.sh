#!/bin/bash

# Dependencies
echo "Updating system..."
sudo pacman -Syu --noconfirm

echo "Installing dependencies..."
sudo pacman -S --noconfirm --needed python3 nmap gobuster hashcat sqlmap metasploit termshark binwalk bubblewrap

# Environment
echo "Setting up the environment..."

# Instance folder
mkdir instance
mkdir instance/gobuster
mkdir instance/hashcat
mkdir instance/logs
mkdir instance/metasploit
mkdir instance/sqlmap

# Hashcat necessary
mkdir instance/hashcat/temp
touch instance/hashcat/attack_presets.json
touch instance/hashcat/hashcat_sessions.db
touch instance/hashcat/hashcat_modes.csv

# Sessions
mkdir sessions

# Plans
mkdir static/plans

# Playground
mkdir playground

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

TERMINAL_SAFE_DIRS=$PWD/playground,$PWD/static/plans,$PWD/wordlists,$PWD/instance,/opt/metasploit

HASHCAT_PATH=$PWD/instance/hashcat/temp/
HASHCAT_SESSION_DB=$PWD/instance/hashcat/hashcat_sessions.db
HASHCAT_MODES_CSV=$PWD/instance/hashcat/hashcat_modes.csv
PRESETS_FILE_PATH=$PWD/instance/hashcat/attack_presets.json
HASHCAT_SAFE_DIRS=$PWD/wordlists/,$PWD/instance/hashcat/,$PWD/playground/
HASHCAT_DEFAULT_WORDLISTS=$PWD/wordlists/Passwords/Leaked-Databases/rockyou-75.txt

FASTMCP_LOG_LEVEL='ERROR'
" > .env

echo "Setup Complete!"
echo "Note: Please add your deepseek API key in .env"
