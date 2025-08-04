import subprocess
import sys
import os
import shutil

def run_command(command, description):
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, check=True, shell=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def main():
    print("=" * 50)
    print("Personal AI Assistant - Build Script")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("gui_app.py"):
        print("Error: gui_app.py not found. Please run this script from the project directory.")
        sys.exit(1)
    
    # Check if models directory exists
    if not os.path.exists("models"):
        print("Warning: models directory not found. Creating it...")
        os.makedirs("models")
        print("Please place your model file 'Phi-3-mini-4k-instruct-q4.gguf' in the models directory.")
    
    # Install dependencies
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        sys.exit(1)
    
    # Clean previous builds
    if os.path.exists("dist"):
        print("\nCleaning previous builds...")
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")
    
    # Build executable
    build_command = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name", "PersonalAI",
        "--add-data", "models;models",
        "--distpath", "dist",
        "--workpath", "build",
        "--specpath", ".",
        "gui_app.py"
    ]
    
    if not run_command(" ".join(build_command), "Building executable"):
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("Build completed successfully!")
    print("=" * 50)
    print(f"Executable location: {os.path.abspath('dist/PersonalAI.exe')}")
    print("\nTo distribute your application:")
    print("1. Copy the entire 'dist' folder to the target machine")
    print("2. Ensure the 'models' folder is in the same directory as the executable")
    print("3. Run PersonalAI.exe")
    print("\nNote: The target machine needs to have Visual C++ Redistributable installed.")

if __name__ == "__main__":
    main()
