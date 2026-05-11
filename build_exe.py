import PyInstaller.__main__
import os
import sys

def build_exe():
    # Define the entry point
    script_name = 'vtx_vrx_gui.py'

    if not os.path.exists(script_name):
        print(f"Error: {script_name} not found.")
        return

    print(f"Starting build for {script_name}...")

    # PyInstaller arguments
    # --onefile: Create a single executable
    # --windowed: No console window
    # --name: Output executable name
    # --clean: Clean cache before build
    # --collect-all: Ensure tkintermapview dependencies are included

    args = [
        script_name,
        '--onefile',
        '--windowed',
        '--name=VTX_VRX_Pro_Controller',
        '--clean',
        '--collect-all=tkintermapview',
        '--hidden-import=PIL.ImageTk',
        '--hidden-import=PIL.Image',
    ]

    try:
        PyInstaller.__main__.run(args)
        print("\nBuild successful! Your executable is in the 'dist' folder.")
    except Exception as e:
        print(f"\nBuild failed: {e}")

if __name__ == "__main__":
    # Check if pyinstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("Error: PyInstaller is not installed. Run 'pip install pyinstaller'")
        sys.exit(1)

    build_exe()
