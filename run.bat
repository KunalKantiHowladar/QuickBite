@echo off
echo Starting QuickBite...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.8 or later from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist venv (
    echo Creating new virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Run the Flask application
echo Starting Flask application...
echo Application will run at http://127.0.0.1:8080
set FLASK_APP=app.py
set FLASK_ENV=development
python app.py

REM Keep the window open if there's an error
if %errorlevel% neq 0 (
    echo An error occurred. Please check the logs above.
    pause
    exit /b 1
) 