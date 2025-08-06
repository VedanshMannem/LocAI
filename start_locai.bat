@echo off
title LocAI Personal Assistant

echo ===============================================
echo    LocAI Personal Assistant - Quick Start
echo ===============================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    echo.
    pause
    exit /b 1
)

:: Check if requirements are installed
python -c "import customtkinter" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install requirements
        pause
        exit /b 1
    )
    echo.
)

echo Starting LocAI...
echo.
python gui_app.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start LocAI
    echo Check the console output above for details
    pause
)
