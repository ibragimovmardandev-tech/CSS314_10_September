"""TASK 2: PRNG state bottleneck (four true OS threads, 40M Monte Carlo points).

Requires Windows PowerShell (already installed on Windows), not numpy/numba/pip.

  python task2.py 230103054
  python task2.py 230103054 --samples 100000   # fast smoke test

Creates task2_output.txt beside this Python file.
"""

import argparse
from pathlib import Path
import platform
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("student_id", nargs="?", help="Student ID containing digits")
    parser.add_argument("--samples", type=int, default=40_000_000,
                        help="Points PER MODE; default is 40,000,000")
    args = parser.parse_args()
    student_id = args.student_id or input("Enter Student ID: ").strip()
    if not student_id.isascii() or not student_id.isdecimal():
        parser.error("Student ID must contain only ASCII digits")
    if int(student_id) > (2**64 - 4) // 10:
        parser.error("Student ID is too large for the requested 64-bit PRNG seeds")
    if args.samples <= 0 or args.samples > 2**63 - 1:
        parser.error("--samples must be between 1 and 9223372036854775807")
    if platform.system() != "Windows":
        parser.error("This no-dependency version requires Windows PowerShell")

    base = Path(__file__).resolve().parent
    ps_script = base / "task2.ps1"
    if not ps_script.is_file():
        parser.error("task2.ps1 is missing. Put task2.py and task2.ps1 in the same folder")
    output_file = base / "task2_output.txt"
    cmd = [
        "powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
        "-File", str(ps_script), "-StudentId", student_id,
        "-Samples", str(args.samples), "-OutputFile", str(output_file),
    ]
    try:
        result = subprocess.run(cmd, check=False)
    except FileNotFoundError:
        parser.error("powershell.exe could not be found on your Windows system")
    if result.returncode != 0:
        raise SystemExit("TASK 2 failed. See the first red PowerShell error above.")
    if not output_file.is_file():
        raise SystemExit("TASK 2 ended without creating task2_output.txt")


if __name__ == "__main__":
    main()
