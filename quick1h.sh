#!/bin/bash

# Ultra-quick 1-hour export script

if [ -z "$1" ]; then
    echo "Usage: ./quick1h.sh <chat_url>"
    echo "Example: ./quick1h.sh https://t.me/c/123456789/12345"
    exit 1
fi

source venv/bin/activate

echo "Exporting last hour..."
poetry run tg_export quick --chat-url "$1" --hours 1

# Find the most recent export
latest_file=$(ls -t exports/quick/quick_1h_*.txt 2>/dev/null | head -1)

if [ -f "$latest_file" ]; then
    echo
    echo "✅ Export complete!"
    echo
    
    # Copy to clipboard based on OS
    if command -v pbcopy > /dev/null; then
        pbcopy < "$latest_file"
        echo "📋 Copied to clipboard! Paste into your LLM chat."
    elif command -v xclip > /dev/null; then
        xclip -selection clipboard < "$latest_file"
        echo "📋 Copied to clipboard! Paste into your LLM chat."
    else
        echo "📁 File saved to: $latest_file"
        echo "Copy manually to use with your LLM."
    fi
fi