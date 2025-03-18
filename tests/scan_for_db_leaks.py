"""
Scan the codebase for potential database session leaks.

This script analyzes the codebase to identify places where database sessions might not be
properly closed or where try-finally blocks might be missing.
"""

import os
import re
import sys
import argparse
from typing import Dict, List, Set, Tuple
import ast
import astor


class DatabaseSessionVisitor(ast.NodeVisitor):
    """AST visitor that identifies database session usage patterns."""
    
    def __init__(self):
        self.session_vars = set()
        self.properly_closed_sessions = set()
        self.session_creation_lines = {}
        self.potential_leaks = []
        self.context_manager_usage = []
        self.current_function = None
        self.current_class = None
        self.current_file = ""
    
    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        old_function = self.current_function
        self.current_function = node.name
        # Look for function parameters that might be database sessions
        for arg in node.args.args:
            arg_name = getattr(arg, 'arg', None)
            arg_annotation = getattr(arg, 'annotation', None)
            
            # Check if parameter is annotated as Session
            if arg_annotation and isinstance(arg_annotation, ast.Name) and arg_annotation.id == 'Session':
                # Function has a db session parameter, which is good practice
                pass
        
        self.generic_visit(node)
        self.current_function = old_function
    
    def visit_ClassDef(self, node):
        """Visit class definitions."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_Assign(self, node):
        """Visit assignments to detect session creation."""
        self.generic_visit(node)
        
        # Check for session creation
        if isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Name) and func.id == 'SessionLocal':
                # Found a session creation
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.session_vars.add(target.id)
                        self.session_creation_lines[target.id] = node.lineno
    
    def visit_With(self, node):
        """Visit with statements to detect context manager usage."""
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                func = item.context_expr.func
                # Check for SessionLocal() or SessionManager()
                if (isinstance(func, ast.Name) and func.id in ['SessionLocal', 'SessionManager']):
                    # Found proper usage with context manager
                    var_name = None
                    if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                        var_name = item.optional_vars.id
                    
                    self.context_manager_usage.append({
                        "line": node.lineno,
                        "var_name": var_name,
                        "context": f"{self.current_class}.{self.current_function}" if self.current_class else self.current_function
                    })
        
        self.generic_visit(node)
    
    def visit_Try(self, node):
        """Visit try blocks to detect session cleanup in finally."""
        self.generic_visit(node)
        
        # Check for sessions being closed in finally block
        if node.finalbody:
            for stmt in node.finalbody:
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                    call = stmt.value
                    if isinstance(call.func, ast.Attribute):
                        if call.func.attr == 'close' and isinstance(call.func.value, ast.Name):
                            session_var = call.func.value.id
                            if session_var in self.session_vars:
                                self.properly_closed_sessions.add(session_var)
                
                # Check for multi-statement or nested expressions in finally
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                    # This is a direct call expression
                    pass
                elif isinstance(stmt, ast.If) or isinstance(stmt, ast.For) or isinstance(stmt, ast.While):
                    # Complex finally block - would need deeper analysis
                    pass


def scan_file(file_path: str) -> Dict:
    """Scan a Python file for database session usage patterns."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content, filename=file_path)
    except SyntaxError as e:
        return {
            "error": f"Syntax error in {file_path}: {str(e)}",
            "session_creations": [],
            "context_managers": [],
            "potential_leaks": []
        }
    
    visitor = DatabaseSessionVisitor()
    visitor.current_file = file_path
    visitor.visit(tree)
    
    # Find potential leaks (sessions created but not properly closed)
    potential_leaks = []
    for session_var in visitor.session_vars:
        if session_var not in visitor.properly_closed_sessions:
            potential_leaks.append({
                "var_name": session_var,
                "line": visitor.session_creation_lines.get(session_var, "unknown"),
                "file": file_path
            })
    
    # Manual regex check for raw SessionLocal() usage 
    session_direct_uses = []
    direct_session_pattern = r'(\w+)\s*=\s*SessionLocal\(\)'
    for match in re.finditer(direct_session_pattern, content):
        session_var = match.group(1)
        line_no = content[:match.start()].count('\n') + 1
        session_direct_uses.append({
            "var_name": session_var,
            "line": line_no,
            "file": file_path
        })
    
    # Check for try-finally patterns manually
    try_finally_blocks = []
    try_finally_pattern = r'try:(?:[^#](?!finally))*?(\w+)\s*=\s*SessionLocal\(\)(?:[^#](?!finally))*?finally:(?:[^#])*?(\1)\.close\(\)'
    for match in re.finditer(try_finally_pattern, content, re.DOTALL):
        session_var = match.group(1)
        line_no = content[:match.start()].count('\n') + 1
        try_finally_blocks.append({
            "var_name": session_var,
            "line": line_no,
            "file": file_path
        })
    
    return {
        "file": file_path,
        "session_creations": [
            {"var_name": var, "line": visitor.session_creation_lines.get(var, "unknown")} 
            for var in visitor.session_vars
        ],
        "context_managers": visitor.context_manager_usage,
        "potential_leaks": potential_leaks,
        "direct_uses": session_direct_uses,
        "try_finally_blocks": try_finally_blocks
    }


