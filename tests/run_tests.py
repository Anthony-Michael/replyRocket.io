#!/usr/bin/env python
"""
Test runner script for ReplyRocket.io.

This script provides a convenient way to run different types of tests
and generate coverage reports for the ReplyRocket.io application.

Usage:
    python -m tests.run_tests [options]
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def setup_environment():
    """Set up the environment for testing."""
    # Ensure we're using the test environment
    os.environ["ENVIRONMENT"] = "test"
    os.environ["TESTING"] = "True"
    
    # Disable OpenAI API calls during tests
    os.environ["OPENAI_API_KEY"] = "test_key"


def run_unit_tests(args):
    """Run unit tests."""
    print("Running unit tests...")
    
    cmd = ["pytest"]
    
    # Add verbosity if requested
    if args.verbose:
        cmd.append("-v")
    
    # Add modules to test
    if args.modules:
        for module in args.modules:
            if module == "services":
                cmd.append("tests/test_*_service.py")
            elif module == "api":
                cmd.append("tests/test_*_endpoints.py")
            elif module == "core":
                cmd.append("tests/test_auth.py")
                cmd.append("tests/test_error_handling.py")
            else:
                cmd.append(f"tests/test_{module}.py")
    else:
        # Find test files that include 'service' in the name
        test_files = []
        for path in Path("tests").glob("test_*_service.py"):
            test_files.append(str(path))
        
        if test_files:
            cmd.extend(test_files)
        else:
            cmd.append("tests/")
    
    # Run tests
    result = subprocess.run(cmd)
    return result.returncode


def run_integration_tests(args):
    """Run integration tests."""
    print("Running integration tests...")
    
    cmd = ["pytest"]
    
    # Add verbosity if requested
    if args.verbose:
        cmd.append("-v")
    
    # Find test files that include 'endpoints' in the name
    test_files = []
    for path in Path("tests").glob("test_*_endpoints.py"):
        test_files.append(str(path))
    
    if test_files:
        cmd.extend(test_files)
    else:
        print("No integration tests found.")
        return 0
    
    # Run tests
    result = subprocess.run(cmd)
    return result.returncode


def run_specific_tests(args):
    """Run specific tests specified by pattern."""
    print(f"Running tests matching pattern: {args.pattern}")
    
    cmd = ["pytest", "-k", args.pattern]
    
    # Add verbosity if requested
    if args.verbose:
        cmd.append("-v")
    
    # Run tests
    result = subprocess.run(cmd)
    return result.returncode


def run_coverage(args):
    """Run test coverage report."""
    print("Running test coverage report...")
    
    cmd = ["python", "-m", "tests.generate_coverage_report"]
    
    # Add quiet mode if not verbose
    if not args.verbose:
        cmd.append("--quiet")
    
    # Add specific tests to run
    if args.modules:
        test_files = []
        for module in args.modules:
            if module == "services":
                for path in Path("tests").glob("test_*_service.py"):
                    test_files.append(str(path))
            elif module == "api":
                for path in Path("tests").glob("test_*_endpoints.py"):
                    test_files.append(str(path))
            else:
                test_files.append(f"tests/test_{module}.py")
        
        if test_files:
            cmd.append("--tests")
            cmd.extend(test_files)
    
    # Run coverage report
    result = subprocess.run(cmd)
    return result.returncode


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Run tests for ReplyRocket.io")
    
    # Test type
    test_type = parser.add_mutually_exclusive_group()
    test_type.add_argument("--unit", action="store_true", help="Run unit tests only")
    test_type.add_argument("--integration", action="store_true", help="Run integration tests only")
    test_type.add_argument("--coverage", action="store_true", help="Run tests with coverage report")
    test_type.add_argument("--pattern", type=str, help="Run tests matching the specified pattern")
    
    # Options
    parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity")
    parser.add_argument("--modules", nargs="+", help="Specific modules to test (e.g., services, api)")
    
    args = parser.parse_args()
    
    # Set up the environment
    setup_environment()
    
    # Run the appropriate test type
    if args.unit:
        return run_unit_tests(args)
    elif args.integration:
        return run_integration_tests(args)
    elif args.pattern:
        return run_specific_tests(args)
    elif args.coverage:
        return run_coverage(args)
    else:
        # Default action: run all tests
        print("Running all tests...")
        result = subprocess.run(["pytest", "-v" if args.verbose else ""])
        return result.returncode


if __name__ == "__main__":
    sys.exit(main()) 