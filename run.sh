#!/bin/bash

source venv/bin/activate

case "$1" in
    "login")
        echo "=== Telegram Login ==="
        echo "You'll receive a code on your Telegram app"
        echo
        poetry run tg_export login
        ;;
    
    "export")
        echo "=== Export Telegram Chat ==="
        echo
        echo "How to get your chat URL:"
        echo "1. Open the group in Telegram"
        echo "2. Click the group name at the top"
        echo "3. Look for 'Invite Link' (for private groups)"
        echo "4. Copy the link - it should look like https://t.me/c/1234567890"
        echo
        read -p "Paste your Telegram chat URL: " chat_url
        
        # Create output directory
        mkdir -p exports
        
        # Generate filename with timestamp
        timestamp=$(date +%Y%m%d_%H%M%S)
        output_file="exports/telegram_export_${timestamp}.jsonl"
        
        echo
        echo "Exporting messages..."
        echo "This may take a few minutes for large groups..."
        echo
        
        poetry run tg_export dump --chat-url "$chat_url" --out "$output_file"
        
        echo
        echo "✅ Export complete!"
        echo "📁 File saved to: $output_file"
        echo
        
        # Ask if user wants to clean the data
        read -p "Would you like to clean the data for easier LLM reading? (y/n): " clean_choice
        
        if [[ "$clean_choice" == "y" || "$clean_choice" == "Y" ]]; then
            echo
            echo "Cleaning data..."
            poetry run python -m tg_export.clean_export --input "$output_file" --format txt
        fi
        
        echo
        echo "You can now:"
        echo "- Upload the clean .txt file to Claude, ChatGPT, etc."
        echo "- The clean version filters out bots and URLs"
        echo "- Original JSONL file is preserved if you need it"
        ;;
    
    "clean")
        echo "=== Clean Exported Data ==="
        echo
        echo "Available exports:"
        ls -la exports/*.jsonl 2>/dev/null || echo "No exports found"
        echo
        read -p "Enter the filename to clean (or full path): " input_file
        
        poetry run python -m tg_export.clean_export --input "$input_file" --format txt
        ;;
    
    "quick")
        echo "=== Quick Export (Last Hour) ==="
        echo
        read -p "Paste your Telegram chat URL: " chat_url
        read -p "How many hours back? (default: 1): " hours
        
        # Default to 1 hour if not specified
        hours=${hours:-1}
        
        echo
        echo "Exporting last $hours hour(s)..."
        echo
        
        poetry run tg_export quick --chat-url "$chat_url" --hours "$hours"
        ;;
    
    "web")
        echo "=== Starting Web UI ==="
        echo
        
        # Start the web server
        source venv/bin/activate
        pip install flask --quiet
        
        # Note: Browser will open automatically to the correct port
        python web_server.py
        ;;
    
    *)
        echo "Usage:"
        echo "  ./run.sh login    - Login to Telegram (do this first)"
        echo "  ./run.sh export   - Export a chat"
        echo "  ./run.sh clean    - Clean an existing export for LLM use"
        echo "  ./run.sh quick    - Quick export last N hours (for LLM)"
        echo "  ./run.sh web      - Start web UI for easy exports"
        ;;
esac