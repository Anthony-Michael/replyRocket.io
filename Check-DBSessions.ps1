# Database Session Checker for ReplyRocket.io
# This script helps maintain proper database session handling by running
# various tools to check for issues and test performance.

# Colors for better output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    else {
        $input | Write-Output
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Success($message) {
    Write-ColorOutput Green "✓ $message"
}

function Write-Info($message) {
    Write-ColorOutput Cyan $message
}

function Write-Warning($message) {
    Write-ColorOutput Yellow $message
}

function Write-Error($message) {
    Write-ColorOutput Red "Error: $message"
}

# Print header
Write-Info "================================="
Write-Info "ReplyRocket.io DB Session Checker"
Write-Info "================================="
Write-Output ""

# Function to check if Python is installed
function Check-Python {
    try {
        $pythonVersion = python --version 2>&1
        Write-Success "Python is installed: $pythonVersion"
        return $true
    }
    catch {
        Write-Error "Python is not installed or not in PATH"
        return $false
    }
}

# Function to check requirements
function Check-Requirements {
    Write-Info "`nChecking dependencies..."
    
    $requiredPackages = @("pytest", "coverage", "pytest-cov", "astor")
    $missingPackages = @()
    
    foreach ($package in $requiredPackages) {
        $result = python -c "import $package" 2>&1
        if ($LASTEXITCODE -ne 0) {
            $missingPackages += $package
        }
    }
    
    if ($missingPackages.Count -gt 0) {
        Write-Warning "Missing required packages: $($missingPackages -join ', ')"
        $installChoice = Read-Host "Install missing packages? (y/n)"
        
        if ($installChoice -eq "y" -or $installChoice -eq "Y") {
            foreach ($package in $missingPackages) {
                Write-Output "Installing $package..."
                python -m pip install $package
            }
        }
        else {
            Write-Warning "Please install the required packages manually and run again."
            return $false
        }
    }
    else {
        Write-Success "All required packages are installed"
    }
    
    return $true
}

# Function to run the session leak scanner
function Run-LeakScanner {
    Write-Info "`nRunning database session leak scanner..."
    
    # Check if the scanner script exists
    if (-not (Test-Path "tests/scan_for_db_leaks.py")) {
        Write-Error "Database session leak scanner not found"
        return $false
    }
    
    # Run the scanner
    python tests/scan_for_db_leaks.py --dir app
    
    Write-Success "Session leak scan completed"
    return $true
}

# Function to run performance tests
function Run-PerformanceTests {
    Write-Info "`nRunning database performance tests..."
    
    # Check if the test script exists
    if (-not (Test-Path "tests/test_db_performance.py")) {
        Write-Error "Database performance test script not found"
        return $false
    }
    
    # Run the performance tests
    python tests/test_db_performance.py
    
    Write-Success "Performance tests completed"
    return $true
}

# Function to scan for raw session usage
function Scan-RawSessions {
    Write-Info "`nScanning for raw database session usage..."
    
    # Count instances of SessionLocal direct usage without proper handling
    $sessionDirect = (Select-String -Path "app\*.py" -Pattern "SessionLocal\(\)" -Recurse).Count
    $sessionWith = (Select-String -Path "app\*.py" -Pattern "with SessionLocal" -Recurse).Count
    
    # Try-finally is harder to match with regex in PowerShell, using simplified approach
    $tryBlocks = Select-String -Path "app\*.py" -Pattern "try:" -Recurse
    $sessionTry = 0
    foreach ($tryBlock in $tryBlocks) {
        $fileContent = Get-Content $tryBlock.Path
        $lineNumber = $tryBlock.LineNumber
        
        # Check next few lines for SessionLocal()
        $endLine = [Math]::Min($lineNumber + 5, $fileContent.Count)
        for ($i = $lineNumber; $i -lt $endLine; $i++) {
            if ($fileContent[$i] -match "SessionLocal\(\)") {
                $sessionTry++
                break
            }
        }
    }
    
    Write-Output "Raw SessionLocal() usage: $sessionDirect instances"
    Write-Output "With context manager usage: $sessionWith instances"
    Write-Output "Try-except usage: $sessionTry instances"
    
    if ($sessionDirect -gt 0) {
        Write-Warning "`nFiles with raw SessionLocal() usage:"
        $files = Select-String -Path "app\*.py" -Pattern "SessionLocal\(\)" -Recurse | 
                Select-Object -ExpandProperty Path -Unique
        foreach ($file in $files) {
            Write-Output "  - $file"
        }
    }
    
    Write-Success "Raw session usage scan completed"
    return $true
}

