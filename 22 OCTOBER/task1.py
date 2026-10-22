"""Task 1: hardware probe and strictly serial NumPy baseline.

Requires: python -m pip install numpy
Run: python task1.py > task1_output.txt
"""

import os

# Keep numerical libraries single-threaded for the serial baseline.
# These must be set before importing NumPy.
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

import numpy as np

STUDENT_ID = 230103054
ARRAY_SIZE = 20_000_000


def cpu_model() -> str:
    """Best-effort model details across Linux, Windows and macOS."""
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


def main() -> None:
    print("TASK 1 - Hardware Probe & Serial Baseline")
    print(f"Student ID: {STUDENT_ID}")
    print(f"OS: {platform.platform()}")
    print(f"CPU model/platform: {cpu_model()}")
    print(f"Logical cores (os.cpu_count): {os.cpu_count()}")
    print(f"Array length: {ARRAY_SIZE:,} float64 elements")
    print(f"Random seed: {STUDENT_ID}")

    values = np.random.default_rng(STUDENT_ID).random(ARRAY_SIZE, dtype=np.float64)
    assert values.dtype == np.float64

    # The timed section covers numerical computation only, not array creation.
    start_ns = time.perf_counter_ns()
    total = float(np.sum(values, dtype=np.float64))
    standard_deviation = float(np.std(values, dtype=np.float64, ddof=0))
    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000

    print("Execution: single-threaded (serial)")
    print(f"Sum: {total:.12f}")
    print(f"Standard deviation (population): {standard_deviation:.12f}")
    print(f"Wall-clock time: {elapsed_ms:.3f} ms")


if __name__ == "__main__":
    main()
