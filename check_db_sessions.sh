#!/bin/bash

# Database Session Checker for ReplyRocket.io
# This script helps maintain proper database session handling by running
# various tools to check for issues and test performance.

set -e  # Exit on error

# Colors for better output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================${NC}"
echo -e "${BLUE}ReplyRocket.io DB Session Checker${NC}"
echo -e "${BLUE}=================================${NC}\n"

# Function to check if Python is installed
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is not installed or not in PATH${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Python 3 is installed${NC}"
}

# Function to check requirements
check_requirements() {
    echo -e "\n${BLUE}Checking dependencies...${NC}"
    
    REQUIRED_PACKAGES=("pytest" "coverage" "pytest-cov" "astor")
    MISSING_PACKAGES=()
    
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if ! python3 -c "import $package" 2>/dev/null; then
            MISSING_PACKAGES+=("$package")
        fi
    done
    
    if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
        echo -e "${YELLOW}Missing required packages: ${MISSING_PACKAGES[*]}${NC}"
        read -p "Install missing packages? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 -m pip install "${MISSING_PACKAGES[@]}"
        else
            echo -e "${YELLOW}Please install the required packages manually and run again.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✓ All required packages are installed${NC}"
    fi
}

# Function to run the session leak scanner
run_leak_scanner() {
    echo -e "\n${BLUE}Running database session leak scanner...${NC}"
    
    # Check if the scanner script exists
    if [ ! -f "tests/scan_for_db_leaks.py" ]; then
        echo -e "${RED}Error: Database session leak scanner not found${NC}"
        return 1
    fi
    
    # Run the scanner
    python3 tests/scan_for_db_leaks.py --dir app
    
    echo -e "\n${GREEN}✓ Session leak scan completed${NC}"
}

# Function to run performance tests
run_performance_tests() {
    echo -e "\n${BLUE}Running database performance tests...${NC}"
    
    # Check if the test script exists
    if [ ! -f "tests/test_db_performance.py" ]; then
        echo -e "${RED}Error: Database performance test script not found${NC}"
        return 1
    fi
    
    # Run the performance tests
    python3 tests/test_db_performance.py
    
    echo -e "\n${GREEN}✓ Performance tests completed${NC}"
}

# Function to scan for raw session usage
scan_raw_sessions() {
    echo -e "\n${BLUE}Scanning for raw database session usage...${NC}"
    
    # Count instances of SessionLocal direct usage without proper handling
    SESSION_DIRECT=$(grep -r "SessionLocal()" --include="*.py" app | wc -l)
    SESSION_WITH=$(grep -r "with SessionLocal" --include="*.py" app | wc -l)
    SESSION_TRY=$(grep -r -A 2 "try:" --include="*.py" app | grep -c "SessionLocal()")
    
    echo "Raw SessionLocal() usage: $SESSION_DIRECT instances"
    echo "With context manager usage: $SESSION_WITH instances"
    echo "Try-except usage: $SESSION_TRY instances"
    
    if [ "$SESSION_DIRECT" -gt 0 ]; then
        echo -e "\n${YELLOW}Files with raw SessionLocal() usage:${NC}"
        grep -r "SessionLocal()" --include="*.py" app | cut -d: -f1 | sort | uniq
    fi
    
    echo -e "\n${GREEN}✓ Raw session usage scan completed${NC}"
}

# Function to check import of get_db dependency
check_get_db_usage() {
    echo -e "\n${BLUE}Checking for get_db dependency usage...${NC}"
    
    # Count instances of get_db import and usage
    GET_DB_IMPORT=$(grep -r "from app.api.deps import get_db" --include="*.py" app | wc -l)
    GET_DB_DEPEND=$(grep -r "Depends(get_db)" --include="*.py" app | wc -l)
    
    echo "get_db imports: $GET_DB_IMPORT instances"
    echo "Depends(get_db) usage: $GET_DB_DEPEND instances"
    
    # Check for endpoints that might not use get_db
    ROUTER_FILES=$(find app -name "*.py" -exec grep -l "APIRouter" {} \;)
    MISSING_GET_DB=()
    
    for file in $ROUTER_FILES; do
        if ! grep -q "get_db" "$file"; then
            MISSING_GET_DB+=("$file")
        fi
    done
    
    if [ ${#MISSING_GET_DB[@]} -gt 0 ]; then
        echo -e "\n${YELLOW}Potential API files missing get_db dependency:${NC}"
        for file in "${MISSING_GET_DB[@]}"; do
            echo "  - $file"
        done
    else
        echo -e "\n${GREEN}✓ All API router files seem to use get_db${NC}"
    fi
}

# Function to run pytest with database session focus
run_db_tests() {
    echo -e "\n${BLUE}Running database-related tests...${NC}"
    
    # Check if any tests exist
    if ! find tests -name "test_*.py" | grep -q .; then
        echo -e "${YELLOW}No test files found${NC}"
        return 0
    fi
    
    # Run tests with database session focus
    python -m pytest tests -xvs -k "db or database or session" --no-header
    
    echo -e "\n${GREEN}✓ Database tests completed${NC}"
}

# Main function
main() {
    check_python
    check_requirements
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --all)
                scan_raw_sessions
                check_get_db_usage
                run_leak_scanner
                run_performance_tests
                run_db_tests
                exit 0
                ;;
            --leaks)
                run_leak_scanner
                exit 0
                ;;
            --performance)
                run_performance_tests
                exit 0
                ;;
            --scan)
                scan_raw_sessions
                check_get_db_usage
                exit 0
                ;;
            --tests)
                run_db_tests
                exit 0
                ;;
            --help|-h)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --all          Run all checks and tests"
                echo "  --leaks        Run only the session leak scanner"
                echo "  --performance  Run only the performance tests"
                echo "  --scan         Scan for raw session usage and get_db usage"
                echo "  --tests        Run database-related tests"
                echo "  --help, -h     Show this help message"
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                echo "Use --help for available options"
                exit 1
                ;;
        esac
    done
    
    # If no arguments provided, show menu
    echo -e "Choose an option:"
    echo "1) Run all checks and tests"
    echo "2) Scan for raw session usage and get_db dependency"
    echo "3) Run session leak scanner"
    echo "4) Run performance tests"
    echo "5) Run database-related tests"
    echo "q) Quit"
    
    read -p "Enter choice [1-5 or q]: " choice
    
    case $choice in
        1)
            scan_raw_sessions
            check_get_db_usage
            run_leak_scanner
            run_performance_tests
            run_db_tests
            ;;
        2)
            scan_raw_sessions
            check_get_db_usage
            ;;
        3)
            run_leak_scanner
            ;;
        4)
            run_performance_tests
            ;;
        5)
            run_db_tests
            ;;
        q|Q)
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            exit 1
            ;;
    esac
}

# Run the main function
main "$@" 