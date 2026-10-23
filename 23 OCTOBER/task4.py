"""TASK 4: CPU Host-to-Process IPC Overhead vs Zero-Copy Shared Memory.

Uses only the Python standard library; supports Windows Python 3.14.

Run from PowerShell:
    python task4.py 230103054
    python task4.py                 # prompts for Student ID
    python task4.py 230103054 --sizes 1000 10000 --runs 1   # short test

The benchmark measures the time to deliver data to an *already-running* child
process and receive its acknowledgement. With a pipe, payload data is pickled
and copied. With shared memory, the parent first places the data in a mapped
segment OUTSIDE the measured interval, and the child receives only a small
memory name/length notification; this isolates zero-copy handoff latency.
Startup, random input generation and shared-memory initial staging are not
included in the reported transfer times. These are important qualifications
when interpreting the numbers as a transfer/handoff microbenchmark.
"""

from __future__ import annotations

import argparse
from array import array
import math
import multiprocessing as mp
from multiprocessing import shared_memory
from pathlib import Path
import random
import statistics
import sys
import time
import traceback

DEFAULT_SIZES = (100_000, 1_000_000, 10_000_000)
CHUNK_ELEMENTS = 262_144  # 2 MiB chunks (8-byte int64), avoids large Pipe messages
OUTPUT_PATH = Path(__file__).resolve().with_name("task4_output.txt")


