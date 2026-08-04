#!/usr/bin/env python3
"""
Thread-safe in-memory key-value store with transactions.
Supports nested transactions (savepoints) and ACID atomicity.
"""

import threading
from typing import Any, Dict

# Sentinel value to distinguish "deleted" from "value is None"
_DELETED = object()


class KVStore:
    """Thread-safe transactional in-memory key-value store."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {}
        self._local = threading.local()

    def _tx_stack(self) -> list:
        """Get the thread-local transaction stack."""
        if not hasattr(self._local, "stack"):
            self._local.stack = []
        return self._local.stack

    def get(self, key: str) -> Any:
        """Get value by key. Returns None if key not found."""
        with self._lock:
            # Search transaction stack from newest to oldest
            for tx in reversed(self._tx_stack()):
                if key in tx:
                    value = tx[key]
                    return None if value is _DELETED else value
            # Fall back to committed data
            return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        """Set key to value."""
        with self._lock:
            if self._tx_stack():
                self._tx_stack()[-1][key] = value
            else:
                self._data[key] = value

    def delete(self, key: str) -> None:
        """Delete key from store."""
        with self._lock:
            if self._tx_stack():
                self._tx_stack()[-1][key] = _DELETED
            else:
                self._data.pop(key, None)

    def begin(self) -> None:
        """Begin a new transaction. Supports nesting."""
        with self._lock:
            self._tx_stack().append({})

    def commit(self) -> None:
        """Commit the current transaction."""
        with self._lock:
            stack = self._tx_stack()
            if not stack:
                raise RuntimeError("No active transaction to commit")
            tx = stack.pop()
            if stack:
                # Merge into parent transaction
                stack[-1].update(tx)
            else:
                # Apply to committed data
                for k, v in tx.items():
                    if v is _DELETED:
                        self._data.pop(k, None)
                    else:
                        self._data[k] = v

    def rollback(self) -> None:
        """Rollback the current transaction."""
        with self._lock:
            stack = self._tx_stack()
            if not stack:
                raise RuntimeError("No active transaction to rollback")
            stack.pop()


def run_tests():
    """Run all tests and print pass/fail summary."""
    tests_passed = 0
    tests_failed = 0

    def check(name: str, condition: bool):
        nonlocal tests_passed, tests_failed
        if condition:
            print(f"  [PASS] {name}")
            tests_passed += 1
        else:
            print(f"  [FAIL] {name}")
            tests_failed += 1

    # Test 1: Basic operations
    print("Test 1: Basic operations")
    store = KVStore()
    store.set("a", 1)
    check("get after set", store.get("a") == 1)
    store.delete("a")
    check("get after delete", store.get("a") is None)
    check("delete nonexistent key", store.delete("nonexistent") is None)

    # Test 2: Transaction commit
    print("\nTest 2: Transaction commit")
    store = KVStore()
    store.begin()
    store.set("x", 10)
    check("get in transaction", store.get("x") == 10)
    store.commit()
    check("get after commit", store.get("x") == 10)

    # Test 3: Transaction rollback
    print("\nTest 3: Transaction rollback")
    store = KVStore()
    store.set("y", 5)
    store.begin()
    store.set("y", 99)
    check("get in transaction before rollback", store.get("y") == 99)
    store.rollback()
    check("get after rollback", store.get("y") == 5)

    # Test 4: Nested transactions
    print("\nTest 4: Nested transactions")
    store = KVStore()
    store.set("z", 1)
    store.begin()         # tx1
    store.set("z", 2)
    store.begin()         # tx2
    store.set("z", 3)
    check("get in inner transaction", store.get("z") == 3)
    store.rollback()      # rollback tx2
    check("get after inner rollback", store.get("z") == 2)
    store.commit()        # commit tx1
    check("get after outer commit", store.get("z") == 2)

    # Test 5: Isolation
    print("\nTest 5: Isolation")
    store = KVStore()
    store.set("a", 1)
    store.begin()
    store.set("a", 2)
    check("get in transaction sees uncommitted", store.get("a") == 2)

    # New reader in another thread should see committed value only
    reader_result = []

    def reader():
        reader_result.append(store.get("a"))

    t = threading.Thread(target=reader)
    t.start()
    t.join()
    check("new reader sees committed value", reader_result[0] == 1)
    store.rollback()
    check("value unchanged after rollback", store.get("a") == 1)

    # Test 6: Thread safety
    print("\nTest 6: Thread safety")
    store = KVStore()
    store.set("counter", 0)

    def increment_100():
        for _ in range(100):
            store.begin()
            val = store.get("counter") or 0
            store.set("counter", val + 1)
            store.commit()

    threads = [threading.Thread(target=increment_100) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    check("10 threads x 100 increments = 1000", store.get("counter") == 1000)

    # Summary
    print(f"\n{'='*40}")
    print(f"Results: {tests_passed} passed, {tests_failed} failed")
    print(f"{'='*40}")
    return tests_failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
