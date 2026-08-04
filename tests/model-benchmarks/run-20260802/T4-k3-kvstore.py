#!/usr/bin/env python3
"""
Thread-safe in-memory key-value store with transactions.
Supports nested transactions (savepoints).
"""

import contextlib
import threading
import time
from typing import Any, Dict, List

# Sentinel value to mark deleted keys in transaction changes
_DELETED = object()


class KVStore:
    """Thread-safe in-memory key-value store with transaction support."""

    def __init__(self):
        self._store: Dict[str, Any] = {}  # Committed data
        self._lock = threading.Lock()
        self._local = threading.local()

    def _get_stack(self) -> List[Dict[str, Any]]:
        """Get the thread-local transaction stack."""
        if not hasattr(self._local, "stack"):
            self._local.stack = []
        return self._local.stack

    def _in_transaction(self) -> bool:
        """Check if current thread is inside a transaction."""
        return len(self._get_stack()) > 0

    def _lock_context(self):
        """Return lock context manager. No-op if already in transaction."""
        if self._in_transaction():
            return contextlib.nullcontext()
        return self._lock

    def get(self, key: str) -> Any:
        """Get value by key. Raises KeyError if not found."""
        with self._lock_context():
            # Search transaction stack from innermost to outermost
            for changes in reversed(self._get_stack()):
                if key in changes:
                    if changes[key] is _DELETED:
                        raise KeyError(key)
                    return changes[key]
            # Fall through to committed store
            if key not in self._store:
                raise KeyError(key)
            return self._store[key]

    def set(self, key: str, value: Any) -> None:
        """Set key to value."""
        with self._lock_context():
            if self._in_transaction():
                self._get_stack()[-1][key] = value
            else:
                self._store[key] = value

    def delete(self, key: str) -> None:
        """Delete key. Raises KeyError if not found in committed store (outside tx)."""
        with self._lock_context():
            if self._in_transaction():
                self._get_stack()[-1][key] = _DELETED
            else:
                if key not in self._store:
                    raise KeyError(key)
                del self._store[key]

    def begin(self) -> None:
        """Begin a new transaction. Acquires lock for top-level tx."""
        if not self._in_transaction():
            self._lock.acquire()
        self._get_stack().append({})

    def commit(self) -> None:
        """Commit current transaction."""
        stack = self._get_stack()
        if not stack:
            raise RuntimeError("No active transaction to commit")

        current = stack.pop()
        if stack:
            # Nested transaction: merge changes into parent
            for k, v in current.items():
                stack[-1][k] = v
        else:
            # Top-level transaction: write to store and release lock
            for k, v in current.items():
                if v is _DELETED:
                    self._store.pop(k, None)
                else:
                    self._store[k] = v
            self._lock.release()

    def rollback(self) -> None:
        """Rollback current transaction."""
        stack = self._get_stack()
        if not stack:
            raise RuntimeError("No active transaction to rollback")

        stack.pop()
        if not stack:
            # Top-level rollback: release lock
            self._lock.release()

    def transaction(self):
        """Context manager for transactions."""
        return _TransactionContext(self)


class _TransactionContext:
    def __init__(self, store: KVStore):
        self._store = store

    def __enter__(self):
        self._store.begin()
        return self._store

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._store.commit()
        else:
            self._store.rollback()
        return False


def run_tests():
    """Run all tests. Returns True if all pass, False otherwise."""
    tests_passed = 0
    tests_failed = 0

    # Test 1: Basic get/set/delete
    print("Test 1: Basic get/set/delete")
    try:
        store = KVStore()
        store.set("a", 1)
        assert store.get("a") == 1
        store.set("a", 2)
        assert store.get("a") == 2
        store.delete("a")
        try:
            store.get("a")
            assert False, "Should have raised KeyError"
        except KeyError:
            pass
        print("  PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        tests_failed += 1

    # Test 2: Simple transaction
    print("Test 2: Simple transaction")
    try:
        store = KVStore()
        store.begin()
        store.set("x", 10)
        assert store.get("x") == 10
        store.commit()
        assert store.get("x") == 10
        print("  PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        tests_failed += 1

    # Test 3: Rollback
    print("Test 3: Rollback restores original value")
    try:
        store = KVStore()
        store.set("y", "original")
        store.begin()
        store.set("y", "new")
        assert store.get("y") == "new"
        store.rollback()
        assert store.get("y") == "original"
        print("  PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        tests_failed += 1

    # Test 4: Nested transactions
    print("Test 4: Nested transactions")
    try:
        store = KVStore()
        store.begin()
        store.set("z", "outer")
        store.begin()
        store.set("z", "inner")
        assert store.get("z") == "inner"
        store.rollback()  # rollback inner
        assert store.get("z") == "outer"
        store.commit()  # commit outer
        assert store.get("z") == "outer"
        print("  PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        tests_failed += 1

    # Test 5: Thread safety
    print("Test 5: Thread safety - concurrent increments")
    try:
        store = KVStore()
        store.set("counter", 0)

        def worker():
            for _ in range(100):
                store.begin()
                try:
                    val = store.get("counter")
                    store.set("counter", val + 1)
                    store.commit()
                except Exception:
                    store.rollback()
                    raise

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert store.get("counter") == 1000, f"Expected 1000, got {store.get('counter')}"
        print("  PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        tests_failed += 1

    # Test 6: Isolation
    print("Test 6: Isolation - uncommitted changes not visible outside tx")
    try:
        store = KVStore()
        store.set("iso", "committed")

        result = []

        def tx_thread():
            store.begin()
            store.set("iso", "uncommitted")
            # Hold transaction open briefly
            time.sleep(0.2)
            store.rollback()

        def reader_thread():
            result.append(store.get("iso"))

        t1 = threading.Thread(target=tx_thread)
        t1.start()
        time.sleep(0.05)  # Let tx_thread acquire lock and modify

        t2 = threading.Thread(target=reader_thread)
        t2.start()
        # Reader should block until tx_thread rolls back
        t2.join(timeout=0.3)

        # After rollback, reader should see the committed value
        assert result == ["committed"], f"Expected ['committed'], got {result}"
        t1.join(timeout=1)

        # Verify inside tx we saw the uncommitted value
        store.begin()
        store.set("iso", "modified")
        assert store.get("iso") == "modified"
        store.rollback()
        assert store.get("iso") == "committed"

        print("  PASS")
        tests_passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        tests_failed += 1

    print(f"\n{tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
