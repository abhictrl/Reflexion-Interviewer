#!/bin/bash

# Quick start script for Reflexion Interviewer

echo "🚀 Starting Reflexion Interviewer..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: python3 -m venv venv && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found."
    if [ -f ".env.example" ]; then
        echo "Creating .env from template..."
        cp .env.example .env
    else
        echo "Creating basic .env file..."
        cat > .env << EOF
# NVIDIA NIM API Configuration
# Get your API key from: https://build.nvidia.com/
NVIDIA_API_KEY=your_nvidia_api_key_here
EOF
    fi
    echo "⚠️  Please edit .env and add your NVIDIA_API_KEY before using the application."
    echo ""
fi

# Start the FastAPI server
echo "Starting FastAPI server..."
echo "📱 Frontend will be available at: http://localhost:8000"
echo "📚 API docs will be available at: http://localhost:8000/docs"
echo ""
cd backend
../venv/bin/python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

