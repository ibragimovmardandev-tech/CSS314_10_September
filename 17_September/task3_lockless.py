import threading
import time

TOTAL_OPS = 2_000_000
NUM_THREADS = 4

def lockless_thread_local():
    ops_per_thread = TOTAL_OPS // NUM_THREADS
    partial = [0] * NUM_THREADS

    def work(thread_id):
        local = 0
        for _ in range(ops_per_thread):
            local += 1
        partial[thread_id] = local

    threads = [threading.Thread(target=work, args=(i,)) for i in range(NUM_THREADS)]
    start = time.perf_counter()

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    total = sum(partial)
    elapsed = time.perf_counter() - start
    return total, elapsed

if __name__ == "__main__":
    total, elapsed = lockless_thread_local()
    print(f"Lockless Thread-Local: Value = {total:,} / {TOTAL_OPS:,} | Time: {elapsed:.4f}s")
