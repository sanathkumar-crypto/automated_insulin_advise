#!/bin/bash
# Test runner script for Insulin Recommendation System

echo "Automated Insulin Dose Recommendation System - Test Suite"
echo "========================================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run setup.py first."
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if Flask app is running
echo "Checking if Flask application is running..."
if ! curl -s http://localhost:5000 > /dev/null; then
    echo "Flask application is not running!"
    echo "Please start the Flask app first:"
    echo "  ./run_app.sh"
    echo "Or manually:"
    echo "  source venv/bin/activate && python app.py"
    exit 1
fi

echo "✓ Flask application is running"

# Run the test suite
echo "Running test suite..."
python test_insulin_app.py

