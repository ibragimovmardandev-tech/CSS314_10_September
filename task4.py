"""TASK 4 — Work Stealing & Scheduling Under Skew.

Compare static contiguous partitioning against dynamic scheduling from a
shared work queue. Four Python threads can overlap because time.sleep()
releases the GIL; this is a simulation of irregular waiting workloads,
not a CPU-bound multicore speedup benchmark.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass

STUDENT_ID = "230103054"
ITEM_COUNT = 1_000
WORKERS = 4
DYNAMIC_CHUNK_SIZE = 5
SLEEP_MULTIPLIER_SECONDS = 0.0001
EXPECTED_CHECKSUM = ITEM_COUNT * (ITEM_COUNT - 1) // 2


@dataclass
class BenchmarkResult:
    strategy: str
    elapsed_ms: float
    first_finish_ms: float
    last_finish_ms: float
    finish_delta_ms: float
    completed_items: int
    checksum: int
    per_worker_items: list[int]


def do_work(item: int) -> None:
    """Sleep to simulate non-uniform per-item execution costs."""
    time.sleep(SLEEP_MULTIPLIER_SECONDS * (item % 20))


def run_benchmark(*, dynamic: bool) -> BenchmarkResult:
    finish_times = [0.0] * WORKERS
    per_worker_items = [0] * WORKERS
    per_worker_checksum = [0] * WORKERS
    start_clock = [0.0]

    # Barrier synchronizes starting measurements across all four workers.
    start_barrier = threading.Barrier(
        WORKERS + 1,
        action=lambda: start_clock.__setitem__(0, time.perf_counter()),
    )

    pending: queue.SimpleQueue[tuple[int, int]] | None = None
    if dynamic:
        pending = queue.SimpleQueue()
        for begin in range(0, ITEM_COUNT, DYNAMIC_CHUNK_SIZE):
            pending.put((begin, min(begin + DYNAMIC_CHUNK_SIZE, ITEM_COUNT)))

    def worker(worker_id: int) -> None:
        count = 0
        checksum = 0
        start_barrier.wait()

        if dynamic:
            assert pending is not None
            while True:
                try:
                    begin, end = pending.get_nowait()
                except queue.Empty:
                    break
                for i in range(begin, end):
                    do_work(i)
                    count += 1
                    checksum += i
        else:
            # Four equal, contiguous chunks: [0..249], [250..499], etc.
            begin = worker_id * ITEM_COUNT // WORKERS
            end = (worker_id + 1) * ITEM_COUNT // WORKERS
            for i in range(begin, end):
                do_work(i)
                count += 1
                checksum += i

        per_worker_items[worker_id] = count
        per_worker_checksum[worker_id] = checksum
        finish_times[worker_id] = time.perf_counter()

    threads = [threading.Thread(target=worker, args=(i,), name=f"worker-{i + 1}")
               for i in range(WORKERS)]
    for thread in threads:
        thread.start()

    start_barrier.wait()  # Releases the four workers simultaneously.
    for thread in threads:
        thread.join()

    total_items = sum(per_worker_items)
    total_checksum = sum(per_worker_checksum)
    if total_items != ITEM_COUNT or total_checksum != EXPECTED_CHECKSUM:
        raise RuntimeError("Task validation failed: missing or duplicate work items")

    first = min(finish_times)
    last = max(finish_times)
    start = start_clock[0]
    label = "Dynamic queue (chunk=5)" if dynamic else "Static equal blocks"
    return BenchmarkResult(
        strategy=label,
        elapsed_ms=(last - start) * 1_000,
        first_finish_ms=(first - start) * 1_000,
        last_finish_ms=(last - start) * 1_000,
        finish_delta_ms=(last - first) * 1_000,
        completed_items=total_items,
        checksum=total_checksum,
        per_worker_items=per_worker_items,
    )


def main() -> None:
    print("TASK 4 - Work Stealing & Scheduling Under Skew")
    print(f"Student ID: {STUDENT_ID}")
    print(f"Items: {ITEM_COUNT} (indices 0..{ITEM_COUNT - 1})")
    print(f"Worker threads: {WORKERS}")
    print("Per-item cost: sleep(0.0001 * (i % 20))")
    print(f"Static strategy: {WORKERS} equal contiguous blocks")
    print(f"Dynamic strategy: shared queue, chunk size = {DYNAMIC_CHUNK_SIZE}")
    print("Threads: Python threading (time.sleep releases the GIL)")
    print()

    static = run_benchmark(dynamic=False)
    dynamic = run_benchmark(dynamic=True)

    print(f"{'Strategy':<26} {'Wall (ms)':>11} {'First (ms)':>12} "
          f"{'Last (ms)':>11} {'Finish delta (ms)':>19}")
    print("-" * 85)
    for row in (static, dynamic):
        print(f"{row.strategy:<26} {row.elapsed_ms:>11.3f} "
              f"{row.first_finish_ms:>12.3f} {row.last_finish_ms:>11.3f} "
              f"{row.finish_delta_ms:>19.3f}")

    print()
    for row in (static, dynamic):
        print(f"{row.strategy}:")
        print(f"  Items per worker: {row.per_worker_items}")
        print(f"  Processed items: {row.completed_items}/{ITEM_COUNT}")
        print(f"  Checksum: {row.checksum} (expected {EXPECTED_CHECKSUM}) -> PASS")

    print()
    print(f"Wall-time ratio (Static / Dynamic): {static.elapsed_ms / dynamic.elapsed_ms:.3f}x")
    print("Completion delta = last worker finish time - first worker finish time")
    print("Note: smaller wall time and smaller completion delta are better;")
    print("      single-run timing is affected by OS scheduling and sleep precision.")


if __name__ == "__main__":
    main()
