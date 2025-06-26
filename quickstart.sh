#!/bin/bash

echo "=== Telegram Quick Export Web UI ==="
echo

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Run ./setup.sh first"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Install Flask if needed
pip install flask --quiet

# Check if logged in
if [ ! -f ".session" ]; then
    echo "⚠️  Not logged in to Telegram!"
    echo "Run: ./run.sh login"
    echo
    exit 1
fi

echo "Starting Quick Export server..."
echo
echo "📱 Open your browser to: http://localhost:5000"
echo
echo "Features:"
echo "  • Export last 1h, 6h, 24h, or custom time range"
echo "  • Automatic bot filtering and LLM formatting"  
echo "  • Download clean .txt files ready for AI analysis"
echo "  • Recent exports history"
echo
echo "Press Ctrl+C to stop the server"
echo

# Run the Flask app
python -m tg_export.quick_export