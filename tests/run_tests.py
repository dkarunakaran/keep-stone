"""
Test runner script and example usage
"""
import os
import sys
import subprocess

def run_all_tests():
    """Run all test suites"""
    print("🧪 Running KeepStone Test Suite")
    print("=" * 50)
    
    # Change to project directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    # Test commands to run
    test_commands = [
        # Run all tests with coverage
        ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
        
        # Run only unit tests
        ["python", "-m", "pytest", "tests/", "-v", "-m", "unit"],
        
        # Run only integration tests
        ["python", "-m", "pytest", "tests/", "-v", "-m", "integration"],
        
        # Run tests with coverage report
        ["python", "-m", "pytest", "tests/", "--cov=.", "--cov-report=html", "--cov-report=term"],
    ]
    
    print("\n📋 Available test commands:")
    for i, cmd in enumerate(test_commands, 1):
        print(f"  {i}. {' '.join(cmd)}")
    
    print(f"\n🔧 To run tests manually:")
    print(f"  cd {project_root}")
    print(f"  python -m pytest tests/ -v")
    print(f"\n📊 For coverage report:")
    print(f"  python -m pytest tests/ --cov=. --cov-report=html")
    print(f"\n🏷️  To run specific test markers:")
    print(f"  python -m pytest tests/ -m unit")
    print(f"  python -m pytest tests/ -m integration")
    print(f"  python -m pytest tests/ -m config")
    print(f"\n📁 Test files created:")
    print(f"  • tests/conftest.py - Test configuration and fixtures")
    print(f"  • tests/test_config_utils.py - Configuration utility tests")
    print(f"  • tests/test_models.py - Database model tests")
    print(f"  • tests/test_utility.py - Utility function tests")
    print(f"  • tests/test_routes.py - Flask route/API tests")
    print(f"  • pytest.ini - Pytest configuration")
    print(f"  • test-requirements.txt - Test dependencies")

def install_test_dependencies():
    """Install test dependencies"""
    print("📦 Installing test dependencies...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "test-requirements.txt"
        ], check=True)
        print("✅ Test dependencies installed successfully!")
    except subprocess.CalledProcessError:
        print("❌ Failed to install test dependencies")
        print("💡 Try manually: pip install -r test-requirements.txt")

if __name__ == "__main__":
    print("KeepStone Test Suite Setup")
    print("=" * 30)
    
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        install_test_dependencies()
    else:
        run_all_tests()
        
        print(f"\n🚀 Quick Start:")
        print(f"  1. Install test dependencies: python {__file__} install")
        print(f"  2. Run tests: python -m pytest tests/ -v")
        print(f"  3. Run with coverage: python -m pytest tests/ --cov=.")
        print(f"\n📖 Test Structure:")
        print(f"  • Unit tests: Fast, isolated component tests")
        print(f"  • Integration tests: Component interaction tests")
        print(f"  • API tests: Flask route and endpoint tests")
        print(f"  • Database tests: Model and database operation tests")
        print(f"  • Config tests: Configuration system tests")
