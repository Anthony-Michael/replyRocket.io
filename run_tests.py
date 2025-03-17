#!/usr/bin/env python
"""
Test runner for ReplyRocket.io tests.

This script runs the test suite with coverage reporting and provides a summary of the results.
"""

import os
import sys
import subprocess
import webbrowser
from pathlib import Path


def run_tests():
    """Run the test suite with coverage reporting."""
    print("\n========== Running ReplyRocket.io Tests ==========\n")
    
    # Get the absolute path to the project root directory
    root_dir = Path(__file__).parent.absolute()
    
    # Create a directory for coverage reports if it doesn't exist
    html_cov_dir = root_dir / "htmlcov"
    if not html_cov_dir.exists():
        os.makedirs(html_cov_dir)
    
    # Build the pytest command with coverage
    cmd = [
        "pytest",
        "-xvs",  # Show output, verbose, stop on first error
        "--cov=app",  # Coverage for the app package
        "--cov-report=term",  # Terminal coverage report
        "--cov-report=html",  # HTML coverage report
        "tests/"  # Test directory
    ]
    
    try:
        # Run pytest with the specified options
        result = subprocess.run(cmd, check=False)
        
        # Report results
        if result.returncode == 0:
            print("\n✅ All tests passed successfully!")
        else:
            print(f"\n❌ Tests failed with return code: {result.returncode}")
        
        # Open the HTML coverage report in a browser
        if os.path.exists("htmlcov/index.html"):
            print("\nOpening coverage report in browser...")
            try:
                webbrowser.open("htmlcov/index.html")
            except webbrowser.Error:
                print("Could not open browser automatically. Coverage report is available at: htmlcov/index.html")
        
        return result.returncode
        
    except Exception as e:
        print(f"\n❌ Error running tests: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests()) 