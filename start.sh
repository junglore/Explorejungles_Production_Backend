#!/bin/bash

# Junglore Backend Production Server - Startup Script
# This script handles environment setup and starts the server

set -e  # Exit on any error

echo "🌿 Junglore Backend Production Server"
echo "======================================"

# Check if we're in the right directory
if [ ! -f "start_with_large_limits.py" ]; then
    echo "❌ Error: Please run this script from the Junglore_Backend_Production directory"
    echo "   Current directory: $(pwd)"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Error: Python $REQUIRED_VERSION or higher required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python version: $PYTHON_VERSION"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "✅ Virtual environment already active: $VIRTUAL_ENV"
fi

# Check if dependencies are installed
if [ ! -f "venv/lib/python*/site-packages/fastapi/__init__.py" ]; then
    echo "📥 Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies already installed"
fi

# Create uploads directory if it doesn't exist
if [ ! -d "uploads" ]; then
    echo "📁 Creating uploads directory..."
    mkdir -p uploads
    chmod 755 uploads
    echo "✅ Uploads directory created"
fi

# Check if database file exists (for SQLite)
if [ ! -f "junglore.db" ]; then
    echo "🗄️  Database not found. It will be created on first run."
fi

echo ""
echo "🚀 Starting Junglore Backend Server..."
echo "   Server URL: http://127.0.0.1:8000"
echo "   Admin Panel: http://127.0.0.1:8000/admin"
echo "   API Docs: http://127.0.0.1:8000/api/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo "======================================"

# Start the server
python3 start_with_large_limits.py
