#!/bin/bash
# Activation and run script for Insulin Recommendation System

echo "Automated Insulin Dose Recommendation System"
echo "============================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run setup.py first."
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Please update with your Google OAuth credentials."
    echo "You can copy from .env.example if it exists."
fi

# Run the application
echo "Starting Flask application..."
python app.py