def scan_directory(directory: str, file_pattern: str = r'\.py$') -> List[Dict]:
    """Scan a directory recursively for Python files with database session usage."""
    results = []
    
    pattern = re.compile(file_pattern)
    for root, _, files in os.walk(directory):
        for file in files:
            if pattern.search(file):
                file_path = os.path.join(root, file)
                result = scan_file(file_path)
                if result.get("session_creations") or result.get("context_managers") or result.get("potential_leaks"):
                    results.append(result)
    
    return results


def print_scan_results(results: List[Dict]) -> None:
    """Print scan results in a formatted way."""
    total_files = len(results)
    total_sessions = sum(len(r.get("session_creations", [])) for r in results)
    total_context_managers = sum(len(r.get("context_managers", [])) for r in results)
    total_potential_leaks = sum(len(r.get("potential_leaks", [])) for r in results)
    
    print(f"\n=== DATABASE SESSION USAGE SCAN RESULTS ===")
    print(f"Scanned {total_files} files")
    print(f"Found {total_sessions} session creations")
    print(f"Found {total_context_managers} context manager usages")
    print(f"Found {total_potential_leaks} potential session leaks")
    print("=" * 50)
    
    if total_potential_leaks > 0:
        print("\nPOTENTIAL SESSION LEAKS:")
        print("-" * 50)
        for result in results:
            for leak in result.get("potential_leaks", []):
                print(f"File: {leak['file']}")
                print(f"Line: {leak['line']}")
                print(f"Variable: {leak['var_name']}")
                print("-" * 30)
    
    print("\nSESSION USAGE PATTERNS:")
    print("-" * 50)
    
    context_manager_count = 0
    try_finally_count = 0
    direct_use_count = 0
    
    for result in results:
        context_manager_count += len(result.get("context_managers", []))
        try_finally_count += len(result.get("try_finally_blocks", []))
        direct_use_count += len(result.get("direct_uses", []))
    
    print(f"Context manager usage: {context_manager_count}")
    print(f"Try-finally blocks: {try_finally_count}")
    print(f"Direct session uses: {direct_use_count}")
    
    # Files with most session usage
    file_usage = {}
    for result in results:
        file_path = result.get("file", "")
        usage_count = len(result.get("session_creations", [])) + len(result.get("context_managers", []))
        file_usage[file_path] = usage_count
    
    if file_usage:
        print("\nFILES WITH MOST DB SESSION USAGE:")
        print("-" * 50)
        sorted_files = sorted(file_usage.items(), key=lambda x: x[1], reverse=True)
        for file_path, count in sorted_files[:10]:  # Top 10
            if count > 0:
                print(f"{file_path}: {count} usages")


def main():
    """Run the database session leak scanner."""
    parser = argparse.ArgumentParser(description="Scan for potential database session leaks")
    parser.add_argument("--dir", type=str, default="app", help="Directory to scan")
    parser.add_argument("--pattern", type=str, default=r'\.py$', help="File pattern to match")
    args = parser.parse_args()
    
    print(f"Scanning directory: {args.dir}")
    results = scan_directory(args.dir, args.pattern)
    print_scan_results(results)


if __name__ == "__main__":
    main() 