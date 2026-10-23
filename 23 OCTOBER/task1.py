"""TASK 1: parallel row-major vs. column-major cache traversal.

Windows-only, standard-library launcher: NO numpy / numba / pip required.
Uses PowerShell's built-in Add-Type to JIT-compile a C# parallel benchmark.

Run in Windows PowerShell or VS Code terminal:
    python task1.py 230103054

Output: task1_output.txt beside this file.
Memory required: approximately 512 MB plus process overhead for 8000 x 8000.
"""

import argparse
from pathlib import Path
import platform
import subprocess
import sys
import tempfile


# PowerShell ships with Windows; the .NET Framework C# compiler is invoked by Add-Type.
# This avoids third-party Python dependencies and MSYS/MinGW pip build issues.
POWERSHELL_SCRIPT = r'''param(
    [Parameter(Mandatory=$true)][string]$StudentId,
    [Parameter(Mandatory=$true)][int]$Size,
    [Parameter(Mandatory=$true)][int]$Runs,
    [Parameter(Mandatory=$true)][string]$OutputFile
)

$ErrorActionPreference = 'Stop'

# Get the physical core count from Windows itself, rather than counting hyperthreads.
$physical = 0
try {
    $physical = [int](Get-CimInstance -ClassName Win32_Processor -ErrorAction Stop |
        Measure-Object -Property NumberOfCores -Sum).Sum
} catch {
    try {
        $physical = [int](Get-WmiObject -Class Win32_Processor -ErrorAction Stop |
            Measure-Object -Property NumberOfCores -Sum).Sum
    } catch {
        throw 'Could not read physical CPU cores from Windows. Run PowerShell normally (not MSYS bash).'
    }
}
if ($physical -lt 1) {
    throw 'Windows returned an invalid physical core count.'
}

$source = @'
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading.Tasks;

namespace SpatialCacheTask
{
    public static class Benchmark
    {
        private static readonly CultureInfo C = CultureInfo.InvariantCulture;

        private static double ParallelRowMajor(double[] matrix, int n, int workers)
        {
            double[] partial = new double[workers];
            ParallelOptions opts = new ParallelOptions();
            opts.MaxDegreeOfParallelism = workers;
            Parallel.For(0, workers, opts, delegate(int worker)
            {
                int firstRow = (int)((long)worker * n / workers);
                int lastRow  = (int)((long)(worker + 1) * n / workers);
                double total = 0.0;
                for (int row = firstRow; row < lastRow; row++)
                {
                    int offset = row * n;
                    for (int col = 0; col < n; col++)
                    {
                        total += matrix[offset + col]; // contiguous cache-friendly
                    }
                }
                partial[worker] = total;
            });
            double result = 0.0;
            for (int i = 0; i < partial.Length; i++) result += partial[i];
            return result;
        }

        private static double ParallelColumnMajor(double[] matrix, int n, int workers)
        {
            double[] partial = new double[workers];
            ParallelOptions opts = new ParallelOptions();
            opts.MaxDegreeOfParallelism = workers;
            Parallel.For(0, workers, opts, delegate(int worker)
            {
                int firstCol = (int)((long)worker * n / workers);
                int lastCol  = (int)((long)(worker + 1) * n / workers);
                double total = 0.0;
                for (int col = firstCol; col < lastCol; col++)
                {
                    for (int row = 0; row < n; row++)
                    {
                        total += matrix[row * n + col]; // stride = n * 8 bytes
                    }
                }
                partial[worker] = total;
            });
            double result = 0.0;
            for (int i = 0; i < partial.Length; i++) result += partial[i];
            return result;
        }

        private static double Milliseconds(Stopwatch watch)
        {
            return 1000.0 * (double)watch.ElapsedTicks / Stopwatch.Frequency;
        }

        private static double Median(List<double> times)
        {
            double[] copy = times.ToArray();
            Array.Sort(copy);
            int middle = copy.Length / 2;
            return (copy.Length % 2 == 0)
                ? (copy[middle - 1] + copy[middle]) / 2.0
                : copy[middle];
        }

        private static void Verify(double a, double b)
        {
            double tolerance = Math.Max(0.00001, Math.Abs(a) * 1.0e-10);
            if (Math.Abs(a - b) > tolerance)
                throw new InvalidOperationException("Mismatch between sums: " +
                    a.ToString("R", C) + " vs " + b.ToString("R", C));
        }

        public static void Run(string studentId, int n, int runs, string outputFile,
                               int physicalCores)
        {
            int logicalCores = Environment.ProcessorCount;
            int workers = Math.Max(1, Math.Min(Math.Min(physicalCores, logicalCores), n));

            // Stable deterministic numeric Student ID seed.
            ulong id = ulong.Parse(studentId, NumberStyles.None, C);
            int seed = unchecked((int)(id ^ (id >> 32)));
            int elementCount = checked(n * n);
            Console.WriteLine("TASK 1 - Row-Major vs. Column-Major Parallel Cache Traversal");
            Console.WriteLine("Student ID: " + studentId);
            Console.WriteLine("Logical core count: " + logicalCores);
            Console.WriteLine("Physical core count: " + physicalCores);
            Console.WriteLine("Parallel workers used: " + workers);
            Console.WriteLine("Matrix: " + n + " x " + n + " (float64, row-major, " +
                ((long)elementCount * 8L / (1024 * 1024)) + " MiB)");
            Console.WriteLine("Initializing matrix from Student ID seed...");

            double[] matrix = new double[elementCount];
            Random rng = new Random(seed);
            for (int i = 0; i < matrix.Length; i++) matrix[i] = rng.NextDouble();

            Console.WriteLine("Warming up both modes (excluded from timing)...");
            double warmA = ParallelRowMajor(matrix, n, workers);
            double warmB = ParallelColumnMajor(matrix, n, workers);
            Verify(warmA, warmB);

            List<double> timesA = new List<double>();
            List<double> timesB = new List<double>();
            double lastA = warmA;
            double lastB = warmB;

            // Alternate measurement order to reduce bias from temperature/cache state.
            for (int run = 0; run < runs; run++)
            {
                for (int slot = 0; slot < 2; slot++)
                {
                    bool modeA = ((run + slot) % 2 == 0);
                    Stopwatch watch = Stopwatch.StartNew();
                    double value = modeA
                        ? ParallelRowMajor(matrix, n, workers)
                        : ParallelColumnMajor(matrix, n, workers);
                    watch.Stop();
                    double ms = Milliseconds(watch);
                    if (modeA) { timesA.Add(ms); lastA = value; }
                    else       { timesB.Add(ms); lastB = value; }
                    Console.WriteLine("Run " + (run + 1) + "/" + runs + " mode " +
                        (modeA ? "A" : "B") + ": " + ms.ToString("F3", C) + " ms");
                }
            }
            Verify(lastA, lastB);
            double aMs = Median(timesA);
            double bMs = Median(timesB);
            double factor = bMs / aMs;
            StringBuilder report = new StringBuilder();
            report.AppendLine("TASK 1 - Row-Major vs. Column-Major Parallel Cache Traversal");
            report.AppendLine("Student ID: " + studentId);
            report.AppendLine("Logical core count: " + logicalCores);
            report.AppendLine("Physical core count: " + physicalCores);
            report.AppendLine("Parallel worker count: " + workers);
            report.AppendLine("Matrix: " + n + " x " + n + ", float64, row-major storage");
            report.AppendLine("Student ID numeric random seed: " + seed);
            report.AppendLine("Measured runs per mode: " + runs + " (median)");
            report.AppendLine("Mode A (Row-Major) runtime: " + aMs.ToString("F3", C) + " ms");
            report.AppendLine("Mode B (Column-Major / Strided) runtime: " + bMs.ToString("F3", C) + " ms");
            report.AppendLine("Cache penalty factor (B / A): " + factor.ToString("F3", C) + "x");
            report.AppendLine("Mode A sum: " + lastA.ToString("R", C));
            report.AppendLine("Mode B sum: " + lastB.ToString("R", C));
            report.AppendLine("Validation: PASS");
            report.AppendLine("Note: timings are wall-clock measurements on the local CPU.");
            string text = report.ToString();
            Console.WriteLine();
            Console.WriteLine(text);
            File.WriteAllText(outputFile, text, new UTF8Encoding(false));
            Console.WriteLine("Saved: " + outputFile);
        }
    }
}
'@

# Compiles using the C# compiler already included with Windows PowerShell/.NET.
Add-Type -TypeDefinition $source -ReferencedAssemblies @('System.dll', 'System.Core.dll') -ErrorAction Stop
[SpatialCacheTask.Benchmark]::Run($StudentId, $Size, $Runs, $OutputFile, $physical)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("student_id", nargs="?", help="Numeric Student ID (e.g. 230103054)")
    parser.add_argument("--size", type=int, default=8000,
                        help="Matrix size, default 8000 (use 100 for a quick smoke test)")
    parser.add_argument("--runs", type=int, default=3,
                        help="Number of benchmark trials per mode, default 3")
    args = parser.parse_args()

    student_id = args.student_id or input("Enter Student ID: ").strip()
    if not student_id.isascii() or not student_id.isdecimal():
        parser.error("Student ID must contain ASCII digits only")
    if len(student_id) > 19 or int(student_id) >= 2**64:
        parser.error("Student ID must fit into an unsigned 64-bit integer")
    if args.size <= 0 or args.size > 46340 or args.runs <= 0:
        parser.error("Invalid --size or --runs")
    if platform.system() != "Windows":
        parser.error("This dependency-free version requires Windows PowerShell")

    output = Path(__file__).resolve().with_name("task1_output.txt")
    with tempfile.TemporaryDirectory(prefix="task1_cache_") as tmp:
        ps_path = Path(tmp) / "runner.ps1"
        ps_path.write_text(POWERSHELL_SCRIPT, encoding="utf-8-sig")
        command = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(ps_path), "-StudentId", student_id, "-Size", str(args.size),
            "-Runs", str(args.runs), "-OutputFile", str(output),
        ]
        try:
            completed = subprocess.run(command, check=False)
        except FileNotFoundError:
            parser.error("powershell.exe not found. Run from a Windows computer")
        if completed.returncode != 0:
            raise SystemExit("\nTASK 1 failed. Copy the FIRST red error above to diagnose it.")
    if not output.is_file():
        raise SystemExit("Benchmark finished but did not create task1_output.txt")


if __name__ == "__main__":
    main()
