"""TASK 3 - Inclusive Prefix Scan: Serial vs. Parallel (2 passes).

No third-party packages are needed. The parallel implementation uses multiple
CPU processes with shared-memory buffers so it can run on multiple cores even
on Python builds that have the GIL.

Windows / VS Code examples:
    python task3.py 230103054
    python task3.py 230103054 --size 20000 --workers 4   # quick test

Full run: 2,000,000 seeded integers (1..10), 4 workers by default.
Creates task3_output.txt next to this .py file.
"""

import argparse
from array import array
import multiprocessing as mp
from multiprocessing import shared_memory
from pathlib import Path
import random
import sys
import time

DEFAULT_SIZE = 2_000_000
DEFAULT_WORKERS = 4


def first_pass(job):
    """Inclusive scan *within* one chunk. Return the chunk's total sum."""
    input_name, output_name, begin, end = job
    in_shm = shared_memory.SharedMemory(name=input_name)
    out_shm = shared_memory.SharedMemory(name=output_name)
    in_view = None
    out_view = None
    try:
        in_view = in_shm.buf.cast('i')  # signed 32-bit input integers
        out_view = out_shm.buf.cast('q')  # signed 64-bit prefix sums
        running = 0
        for i in range(begin, end):
            running += in_view[i]
            out_view[i] = running
        return running
    finally:
        if in_view is not None:
            in_view.release()
        if out_view is not None:
            out_view.release()
        in_shm.close()
        out_shm.close()