# Function to check import of get_db dependency
function Check-GetDbUsage {
    Write-Info "`nChecking for get_db dependency usage..."
    
    # Count instances of get_db import and usage
    $getDbImport = (Select-String -Path "app\*.py" -Pattern "from app.api.deps import get_db" -Recurse).Count
    $getDbDepend = (Select-String -Path "app\*.py" -Pattern "Depends\(get_db\)" -Recurse).Count
    
    Write-Output "get_db imports: $getDbImport instances"
    Write-Output "Depends(get_db) usage: $getDbDepend instances"
    
    # Check for endpoints that might not use get_db
    $routerFiles = Select-String -Path "app\*.py" -Pattern "APIRouter" -Recurse | 
                   Select-Object -ExpandProperty Path -Unique
    $missingGetDb = @()
    
    foreach ($file in $routerFiles) {
        $hasGetDb = Select-String -Path $file -Pattern "get_db" -Quiet
        if (-not $hasGetDb) {
            $missingGetDb += $file
        }
    }
    
    if ($missingGetDb.Count -gt 0) {
        Write-Warning "`nPotential API files missing get_db dependency:"
        foreach ($file in $missingGetDb) {
            Write-Output "  - $file"
        }
    }
    else {
        Write-Success "All API router files seem to use get_db"
    }
    
    return $true
}

# Function to run pytest with database session focus
function Run-DbTests {
    Write-Info "`nRunning database-related tests..."
    
    # Check if any tests exist
    $testFiles = Get-ChildItem -Path "tests" -Filter "test_*.py" -Recurse -ErrorAction SilentlyContinue
    if (-not $testFiles) {
        Write-Warning "No test files found"
        return $true
    }
    
    # Run tests with database session focus
    python -m pytest tests -xvs -k "db or database or session" --no-header
    
    Write-Success "Database tests completed"
    return $true
}

# Main function
function Main {
    param (
        [Parameter(Mandatory=$false)]
        [string]$Option
    )
    
    $pythonOk = Check-Python
    if (-not $pythonOk) {
        return
    }
    
    $requirementsOk = Check-Requirements
    if (-not $requirementsOk) {
        return
    }
    
    # Process command line option if provided
    if ($Option) {
        switch ($Option) {
            "all" {
                Scan-RawSessions
                Check-GetDbUsage
                Run-LeakScanner
                Run-PerformanceTests
                Run-DbTests
            }
            "leaks" {
                Run-LeakScanner
            }
            "performance" {
                Run-PerformanceTests
            }
            "scan" {
                Scan-RawSessions
                Check-GetDbUsage
            }
            "tests" {
                Run-DbTests
            }
            default {
                Write-Error "Unknown option: $Option"
                Write-Output "Use -Option 'help' for available options"
            }
        }
        return
    }
    
    # If no arguments provided, show menu
    Write-Output "`nChoose an option:"
    Write-Output "1) Run all checks and tests"
    Write-Output "2) Scan for raw session usage and get_db dependency"
    Write-Output "3) Run session leak scanner"
    Write-Output "4) Run performance tests"
    Write-Output "5) Run database-related tests"
    Write-Output "q) Quit"
    
    $choice = Read-Host "`nEnter choice [1-5 or q]"
    
    switch ($choice) {
        "1" {
            Scan-RawSessions
            Check-GetDbUsage
            Run-LeakScanner
            Run-PerformanceTests
            Run-DbTests
        }
        "2" {
            Scan-RawSessions
            Check-GetDbUsage
        }
        "3" {
            Run-LeakScanner
        }
        "4" {
            Run-PerformanceTests
        }
        "5" {
            Run-DbTests
        }
        "q" {
            return
        }
        "Q" {
            return
        }
        default {
            Write-Error "Invalid choice"
            return
        }
    }
}

# Display help if requested
if ($args -contains "-help" -or $args -contains "--help" -or $args -contains "-h") {
    Write-Output "Usage: .\Check-DBSessions.ps1 [-Option <option>]"
    Write-Output "Options:"
    Write-Output "  all          Run all checks and tests"
    Write-Output "  leaks        Run only the session leak scanner"
    Write-Output "  performance  Run only the performance tests"
    Write-Output "  scan         Scan for raw session usage and get_db usage"
    Write-Output "  tests        Run database-related tests"
    Write-Output "  help         Show this help message"
    exit 0
}

# Run with option if provided
if ($args.Count -gt 0) {
    Main -Option $args[0]
}
else {
    # Run interactive mode
    Main
} 