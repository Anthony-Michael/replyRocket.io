#!/usr/bin/env python
"""
Generate a test coverage report for the ReplyRocket.io application.

This script runs pytest with coverage options and generates a detailed
report showing which areas of the codebase need more test coverage.

Usage:
    python -m tests.generate_coverage_report
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime
import argparse


def run_coverage(output_to_console=True, specific_tests=None):
    """Run pytest with coverage and generate reports.
    
    Args:
        output_to_console: Whether to print test output to console
        specific_tests: Optional list of specific test files/modules to run
        
    Returns:
        Path to the generated JSON coverage report
    """
    print("Running tests with coverage...")
    
    # Create reports directory if it doesn't exist
    reports_dir = Path("./reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Create html reports directory if it doesn't exist
    html_reports_dir = reports_dir / "html"
    html_reports_dir.mkdir(exist_ok=True)
    
    # Get timestamp for report names
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Basic command with coverage options
    cmd = [
        "pytest",
        "--cov=app",
        "--cov-report=term-missing",
        f"--cov-report=html:./reports/html/coverage_{timestamp}",
        f"--cov-report=json:./reports/coverage_{timestamp}.json",
    ]
    
    # Add specific test targets if provided
    if specific_tests:
        cmd.extend(specific_tests)
    else:
        cmd.append("tests/")
    
    # Run pytest with coverage
    if output_to_console:
        # Display output in real-time
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print("Warning: Tests failed with return code", result.returncode)
    else:
        # Capture output
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Errors:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
    
    # Return the latest json report filename
    return f"./reports/coverage_{timestamp}.json"


def analyze_coverage(report_file):
    """Analyze coverage data and print summary.
    
    Args:
        report_file: Path to the JSON coverage report
    """
    if not os.path.exists(report_file):
        print(f"Error: Coverage report file {report_file} not found!")
        return
    
    with open(report_file, 'r') as f:
        coverage_data = json.load(f)
    
    total_coverage = coverage_data["totals"]["percent_covered"]
    total_statements = coverage_data["totals"]["num_statements"]
    covered_statements = coverage_data["totals"]["covered_lines"]
    
    print("\n" + "=" * 80)
    print(f"COVERAGE SUMMARY: {total_coverage:.2f}% covered")
    print(f"  {covered_statements} of {total_statements} statements covered")
    print("=" * 80)
    
    # Group files by module
    modules = {}
    for file_path, data in coverage_data["files"].items():
        # Extract module name (first part of the path after 'app/')
        parts = file_path.split('/')
        if len(parts) >= 2 and parts[0] == 'app':
            module = parts[1] if len(parts) > 2 else 'root'
            if module not in modules:
                modules[module] = {
                    "files": [],
                    "total_statements": 0,
                    "covered_statements": 0
                }
            
            file_info = {
                "path": file_path,
                "coverage": data["summary"]["percent_covered"],
                "missing_lines": data["missing_lines"],
                "total_lines": data["summary"]["num_statements"],
                "covered_lines": data["summary"]["covered_lines"]
            }
            
            modules[module]["files"].append(file_info)
            modules[module]["total_statements"] += file_info["total_lines"]
            modules[module]["covered_statements"] += file_info["covered_lines"]
    
    # Calculate module coverage percentages
    for module, info in modules.items():
        if info["total_statements"] > 0:
            info["coverage"] = (info["covered_statements"] / info["total_statements"]) * 100
        else:
            info["coverage"] = 0
    
    # Print module coverage breakdown
    print("\nMODULE COVERAGE:")
    print("-" * 80)
    
    # Sort modules by coverage
    sorted_modules = sorted(modules.items(), key=lambda x: x[1]["coverage"])
    
    for module, info in sorted_modules:
        print(f"{module}: {info['coverage']:.2f}% covered ({info['covered_statements']}/{info['total_statements']} statements)")
    
    # Print files with less than 100% coverage
    print("\nFILES NEEDING MORE TEST COVERAGE:")
    print("-" * 80)
    
    # Sort all files by coverage percentage
    file_reports = []
    for file_path, data in coverage_data["files"].items():
        if data["summary"]["percent_covered"] < 100:
            file_reports.append({
                "path": file_path,
                "coverage": data["summary"]["percent_covered"],
                "missing_lines": data["missing_lines"],
                "total_lines": data["summary"]["num_statements"]
            })
    
    file_reports.sort(key=lambda x: x["coverage"])
    
    for report in file_reports:
        print(f"{report['path']}: {report['coverage']:.2f}% covered")
        print(f"  Missing {len(report['missing_lines'])} of {report['total_lines']} lines")
        
        # Group consecutive missing lines
        if report['missing_lines']:
            groups = []
            current_group = [report['missing_lines'][0]]
            
            for line in report['missing_lines'][1:]:
                if line == current_group[-1] + 1:
                    current_group.append(line)
                else:
                    groups.append(current_group)
                    current_group = [line]
            
            groups.append(current_group)
            
            # Print grouped missing lines
            print("  Missing lines:", end=" ")
            for i, group in enumerate(groups):
                if len(group) == 1:
                    print(f"{group[0]}", end="")
                else:
                    print(f"{group[0]}-{group[-1]}", end="")
                
                if i < len(groups) - 1:
                    print(", ", end="")
            print()
        
        print()
    
    print("=" * 80)
    print("RECOMMENDATIONS:")
    
    # Overall coverage assessment
    if total_coverage < 70:
        print("- Overall coverage is below 70%. Focus on adding more tests.")
    elif total_coverage < 80:
        print("- Overall coverage is below 80%. Consider adding more tests to reach at least 80%.")
    elif total_coverage < 90:
        print("- Overall coverage is good but could be improved to reach 90%+.")
    else:
        print("- Overall coverage is excellent (90%+). Focus on covering the remaining edge cases.")
    
    # Identify critical modules with low coverage
    critical_modules = ['services', 'api', 'core']
    for module in critical_modules:
        if module in modules and modules[module]["coverage"] < 80:
            print(f"- The '{module}' module has low coverage ({modules[module]['coverage']:.2f}%). This is a critical module that should have high test coverage.")
    
    # Identify critical areas with low coverage
    critical_services = [r for r in file_reports if "services" in r["path"] and r["coverage"] < 80]
    if critical_services:
        print("- Critical service modules need more tests:")
        for service in critical_services:
            print(f"  * {service['path']}: {service['coverage']:.2f}%")
    
    # Identify endpoints with low coverage
    endpoint_files = [r for r in file_reports if "endpoints" in r["path"] and r["coverage"] < 80]
    if endpoint_files:
        print("- API endpoints need more integration tests:")
        for endpoint in endpoint_files:
            print(f"  * {endpoint['path']}: {endpoint['coverage']:.2f}%")
    
    # Core modules that should have high coverage
    core_files = [r for r in file_reports if "core" in r["path"] and r["coverage"] < 90]
    if core_files:
        print("- Core modules should have very high test coverage:")
        for core_file in core_files:
            print(f"  * {core_file['path']}: {core_file['coverage']:.2f}%")
    
    # Get timestamp from filename
    timestamp = report_file.split("_")[-1].replace(".json", "")
    print("\nHTML report generated at:", os.path.abspath(f"./reports/html/coverage_{timestamp}/index.html"))
    print("=" * 80)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Generate test coverage report for ReplyRocket.io")
    parser.add_argument("--quiet", action="store_true", help="Don't output test results to console")
    parser.add_argument("--tests", nargs="+", help="Specific test files or modules to run")
    args = parser.parse_args()
    
    # Run coverage and get report file
    report_file = run_coverage(
        output_to_console=not args.quiet,
        specific_tests=args.tests
    )
    
    # Analyze and print report
    analyze_coverage(report_file)


if __name__ == "__main__":
    main() 