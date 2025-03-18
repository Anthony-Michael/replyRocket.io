#!/usr/bin/env python
"""
Test runner for ReplyRocket.io tests.

This script runs the test suite with coverage reporting and provides a summary of the results.
"""

import os
import sys
import argparse
import subprocess
import webbrowser
from pathlib import Path


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run ReplyRocket.io tests with coverage reporting")
    
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--stress", action="store_true", help="Run stress tests")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--no-browser", action="store_true", help="Don't open coverage report in browser")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--threshold", type=int, default=80, help="Coverage threshold percentage (default: 80)")
    parser.add_argument("--gap-analysis", action="store_true", help="Generate a detailed coverage gap analysis")
    
    return parser.parse_args()


def run_tests(args):
    """Run the test suite with coverage reporting based on command line arguments."""
    print("\n========== Running ReplyRocket.io Tests ==========\n")
    
    # Get the absolute path to the project root directory
    root_dir = Path(__file__).parent.absolute()
    
    # Create a directory for coverage reports if it doesn't exist
    html_cov_dir = root_dir / "htmlcov"
    if not html_cov_dir.exists():
        os.makedirs(html_cov_dir)
    
    # Check if we should just run the gap analysis
    if args.gap_analysis and not any([args.unit, args.integration, args.stress, args.all]):
        return run_coverage_gap_analysis()
    
    # Determine which tests to run
    if not any([args.unit, args.integration, args.stress, args.all]):
        args.all = True  # Default to running all tests
    
    # Build the pytest base command
    base_cmd = ["pytest"]
    if args.verbose:
        base_cmd.append("-v")
    
    # Track overall test success
    all_tests_passed = True
    
    # Run unit tests if requested
    if args.unit or args.all:
        print("\n----- Running Unit Tests -----\n")
        unit_cmd = base_cmd.copy()
        unit_cmd.append("-m")
        unit_cmd.append("unit")
        
        if args.coverage:
            unit_cmd.extend([
                "--cov=app",
                "--cov-report=term",
                "--cov-report=html"
            ])
        
        result = subprocess.run(unit_cmd, check=False)
        if result.returncode != 0:
            all_tests_passed = False
    
    # Run integration tests if requested
    if args.integration or args.all:
        print("\n----- Running Integration Tests -----\n")
        integration_cmd = base_cmd.copy()
        integration_cmd.append("-m")
        integration_cmd.append("integration")
        
        if args.coverage:
            integration_cmd.extend([
                "--cov=app",
                "--cov-append",
                "--cov-report=term",
                "--cov-report=html"
            ])
        
        result = subprocess.run(integration_cmd, check=False)
        if result.returncode != 0:
            all_tests_passed = False
    
    # Run stress tests if requested
    if args.stress:
        print("\n----- Running Stress Tests -----\n")
        stress_cmd = base_cmd.copy()
        stress_cmd.append("-m")
        stress_cmd.append("stress")
        
        result = subprocess.run(stress_cmd, check=False)
        if result.returncode != 0:
            all_tests_passed = False
    
    # Check coverage threshold if coverage is enabled
    if args.coverage and (args.unit or args.integration or args.all):
        print("\n----- Checking Coverage Threshold -----\n")
        threshold_cmd = ["coverage", "report", f"--fail-under={args.threshold}"]
        result = subprocess.run(threshold_cmd, check=False)
        if result.returncode != 0:
            print(f"\n❌ Coverage is below the threshold of {args.threshold}%")
            all_tests_passed = False
        else:
            print(f"\n✅ Coverage meets the threshold of {args.threshold}%")
        
        # Open the HTML coverage report in a browser
        if not args.no_browser and os.path.exists("htmlcov/index.html"):
            print("\nOpening coverage report in browser...")
            try:
                webbrowser.open("htmlcov/index.html")
            except webbrowser.Error:
                print("Could not open browser automatically. Coverage report is available at: htmlcov/index.html")
    
    # Run gap analysis if requested
    if args.gap_analysis:
        gap_analysis_result = run_coverage_gap_analysis()
        if gap_analysis_result != 0:
            all_tests_passed = False
    
    # Report overall results
    if all_tests_passed:
        print("\n✅ All tests passed successfully!")
    else:
        print("\n❌ Some tests failed")
    
    return 0 if all_tests_passed else 1


def run_coverage_gap_analysis():
    """Run the coverage gap analysis script."""
    print("\n----- Running Coverage Gap Analysis -----\n")
    
    try:
        # Run the gap analysis script
        result = subprocess.run([sys.executable, "tests/test_coverage_report.py"], check=False)
        
        # Open the report if it was generated
        if result.returncode == 0 and os.path.exists("coverage_gaps.md"):
            print("\nCoverage gap analysis completed successfully.")
            
            # Convert to HTML for better viewing
            try:
                from markdown import markdown
                with open("coverage_gaps.md", "r") as md_file:
                    md_content = md_file.read()
                
                html_content = f"""<!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>ReplyRocket.io Coverage Gap Analysis</title>
                    <style>
                        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; line-height: 1.5; }}
                        pre {{ background-color: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; }}
                        code {{ background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px; }}
                        h1, h2, h3 {{ margin-top: 30px; }}
                        table {{ border-collapse: collapse; width: 100%; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                        th {{ background-color: #f2f2f2; }}
                    </style>
                </head>
                <body>
                    {markdown(md_content)}
                </body>
                </html>"""
                
                with open("coverage_gaps.html", "w") as html_file:
                    html_file.write(html_content)
                
                print("Opening coverage gap report in browser...")
                webbrowser.open("coverage_gaps.html")
            except ImportError:
                print("The 'markdown' package is not installed. Viewing the raw markdown file.")
                # Open the markdown file directly
                try:
                    if sys.platform.startswith('darwin'):  # macOS
                        subprocess.run(['open', 'coverage_gaps.md'])
                    elif sys.platform.startswith('win'):  # Windows
                        os.startfile('coverage_gaps.md')
                    else:  # Linux
                        subprocess.run(['xdg-open', 'coverage_gaps.md'])
                except Exception:
                    print("Could not open the report automatically. Report is available at: coverage_gaps.md")
        else:
            print("\n❌ Failed to generate coverage gap analysis.")
            return 1
        
        return result.returncode
    except Exception as e:
        print(f"Error running coverage gap analysis: {str(e)}")
        return 1


if __name__ == "__main__":
    args = parse_args()
    sys.exit(run_tests(args)) 