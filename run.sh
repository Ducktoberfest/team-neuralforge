#!/usr/bin/env bash
set -e

# DuckTutor Local Launcher
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment '.venv' not found."
    echo "Please create and initialize it first:"
    echo "  python3 -m venv .venv"
    echo "  .venv/bin/pip install -r requirements.txt"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "Notice: No .env file found in project root."
    if [ -f ".env.example" ]; then
        echo "Tip: Copy .env.example to .env to persist your GEMINI_API_KEY:"
        echo "  cp .env.example .env"
    fi
fi

echo "🦆 Starting DuckTutor..."
exec .venv/bin/python -m streamlit run app.py "$@"
