"""Task 2: benchmark summation scaling against Amdahl's Law.

Requires: python -m pip install numpy
Run: python task2.py > task2_output.txt

Each measurement times the summation plus thread-pool overhead, but excludes
creation of the common NumPy float64 array. NumPy's sum releases the GIL,
allowing workers to sum distinct read-only chunks concurrently.
"""

import os

# Prevent nested BLAS/OpenMP pools from interfering with worker scaling.
for variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[variable] = "1"

import platform
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

STUDENT_ID = 230103054
ARRAY_SIZE = 20_000_000
PARALLEL_FRACTION = 0.95


def cpu_model() -> str:
    if platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo", encoding="utf-8") as cpu_info:
                for line in cpu_info:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except OSError:
            pass
    return (
        platform.processor()
        or os.environ.get("PROCESSOR_IDENTIFIER")
        or platform.machine()
    )


def chunk_sum(chunk: np.ndarray) -> float:
    return float(np.sum(chunk, dtype=np.float64))


def parallel_sum(values: np.ndarray, workers: int) -> float:
    """Read-only chunks avoid copying the input array across workers."""
    if workers == 1:
        return chunk_sum(values)

    size = len(values)
    chunks = [
        values[(i * size) // workers : ((i + 1) * size) // workers]
        for i in range(workers)
    ]
    # Thread creation and synchronization count toward the wall-clock time.
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return float(sum(executor.map(chunk_sum, chunks)))


def amdahl_upper_bound(workers: int) -> float:
    return 1.0 / ((1.0 - PARALLEL_FRACTION) + PARALLEL_FRACTION / workers)


def main() -> None:
    max_cores = os.cpu_count() or 1
    worker_counts = list(dict.fromkeys([1, 2, 4, max_cores, max_cores * 2]))

    print("TASK 2 - Multi-Core Scaling vs. Amdahl's Law")
    print(f"Student ID: {STUDENT_ID}")
    print(f"OS: {platform.platform()}")
    print(f"CPU model/platform: {cpu_model()}")
    print(f"Logical cores (os.cpu_count): {max_cores}")
    print(f"Array length: {ARRAY_SIZE:,} float64 elements")
    print(f"Random seed: {STUDENT_ID}")
    print(f"Parallel fraction for Amdahl: {PARALLEL_FRACTION:.2f}")
    print("Timed work: summation only (excludes array generation)")

    values = np.random.default_rng(STUDENT_ID).random(ARRAY_SIZE, dtype=np.float64)
    assert values.dtype == np.float64
    results = []
    baseline_sum = None
    baseline_ms = None

    for workers in worker_counts:
        start_ns = time.perf_counter_ns()
        total = parallel_sum(values, workers)
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000

        if baseline_ms is None:
            baseline_ms = elapsed_ms
            baseline_sum = total
        elif not np.isclose(total, baseline_sum, rtol=1e-12, atol=0.0):
            raise ArithmeticError(f"Sum mismatch for {workers} workers")

        speedup = baseline_ms / elapsed_ms
        results.append((workers, elapsed_ms, speedup, amdahl_upper_bound(workers)))

    print(f"Reference sum (1 worker): {baseline_sum:.12f}")
    print()
    print(f"{'Cores':>8} | {'Wall Time (ms)':>16} | {'Speedup':>10} | {'Amdahl Upper Bound':>18}")
    print("-" * 64)
    for workers, elapsed_ms, speedup, upper_bound in results:
        print(f"{workers:>8} | {elapsed_ms:>16.3f} | {speedup:>9.3f}x | {upper_bound:>17.3f}x")


if __name__ == "__main__":
    main()
