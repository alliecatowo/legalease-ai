#!/usr/bin/env python3
"""
Test script to verify Celery setup is configured correctly.
This script does not require Redis to be running.
"""

import sys


def test_celery_import():
    """Test that Celery app can be imported"""
    print("Testing Celery import...")
    try:
        from app.workers.celery_app import celery_app
        print("✓ Celery app imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import Celery app: {e}")
        return False


def test_celery_config():
    """Test Celery configuration"""
    print("\nTesting Celery configuration...")
    try:
        from app.workers.celery_app import celery_app

        print(f"  Broker URL: {celery_app.conf.broker_url}")
        print(f"  Result Backend: {celery_app.conf.result_backend}")
        print(f"  Task Serializer: {celery_app.conf.task_serializer}")
        print(f"  Result Serializer: {celery_app.conf.result_serializer}")
        print(f"  Timezone: {celery_app.conf.timezone}")
        print(f"  Default Queue: {celery_app.conf.task_default_queue}")

        print("✓ Celery configuration loaded successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to load Celery configuration: {e}")
        return False


def test_task_queues():
    """Test that task queues are configured"""
    print("\nTesting task queues...")
    try:
        from app.workers.celery_app import celery_app

        queues = celery_app.conf.task_queues
        print(f"  Configured queues: {len(queues)}")
        for queue in queues:
            print(f"    - {queue.name} (routing_key: {queue.routing_key})")

        print("✓ Task queues configured successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to load task queues: {e}")
        return False


def test_task_routes():
    """Test that task routes are configured"""
    print("\nTesting task routes...")
    try:
        from app.workers.celery_app import celery_app

        routes = celery_app.conf.task_routes
        print(f"  Configured routes: {len(routes)}")
        for task_name, route_config in routes.items():
            print(f"    - {task_name} → {route_config['queue']}")

        print("✓ Task routes configured successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to load task routes: {e}")
        return False


def test_registered_tasks():
    """Test that tasks are registered"""
    print("\nTesting registered tasks...")
    try:
        from app.workers.celery_app import celery_app

        # Get only our custom tasks (exclude built-in celery tasks)
        custom_tasks = [
            task for task in celery_app.tasks.keys()
            if not task.startswith('celery.')
        ]

        print(f"  Registered custom tasks: {len(custom_tasks)}")
        for task in sorted(custom_tasks):
            print(f"    - {task}")

        # Verify expected tasks are present
        expected_tasks = [
            'process_document',
            'generate_document',
            'process_uploaded_document',
            'transcribe_audio',
            'process_transcription',
        ]

        missing_tasks = [task for task in expected_tasks if task not in custom_tasks]
        if missing_tasks:
            print(f"\n  ✗ Missing expected tasks: {missing_tasks}")
            return False

        print("✓ All expected tasks are registered")
        return True
    except Exception as e:
        print(f"✗ Failed to load registered tasks: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_imports():
    """Test that individual tasks can be imported"""
    print("\nTesting task imports...")
    try:
        from app.workers.tasks.document_processing import (
            process_document,
            generate_document,
            process_uploaded_document,
        )
        from app.workers.tasks.transcription import (
            transcribe_audio,
            process_transcription,
        )

        print("✓ All tasks imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import tasks: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Celery Setup Verification")
    print("=" * 60)

    tests = [
        test_celery_import,
        test_celery_config,
        test_task_queues,
        test_task_routes,
        test_task_imports,
        test_registered_tasks,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
        print()

    print("=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)

    if all(results):
        print("\n✓ All tests passed! Celery is configured correctly.")
        print("\nTo start the worker, run:")
        print("  uv run celery -A app.workers.celery_app worker -l info")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
