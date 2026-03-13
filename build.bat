@echo off
REM Build script for Kiro Gateway Windows executable
REM This script packages the application into a standalone .exe file

echo ========================================
echo Kiro Gateway - Build Script
echo ========================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [ERROR] PyInstaller is not installed.
    echo.
    echo Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller.
        pause
        exit /b 1
    )
)

REM Check if Pillow is installed
python -c "import PIL" 2>nul
if errorlevel 1 (
    echo [WARNING] Pillow is not installed. Skipping ICO creation.
) else (
    echo [INFO] Creating ICO files from PNG icons...
    python create_ico.py
    echo.
)

echo [INFO] Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist KiroGateway.exe del /q KiroGateway.exe

echo.
echo [INFO] Building executable with PyInstaller...
echo This may take a few minutes...
echo.
pyinstaller kiro_gateway.spec

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo [SUCCESS] Build completed successfully!
echo ========================================
echo.
echo Executable location: dist\KiroGateway.exe
echo File size: 
dir dist\KiroGateway.exe | find "KiroGateway.exe"
echo.
echo You can now:
echo   1. Double-click dist\KiroGateway.exe to run (tray mode)
echo   2. Copy dist\KiroGateway.exe to any location
echo   3. Create a desktop shortcut
echo   4. Set up auto-start from the tray menu
echo.
echo Note: The .exe file is standalone and includes all dependencies.
echo       Configure your credentials before running (see .env.example)
echo.

pause