def check_indices(n: int) -> tuple[int, ...]:
    return tuple(sorted({0, n // 2, n - 1}))


def child_worker(conn) -> None:
    """Accept pipe payloads or map shared memory, then acknowledge consumption."""
    try:
        while True:
            command = conn.recv()
            op = command[0]
            if op == "STOP":
                return
            if op == "PIPE":
                n = command[1]
                checkpoint = check_indices(n)
                found = {}
                consumed = 0
                while consumed < n:
                    chunk = conn.recv()  # unpickling occurs here
                    if not isinstance(chunk, array) or chunk.typecode != "q":
                        raise TypeError("Expected an array('q') sent over Pipe")
                    length = len(chunk)
                    if length == 0 or consumed + length > n:
                        raise RuntimeError("Invalid pipe chunk size")
                    for idx in checkpoint:
                        if consumed <= idx < consumed + length:
                            found[idx] = chunk[idx - consumed]
                    consumed += length
                if len(found) != len(checkpoint):
                    raise RuntimeError("Missing pipe data checkpoints")
                conn.send(("OK", consumed, tuple(found[i] for i in checkpoint)))
            elif op == "SHM":
                _, name, n = command
                shm = shared_memory.SharedMemory(name=name, create=False)
                try:
                    view = shm.buf.cast("q")
                    try:
                        # On Windows, a named shared-memory mapping may be rounded up
                        # to the OS allocation granularity. Its accessible view can
                        # therefore contain MORE than the requested n int64 values.
                        # n is the logical payload length supplied by the parent.
                        if len(view) < n:
                            raise RuntimeError(
                                f"Shared memory is too short: {len(view)} elements for {n} requested"
                            )
                        found = tuple(view[i] for i in check_indices(n))
                    finally:
                        view.release()
                finally:
                    shm.close()
                conn.send(("OK", n, found))
            else:
                raise ValueError(f"Unknown command: {op!r}")
    except (EOFError, BrokenPipeError):
        return
    except Exception as exc:
        try:
            conn.send(("ERROR", f"{type(exc).__name__}: {exc}"))
        except Exception:
            pass
    finally:
        conn.close()


def validate_reply(reply, values: array, n: int, path: str) -> None:
    if not (isinstance(reply, tuple) and reply and reply[0] == "OK"):
        raise RuntimeError(f"{path}: worker returned {reply!r}")
    expected = tuple(values[index] for index in check_indices(n))
    if reply[1] != n or reply[2] != expected:
        raise AssertionError(
            f"{path}: data mismatch: received {reply[2]!r}, expected {expected!r}"
        )


def ack(conn, timeout: float = 120.0):
    if not conn.poll(timeout):
        raise TimeoutError("Worker did not acknowledge the transfer")
    return conn.recv()


def run_pipe(conn, values: array) -> float:
    n = len(values)
    start = time.perf_counter_ns()
    conn.send(("PIPE", n))
    for pos in range(0, n, CHUNK_ELEMENTS):
        # Slice construction and pickle/pipe serialization are included in time.
        conn.send(values[pos : pos + CHUNK_ELEMENTS])
    reply = ack(conn)
    end = time.perf_counter_ns()
    validate_reply(reply, values, n, "Pipe IPC")
    return (end - start) / 1_000_000.0


def run_shm(conn, shm: shared_memory.SharedMemory, values: array) -> float:
    n = len(values)
    start = time.perf_counter_ns()
    # The array is ALREADY in shared memory; only a tiny control message moves.
    conn.send(("SHM", shm.name, n))
    reply = ack(conn)
    end = time.perf_counter_ns()
    validate_reply(reply, values, n, "Shared memory")
    return (end - start) / 1_000_000.0


def fill_shared_memory(shm: shared_memory.SharedMemory, values: array) -> float:
    """Stages bytes in shared memory; intentionally reported separately."""
    source = memoryview(values).cast("B")
    try:
        start = time.perf_counter_ns()
        shm.buf[: len(source)] = source
        end = time.perf_counter_ns()
    finally:
        source.release()
    return (end - start) / 1_000_000.0


def format_output(student_id, runs, results) -> str:
    lines = [
        "TASK 4 - Host-to-Process Transfer Penalty (CPU / IPC)",
        f"Student ID: {student_id}",
        "Environment: CPU, Python multiprocessing (standard library)",
        "Element type: signed 64-bit integers (8 bytes each)",
        "Path A: Pickle serialization over multiprocessing.Pipe (2 MiB chunks)",
        "Path B: multiprocessing.shared_memory (zero-copy worker access)",
        f"Runs per path and size: {runs} (median reported)",
        "Timing: parent send/notify through worker acknowledgement; worker pre-started",
        "NOTE: Shared memory allocation and INITIAL COPY are excluded from Path B",
        "      handoff timing and shown separately as setup/staging cost.",
        "NOTE: Path A includes chunk slicing, pickle and IPC transfers.",
        "",
        f"{'N':>12} | {'Data (MiB)':>10} | {'Pipe A (ms)':>13} | {'Shared B (ms)':>13} | {'A/B ratio':>10} | {'SHM fill (ms)':>13}",
        "-" * 91,
    ]
    for n, a, b, staging in results:
        lines.append(
            f"{n:12,d} | {n * 8 / (1024 * 1024):10.2f} | {a:13.3f} | {b:13.3f} | {a / b:9.2f}x | {staging:13.3f}"
        )
    lines += [
        "",
        "Verification Status: PASS (size and three sample values checked for each path)",
        "Interpretation: Pipe moves serialized data; shared memory passes only a handle.",
        "The A/B ratio compares handoff costs after the SHM region is populated.",
        f"Saved: {OUTPUT_PATH}",
    ]
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="TASK 4: Pipe IPC vs zero-copy shared memory")
    parser.add_argument("student_id", nargs="?", type=int, help="Student ID")
    parser.add_argument("--sizes", nargs="+", type=int, default=list(DEFAULT_SIZES),
                        help="Array element counts; default 100000 1000000 10000000")
    parser.add_argument("--runs", type=int, default=3, help="Timing runs per path (default: 3)")
    args = parser.parse_args()
    if args.student_id is None:
        args.student_id = int(input("Enter Student ID: ").strip())
    if args.student_id < 0 or args.runs < 1 or any(n <= 0 for n in args.sizes):
        parser.error("Student ID must be nonnegative; runs and all sizes must be positive")
    return args


def main() -> int:
    args = parse_args()
    print("TASK 4 - CPU IPC vs. Zero-Copy Shared Memory", flush=True)
    print(f"Student ID: {args.student_id}", flush=True)
    print("N values: " + ", ".join(f"{n:,}" for n in args.sizes), flush=True)
    print(f"Runs per path: {args.runs}", flush=True)

    ctx = mp.get_context("spawn")  # works on Windows as well as Linux/macOS
    parent_conn, child_conn = ctx.Pipe(duplex=True)
    worker = ctx.Process(target=child_worker, args=(child_conn,), name="task4-worker")
    worker.start()
    child_conn.close()
    results = []
    try:
        # Warm up the spawned worker and both transport protocols so that
        # interpreter/process startup is never counted as transfer overhead.
        warm_values = array("q", [1, 2, 3, 4, 5, 6, 7, 8])
        warm_shm = shared_memory.SharedMemory(create=True, size=len(warm_values) * 8)
        try:
            fill_shared_memory(warm_shm, warm_values)
            run_pipe(parent_conn, warm_values)
            run_shm(parent_conn, warm_shm, warm_values)
        finally:
            warm_shm.close()
            warm_shm.unlink()
        print("Worker startup and transport warm-up complete (not timed).", flush=True)

        for n in args.sizes:
            print(f"\nPreparing N={n:,} ({n * 8 / (1024 * 1024):.2f} MiB)...", flush=True)
            # Seeded, reproducible int64 values 1..10. Generation excluded from timing.
            rng = random.Random(args.student_id)
            values = array("q", (rng.randint(1, 10) for _ in range(n)))
            if values.itemsize != 8:
                raise RuntimeError("This Python environment does not use 8-byte array('q')")

            shm = shared_memory.SharedMemory(create=True, size=n * 8)
            try:
                staging_ms = fill_shared_memory(shm, values)
                samples_pipe = []
                samples_shared = []
                for i in range(args.runs):
                    # Alternating order reduces systematic warm-up/order bias.
                    order = ("pipe", "shared") if i % 2 == 0 else ("shared", "pipe")
                    for mode in order:
                        if mode == "pipe":
                            ms = run_pipe(parent_conn, values)
                            samples_pipe.append(ms)
                        else:
                            ms = run_shm(parent_conn, shm, values)
                            samples_shared.append(ms)
                a = statistics.median(samples_pipe)
                b = statistics.median(samples_shared)
                results.append((n, a, b, staging_ms))
                print(
                    f"N={n:,}: Pipe A = {a:.3f} ms | Shared B = {b:.3f} ms | "
                    f"A/B = {a / b:.2f}x | Verification: PASS", flush=True
                )
            finally:
                shm.close()
                shm.unlink()
            del values

        report = format_output(args.student_id, args.runs, results)
        print("\n" + report, flush=True)
        OUTPUT_PATH.write_text(report + "\n", encoding="utf-8")
        return 0
    except Exception:
        print("\nVerification Status: FAIL", file=sys.stderr)
        traceback.print_exc()
        return 1
    finally:
        try:
            if worker.is_alive():
                parent_conn.send(("STOP",))
        except (OSError, EOFError, BrokenPipeError):
            pass
        parent_conn.close()
        worker.join(timeout=5)
        if worker.is_alive():
            worker.terminate()
            worker.join(timeout=5)


if __name__ == "__main__":
    mp.freeze_support()
    sys.exit(main())
