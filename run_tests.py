#!/usr/bin/env python3
"""
Simple test runner for ComfyUI-Manager tests.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py -k test_task_queue # Run specific tests
    python run_tests.py --cov             # Run with coverage
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Run pytest with appropriate arguments"""
    # Ensure we're in the project directory
    project_root = Path(__file__).parent
    
    # Base pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    # Add any command line arguments passed to this script
    cmd.extend(sys.argv[1:])
    
    # Add default arguments if none provided
    if len(sys.argv) == 1:
        cmd.extend([
            "tests/",
            "-v",
            "--tb=short"
        ])
    
    print(f"Running: {' '.join(cmd)}")
    print(f"Working directory: {project_root}")
    
    # Run pytest
    result = subprocess.run(cmd, cwd=project_root)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()