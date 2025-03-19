#!/usr/bin/env python
"""
Script to run tests with coverage and generate reports.

This script runs pytest with coverage measurement and generates
both a terminal report and an HTML report for detailed analysis.
"""

import os
import sys
import subprocess
import argparse


def run_coverage(specific_tests=None, html_report=True, show_missing=True):
    """
    Run pytest with coverage and generate reports.
    
    Args:
        specific_tests: Optional list of test files/paths to run
        html_report: Whether to generate an HTML report
        show_missing: Whether to show missing lines in the report
    """
    # Ensure we're in the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    # Build command
    cmd = ["python", "-m", "pytest"]
    
    # Add coverage parameters
    cmd.extend([
        "--cov=app",
        "--cov-report=term",
    ])
    
    if html_report:
        cmd.append("--cov-report=html")
    
    if show_missing:
        cmd.append("--cov-report=term-missing")
    
    # Add specific tests if provided
    if specific_tests:
        cmd.extend(specific_tests)
    else:
        cmd.append("tests/")
    
    # Print the command for visibility
    print(f"Running: {' '.join(cmd)}")
    
    # Run the command
    result = subprocess.run(cmd, capture_output=False)
    
    # Print output location of HTML report
    if html_report and result.returncode == 0:
        html_dir = os.path.join(project_root, "htmlcov")
        print(f"\nHTML coverage report is available at: {html_dir}")
        print(f"Open {os.path.join(html_dir, 'index.html')} in your browser to view it.\n")
    
    return result.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run tests with coverage and generate reports")
    parser.add_argument(
        "tests", 
        nargs="*", 
        help="Specific test files or directories to run (default: all tests)"
    )
    parser.add_argument(
        "--no-html", 
        action="store_true", 
        help="Don't generate HTML report"
    )
    parser.add_argument(
        "--no-missing", 
        action="store_true", 
        help="Don't show missing lines in coverage"
    )
    
    args = parser.parse_args()
    
    # Run tests with coverage
    exit_code = run_coverage(
        specific_tests=args.tests if args.tests else None,
        html_report=not args.no_html,
        show_missing=not args.no_missing
    )
    
    # Exit with the same code as pytest
    sys.exit(exit_code) 