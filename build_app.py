#!/usr/bin/env python3
"""
Cross-platform build script for LocAI Personal Assistant
Supports Windows, macOS, and Linux
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def run_command(cmd, shell=False):
    """Run a command and handle errors"""
    try:
        result = subprocess.run(cmd, shell=shell, check=True, capture_output=True, text=True)
        print(f"✓ {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"✗ Error running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        print(f"  Error: {e.stderr}")
        return None

def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")
    
    # Upgrade pip first
    run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    
    # Install requirements
    run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def create_pyinstaller_spec():
    """Create PyInstaller spec file for the current platform"""
    print("Creating PyInstaller spec file...")
    
    current_os = platform.system().lower()
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('models', 'models'),
        ('README.md', '.'),
    ],
    hiddenimports=[
        'customtkinter',
        'sentence_transformers',
        'faiss',
        'llama_cpp',
        'PIL',
        'PIL._tkinter_finder',
        'tkinter',
        'tkinter.ttk',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LocAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''

    # Add platform-specific configurations
    if current_os == "darwin":  # macOS
        spec_content += '''
app = BUNDLE(
    exe,
    name='LocAI.app',
    icon=None,
    bundle_identifier='com.yourname.locai',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'NSRequiresAquaSystemAppearance': 'False',
    },
)
'''

    with open("LocAI.spec", "w") as f:
        f.write(spec_content)

def build_executable():
    """Build the executable using PyInstaller"""
    print("Building executable...")
    
    # Clean previous builds
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    
    # Create spec file
    create_pyinstaller_spec()
    
    # Build
    result = run_command([sys.executable, "-m", "PyInstaller", "LocAI.spec", "--clean"])
    
    if result:
        current_os = platform.system().lower()
        if current_os == "darwin":
            print("✓ macOS app bundle created in dist/LocAI.app")
        elif current_os == "windows":
            print("✓ Windows executable created in dist/LocAI.exe")
        else:
            print("✓ Linux executable created in dist/LocAI")

def create_installer_scripts():
    """Create installation scripts for different platforms"""
    
    # Windows batch installer
    windows_installer = '''@echo off
echo Installing LocAI Personal Assistant...

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

:: Install dependencies
echo Installing Python dependencies...
pip install -r requirements.txt

echo.
echo Installation complete!
echo Run "python gui_app.py" to start the application.
pause
'''
    
    # macOS/Linux shell installer
    unix_installer = '''#!/bin/bash
echo "Installing LocAI Personal Assistant..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Install dependencies
echo "Installing Python dependencies..."
python3 -m pip install -r requirements.txt

echo ""
echo "Installation complete!"
echo "Run 'python3 gui_app.py' to start the application."
'''
    
    with open("install.bat", "w") as f:
        f.write(windows_installer)
    
    with open("install.sh", "w") as f:
        f.write(unix_installer)
    
    # Make shell script executable
    if platform.system() != "Windows":
        os.chmod("install.sh", 0o755)
    
    print("✓ Installation scripts created (install.bat, install.sh)")

def main():
    """Main build function"""
    print("LocAI Personal Assistant Build Script")
    print("=" * 40)
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Python: {sys.version}")
    print()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
    else:
        command = "all"
    
    if command in ["deps", "all"]:
        install_dependencies()
        print()
    
    if command in ["exe", "all"]:
        build_executable()
        print()
    
    if command in ["installer", "all"]:
        create_installer_scripts()
        print()
    
    print("Build process complete!")
    print()
    print("Next steps:")
    print("1. Test the executable in the 'dist' folder")
    print("2. For GitHub: commit and push your changes")
    print("3. For distribution: share the 'dist' folder or create releases")

if __name__ == "__main__":
    main()
