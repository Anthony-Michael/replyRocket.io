"""
Test coverage report generator for ReplyRocket.io.

This module analyzes test coverage data to identify untested functions
and provides a detailed report on coverage gaps.
"""

import os
import sys
import json
import importlib
import inspect
import re
import subprocess
from typing import Dict, List, Set, Tuple, Any, Optional
from pathlib import Path

# Constants
APP_DIR = "app"
COVERAGE_DIR = ".coverage"
COVERAGE_FILE = "coverage.json"
REPORT_FILE = "coverage_gaps.md"


def run_coverage_json() -> None:
    """Run pytest with coverage and output JSON coverage data."""
    # Ensure we're in the project root
    if not os.path.exists(APP_DIR):
        print(f"Error: This script must be run from the project root containing '{APP_DIR}'")
        sys.exit(1)
    
    # First, run tests with coverage
    print("Running tests with coverage...")
    cmd = [
        "pytest",
        "--cov=" + APP_DIR,
        "--cov-report=json",
        "tests/"
    ]
    result = subprocess.run(cmd, check=False, capture_output=True)
    
    if result.returncode != 0:
        print("Warning: Some tests failed, but proceeding with coverage analysis")
    
    # Check that coverage data was generated
    if not os.path.exists(COVERAGE_FILE):
        print(f"Error: Could not generate coverage data. Ensure pytest-cov is installed.")
        sys.exit(1)


