#!/usr/bin/env python3

import sys
import os
import subprocess
import importlib.util

# Print Python version and environment info
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
print("Working directory:", os.getcwd())
print("Directory contents:", os.listdir("."))

# List all installed packages
print("\n--- Installed Packages ---")
subprocess.run([sys.executable, "-m", "pip", "list"])

# Try to import runpod and show its location
print("\n--- Trying to import runpod ---")
try:
    import runpod
    print(f"RunPod version: {runpod.__version__}")
    print(f"RunPod location: {runpod.__file__}")
    
    # Check if the serverless module exists
    if hasattr(runpod, 'serverless'):
        print("runpod.serverless module exists")
        
        # Check if the start module exists
        if importlib.util.find_spec('runpod.serverless.start'):
            print("runpod.serverless.start module exists")
        else:
            print("runpod.serverless.start module NOT FOUND")
    else:
        print("runpod.serverless module NOT FOUND")
        
    # Show the runpod package structure
    package_dir = os.path.dirname(runpod.__file__)
    print("\nRunPod package directory structure:")
    for root, dirs, files in os.walk(package_dir):
        level = root.replace(package_dir, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = ' ' * 4 * (level + 1)
        for file in files:
            print(f"{sub_indent}{file}")
            
except ImportError as e:
    print(f"Failed to import runpod: {e}")

# Try to run the actual serverless start
print("\n--- Attempting to run runpod.serverless.start ---")
try:
    result = subprocess.run(
        [sys.executable, "-m", "runpod.serverless.start"],
        capture_output=True,
        text=True
    )
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
except Exception as e:
    print(f"Error running serverless.start: {e}")

print("\nDebug complete") 