def second_pass(job):
    """Add the sum of preceding chunks to each local prefix."""
    output_name, begin, end, offset = job
    out_shm = shared_memory.SharedMemory(name=output_name)
    out_view = None
    try:
        out_view = out_shm.buf.cast('q')
        if offset:
            for i in range(begin, end):
                out_view[i] += offset
    finally:
        if out_view is not None:
            out_view.release()
        out_shm.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('student_id', nargs='?', help='Student ID consisting of digits')
    parser.add_argument('--size', type=int, default=DEFAULT_SIZE,
                        help='Array length (default: 2000000)')
    parser.add_argument('--workers', type=int, default=DEFAULT_WORKERS,
                        help='Parallel worker processes (default: 4)')
    args = parser.parse_args()

    student_id = args.student_id or input('Enter Student ID: ').strip()
    if not student_id.isascii() or not student_id.isdecimal():
        parser.error('Student ID must contain ASCII digits only')
    if args.size <= 0 or args.size > 50_000_000:
        parser.error('--size must be from 1 to 50000000')
    if not 1 <= args.workers <= 64:
        parser.error('--workers must be from 1 to 64')
    if args.size > 2_000_000:
        print('NOTE: The assignment requires exactly 2,000,000 elements.', flush=True)

    n = args.size
    workers = min(args.workers, n)
    filename = Path(__file__).resolve().parent / 'task3_output.txt'
    input_shm = None
    output_shm = None
    input_view = None
    parallel_output = None
    try:
        # Each input element is a 32-bit int; each output prefix is a 64-bit int.
        input_shm = shared_memory.SharedMemory(create=True, size=n * 4)
        output_shm = shared_memory.SharedMemory(create=True, size=n * 8)
        input_view = input_shm.buf.cast('i')
        parallel_output = output_shm.buf.cast('q')

        print('TASK 3 - Prefix Scan: Step Efficiency vs. Work Efficiency', flush=True)
        print('Student ID:', student_id, flush=True)
        print('Array size:', f'{n:,}', flush=True)
        print('Value range: 1 to 10', flush=True)
        print('Parallel workers:', workers, '(CPU processes)', flush=True)
        print('Generating reproducible data...', flush=True)
        rng = random.Random(int(student_id))
        for i in range(n):
            input_view[i] = rng.randint(1, 10)

        # Serial inclusive prefix scan, benchmark only the computation.
        print('Running serial inclusive prefix sum...', flush=True)
        serial_output = array('q', [0]) * n
        start = time.perf_counter()
        running = 0
        for i in range(n):
            running += input_view[i]
            serial_output[i] = running
        serial_ms = (time.perf_counter() - start) * 1000.0

        # Divide the entire array into non-overlapping adjacent chunks.
        chunks = [(i * n // workers, (i + 1) * n // workers)
                  for i in range(workers)]
        jobs_first = [(input_shm.name, output_shm.name, begin, end)
                      for begin, end in chunks]

        # Actual multi-core parallelism: shared input/output buffers; no copying
        # 2 million elements through worker IPC. Both passes share a worker pool.
        print('Running parallel 2-pass chunked prefix scan...', flush=True)
        ctx = mp.get_context('spawn')  # works on Windows and other platforms
        with ctx.Pool(processes=workers) as pool:
            # Warm up the pool first. Worker startup is excluded from benchmark,
            # as is input generation; synchronization for the two passes is timed.
            pool.map(int, range(workers))
            start = time.perf_counter()
            # Pass 1: compute per-chunk inclusive prefixes and chunk sums.
            chunk_sums = pool.map(first_pass, jobs_first)
            # Reduction: prefix over chunk totals gives each chunk's offset.
            offsets = []
            preceding_sum = 0
            for total in chunk_sums:
                offsets.append(preceding_sum)
                preceding_sum += total
            # Pass 2: apply offsets in parallel.
            jobs_second = [(output_shm.name, begin, end, offsets[i])
                           for i, (begin, end) in enumerate(chunks)]
            pool.map(second_pass, jobs_second)
            parallel_ms = (time.perf_counter() - start) * 1000.0

        speedup = serial_ms / parallel_ms if parallel_ms > 0 else float('inf')
        # Explicit assignment-required assertion. If false, exit code MUST be 1.
        try:
            assert parallel_output[-1] == serial_output[-1], (
                f'Last prefix differs: parallel={parallel_output[-1]}, '
                f'serial={serial_output[-1]}')
            # Stronger supplementary verification: all elements must match.
            for i in range(n):
                if parallel_output[i] != serial_output[i]:
                    raise AssertionError(
                        f'Prefix differs at index {i}: '
                        f'parallel={parallel_output[i]}, serial={serial_output[i]}')
            verification = 'PASS'
        except AssertionError as exc:
            verification = 'FAIL'
            print('Assertion failed:', exc, file=sys.stderr, flush=True)

        report = '\n'.join([
            'TASK 3 - Prefix Scan (Step Efficiency vs. Work Efficiency)',
            f'Student ID: {student_id}',
            f'Array size: {n:,} integers (values 1..10)',
            f'Parallel worker processes: {workers}',
            'Algorithm: serial inclusive prefix / parallel 2-pass chunked scan',
            f'Serial Time (ms): {serial_ms:.3f}',
            f'Parallel Time (ms): {parallel_ms:.3f}',
            f'Speedup (Serial / Parallel): {speedup:.3f}x',
            f'Serial output[-1]: {serial_output[-1]}',
            f'Parallel output[-1]: {parallel_output[-1]}',
            f'Verification Status: {verification}',
            'Note: wall-clock scan computation; data generation and worker startup excluded.',
            'Note: verification checks both last element (assert) and entire output array.',
        ]) + '\n'
        print('\n' + report, flush=True)
        filename.write_text(report, encoding='utf-8')
        print('Saved:', filename, flush=True)
        return 0 if verification == 'PASS' else 1
    finally:
        if input_view is not None:
            input_view.release()
        if parallel_output is not None:
            parallel_output.release()
        if input_shm is not None:
            input_shm.close()
            input_shm.unlink()
        if output_shm is not None:
            output_shm.close()
            output_shm.unlink()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'TASK 3 FAILED: {type(exc).__name__}: {exc}', file=sys.stderr)
        sys.exit(1)
