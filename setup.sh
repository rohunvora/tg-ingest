#!/bin/bash

echo "=== Telegram Chat Exporter Setup ==="
echo

# Check if Python 3.10+ is installed
if ! python3 --version | grep -E "3\.(1[0-9]|[2-9][0-9])" > /dev/null; then
    echo "Error: Python 3.10 or higher is required"
    echo "Please install Python from https://python.org"
    exit 1
fi

# Create virtual environment
echo "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# Install poetry
echo "Installing Poetry..."
pip install poetry

# Install dependencies
echo "Installing dependencies..."
poetry install --no-root

# Create .env file
echo
echo "=== API Credentials Setup ==="
echo "You need to get these from https://my.telegram.org/apps"
echo

read -p "Enter your Telegram API ID: " api_id
read -p "Enter your Telegram API Hash: " api_hash

cat > .env << EOF
TELEGRAM_API_ID=$api_id
TELEGRAM_API_HASH=$api_hash
EOF

echo
echo "✅ Setup complete!"
echo
echo "Now run: ./run.sh login"
echo "Then: ./run.sh export"