def load_coverage_data() -> Dict[str, Any]:
    """Load JSON coverage data from the coverage file."""
    try:
        with open(COVERAGE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading coverage data: {str(e)}")
        sys.exit(1)


def extract_covered_functions(coverage_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Extract covered functions from coverage data.
    
    Returns:
        Dictionary mapping module paths to lists of covered function names
    """
    covered_functions = {}
    
    for file_path, file_data in coverage_data['files'].items():
        if not file_path.startswith(APP_DIR):
            continue
        
        # Convert to Python module path
        module_path = file_path.replace('/', '.').replace('\\', '.')
        if module_path.endswith('.py'):
            module_path = module_path[:-3]
        
        # Find covered line numbers
        covered_lines = set()
        for line_num, execution_count in enumerate(file_data['executed_lines']):
            if execution_count > 0:
                covered_lines.add(file_data['executed_lines'][line_num])
        
        # Read the file to extract function definitions
        module_functions = extract_functions_from_file(file_path, covered_lines)
        covered_functions[file_path] = module_functions
    
    return covered_functions


def extract_functions_from_file(file_path: str, covered_lines: Set[int]) -> List[str]:
    """
    Extract functions and their coverage status from a Python file.
    
    Args:
        file_path: Path to the Python file
        covered_lines: Set of line numbers that were covered by tests
    
    Returns:
        List of covered function names
    """
    covered_functions = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.readlines()
        
        # Find function definitions
        function_pattern = re.compile(r'^\s*def\s+([a-zA-Z0-9_]+)\s*\(')
        for i, line in enumerate(source):
            match = function_pattern.match(line)
            if match:
                function_name = match.group(1)
                if i + 1 in covered_lines:  # Function is covered if first line is covered
                    covered_functions.append(function_name)
    
    except Exception as e:
        print(f"Error processing file {file_path}: {str(e)}")
    
    return covered_functions


def get_all_functions(directory: str = APP_DIR) -> Dict[str, List[str]]:
    """
    Get all functions defined in the app directory.
    
    Returns:
        Dictionary mapping module paths to lists of all function names
    """
    all_functions = {}
    
    # Walk through all Python files in the app directory
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path)
                
                # Extract functions using AST
                function_names = extract_all_functions_from_file(file_path)
                if function_names:
                    all_functions[rel_path] = function_names
    
    return all_functions


def extract_all_functions_from_file(file_path: str) -> List[str]:
    """
    Extract all function names from a Python file using regex.
    
    Args:
        file_path: Path to the Python file
    
    Returns:
        List of all function names
    """
    functions = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Find function definitions, excluding ones in classes or nested functions
        pattern = r'(?:^|\n)\s*def\s+([a-zA-Z0-9_]+)\s*\('
        matches = re.finditer(pattern, source)
        for match in matches:
            functions.append(match.group(1))
        
    except Exception as e:
        print(f"Error reading {file_path}: {str(e)}")
    
    return functions


def calculate_coverage_gap(
    all_functions: Dict[str, List[str]], 
    covered_functions: Dict[str, List[str]]
) -> Dict[str, List[str]]:
    """
    Calculate which functions are not covered by tests.
    
    Args:
        all_functions: Dictionary mapping file paths to all function names
        covered_functions: Dictionary mapping file paths to covered function names
    
    Returns:
        Dictionary mapping file paths to uncovered function names
    """
    uncovered_functions = {}
    
    for file_path, functions in all_functions.items():
        file_covered_functions = covered_functions.get(file_path, [])
        uncovered = [f for f in functions if f not in file_covered_functions]
        
        if uncovered:
            uncovered_functions[file_path] = uncovered
    
    return uncovered_functions


def generate_report(
    uncovered_functions: Dict[str, List[str]], 
    all_functions: Dict[str, List[str]],
    output_file: str = REPORT_FILE
) -> None:
    """
    Generate a markdown report of uncovered functions.
    
    Args:
        uncovered_functions: Dictionary mapping file paths to uncovered function names
        all_functions: Dictionary mapping file paths to all function names
        output_file: Path to the output report file
    """
    # Calculate coverage statistics
    total_files = len(all_functions)
    total_functions = sum(len(functions) for functions in all_functions.values())
    uncovered_files = len(uncovered_functions)
    uncovered_function_count = sum(len(functions) for functions in uncovered_functions.values())
    
    file_coverage_pct = (total_files - uncovered_files) / total_files * 100 if total_files > 0 else 0
    function_coverage_pct = (total_functions - uncovered_function_count) / total_functions * 100 if total_functions > 0 else 0
    
    # Generate the report
    with open(output_file, 'w') as report:
        report.write("# ReplyRocket.io Test Coverage Report\n\n")
        
        # Summary
        report.write("## Coverage Summary\n\n")
        report.write(f"- **Files**: {total_files - uncovered_files}/{total_files} ({file_coverage_pct:.1f}% covered)\n")
        report.write(f"- **Functions**: {total_functions - uncovered_function_count}/{total_functions} ({function_coverage_pct:.1f}% covered)\n\n")
        
        # Uncovered functions by module
        report.write("## Uncovered Functions by Module\n\n")
        
        if not uncovered_functions:
            report.write("All functions are covered by tests! 🎉\n\n")
        else:
            # Sort modules by coverage percentage (ascending)
            sorted_modules = sorted(
                uncovered_functions.items(),
                key=lambda x: len(x[1]) / len(all_functions[x[0]]) if x[0] in all_functions else 0,
                reverse=True
            )
            
            for file_path, functions in sorted_modules:
                all_count = len(all_functions[file_path]) if file_path in all_functions else 0
                covered_count = all_count - len(functions)
                coverage_pct = covered_count / all_count * 100 if all_count > 0 else 0
                
                report.write(f"### {file_path} ({coverage_pct:.1f}% covered)\n\n")
                report.write("The following functions need test coverage:\n\n")
                for function in sorted(functions):
                    report.write(f"- `{function}()`\n")
                report.write("\n")
        
        # Recommendations
        report.write("## Recommendations\n\n")
        report.write("To improve test coverage, focus on the following areas:\n\n")
        
        if uncovered_functions:
            # Find modules with lowest coverage
            priority_modules = sorted(
                uncovered_functions.items(),
                key=lambda x: len(x[1]) / len(all_functions[x[0]]) if x[0] in all_functions else 0,
                reverse=True
            )[:5]  # Top 5 modules with lowest coverage
            
            for file_path, functions in priority_modules:
                all_count = len(all_functions[file_path]) if file_path in all_functions else 0
                covered_count = all_count - len(functions)
                coverage_pct = covered_count / all_count * 100 if all_count > 0 else 0
                
                report.write(f"1. **{file_path}** ({coverage_pct:.1f}% covered): Focus on testing critical functions like ")
                report.write(", ".join([f"`{f}()`" for f in functions[:3]]))
                if len(functions) > 3:
                    report.write(f" and {len(functions) - 3} others")
                report.write(".\n")
        else:
            report.write("- Maintain current coverage as new features are developed\n")
            report.write("- Consider adding more edge case tests\n")
        
        # Report generation timestamp
        from datetime import datetime
        report.write(f"\n\n*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    
    print(f"Coverage report generated: {output_file}")


def main() -> None:
    """Main entry point for the coverage gap analyzer."""
    print("ReplyRocket.io Test Coverage Analyzer")
    print("====================================")
    
    # Run tests with coverage
    run_coverage_json()
    
    # Load coverage data
    coverage_data = load_coverage_data()
    
    # Extract covered functions
    covered_functions = extract_covered_functions(coverage_data)
    
    # Get all functions in the app directory
    all_functions = get_all_functions()
    
    # Calculate coverage gap
    uncovered_functions = calculate_coverage_gap(all_functions, covered_functions)
    
    # Generate report
    generate_report(uncovered_functions, all_functions)
    
    # Cleanup coverage file
    if os.path.exists(COVERAGE_FILE):
        os.remove(COVERAGE_FILE)


if __name__ == "__main__":
    main() 