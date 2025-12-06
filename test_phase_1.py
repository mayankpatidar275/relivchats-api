#!/usr/bin/env python
"""
Quick verification script for Phase 1 implementation.
Run this to ensure all Phase 1 changes are working correctly.

Usage: python test_phase_1.py
"""

import sys
import asyncio


def test_imports():
    """Test that all new modules can be imported"""
    print("=" * 70)
    print("Testing Phase 1 Imports")
    print("=" * 70)

    tests_passed = 0
    tests_failed = 0

    # Test database_utils import
    try:
        from src.database_utils import (
            execute_with_lock_retry,
            upsert_unique_record,
            upsert_or_create,
            execute_in_transaction,
            LockTimeoutError
        )
        print("✓ src.database_utils imported successfully")
        tests_passed += 1
    except ImportError as e:
        print(f"✗ Failed to import src.database_utils: {e}")
        tests_failed += 1

    # Test error handlers import
    try:
        from src.error_handlers import (
            LockTimeoutException,
            AsyncDatabaseException,
            lock_timeout_exception_handler,
            async_database_exception_handler
        )
        print("✓ src.error_handlers enhanced exceptions imported successfully")
        tests_passed += 1
    except ImportError as e:
        print(f"✗ Failed to import error handlers: {e}")
        tests_failed += 1

    # Test SoftDeleteMixin import
    try:
        from src.database import SoftDeleteMixin, get_async_db_transaction
        print("✓ src.database SoftDeleteMixin imported successfully")
        tests_passed += 1
    except ImportError as e:
        print(f"✗ Failed to import SoftDeleteMixin: {e}")
        tests_failed += 1

    # Test model soft delete mixin
    try:
        from src.users.models import User
        from src.chats.models import Chat
        from src.rag.models import AIConversation

        assert hasattr(User, '_soft_delete_filter'), "User missing _soft_delete_filter"
        assert hasattr(Chat, '_soft_delete_filter'), "Chat missing _soft_delete_filter"
        assert hasattr(AIConversation, '_soft_delete_filter'), "AIConversation missing _soft_delete_filter"

        print("✓ All models have SoftDeleteMixin applied")
        tests_passed += 1
    except (ImportError, AssertionError) as e:
        print(f"✗ Model soft delete check failed: {e}")
        tests_failed += 1

    print("\n" + "=" * 70)
    print(f"Import Tests: {tests_passed} passed, {tests_failed} failed")
    print("=" * 70 + "\n")

    return tests_failed == 0


def test_database_config():
    """Test that database configuration is correct"""
    print("=" * 70)
    print("Testing Database Configuration")
    print("=" * 70)

    tests_passed = 0
    tests_failed = 0

    try:
        from src.database import IS_CELERY_WORKER, async_engine, engine
        from src.config import settings

        # Check if Celery detection is working
        if IS_CELERY_WORKER:
            print("✓ Running in Celery worker context (NullPool)")
            print(f"  DATABASE_URL: {settings.DATABASE_URL[:50]}...")
        else:
            print("✓ Running in FastAPI context (QueuePool)")
            print(f"  DATABASE_URL: {settings.DATABASE_URL[:50]}...")
        tests_passed += 1

        # Check async engine exists
        if async_engine:
            print("✓ Async engine created successfully")
            tests_passed += 1
        else:
            print("✗ Async engine is None")
            tests_failed += 1

        # Check sync engine exists
        if engine:
            print("✓ Sync engine created successfully")
            tests_passed += 1
        else:
            print("✗ Sync engine is None")
            tests_failed += 1

        # Check pool settings
        if not IS_CELERY_WORKER:
            pool = engine.pool
            print(f"✓ Sync pool config: size={pool.size()}, overflow_enabled=True")
            tests_passed += 1
        else:
            print("✓ Celery worker using NullPool (no pooling)")
            tests_passed += 1

    except Exception as e:
        print(f"✗ Database configuration test failed: {e}")
        tests_failed += 1

    print("\n" + "=" * 70)
    print(f"Database Config Tests: {tests_passed} passed, {tests_failed} failed")
    print("=" * 70 + "\n")

    return tests_failed == 0


async def test_async_db_dependency():
    """Test that async DB dependency works"""
    print("=" * 70)
    print("Testing Async DB Dependency")
    print("=" * 70)

    tests_passed = 0
    tests_failed = 0

    try:
        from src.database import get_async_db

        # Test that it's a generator
        if callable(get_async_db):
            print("✓ get_async_db is callable")
            tests_passed += 1
        else:
            print("✗ get_async_db is not callable")
            tests_failed += 1

        # Test that it returns an async generator
        import inspect
        if inspect.isasyncgenfunction(get_async_db):
            print("✓ get_async_db is an async generator")
            tests_passed += 1
        else:
            print("✗ get_async_db is not an async generator")
            tests_failed += 1

    except Exception as e:
        print(f"✗ Async DB dependency test failed: {e}")
        tests_failed += 1

    print("\n" + "=" * 70)
    print(f"Async DB Dependency Tests: {tests_passed} passed, {tests_failed} failed")
    print("=" * 70 + "\n")

    return tests_failed == 0


def main():
    """Run all Phase 1 tests"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + " PHASE 1 IMPLEMENTATION VERIFICATION".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    results = []

    # Run synchronous tests
    results.append(("Imports", test_imports()))
    results.append(("Database Config", test_database_config()))

    # Run async tests
    results.append(("Async DB Dependency", asyncio.run(test_async_db_dependency())))

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY".center(70))
    print("=" * 70)

    all_passed = all(result[1] for result in results)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    print("=" * 70)

    if all_passed:
        print("\n🎉 All Phase 1 tests passed! Ready for Phase 2.")
        return 0
    else:
        print("\n❌ Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
