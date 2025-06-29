#!/bin/bash
echo "Starting QuickBite..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed or not in PATH."
    echo "Please install Python 3.8 or later from https://www.python.org/downloads/"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating new virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run the Flask application
echo "Starting Flask application..."
echo "Application will run at http://127.0.0.1:8080"
export FLASK_APP=app.py
export FLASK_ENV=development
python3 app.py

# If this point is reached, check if the app exited with an error
if [ $? -ne 0 ]; then
    echo "An error occurred. Please check the logs above."
    read -p "Press Enter to continue..."
    exit 1
fi 