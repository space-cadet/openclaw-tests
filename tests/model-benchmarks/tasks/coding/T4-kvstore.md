# Task T4: Concurrent In-Memory Key-Value Store

## Difficulty: Medium-Hard

Build a thread-safe in-memory key-value store with transactions.

### Requirements
1. Basic operations: `get(key)`, `set(key, value)`, `delete(key)`
2. Transactions:
   - `begin()` — start a transaction
   - `commit()` — commit all changes in transaction
   - `rollback()` — discard all changes in transaction
3. Nesting: transactions can be nested (savepoints)
4. Concurrency: thread-safe for concurrent access
5. Persistence: optional — write-ahead log (WAL) to disk
6. Atomicity: all operations in a transaction succeed or none do

### Test Cases (must all pass)

```python
# Basic ops
store = KVStore()
store.set("a", 1)
store.get("a") => 1
store.delete("a")
store.get("a") => None

# Simple transaction
store = KVStore()
store.begin()
store.set("x", 10)
store.commit()
store.get("x") => 10

# Rollback
store = KVStore()
store.set("y", 5)
store.begin()
store.set("y", 99)
store.rollback()
store.get("y") => 5

# Nested transactions
store = KVStore()
store.set("z", 1)
store.begin()      # tx1
store.set("z", 2)
store.begin()      # tx2 (nested)
store.set("z", 3)
store.rollback()   # rollback tx2
store.get("z") => 2  # tx1 value
store.commit()     # commit tx1
store.get("z") => 2

# Isolation
store = KVStore()
store.set("a", 1)
store.begin()
store.set("a", 2)
# Before commit, "a" should still be 1 for new readers
store.commit()
store.get("a") => 2

# WAL recovery (if implemented)
store = KVStore(wal_path="test.wal")
store.set("k", "v")
store2 = KVStore(wal_path="test.wal")
store2.get("k") => "v"
```

### Output Format
Write `kvstore.py` with `KVStore` class and `run_tests()`.

### Scoring
- Correctness: all tests pass
- Thread safety: no race conditions
- Transaction correctness: ACID properties
- Code quality: clean separation of concerns
