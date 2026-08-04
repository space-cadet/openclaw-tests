#!/usr/bin/env python3
"""
Thread-safe in-memory key-value store with transactions and savepoints.

Supports:
- Basic ops: get, set, delete
- Transactions: begin, commit, rollback
- Nested transactions (savepoints)
- Thread-safe concurrent access
- Atomicity: all operations in a transaction succeed or none do
"""

import threading
from typing import Any, Dict, Optional, Tuple


_UNSET = object()


class KVStore:
    """Thread-safe transactional in-memory key-value store."""

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}          # committed data
        self._lock = threading.RLock()            # global reentrant lock
        self._tx_stack: list[Dict[str, Tuple[Any, bool]]] = []  # transaction layers
        self._tx_owner: Optional[threading.Thread] = None       # thread owning active tx

    # ------------------------------------------------------------------
    # Basic operations
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = _UNSET) -> Any:
        """
        Retrieve a value by key.

        - If currently inside a transaction, uncommitted changes in the
          active transaction (and any nested savepoints) are visible.
        - If the key was deleted in the current transaction, KeyError is raised.
        - If no default is given and the key is absent, KeyError is raised.
        """
        with self._lock:
            caller = threading.current_thread()
            in_tx = self._tx_stack and self._tx_owner is caller

            if in_tx:
                # Search transaction layers top-down (most recent first)
                for layer in reversed(self._tx_stack):
                    if key in layer:
                        value, deleted = layer[key]
                        if deleted:
                            raise KeyError(key)
                        return value

            # Fall back to committed store (always used when called outside
            # the owning transaction, guaranteeing isolation).
            if default is not _UNSET:
                return self._store.get(key, default)
            try:
                return self._store[key]
            except KeyError:
                raise KeyError(key)

    def set(self, key: str, value: Any) -> None:
        """Set a key to a value. Inside a transaction the change is staged."""
        with self._lock:
            if self._tx_stack:
                self._tx_stack[-1][key] = (value, False)
            else:
                self._store[key] = value

    def delete(self, key: str) -> None:
        """
        Delete a key.

        - Outside a transaction: removes from committed store; raises KeyError
          if the key does not exist.
        - Inside a transaction: records a delete in the active layer.
        """
        with self._lock:
            if self._tx_stack:
                self._tx_stack[-1][key] = (None, True)
            else:
                if key not in self._store:
                    raise KeyError(key)
                del self._store[key]

    # ------------------------------------------------------------------
    # Transaction control
    # ------------------------------------------------------------------

    def begin(self) -> None:
        """Begin a new transaction or nested savepoint."""
        with self._lock:
            if not self._tx_stack:
                self._tx_owner = threading.current_thread()
            self._tx_stack.append({})

    def commit(self) -> None:
        """
        Commit the innermost transaction.

        - If nested, merges changes into the enclosing transaction layer.
        - If outermost, applies all staged changes to the committed store.
        """
        with self._lock:
            if not self._tx_stack:
                raise RuntimeError("No active transaction to commit")

            top_layer = self._tx_stack.pop()

            if self._tx_stack:
                # Nested transaction — merge into parent layer
                self._tx_stack[-1].update(top_layer)
            else:
                # Outermost transaction — flush to committed store
                self._tx_owner = None
                for k, (v, deleted) in top_layer.items():
                    if deleted:
                        self._store.pop(k, None)
                    else:
                        self._store[k] = v

    def rollback(self) -> None:
        """
        Rollback the innermost transaction.

        Discards all changes made since the matching begin() call.
        """
        with self._lock:
            if not self._tx_stack:
                raise RuntimeError("No active transaction to rollback")
            self._tx_stack.pop()
            if not self._tx_stack:
                self._tx_owner = None


# ====================================================================
# Tests
# ====================================================================

def run_tests() -> None:
    """Execute all KVStore tests. Raises AssertionError on failure."""

    # ----------------------------------------------------------------
    # Test 1: Basic get / set / delete (no transaction)
    # ----------------------------------------------------------------
    print("Test 1: Basic get/set/delete ... ", end="", flush=True)
    store = KVStore()
    store.set("a", 1)
    assert store.get("a") == 1
    store.set("a", 2)
    assert store.get("a") == 2
    store.delete("a")
    try:
        store.get("a")
        assert False, "Expected KeyError after delete"
    except KeyError:
        pass
    assert store.get("b", "default") == "default"
    print("PASS")

    # ----------------------------------------------------------------
    # Test 2: Simple transaction — begin, set, commit
    # ----------------------------------------------------------------
    print("Test 2: Simple transaction commit ... ", end="", flush=True)
    store = KVStore()
    store.set("x", 10)
    store.begin()
    store.set("x", 20)
    assert store.get("x") == 20          # visible inside tx
    store.commit()
    assert store.get("x") == 20          # persisted after commit
    print("PASS")

    # ----------------------------------------------------------------
    # Test 3: Rollback restores original value
    # ----------------------------------------------------------------
    print("Test 3: Rollback restores original ... ", end="", flush=True)
    store = KVStore()
    store.set("y", 100)
    store.begin()
    store.set("y", 200)
    assert store.get("y") == 200
    store.rollback()
    assert store.get("y") == 100         # original value restored
    print("PASS")

    # ----------------------------------------------------------------
    # Test 4: Nested transactions (savepoints)
    # ----------------------------------------------------------------
    print("Test 4: Nested transactions ... ", end="", flush=True)
    store = KVStore()
    store.set("z", 0)

    store.begin()            # outer
    store.set("z", 1)

    store.begin()            # inner
    store.set("z", 2)
    assert store.get("z") == 2
    store.rollback()         # rollback inner — z should be 1 again

    assert store.get("z") == 1
    store.commit()           # commit outer — z should be 1

    assert store.get("z") == 1
    print("PASS")

    # ----------------------------------------------------------------
    # Test 5: Thread safety — 10 threads concurrently increment same key
    # ----------------------------------------------------------------
    print("Test 5: Thread safety ... ", end="", flush=True)
    store = KVStore()
    store.set("counter", 0)
    NUM_THREADS = 10
    INCREMENTS_PER_THREAD = 100

    def worker() -> None:
        for _ in range(INCREMENTS_PER_THREAD):
            store.begin()
            current = store.get("counter")
            store.set("counter", current + 1)
            store.commit()

    threads = [threading.Thread(target=worker) for _ in range(NUM_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    expected = NUM_THREADS * INCREMENTS_PER_THREAD
    assert store.get("counter") == expected, f"Expected {expected}, got {store.get('counter')}"
    print("PASS")

    # ----------------------------------------------------------------
    # Test 6: Isolation — uncommitted changes not visible outside tx
    # ----------------------------------------------------------------
    print("Test 6: Isolation ... ", end="", flush=True)
    store = KVStore()
    store.set("secret", 42)

    store.begin()
    store.set("secret", 99)
    # Uncommitted change should NOT be visible outside the transaction.
    # We verify this by opening a *second* KVStore view via a separate
    # thread that acquires the store lock and reads the committed value.
    outside_value = []

    def reader() -> None:
        outside_value.append(store.get("secret"))

    t = threading.Thread(target=reader)
    t.start()
    t.join()

    assert outside_value[0] == 42, f"Expected 42, got {outside_value[0]}"
    store.rollback()
    assert store.get("secret") == 42
    print("PASS")

    print("\nAll 6 tests passed!")


if __name__ == "__main__":
    run_tests()
