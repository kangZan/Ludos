"""Startup script with environment validation."""

import os
import sys
from pathlib import Path


def check_python_version() -> bool:
    """Verify Python version is 3.12.x."""
    version = sys.version_info
    if version.major != 3 or version.minor != 12:
        print(f"Error: Python 3.12.x required, found {version.major}.{version.minor}.{version.micro}")
        return False
    return True


def check_env_file() -> bool:
    """Check for .env file."""
    env_path = Path(".env")
    if not env_path.exists():
        example_path = Path(".env.example")
        if example_path.exists():
            print("Warning: .env file not found. Copying from .env.example...")
            env_path.write_text(example_path.read_text())
            print("Created .env — please edit it with your API keys.")
            return False
        print("Error: .env file not found and no .env.example available.")
        return False
    return True


def check_api_key() -> bool:
    """Verify LLM API key is configured."""
    key = os.environ.get("LLM_API_KEY", "")
    if not key or key == "your-api-key-here":
        print("Error: LLM_API_KEY not set. Edit .env file with your API key.")
        return False
    return True


def check_dependencies() -> bool:
    """Check if required packages are installed."""
    required = ["langgraph", "langchain_core", "langchain_openai", "pydantic", "structlog"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"Error: Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    return True


def main() -> None:
    """Run all environment checks and start the application."""
    print("Ludos - Environment Check")
    print("-" * 40)

    health_mode = "--health" in sys.argv
    if health_mode:
        print("Health check mode enabled.")

    checks = [
        ("Python version", check_python_version),
        ("Environment file", check_env_file),
        ("Dependencies", check_dependencies),
    ]

    all_passed = True
    for name, check_fn in checks:
        passed = check_fn()
        status = "OK" if passed else "FAIL"
        print(f"  [{status}] {name}")
        if not passed:
            all_passed = False

    if not all_passed:
        print("\nSome checks failed. Please fix the issues above.")
        sys.exit(1)

    # Load .env before checking API key
    from dotenv import load_dotenv
    load_dotenv()

    if not check_api_key():
        print("  [FAIL] API Key")
        sys.exit(1)
    print("  [OK] API Key")

    if health_mode:
        print("\nAll checks passed. Running LLM connectivity check...")
        from src.main import main as app_main
        app_main()
        return

    print("\nAll checks passed. Starting Ludos...")
    print("-" * 40)

    from src.main import main as app_main
    app_main()


if __name__ == "__main__":
    main()
