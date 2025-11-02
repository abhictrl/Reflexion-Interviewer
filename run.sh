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
    echo "⚠️  Warning: .env file not found. Creating from template..."
    cp .env.example .env
    echo "Please edit .env and add your NVIDIA_API_KEY"
fi

# Start the FastAPI server
echo "Starting FastAPI server..."
echo "📱 Frontend will be available at: http://localhost:8000"
echo "📚 API docs will be available at: http://localhost:8000/docs"
echo ""
cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

