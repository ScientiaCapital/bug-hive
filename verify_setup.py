#!/usr/bin/env python3
"""Verify BugHive project setup.

This script verifies that the project scaffolding is properly configured.
Run with: uv run python verify_setup.py
"""

import sys


def verify_imports() -> bool:
    """Verify all core imports work."""
    print("Verifying imports...")
    try:
        from src.core import Settings, get_settings, setup_logging  # noqa: F401

        print("✓ Core imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def verify_dependencies() -> bool:
    """Verify all required dependencies are installed."""
    print("\nVerifying dependencies...")
    required_packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "pydantic_settings",
        "sqlalchemy",
        "asyncpg",
        "redis",
        "celery",
        "langgraph",
        "httpx",
        "anthropic",
        "dotenv",  # python-dotenv imports as 'dotenv'
        "structlog",
    ]

    all_present = True
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} not found")
            all_present = False

    return all_present


def verify_dev_tools() -> bool:
    """Verify dev tools are installed."""
    print("\nVerifying dev tools...")
    dev_tools = ["pytest", "ruff", "mypy"]

    all_present = True
    for tool in dev_tools:
        try:
            __import__(tool)
            print(f"✓ {tool}")
        except ImportError:
            print(f"✗ {tool} not found")
            all_present = False

    return all_present


def main() -> int:
    """Run all verification checks."""
    print("=" * 50)
    print("BugHive Project Setup Verification")
    print("=" * 50)

    checks = [verify_imports(), verify_dependencies(), verify_dev_tools()]

    print("\n" + "=" * 50)
    if all(checks):
        print("✓ All verification checks passed!")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and fill in your API keys")
        print("2. Set up PostgreSQL and Redis")
        print("3. Run tests: uv run pytest")
        print("4. Start development!")
        return 0
    else:
        print("✗ Some verification checks failed")
        print("\nPlease run: uv sync --extra dev")
        return 1


if __name__ == "__main__":
    sys.exit(main())
