#!/usr/bin/env python
"""
Test runner script for ReplyRocket.io.

This script runs all pytest tests and generates coverage reports.
"""

import os
import sys
import subprocess
import webbrowser
from pathlib import Path


def run_tests():
    """Run the pytest tests with coverage reporting."""
    print("Running tests with coverage...")
    
    # Create directory for coverage reports if it doesn't exist
    Path("coverage_reports").mkdir(exist_ok=True)
    
    # Run pytest with coverage options
    result = subprocess.run([
        "pytest",
        "tests/",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=html:coverage_reports/html",
        "-v"
    ], capture_output=True, text=True)
    
    # Print the output
    print(result.stdout)
    if result.stderr:
        print("Errors:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    
    # Open coverage report in browser if tests pass
    if result.returncode == 0:
        print("\nTests passed! Opening coverage report in browser...")
        report_path = os.path.abspath("coverage_reports/html/index.html")
        webbrowser.open(f"file://{report_path}")
    else:
        print("\nTests failed. Please check the output above for details.")
    
    return result.returncode


def main():
    """Main entry point for the script."""
    sys.exit(run_tests())


if __name__ == "__main__":
    main() 