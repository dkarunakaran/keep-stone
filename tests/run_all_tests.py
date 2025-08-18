"""
Complete test suite execution script with detailed reporting
Run all tests or specific test categories
"""

import sys
import subprocess
import os
from datetime import datetime
import json

def run_command(cmd, description):
    """Run a command and return result with timing"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print(f"{'='*60}")
    
    start_time = datetime.now()
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"Duration: {duration:.2f} seconds")
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print(f"\nSTDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"\nSTDERR:\n{result.stderr}")
            
        return result.returncode == 0, result.stdout, result.stderr, duration
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"Error running command: {e}")
        return False, "", str(e), duration

def check_requirements():
    """Check if required packages are installed"""
    print("Checking test requirements...")
    
    required_packages = [
        'pytest',
        'pytest-cov',
        'pytest-mock',
        'flask',
        'sqlalchemy'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package} is available")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} is missing")
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Install with: pip install -r test-requirements.txt")
        return False
    
    return True

def run_test_discovery():
    """Discover and list available tests"""
    print("\nDiscovering tests...")
    success, stdout, stderr, duration = run_command(
        "python -m pytest --collect-only -q",
        "Test Discovery"
    )
    
    if success:
        test_count = stdout.count('::')
        print(f"Found {test_count} tests")
        return True
    else:
        print("Test discovery failed")
        return False

def run_syntax_check():
    """Check Python syntax of test files"""
    print("\nChecking test file syntax...")
    test_files = [
        "conftest.py",
        "test_config_utils.py", 
        "test_models.py",
        "test_utility.py",
        "test_routes.py",
        "test_config.py"
    ]
    
    all_good = True
    for test_file in test_files:
        if os.path.exists(test_file):
            success, stdout, stderr, duration = run_command(
                f"python -m py_compile {test_file}",
                f"Syntax check: {test_file}"
            )
            if success:
                print(f"✓ {test_file} - syntax OK")
            else:
                print(f"✗ {test_file} - syntax error")
                all_good = False
        else:
            print(f"? {test_file} - file not found")
    
    return all_good

def run_tests(test_category=None, verbose=False, coverage=False):
    """Run pytest with specified options"""
    
    # Base pytest command
    cmd_parts = ["python", "-m", "pytest"]
    
    # Add verbosity
    if verbose:
        cmd_parts.append("-v")
    else:
        cmd_parts.append("-q")
    
    # Add coverage
    if coverage:
        cmd_parts.extend([
            "--cov=../",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
    
    # Add test category marker
    if test_category:
        cmd_parts.extend(["-m", test_category])
    
    # Add output options
    cmd_parts.extend([
        "--tb=short",
        "--strict-markers",
        "--no-header"
    ])
    
    cmd = " ".join(cmd_parts)
    description = f"Running tests" + (f" (category: {test_category})" if test_category else " (all)")
    
    return run_command(cmd, description)

def generate_report(results):
    """Generate a test execution report"""
    report = {
        "execution_time": datetime.now().isoformat(),
        "results": results,
        "summary": {
            "total_operations": len(results),
            "successful_operations": sum(1 for r in results if r["success"]),
            "failed_operations": sum(1 for r in results if not r["success"]),
            "total_duration": sum(r["duration"] for r in results)
        }
    }
    
    # Save JSON report
    with open("test_execution_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print(f"\n{'='*60}")
    print("TEST EXECUTION SUMMARY")
    print(f"{'='*60}")
    print(f"Total Operations: {report['summary']['total_operations']}")
    print(f"Successful: {report['summary']['successful_operations']}")
    print(f"Failed: {report['summary']['failed_operations']}")
    print(f"Total Duration: {report['summary']['total_duration']:.2f} seconds")
    print(f"Report saved to: test_execution_report.json")
    
    return report

def main():
    """Main test execution function"""
    print("KeepStone Test Suite")
    print("="*60)
    print(f"Execution started at: {datetime.now()}")
    print(f"Working directory: {os.getcwd()}")
    
    results = []
    
    # Check if we're in the right directory
    if not os.path.exists("conftest.py"):
        print("Error: Not in tests directory or conftest.py not found")
        print("Please run this script from the tests/ directory")
        sys.exit(1)
    
    # Parse command line arguments
    args = sys.argv[1:]
    test_category = None
    verbose = False
    coverage = False
    skip_checks = False
    
    for arg in args:
        if arg.startswith("--category="):
            test_category = arg.split("=", 1)[1]
        elif arg == "--verbose" or arg == "-v":
            verbose = True
        elif arg == "--coverage":
            coverage = True
        elif arg == "--skip-checks":
            skip_checks = True
        elif arg == "--help" or arg == "-h":
            print("""
Usage: python run_tests.py [options]

Options:
  --category=CATEGORY   Run tests with specific marker (unit, integration, api, database)
  --verbose, -v         Verbose output
  --coverage           Run with coverage reporting
  --skip-checks        Skip requirement and syntax checks
  --help, -h           Show this help message

Examples:
  python run_tests.py                           # Run all tests
  python run_tests.py --category=unit          # Run only unit tests
  python run_tests.py --verbose --coverage     # Verbose output with coverage
  python run_tests.py --category=api -v        # Run API tests with verbose output
            """)
            sys.exit(0)
    
    # Step 1: Check requirements (unless skipped)
    if not skip_checks:
        print("\nStep 1: Checking requirements...")
        if not check_requirements():
            print("Please install missing requirements and try again")
            sys.exit(1)
        results.append({
            "step": "Requirements Check",
            "success": True,
            "duration": 0,
            "details": "All required packages available"
        })
    
    # Step 2: Syntax check (unless skipped)
    if not skip_checks:
        print("\nStep 2: Syntax check...")
        syntax_ok = run_syntax_check()
        results.append({
            "step": "Syntax Check", 
            "success": syntax_ok,
            "duration": 0,
            "details": "Python syntax validation"
        })
        
        if not syntax_ok:
            print("Syntax errors found. Please fix before running tests.")
            # Continue anyway for demonstration
    
    # Step 3: Test discovery
    print("\nStep 3: Test discovery...")
    discovery_ok = run_test_discovery()
    results.append({
        "step": "Test Discovery",
        "success": discovery_ok, 
        "duration": 0,
        "details": "Pytest test collection"
    })
    
    # Step 4: Run tests
    print(f"\nStep 4: Running tests...")
    success, stdout, stderr, duration = run_tests(test_category, verbose, coverage)
    results.append({
        "step": f"Test Execution{' (' + test_category + ')' if test_category else ''}",
        "success": success,
        "duration": duration,
        "details": f"stdout_lines: {len(stdout.splitlines())}, stderr_lines: {len(stderr.splitlines())}"
    })
    
    # Step 5: Generate report
    print("\nStep 5: Generating report...")
    report = generate_report(results)
    
    # Final status
    if all(r["success"] for r in results):
        print("\n✓ All operations completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Some operations failed. Check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
